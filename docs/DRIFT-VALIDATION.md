# Wykrywanie Driftu i Weryfikacja Zgodności w standardzie wellmanifest/usermanual

**Narzędzie referencyjne:** [`scripts/validate_cqrs.py`](../scripts/validate_cqrs.py)

---

## 1. Na czym polega problem driftu dokumentacji?

W tradycyjnym rozwoju oprogramowania dokumentacja API i instrukcje użytkownika szybko ulegają dezaktualizacji (tzw. *documentation drift*):
- Zmiana ścieżki w kodzie bez aktualizacji dokumentacji prowadzi do martwych linków (błędy 404).
- Dodanie nowego endpointu w serwerze bez opisania go w podręczniku powoduje powstanie nieudokumentowanych "cieniowych" tras.
- Zmiana parametrów zapytania powoduje błędy 400 Bad Request u agentów automatycznych.

Standard `wellmanifest/usermanual` rozwiązuje ten problem poprzez **obowiązkową walidację driftu**.

---

## 2. Dwa tryby detekcji driftu

### Tryb 1: Walidacja statyczna tras w kodzie (Code Route Drift)
Skrypt analizuje zarejestrowane w kodzie źródłowym serwera trasy (np. `apps/faktury/server.py` lub `willmux_agent/app.py`) i zestawia je ze specyfikacją:
```bash
python3 apps/faktury/cqrs_validator.py
```
Raportuje:
- `undocumented_routes`: listę endpointów w kodzie, których brakuje w manualu.

### Tryb 2: Walidacja na żywym serwerze HTTP (Live Server Drift)
Skrypt wykonuje rzeczywiste odpytania HTTP do uruchomionej instancji serwera:
```bash
python3 scripts/validate_cqrs.py /path/to/usermanual --url http://127.0.0.1:8085
```
Walidator:
- Wysyła żądania `GET` dla zadeklarowanych `queries`.
- Sprawdza istnienie tras `POST`/`PUT` dla `commands`.
- **Precyzyjnie odróżnia** biznesową odpowiedź API (np. kod 404 z nagłówkiem `application/json` oznaczający poprawnie obsłużoną trasę i brak szukanego rekordu) od **rzeczywistego braku trasy** (błąd 404 HTML z serwera bazowego).
- W przypadku wykrycia martwej trasy zgłasza:
  ```json
  "drift_detected": true,
  "errors": ["[DRIFT-404-QUERY] Declared query 'willmux.snapshot.get' at /api/queries/snapshot returned 404 Not Found"]
  ```

---

## 3. Integracja w potokach CI / Pytest

Każde repozytorium wdrażające aplikację webową powinno posiadać test conformance:

```python
from scripts.validate_cqrs import CQRSValidator

def test_usermanual_live_drift(running_server: str):
    validator = CQRSValidator(manual_dir, base_url=running_server)
    res = validator.run()
    assert res["valid"] is True, f"Drift errors: {res['errors']}"
    assert res["drift_detected"] is False
```
