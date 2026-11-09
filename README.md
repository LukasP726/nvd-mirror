# NVD Mirror

Lokální mirror databáze zranitelností **National Vulnerability Database (NVD)** ve formátu CVE JSON 2.0. Projekt umožňuje pravidelně stahovat NVD feedy, uchovávat je v persistentním úložišti a zpřístupňovat je prostřednictvím HTTP serveru.

Mirror je určen především pro lokální použití nástroji pro analýzu softwarových závislostí, například OWASP Dependency-Check. Díky lokální kopii feedů není při každém skenování nutné přímo komunikovat se servery NVD.

Projekt obsahuje dvě varianty nasazení:

- Docker Compose – jednoduché lokální nasazení.
- Kubernetes – kontejnerizované nasazení do lokálního clusteru Minikube.

Součástí projektu je také demonstrační Maven projekt, který ověřuje integraci s OWASP Dependency-Check.

## 1. Architektura projektu

Projekt se skládá ze tří hlavních částí:

**Updater**

Python aplikace odpovědná za stahování NVD CVE JSON 2.0 feedů. Stahuje historické roční feedy a průběžně aktualizovaný feed `modified`. Stažené soubory ukládá v komprimovaném formátu `.json.gz` a uchovává související metadata.

**Nginx mirror**

HTTP server poskytující stažené feedy klientským aplikacím. Nginx používá sdílené persistentní úložiště připojené pouze pro čtení.

**Maven demo**

Demonstrační projekt používající OWASP Dependency-Check Maven Plugin. Jeho účelem je ověřit, že lze lokální NVD mirror použít jako zdroj zranitelností při analýze projektových závislostí.

## 2. Struktura repozitáře

```text
nvd-mirror/
├── compose/
│   └── compose.yaml
│
├── deploy/
│   └── kubernetes/
│       ├── namespace.yaml
│       ├── pvc.yaml
│       ├── configmap.yaml
│       ├── deployment.yaml
│       └── service.yaml
│
├── demo/
│   ├── .mvn/
│   │   └── wrapper/
│   ├── mvnw
│   ├── mvnw.cmd
│   ├── pom.xml
│   └── target/
│
├── docs/
│   └── architecture.md
│
├── mirror/
│   └── nginx.conf
│
└── updater/
    ├── Dockerfile
    ├── requirements.txt
    └── updater.py
```

Adresář `data/` může být přítomen pro lokální data, ale Docker Compose používá pojmenovaný volume a Kubernetes používá PersistentVolumeClaim.

## 3. Požadavky

Pro Docker Compose variantu:

- Docker Engine nebo Docker Desktop.
- Docker Compose.

Pro Kubernetes variantu:

- Minikube.
- Docker jako driver Minikube.
- Přístup k příkazu `minikube kubectl`.
- Dostatek prostředků pro běh Kubernetes clusteru a kontejnerů.

Pro demonstrační Maven projekt:

- JDK 23.
- Maven Wrapper, který je součástí projektu.

Na Windows je potřeba mít správně nastavenou proměnnou prostředí `JAVA_HOME`, která ukazuje na kořenový adresář instalace JDK.

## 4. Nasazení pomocí Docker Compose

V kořenovém adresáři projektu spusť:

```powershell
docker compose -f .\compose\compose.yaml up -d --build
```

Docker Compose vytvoří a spustí následující služby:

- `init-data` – jednorázová inicializace persistentního volume a nastavení oprávnění.
- `updater` – pravidelné stahování NVD feedů.
- `mirror` – Nginx HTTP server.

Updater běží pod neprivilegovaným uživatelem s UID/GID `10001`. Nginx má připojené stejné úložiště pouze pro čtení.

### Kontrola služeb

```powershell
docker compose -f .\compose\compose.yaml ps
```

Logy updateru:

```powershell
docker compose -f .\compose\compose.yaml logs -f updater
```

Logy Nginxu:

```powershell
docker compose -f .\compose\compose.yaml logs -f mirror
```

### Přístup k mirroru

Mirror je dostupný na:

```text
http://localhost:8080
```

Test dostupnosti feedu:

```powershell
curl.exe -I http://localhost:8080/nvdcve-2.0-modified.json.gz
```

### Zastavení

```powershell
docker compose -f .\compose\compose.yaml down
```

Pojmenovaný Docker volume zůstává zachován, takže stažená data přežijí zastavení a opětovné spuštění služeb.

Odstranění služeb včetně persistentního volume:

```powershell
docker compose -f .\compose\compose.yaml down -v
```

Pozor: varianta s `-v` odstraní také uložené NVD feedy.

## 5. Nasazení pomocí Kubernetes

Kubernetes varianta je určena pro lokální cluster Minikube.

Nasazení používá samostatný namespace `nvd-mirror`, PersistentVolumeClaim pro uchovávání dat, ConfigMap pro konfiguraci Nginxu, Deployment obsahující dva aplikační kontejnery a Service typu ClusterIP.

### 5.1 Kontrola Minikube

```powershell
minikube status
```

Pokud cluster neběží:

```powershell
minikube start
```

V dalších příkazech používáme `minikube kubectl --`, takže není nutné instalovat samostatný program `kubectl`.

### 5.2 Vytvoření prostředků

Manifesty aplikuj v následujícím pořadí:

```powershell
minikube kubectl -- apply -f .\deploy\kubernetes\namespace.yaml

minikube kubectl -- apply -f .\deploy\kubernetes\pvc.yaml

minikube kubectl -- apply -f .\deploy\kubernetes\configmap.yaml
```

Ověř vytvoření PVC:

```powershell
minikube kubectl -- get pvc -n nvd-mirror
```

Očekávaný stav je `Bound`.

### 5.3 Sestavení updater image

Image updateru sestav přímo v prostředí Minikube:

```powershell
minikube image build -t nvd-updater:1.0 .\updater
```

Tím bude image dostupná internímu container runtime clusteru, kterým je v našem prostředí containerd.

Deployment používá `imagePullPolicy: IfNotPresent`, takže Kubernetes nemusí hledat image v externím registry.

### 5.4 Nasazení aplikace

```powershell
minikube kubectl -- apply -f .\deploy\kubernetes\deployment.yaml
```

Sleduj stav Podu:

```powershell
minikube kubectl -- get pods -n nvd-mirror -w
```

Po úspěšném spuštění očekáváme `2/2 Running`.

Logy updateru:

```powershell
minikube kubectl -- logs deployment/nvd-mirror -n nvd-mirror -c updater
```

Logy Nginxu:

```powershell
minikube kubectl -- logs deployment/nvd-mirror -n nvd-mirror -c nginx
```

### 5.5 Vytvoření Service

```powershell
minikube kubectl -- apply -f .\deploy\kubernetes\service.yaml
```

Kontrola:

```powershell
minikube kubectl -- get services -n nvd-mirror

minikube kubectl -- get endpoints -n nvd-mirror
```

Service používá typ `ClusterIP`, takže je dostupná uvnitř clusteru.

### 5.6 Přístup z lokálního počítače

Pro zpřístupnění služby mimo cluster použij port forwarding:

```powershell
minikube kubectl -- port-forward -n nvd-mirror service/nvd-mirror 8080:8080
```

Mirror je následně dostupný na:

```text
http://localhost:8080
```

Ověření:

```powershell
curl.exe -I http://localhost:8080/nvdcve-2.0-modified.json.gz
```



## 6. Konfigurace updateru

Updater používá následující proměnné prostředí:

| Proměnná | Význam |
|---|---|
| `DATA_DIR` | Adresář pro ukládání feedů |
| `UPDATE_INTERVAL` | Interval aktualizace v sekundách |
| `NVD_FEED` | Výběr feedů ke stažení |

Výchozí interval aktualizace je:

```text
21600 sekund = 6 hodin
```

Updater podporuje výběr feedů pomocí proměnné `NVD_FEED`:

- `all` – všechny podporované feedy.
- `years` – historické roční feedy.
- `modified` – průběžně aktualizovaný feed.
- konkrétní rok – například `2025`.

Stažené feedy jsou ukládány jako komprimované soubory JSON a doprovodné metadata.

## 7. Integrace s OWASP Dependency-Check

Projekt obsahuje demonstrační Maven aplikaci v adresáři `demo/`.

Používá OWASP Dependency-Check Maven Plugin ve verzi `13.0.0` a záměrně obsahuje starší verzi závislosti `commons-text:1.9`, aby bylo možné ověřit detekci známých zranitelností.


Při testování Kubernetes varianty je použit samostatný `dataDirectory`, aby se oddělila lokální databáze Dependency-Check od databáze použité při testování Docker Compose.

### 7.2 Spuštění testu

Nejprve přejdi do adresáře:

```powershell
cd .\demo
```

Ověření prostředí:

```powershell
.\mvnw.cmd -version
```

Aktualizace databáze:

```powershell
.\mvnw.cmd org.owasp:dependency-check-maven:13.0.0:update-only
```

Analýza závislostí:

```powershell
.\mvnw.cmd org.owasp:dependency-check-maven:13.0.0:check
```

Maven Wrapper je součástí projektu, takže není nutné instalovat Maven globálně. Je však potřeba mít dostupné JDK a správně nastavenou proměnnou `JAVA_HOME`.

### 7.3 Očekávané výsledky

Demonstrační projekt obsahuje záměrně zranitelnou závislost `commons-text:1.9`.

Při ověřovacím běhu byly detekovány například:

- CVE-2022-42889 – Apache Commons Text.
- CVE-2025-48924 – Apache Commons Lang.

Výsledkem analýzy je HTML report:

```text
demo/target/dependency-check-report.html
```

Nastavení `failBuildOnCVSS` je v demonstrační konfiguraci nastaveno na `11`, aby nálezy s běžným maximálním CVSS skóre 10 nezpůsobily ukončení buildu chybou.

## 8. Ověřené funkčnosti

V rámci projektu byly ověřeny následující části:

| Funkčnost | Docker Compose | Kubernetes |
|---|---|---|
| Spuštění updateru | Ano | Ano |
| Stahování NVD feedů | Ano | Ano |
| Persistentní ukládání dat | Docker volume | PVC |
| HTTP poskytování feedů | Nginx | Nginx |
| Přístup ke feedům | Port 8080 | Port forwarding 8080 |
| Maven `update-only` | Ověřeno | Ověřeno |
| Maven `check` | Ověřeno | Ověřeno |

## 9. Použité technologie

- Python 3.13
- Requests
- NVD CVE JSON 2.0
- Docker
- Docker Compose
- Kubernetes
- Minikube
- containerd
- Nginx
- PersistentVolumeClaim
- ConfigMap
- Maven
- OWASP Dependency-Check

## 10. Omezení projektu

Kubernetes varianta je ověřena v lokálním jednouzlovém clusteru Minikube, nikoliv v produkčním víceuzlovém prostředí.

Použitá StorageClass `standard` v Minikube má `allowVolumeExpansion=false`, takže změna požadované velikosti PVC po jeho vytvoření nemusí být možná bez opětovného vytvoření úložiště.

Přístup ke Kubernetes Service je v demonstrační konfiguraci zajištěn pomocí port forwardingu, nikoliv veřejným vystavením služby.

Projekt je určen pro lokální demonstraci zrcadlení NVD dat a jejich využití při analýze softwarových závislostí.