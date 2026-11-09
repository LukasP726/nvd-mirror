# Lokální zrcadlení NVD

## 1. O projektu

Cílem projektu je vytvořit lokální HTTP zrcadlo databáze zranitelností **National Vulnerability Database (NVD)**, které umožní využívat lokálně uložené datové feedy při bezpečnostní analýze softwarových závislostí.

Projekt využívá Docker Compose pro správu jednotlivých služeb. Aktualizátor stahuje data z NVD, ukládá je do sdíleného Docker volume a webový server Nginx je zpřístupňuje prostřednictvím HTTP rozhraní.

Součástí projektu je demonstrační Maven aplikace využívající nástroj OWASP Dependency-Check, který kontroluje závislosti projektu z hlediska známých zranitelností.

### Hlavní cíle

* Automatizované stahování a aktualizace NVD feedů.
* Lokální zpřístupnění stažených dat prostřednictvím HTTP.
* Omezení potřeby přímého stahování dat z veřejného serveru NVD při opakovaných analýzách.
* Demonstrace integrace lokálního zrcadla s nástrojem OWASP Dependency-Check.
* Připravení základu pro následnou integraci do CI/CD.

## 2. Architektura

Projekt se skládá z následujících komponent:

| Komponenta    | Technologie                         | Účel                                               |
| ------------- | ----------------------------------- | -------------------------------------------------- |
| `init-data`   | Alpine Linux                        | Inicializace datového volume a nastavení oprávnění |
| `updater`     | Python, Requests                    | Stahování, kontrola a aktualizace NVD feedů        |
| `mirror`      | Nginx                               | Poskytování feedů přes HTTP                        |
| `nvd-data`    | Docker volume                       | Perzistentní ukládání stažených dat                |
| `nvd-network` | Docker bridge network               | Síťová komunikace mezi službami                    |
| `demo`        | Maven, Java, OWASP Dependency-Check | Demonstrace kontroly softwarových závislostí       |

Podrobnější popis komponent a toku dat je uveden v souboru [`docs/architecture.md`](docs/architecture.md).

## 3. Požadavky

Pro spuštění projektu je potřeba:

* Docker Desktop s podporou Docker Compose.
* Java JDK 23 pro demonstrační Maven projekt.
* Připojení k internetu pro stahování NVD feedů a Maven závislostí.

Maven není nutné instalovat samostatně. Projekt `demo` obsahuje Maven Wrapper.

## 4. Spuštění projektu

Všechny příkazy v této části se spouštějí z kořenového adresáře repozitáře.

### 4.1 Spuštění služeb

Sestavení obrazu aktualizátoru a spuštění služeb na pozadí:

```powershell
docker compose -f .\compose\compose.yaml up -d --build
```

Kontrola stavu služeb:

```powershell
docker compose -f .\compose\compose.yaml ps
```

Služba `init-data` po úspěšné inicializaci skončí. Stav `Exited (0)` je očekávaný, protože jde o jednorázový inicializační kontejner.

### 4.2 Kontrola logů

Logy aktualizátoru:

```powershell
docker compose -f .\compose\compose.yaml logs -f updater
```

Logy aktualizátoru a Nginxu:

```powershell
docker compose -f .\compose\compose.yaml logs -f updater mirror
```

Aktualizátor má v konfiguraci nastaven interval `21600` sekund, tedy šest hodin.

### 4.3 Ověření dostupnosti zrcadla

Zrcadlo je dostupné na adrese:

```text
http://localhost:8080
```

Dostupnost metadat feedu `modified` lze ověřit příkazem:

```powershell
Invoke-WebRequest -Method Head `
  -Uri "http://localhost:8080/nvdcve-2.0-modified.meta" `
  -UseBasicParsing
```

Dostupnost komprimovaného feedu:

```powershell
Invoke-WebRequest -Method Head `
  -Uri "http://localhost:8080/nvdcve-2.0-modified.json.gz" `
  -UseBasicParsing
```

Očekávaným výsledkem je HTTP status `200 OK`.

Požadavek `HEAD` ověřuje dostupnost souboru a vrácené HTTP hlavičky, nikoliv správnost celého obsahu feedu.

## 5. Demonstrační Maven projekt

Adresář `demo` obsahuje demonstrační projekt využívající plugin `org.owasp:dependency-check-maven`.

Projekt záměrně obsahuje starší verzi knihovny `commons-text`, na které lze demonstrovat detekci známých zranitelností.

### 5.1 Ověření projektu

Přechod do adresáře:

```powershell
Set-Location .\demo
```

Kontrola konfigurace Maven projektu:

```powershell
.\mvnw.cmd validate
```

### 5.2 Aktualizace databáze Dependency-Check

```powershell
.\mvnw.cmd org.owasp:dependency-check-maven:13.0.0:update-only
```

Tento příkaz aktualizuje lokální databázi nástroje s využitím nakonfigurovaného NVD feedu.

První aktualizace může trvat několik minut.

### 5.3 Analýza závislostí

```powershell
.\mvnw.cmd org.owasp:dependency-check-maven:13.0.0:check
```

Po dokončení analýzy se HTML report nachází v:

```text
target/dependency-check-report.html
```

Otevření reportu:

```powershell
Invoke-Item .\target\dependency-check-report.html
```

Report obsahuje nalezené závislosti a případné známé zranitelnosti.

Konkrétní výsledky se mohou měnit podle aktuálního obsahu databáze NVD a použité verze nástroje.

Po dokončení práce je možné vrátit se do kořenového adresáře:

```powershell
Set-Location ..
```

## 6. Ukládání dat

Stažené NVD feedy jsou ukládány do pojmenovaného Docker volume `nvd-data`.

Volume je připojen:

* do aktualizátoru jako `/data`,
* do Nginxu jako `/usr/share/nginx/html`, a to pouze pro čtení.

## 7. Zastavení projektu

Zastavení a odstranění kontejnerů:

```powershell
docker compose -f .\compose\compose.yaml down
```

Tento příkaz zachová pojmenovaný volume a stažené feedy.

**Upozornění:** příkaz s parametrem `-v` odstraní také pojmenované volumes definované pro projekt, a může tak smazat stažená data.

```powershell
docker compose -f .\compose\compose.yaml down -v
```

Používej jej pouze tehdy, pokud chceš uložená data záměrně odstranit.

## 8. Struktura repozitáře

```text
nvd-mirror/
├── compose/
│   └── compose.yaml
├── updater/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── updater.py
├── mirror/
│   └── nginx.conf
├── demo/
│   ├── .mvn/
│   ├── mvnw
│   ├── mvnw.cmd
│   └── pom.xml
├── deploy/
│   └── kubernetes/
└── docs/
    └── architecture.md
```

Adresář `deploy/kubernetes/` je zatím prázdný. Kubernetes manifesty nejsou součástí aktuální implementace.

## 9. Aktuální omezení

* Zrcadlo je určeno pro lokální demonstrační a vývojové použití.
* HTTP rozhraní zatím nepoužívá TLS ani autentizaci.
* Nginx má vypnutý automatický výpis obsahu adresáře (`autoindex off`).
* Integrace s GitLab CI/CD zatím není implementována.
* Kubernetes nasazení zatím není implementováno.
