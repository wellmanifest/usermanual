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
