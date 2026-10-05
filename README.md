---
{
  "schema": "wellmanifest.guide/v1",
  "id": "wellmanifest-usermanual",
  "version": "1.0.0",
  "status": "standard",
  "updated": "2026-10-05",
  "home": "wellmanifest",
  "shape": "standard_pack",
  "runtime_owner": "system"
}
---

# Standard wellmanifest/usermanual

**Identyfikator normatywny:** `urn:wellmanifest:spec:usermanual:v1`  
**Wersja:** `1.0.0` (2026-10-05)  
**Status:** Obowiązujący standard ekosystemu Wellmanifest / Paxlet

---

## 1. Cel i zakres standardu

Standard **`wellmanifest/usermanual`** definiuje bezwzględny wymóg dokumentacyjny dla wszystkich budowanych aplikacji webowych, mikroserwisów i środowisk roboczych w ekosystemie. Każde repozytorium udostępniające aplikację internetową lub usługę API **MUSI** zawierać w katalogu `doc/*` normatywny podręcznik użytkownika (`doc/USER_MANUAL.md` oraz opcjonalnie zsynchronizowany format maszynowy `doc/usermanual.yaml` / `doc/usermanual.json`).

Podręcznik ten nie jest luźnym opisem tekstowym, lecz **sformalizowanym kontraktem operacyjnym opartym o wzorzec CQRS**, procesy URI, język DSL oraz kontrakt cyfrowego bliźniaka (**Digital Twin**).

---

## 2. Kluczowe filary specyfikacji

Podręcznik użytkownika zgodny z `wellmanifest.usermanual/v1` składa się z 7 zintegrowanych sekcji:

### 2.1. Zmienne środowiskowe (`ENV VARIABLES`)
Kompletny rejestr wszystkich zmiennych konfiguracyjnych determinujących zachowanie usługi:
- Nazwa zmiennej (np. `PORT`, `FAKTURY_NODE`, `FAKTURY_DIR`)
- Typ wartości (`string`, `integer`, `boolean`, `path`, `uri`)
- Wymagalność (`required: true/false`)
- Wartość domyślna (`default`)
- Poziom poufności (`public`, `internal`, `secret`)
- Opis wpływu na logikę biznesową i sieć

### 2.2. Operacje Odczytu — CQRS Queries (`QUERIES`)
Specyfikacja wszystkich niemutujących operacji stanu aplikacji:
- Unikalny identyfikator zapytania (np. `faktury.stats.get`)
- Metoda HTTP (`GET`) i ścieżka URI
- Parametry wejściowe (query params, path params)
- Element interfejsu webowego inicjujący zapytanie (np. kafelki metryk, tabela dokumentów)
- Schemat danych wyjściowych

### 2.3. Operacje Zmiany Stanu — CQRS Commands (`COMMANDS`)
Specyfikacja wszystkich mutacji i transakcji biznesowych:
- Unikalny identyfikator komendy (np. `faktury.scan.upload`)
- Metoda HTTP (`POST`, `PUT`, `DELETE`) i ścieżka URI
- Schemat ładunku wejściowego (JSON / multipart)
- Gwarancje **idempotentności** (np. haszowanie percepcyjne dHash, bitowe SHA-256)
- Skutki uboczne w systemie plików i rejestrach
- Powiązany element UI (np. przycisk formularza, modal parowania)
- Emitowane kanoniczne identyfikatory URN (RFC 8141)

### 2.4. Procesy URI (`PROCESS_URI`)
Mapowanie komend aplikacji na normatywne procedury Dockuri i klastra:
- Schemat URI: `proc://<domena>/<moduł>/<operacja>/<wersja>`
- Wejściowy adapter procedury
- Emitowane dowody wykonania (`ExecutionReceipt`)

### 2.5. Język dziedzinowy DSL (`CAPITALIZE TOKENS`)
Normatywne tokeny akcji pisane wielkimi literami zgodnie ze standardem `wellmanifest/nl-uri-dsl-llm`:
- Przykłady: `SCAN_RECEIPT`, `RECONCILE_TRANSACTIONS`, `ORGANIZE_EMAILS`, `DEDUPLICATE_ARTIFACTS`
- Mapowanie zapytań języka naturalnego (NL) na konkretne wywołania API

### 2.6. Mapa Interakcji Web App (`UI_COMPONENTS`)
Praktyczny przewodnik po elementach interfejsu graficznego:
- Rozmieszczenie kontrolek, pasków narzędzi i paneli
- Powiązanie kliknięć użytkownika z komendami CQRS
- Ścieżki mobilne (np. bezpośrednie przekierowania User-Agent smartfona na `/scan.html`)

### 2.7. Kontrakt Cyfrowego Bliźniaka (`DIGITAL_TWIN`)
Definicja autonomicznego aktora-użytkownika (Digital Twin Persona):
- Kanoniczny URN tożsamości bliźniaka (np. `urn:twin:operator:finance:faktury:v1`)
- Zakres ról, uprawnień i autonomii
- Rutynowe pętle wykonawcze (dzienne, miesięczne, konserwacyjne)
- Sterownik programistyczny (Python/CLI) umożliwiający uruchamianie bliźniaka w trybie headless

---

## 3. Schemat JSON

Formalny schemat JSON Schema znajduje się w:
[`schemas/usermanual.schema.json`](./schemas/usermanual.schema.json)
