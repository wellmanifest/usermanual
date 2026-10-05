# Przewodnik Tworzenia Cyfrowego Bliźniaka (Digital Twin)

**Identyfikator normatywny:** `urn:wellmanifest:spec:usermanual:digital-twin:v1`

---

## 1. Koncepcja Cyfrowego Bliźniaka Użytkownika

Tradycyjne aplikacje webowe projektowane są wyłącznie z myślą o człowieku klikającym w interfejsie graficznym. W ekosystemie Wellmanifest każda aplikacja internetowa posiada zdefiniowanego **Cyfrowego Bliźniaka (Digital Twin)**:
1. **Persona**: Wyrazista tożsamość z przypisanym imieniem, rolą i zakresem odpowiedzialności (np. *Wacław Bilans* dla Faktur, *Maksymilian Mux* dla willmux, *Wiktor Koordynator* dla willman).
2. **URN tożsamości**: Unikalny identyfikator RFC 8141 w przestrzeni `urn:twin:operator:<domena>:<usługa>:v1`.
3. **Możliwości (Capabilities)**: Formalna lista akcji biznesowych, które bliźniak może podejmować autonomicznie.
4. **Rutynowe pętle (Autonomous Routines)**: Częstotliwość i reguły samoczynnego uruchamiania operacji (np. codzienne porządkowanie e-maili, comiesięczne uzgadnianie przelewów).
5. **Sterownik Headless**: Klasa programistyczna w Pythonie/CLI, która komunikuje się z aplikacją webową za pośrednictwem wyłącznie zadeklarowanych w manualu zapytań i komend CQRS.

---

## 2. Podpisywanie pokwitowań (Audit Receipts)

Wszystkie autonomiczne cykle audytowe bliźniaka kończą się wygenerowaniem deterministycznego pokwitowania wykonania:
```python
serialized = json.dumps(audit_summary, sort_keys=True).encode("utf-8")
receipt_hash = hashlib.sha256(serialized).hexdigest()[:16]
audit_receipt_urn = f"urn:twin:receipt:audit:{month}:{receipt_hash}"
```
Pokwitowanie to może być weryfikowane kryptograficznie przez innych subaktorów siatki mesh.
