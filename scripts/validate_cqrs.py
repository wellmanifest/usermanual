#!/usr/bin/env python3
"""CQRS Specification and Implementation Drift Validator for wellmanifest/usermanual."""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False


def load_yaml_or_json(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        if not HAVE_YAML:
            raise RuntimeError("PyYAML required to parse yaml files")
        return yaml.safe_load(text) or {}
    return json.loads(text)


class CQRSValidator:
    def __init__(self, manual_dir: Path, base_url: Optional[str] = None):
        self.manual_dir = manual_dir.resolve()
        self.base_url = base_url.rstrip("/") if base_url else None
        self.queries: List[Dict[str, Any]] = []
        self.commands: List[Dict[str, Any]] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def collect_definitions(self):
        # 1. Collect Queries
        queries_dir = self.manual_dir / "queries"
        if queries_dir.exists():
            for f in sorted(queries_dir.glob("*.yaml")) + sorted(queries_dir.glob("*.json")):
                try:
                    q = load_yaml_or_json(f)
                    q["_file"] = str(f.relative_to(self.manual_dir))
                    self._validate_query_schema(q)
                    self.queries.append(q)
                except Exception as e:
                    self.errors.append(f"Failed parsing query file {f.name}: {e}")

        # 2. Collect Commands
        commands_dir = self.manual_dir / "commands"
        if commands_dir.exists():
            for f in sorted(commands_dir.glob("*.yaml")) + sorted(commands_dir.glob("*.json")):
                try:
                    c = load_yaml_or_json(f)
                    c["_file"] = str(f.relative_to(self.manual_dir))
                    self._validate_command_schema(c)
                    self.commands.append(c)
                except Exception as e:
                    self.errors.append(f"Failed parsing command file {f.name}: {e}")

    def _validate_query_schema(self, q: Dict[str, Any]):
        file_ref = q.get("_file", "query")
        for field in ["id", "method", "endpoint", "description", "ui_trigger"]:
            if not q.get(field):
                self.errors.append(f"[{file_ref}] Missing required field '{field}'")
        if q.get("method") != "GET":
            self.errors.append(f"[{file_ref}] CQRS Query method MUST be 'GET', got '{q.get('method')}'")

    def _validate_command_schema(self, c: Dict[str, Any]):
        file_ref = c.get("_file", "command")
        for field in ["id", "method", "endpoint", "description", "idempotency", "side_effects", "ui_trigger"]:
            if not c.get(field):
                self.errors.append(f"[{file_ref}] Missing required field '{field}'")
        if c.get("method") not in ("POST", "PUT", "DELETE", "PATCH"):
            self.errors.append(f"[{file_ref}] CQRS Command method MUST be mutation (POST/PUT/DELETE/PATCH), got '{c.get('method')}'")

    def verify_live_drift(self):
        """Validate whether defined endpoints exist and respond on the running server."""
        if not self.base_url:
            return

        for q in self.queries:
            raw_endpoint = q.get("endpoint", "")
            # Replace placeholder path variables like {month} with sample values
            test_path = re.sub(r"\{month\}", "2026.06", raw_endpoint)
            test_path = re.sub(r"\{[a-zA-Z0-9_]+\}", "test", test_path)
            full_url = f"{self.base_url}{test_path}"

            try:
                req = urllib.request.Request(full_url, headers={"User-Agent": "CQRSValidator/1.0"})
                with urllib.request.urlopen(req, timeout=3.0) as resp:
                    if resp.status not in (200, 204):
                        self.warnings.append(f"[DRIFT-QUERY] Query '{q.get('id')}' at {test_path} returned HTTP {resp.status}")
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    self.errors.append(f"[DRIFT-404-QUERY] Declared query '{q.get('id')}' at {test_path} returned 404 Not Found")
                else:
                    self.warnings.append(f"[DRIFT-QUERY] Query '{q.get('id')}' at {test_path} returned HTTP {e.code}")
            except Exception as e:
                self.warnings.append(f"[DRIFT-QUERY-CONN] Could not reach query '{q.get('id')}' at {test_path}: {e}")

    def run(self) -> Dict[str, Any]:
        self.collect_definitions()
        if self.base_url:
            self.verify_live_drift()

        valid = len(self.errors) == 0
        return {
            "valid": valid,
            "queries_count": len(self.queries),
            "commands_count": len(self.commands),
            "errors": self.errors,
            "warnings": self.warnings,
            "drift_detected": any("DRIFT" in e for e in self.errors),
        }


def main():
    parser = argparse.ArgumentParser(description="Validate CQRS User Manual files and detect live implementation drift.")
    parser.add_argument("manual_dir", type=Path, help="Path to doc/usermanual directory containing queries/ and commands/")
    parser.add_argument("--url", type=str, default=None, help="Base URL of running server to verify live endpoint drift")
    args = parser.parse_args()

    validator = CQRSValidator(args.manual_dir, args.url)
    res = validator.run()
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["valid"] else 1)


if __name__ == "__main__":
    main()
