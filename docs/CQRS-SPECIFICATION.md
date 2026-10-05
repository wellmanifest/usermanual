# Specyfikacja Standardu CQRS: wellmanifest/usermanual

**Identyfikator normatywny:** `urn:wellmanifest:spec:usermanual:cqrs:v1`  
**Standard bazowy:** `wellmanifest.usermanual/v1`

---

## 1. Wprowadzenie

Wzorzec **Command-Query Responsibility Segregation (CQRS)** w standardzie `wellmanifest/usermanual` rozdziela formalną dokumentację aplikacji internetowej i usług API na dwa rozłączne zbiory operacji:
1. **Queries (Zapytania / Powierzchnia Odczytu)**: Operacje bezpieczne, niemutujące stanu bazodanowego ani dyskowego (`GET`), służące do inspekcji metryk, pobierania list, odczytu plików i statusu.
2. **Commands (Polecenia / Powierzchnia Zapisu i Mutacji)**: Operacje zmieniające stan (`POST`, `PUT`, `DELETE`, `PATCH`), niosące określone skutki uboczne (side effects), wymagające deklaracji idempotencji oraz emitujące identyfikatory URN wytworzonych artefaktów.

---

## 2. Układy struktury katalogów

Standard dopuszcza dwa równorzędne warianty implementacji:

### Wariant A: Modularny układ katalogowy (`layout: modular_cqrs`)
Zalecany dla aplikacji posiadających rozbudowaną liczbę endpointów (np. `willapx:faktury`):

```
doc/usermanual/
├── manifest.yaml                    # Główny manifest (schema: wellmanifest.usermanual/v1)
├── queries/                         # Zapytania (pliki *.query.yaml lub *.queries.yaml)
│   ├── core.queries.yaml
│   ├── finance.queries.yaml
│   └── scan.queries.yaml
├── commands/                        # Komendy (pliki *.command.yaml lub *.commands.yaml)
│   └── commands.yaml
├── env/                             # Zmienne środowiskowe (*.yaml)
│   └── env_variables.yaml
├── twin/                            # Cyfrowy Bliźniak (*.yaml)
│   └── digital_twin.yaml
├── processes/                       # Procedury Dockuri / mesh URIs
│   └── processes.yaml
├── dsl/                             # DSL i tokeny akcji pisane wielkimi literami
│   └── dsl.yaml
└── ui/                              # Komponenty interfejsu graficznego
    └── ui_components.yaml
```

### Wariant B: Zunifikowany plik kontraktu (`docs/usermanual.yaml` lub `docs/usermanual.json`)
Stosowany dla mikrousług i demonów systemowych (np. `willman`, `willmux`), łączący wszystkie sekcje w pojedynczym dokumencie.

---

## 3. Schemat Zapytania (Query)

Plik schematu: [`schemas/query.schema.json`](../schemas/query.schema.json)

Wymagane pola:
- `id` (string): Unikalny kropkowy identyfikator, np. `faktury.stats.get`, `willmux.state.get`.
- `method` (string): Bezwzględnie `"GET"`.
- `endpoint` (string): Ścieżka URL lub szablon ze zmiennymi w nawiasach klamrowych, np. `/api/month/{month}`.
- `description` (string): Precyzyjny opis odczytywanego stanu.
- `ui_trigger` (string): Element interfejsu (przycisk, kafelek, karta) inicjujący wywołanie.
- `response_schema` (object): Oczekiwany schemat odpowiedzi (pola, typy, przykłady).

---

## 4. Schemat Polecenia (Command)

Plik schematu: [`schemas/command.schema.json`](../schemas/command.schema.json)

Wymagane pola:
- `id` (string): Unikalny identyfikator, np. `faktury.scan.upload`, `willman.tasks.create`.
- `method` (string): Mutująca metoda HTTP (`POST`, `PUT`, `DELETE`, `PATCH`).
- `endpoint` (string): Ścieżka URL.
- `payload_schema` (object): Wymagane pola wejściowe i walidacje.
- `description` (string): Opis wykonywanej transakcji.
- `idempotency` (string): Gwarancje deduplikacji (np. hasz SHA-256, dHash, brak duplikatów).
- `side_effects` (array): Lista modyfikowanych zasobów, tabel lub plików.
- `ui_trigger` (string): Akcja użytkownika wyzwalająca polecenie.
- `emitted_urns` (array): Wytworzone URN-y RFC 8141 (np. `urn:fin:doc:receipt:{month}:{hash}`).
