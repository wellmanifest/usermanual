"""Ecosystem-wide CQRS User Manual conformance and drift detection tests."""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pytest
from scripts.validate_cqrs import CQRSValidator


def is_service_online(url: str) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Probe/1.0"})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            return resp.status in (200, 204, 404)
    except Exception:
        return False


def test_willmux_cqrs_usermanual_offline():
    """Verify willmux CQRS user manual specification schema offline."""
    manual_dir = ROOT / "examples" / "willmux"
    validator = CQRSValidator(manual_dir)
    res = validator.run()

    assert res["valid"] is True, f"Errors: {res['errors']}"
    assert res["manifest_id"] == "paxlet:willmux"
    assert res["queries_count"] >= 8
    assert res["commands_count"] >= 5
    assert res["twin_urn"] == "urn:twin:operator:workspace:willmux:v1"
    assert res["drift_detected"] is False


def test_willmux_cqrs_usermanual_live_drift():
    """Verify willmux live endpoints against running willmux daemon on port 7070."""
    if not is_service_online("http://127.0.0.1:7070/api/queries/state"):
        pytest.skip("willmux server is not running on port 7070")

    manual_dir = ROOT / "examples" / "willmux"
    validator = CQRSValidator(manual_dir, base_url="http://127.0.0.1:7070")
    res = validator.run()

    assert res["valid"] is True, f"Live drift errors: {res['errors']}"
    assert res["drift_detected"] is False
    assert len(res["errors"]) == 0


def test_willman_cqrs_usermanual_offline():
    """Verify willman CQRS user manual specification schema offline."""
    manual_dir = ROOT / "examples" / "willman"
    validator = CQRSValidator(manual_dir)
    res = validator.run()

    assert res["valid"] is True, f"Errors: {res['errors']}"
    assert res["manifest_id"] == "willman:coordinator"
    assert res["queries_count"] >= 8
    assert res["commands_count"] >= 5
    assert res["twin_urn"] == "urn:twin:operator:mesh:willman:v1"
    assert res["drift_detected"] is False


def test_willman_cqrs_usermanual_live_drift():
    """Verify willman live endpoints against running willman coordinator on port 8780."""
    if not is_service_online("http://127.0.0.1:8780/health"):
        pytest.skip("willman coordinator is not running on port 8780")

    manual_dir = ROOT / "examples" / "willman"
    validator = CQRSValidator(manual_dir, base_url="http://127.0.0.1:8780")
    res = validator.run()

    assert res["valid"] is True, f"Live drift errors: {res['errors']}"
    assert res["drift_detected"] is False
    assert len(res["errors"]) == 0


def test_willapx_faktury_cqrs_usermanual_live_drift():
    """Verify willapx FakturApp live endpoints against running daemon on port 8085."""
    faktury_dir = Path("/home/tom/github/paxlet-com/willapx/apps/faktury/doc/usermanual")
    if not faktury_dir.exists():
        pytest.skip("willapx faktury doc directory not found")
    if not is_service_online("http://127.0.0.1:8085/health"):
        pytest.skip("FakturApp is not running on port 8085")

    validator = CQRSValidator(faktury_dir, base_url="http://127.0.0.1:8085")
    res = validator.run()

    assert res["valid"] is True, f"Live drift errors: {res['errors']}"
    assert res["drift_detected"] is False
    assert len(res["errors"]) == 0


def test_live_command_drift_probe_is_readonly_by_default(tmp_path):
    """Ensure command drift checks never issue mutating HTTP methods unless opted in."""
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    observed_methods: list[tuple[str, str]] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return

        def _dispatch(self, method: str):
            observed_methods.append((method, self.path))
            if self.path == "/api/state" and method == "GET":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"ok":true}')
            elif self.path == "/api/restart":
                if method == "OPTIONS":
                    self.send_response(405)
                    self.end_headers()
                else:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"restarted":true}')
            else:
                self.send_response(404)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"not found")

        def do_GET(self):
            self._dispatch("GET")

        def do_OPTIONS(self):
            self._dispatch("OPTIONS")

        def do_POST(self):
            self._dispatch("POST")

    manual_file = tmp_path / "usermanual.json"
    base_doc = {
        "schema": "urn:wellmanifest:spec:usermanual:v1",
        "id": "test:service",
        "name": "Test Service",
        "version": "1.0.0",
        "summary": "Read-only drift probe verification",
        "queries": [
            {
                "id": "get_state",
                "method": "GET",
                "endpoint": "/api/state",
                "description": "Read state",
                "ui_trigger": "Ctrl+B 1",
            }
        ],
        "commands": [
            {
                "id": "restart_service",
                "method": "POST",
                "endpoint": "/api/restart",
                "description": "Restart service",
                "idempotency": "non-idempotent",
                "side_effects": "restarts process",
                "ui_trigger": "Ctrl+B :",
            }
        ],
    }
    manual_file.write_text(json.dumps(base_doc), encoding="utf-8")

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_address[1]}"
        ro_res = CQRSValidator(tmp_path, base_url=base_url).run()
        assert ro_res["valid"] is True, ro_res["errors"]
        assert ro_res["allow_mutations"] is False
        assert ("POST", "/api/restart") not in observed_methods
        assert ("OPTIONS", "/api/restart") in observed_methods

        # Missing command route still triggers DRIFT-404-COMMAND via read-only OPTIONS
        missing_doc = dict(base_doc)
        missing_doc["commands"] = [
            {**base_doc["commands"][0], "id": "missing_cmd", "endpoint": "/api/nonexistent"}
        ]
        manual_file.write_text(json.dumps(missing_doc), encoding="utf-8")
        drift_res = CQRSValidator(tmp_path, base_url=base_url).run()
        assert drift_res["valid"] is False
        assert drift_res["drift_detected"] is True
        assert any("DRIFT-404-COMMAND" in err for err in drift_res["errors"])

        # Explicit opt-in sends POST
        manual_file.write_text(json.dumps(base_doc), encoding="utf-8")
        observed_methods.clear()
        rw_res = CQRSValidator(tmp_path, base_url=base_url, allow_mutations=True).run()
        assert rw_res["valid"] is True
        assert rw_res["allow_mutations"] is True
        assert ("POST", "/api/restart") in observed_methods
    finally:
        server.shutdown()
        server.server_close()
