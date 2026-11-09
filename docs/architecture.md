# Architektura systému

## 1. Přehled

Projekt NVD Mirror implementuje lokální zrcadlení databáze zranitelností National Vulnerability Database (NVD), která publikuje informace o známých zranitelnostech ve formátu CVE JSON 2.0.

Hlavním cílem je oddělit získávání dat z externího zdroje od jejich následného poskytování klientským aplikacím. Stahování a aktualizace feedů zajišťuje samostatná komponenta updater, zatímco jejich distribuci zajišťuje HTTP server Nginx.

Stažená data jsou ukládána do persistentního úložiště, které je sdíleno mezi komponentou updater a HTTP serverem. Díky tomu zůstávají data zachována i po restartování aplikačních kontejnerů.

Systém podporuje dvě varianty nasazení:

- Docker Compose.
- Kubernetes.

Obě varianty používají stejný updater, stejný formát dat a stejnou logiku poskytování feedů.

## 2. Logická architektura

Systém se skládá ze tří hlavních komponent.

### 2.1 Updater

Updater je samostatná Python aplikace, která zajišťuje získávání a aktualizaci NVD feedů.

Komunikuje s oficiálním distribučním endpointem NVD:

`https://nvd.nist.gov/feeds/json/cve/2.0`

Stahuje historické roční feedy a průběžně aktualizovaný feed `modified`.

Roční feedy umožňují uchovávat historická data rozdělená podle roku zveřejnění CVE, zatímco feed `modified` slouží k zachycení novějších změn v databázi.

Stažené soubory jsou ukládány v komprimovaném formátu `.json.gz`. Společně s nimi jsou uchovávána metadata umožňující kontrolu vlastností stažených souborů.

Updater používá knihovnu Requests pro HTTP komunikaci a podporuje opakování neúspěšných požadavků. Interval aktualizace je konfigurovatelný prostřednictvím proměnné prostředí `UPDATE_INTERVAL`.

Výchozí hodnota činí 21600 sekund, tedy šest hodin.

Adresář pro ukládání dat určuje proměnná `DATA_DIR`. V obou variantách nasazení je používána cesta `/data`.

Updater běží pod neprivilegovaným uživatelem s UID/GID `10001`, čímž se omezuje rozsah oprávnění procesu uvnitř kontejneru.

### 2.2 Nginx mirror

Nginx představuje HTTP rozhraní systému. Poskytuje klientům přístup ke staženým NVD feedům prostřednictvím standardních HTTP požadavků.

Kořenový adresář serveru je:

`/usr/share/nginx/html`

Do tohoto adresáře je připojeno persistentní úložiště obsahující data vytvořená updaterem.

Nginx používá konfiguraci, která naslouchá na portu `8080`. Automatické vypisování obsahu adresářů je vypnuto pomocí `autoindex off` a přístup ke skrytým souborům je zakázán.

Úložiště je v kontejneru Nginxu připojeno pouze pro čtení. HTTP server tak nemůže prostřednictvím svého filesystemového mountu měnit nebo přepisovat stažené feedy.

### 2.3 Maven klient

Pro ověření funkčnosti mirroru je součástí projektu demonstrační Maven aplikace využívající OWASP Dependency-Check Maven Plugin.

Plugin získává NVD data prostřednictvím nakonfigurovaného HTTP endpointu mirroru. Na základě získaných dat následně analyzuje závislosti projektu a identifikuje známé zranitelnosti.

Tím je ověřena nejen dostupnost HTTP serveru, ale také kompatibilita poskytovaných feedů s reálným konzumentem.

## 3. Datový tok

Základní tok dat systému je následující:

1. Updater naváže HTTP spojení s distribučním endpointem NVD.
2. Stáhne požadované CVE JSON 2.0 feedy.
3. Ověří získaná data a uloží soubory do persistentního úložiště.
4. Nginx zpřístupní obsah úložiště prostřednictvím HTTP.
5. Klientská aplikace získá požadovaný feed.
6. OWASP Dependency-Check použije získaná data při analýze projektových závislostí.

Oddělení stahování a poskytování dat umožňuje, aby HTTP server obsluhoval požadavky nezávisle na právě probíhající aktualizaci feedů.

## 4. Varianta Docker Compose

Docker Compose varianta používá tři služby a jedno pojmenované persistentní volume.

### 4.1 init-data

Služba `init-data` je jednorázová inicializační komponenta.

Používá image Alpine Linux a připojuje pojmenované volume `nvd-data` do adresáře `/data`.

Při inicializaci vytvoří cílový adresář a nastaví jeho vlastníka na UID/GID `10001`.

Tím zajistí, že updater běžící pod neprivilegovaným uživatelem bude mít potřebná oprávnění k zápisu.

Služba se po úspěšném dokončení ukončí. Spuštění updateru je podmíněno jejím úspěšným dokončením.

### 4.2 updater

Služba `updater` sestavuje vlastní image z adresáře `updater/`.

Používá Python 3.13 a běží pod uživatelem s UID `10001`.

Připojuje volume `nvd-data` do `/data` a zapisuje do něj stažené feedy.

Proměnné prostředí:

| Proměnná | Hodnota |
|---|---|
| `DATA_DIR` | `/data` |
| `UPDATE_INTERVAL` | `21600` |

Služba používá restartovací politiku `unless-stopped`, která umožňuje automatické obnovení procesu po jeho neočekávaném ukončení.

### 4.3 mirror

Služba `mirror` používá image `nginx:stable-alpine`.

Připojuje volume `nvd-data` do `/usr/share/nginx/html` pouze pro čtení a používá vlastní konfiguraci z adresáře `mirror/`.

HTTP server naslouchá na portu `8080`, který je zpřístupněn také na hostitelském počítači.

### 4.4 Persistentní úložiště

Docker volume `nvd-data` je sdíleno mezi službami `updater` a `mirror`.

Updater má oprávnění k zápisu, zatímco Nginx používá read-only mount.

Obě služby komunikují v rámci samostatné Docker bridge network `nvd-network`.

## 5. Varianta Kubernetes

Kubernetes varianta zachovává stejnou logickou architekturu, ale využívá nativní prostředky Kubernetes pro správu konfigurace, úložiště, životního cyklu kontejnerů a síťového přístupu.

Nasazení je realizováno v lokálním clusteru Minikube.

### 5.1 Namespace

Všechny aplikační prostředky jsou umístěny v namespace `nvd-mirror`.

Tím jsou odděleny od ostatních prostředků clusteru, například systémových komponent v namespace `kube-system`.

### 5.2 PersistentVolumeClaim

Pro ukládání feedů se používá PersistentVolumeClaim s názvem `nvd-data`.

Požadovaný přístupový režim je `ReadWriteOnce` a požadovaná kapacita je `1Gi`.

PVC používá StorageClass `standard`, která v Minikube zajišťuje dynamické vytvoření odpovídajícího PersistentVolume.

Aplikační Pod připojuje stejné úložiště do obou aplikačních kontejnerů:

- updater: `/data`
- nginx: `/usr/share/nginx/html`

Kontejner updater používá úložiště pro zápis, zatímco Nginx jej připojuje pouze pro čtení.

### 5.3 ConfigMap

Konfigurace Nginxu je uložena v prostředku ConfigMap s názvem `nvd-nginx-config`.

ConfigMap obsahuje konfigurační soubor `default.conf`, který je připojen do kontejneru Nginxu na cestu:

`/etc/nginx/conf.d/default.conf`

Použití ConfigMap odděluje konfiguraci serveru od jeho kontejnerové image a umožňuje její změnu bez vytváření vlastní image Nginxu.

### 5.4 Deployment

Aplikace je nasazena prostřednictvím Deploymentu `nvd-mirror` s jednou replikou.

Každý vytvořený Pod obsahuje:

- initContainer `init-data`,
- aplikační kontejner `updater`,
- aplikační kontejner `nginx`.

Oba aplikační kontejnery jsou umístěny ve stejném Podu a sdílejí jeho síťový a úložný kontext.

#### initContainer

InitContainer používá image Alpine Linux.

Před spuštěním aplikačních kontejnerů připojí PVC a nastaví vlastnictví adresáře `/data` na UID/GID `10001`.

Jeho úspěšné dokončení je podmínkou spuštění aplikačních kontejnerů.

#### updater

Kontejner updater používá vlastní image `nvd-updater:1.0`, sestavenou přímo v prostředí Minikube.

Běží pod neprivilegovaným uživatelem s UID/GID `10001` a připojuje PVC do `/data`.

Proměnné prostředí jsou stejné jako u Docker Compose varianty:

| Proměnná | Hodnota |
|---|---|
| `DATA_DIR` | `/data` |
| `UPDATE_INTERVAL` | `21600` |

Image používá `imagePullPolicy: IfNotPresent`, protože je sestavena a dostupná v interním container runtime clusteru.

#### nginx

Kontejner Nginx používá oficiální image `nginx:stable-alpine`.

PVC připojuje do `/usr/share/nginx/html` v režimu pouze pro čtení. Konfiguraci serveru získává z ConfigMap.

Kontejner naslouchá na portu `8080` a používá readiness a liveness probe založené na TCP kontrole dostupnosti portu.

### 5.5 Service

Síťové zpřístupnění aplikace v clusteru zajišťuje Service `nvd-mirror` typu `ClusterIP`.

Service vyhledává Pod podle labelu `app: nvd-mirror` a předává TCP provoz na port `8080`.

Pro přístup z hostitelského počítače je využit příkaz `kubectl port-forward`, který zpřístupňuje službu na lokálním portu `8081`.

Tím není nutné vystavovat aplikaci prostřednictvím NodePort nebo externího LoadBalanceru.

## 6. Životní cyklus dat a kontejnerů

Persistentní úložiště odděluje životní cyklus dat od životního cyklu aplikačních kontejnerů.

Restart nebo opětovné vytvoření Podu neznamená automatickou ztrátu uložených feedů, protože data jsou uchovávána v PersistentVolume.

V Kubernetes je vlastnictví a přístupová práva úložiště nastavováno initContainerem před spuštěním updateru.

Při každém vytvoření Podu se nejprve provede inicializační krok a až po jeho úspěšném dokončení se spustí oba aplikační kontejnery.

Umístění updateru a Nginxu do stejného Podu zjednodušuje sdílení PVC a zajišťuje jejich společné plánování na stejném uzlu. Současně však znamená, že oba kontejnery sdílejí životní cyklus Podu a nelze je nezávisle škálovat prostřednictvím tohoto Deploymentu.

Pro demonstrační jednouzlové nasazení je tento přístup dostačující.

## 7. Bezpečnostní aspekty

Architektura využívá několik základních bezpečnostních opatření.

Updater běží pod neprivilegovaným uživatelem s UID/GID `10001`, čímž se omezuje rozsah oprávnění procesu uvnitř kontejneru.

Nginx má persistentní úložiště připojené pouze pro čtení, takže nemůže měnit data vytvořená updaterem.

HTTP server má vypnuté automatické vypisování obsahu adresářů a blokuje přístup ke skrytým souborům.

V Kubernetes je konfigurace Nginxu oddělena od kontejnerové image prostřednictvím ConfigMap.

Použití samostatného namespace omezuje organizační a administrační rozsah aplikačních prostředků.

Kubernetes Service používá typ `ClusterIP`, takže aplikace není automaticky vystavena mimo cluster.

Tato opatření představují základní omezení oprávnění a síťové dostupnosti. Nejde o úplnou bezpečnostní izolaci mezi kontejnery stejného Podu, protože kontejnery sdílejí síťový namespace a mohou mít další společné prostředky podle konfigurace Podu.

## 8. Ověření funkčnosti

Funkčnost systému byla ověřena ve dvou prostředích.

V Docker Compose variantě bylo ověřeno spuštění updateru, stahování NVD feedů, jejich ukládání do pojmenovaného volume a poskytování prostřednictvím Nginxu.

V Kubernetes variantě bylo ověřeno vytvoření namespace, PVC, ConfigMap, Deploymentu a Service, spuštění obou aplikačních kontejnerů a dostupnost feedů prostřednictvím port forwardingu.

V obou variantách byla provedena integrace s OWASP Dependency-Check Maven Pluginem.

Ověření zahrnovalo:

1. Aktualizaci lokální databáze pomocí cíle `update-only`.
2. Analýzu závislostí pomocí cíle `check`.
3. Vytvoření HTML reportu.
4. Detekci známých zranitelností v demonstračních závislostech.

Tím byla ověřena kompatibilita poskytovaných NVD feedů s reálným nástrojem pro analýzu softwarových závislostí.