#!/usr/bin/env python3
"""CQRS Specification and Implementation Drift Validator for wellmanifest/usermanual.

Standard: urn:wellmanifest:spec:usermanual:v1
Validates:
1. Manifest (manifest.yaml)
2. Queries (queries/*.yaml, queries/*.json)
3. Commands (commands/*.yaml, commands/*.json)
4. Environment variables (env/*.yaml, env/*.json)
5. Digital Twin specifications (twin/*.yaml, twin/*.json)
6. Processes, DSL, and UI components (processes/, dsl/, ui/)
7. Live endpoint drift against a running HTTP server
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
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
    def __init__(
        self,
        manual_dir: Path,
        base_url: Optional[str] = None,
        allow_mutations: bool = False,
    ):
        self.manual_dir = manual_dir.resolve()
        self.base_url = base_url.rstrip("/") if base_url else None
        self.allow_mutations = bool(allow_mutations)
        self.manifest: Dict[str, Any] = {}
        self.queries: List[Dict[str, Any]] = []
        self.commands: List[Dict[str, Any]] = []
        self.env_variables: List[Dict[str, Any]] = []
        self.twin: Dict[str, Any] = {}
        self.processes: List[Dict[str, Any]] = []
        self.dsl: Dict[str, Any] = {}
        self.ui_components: List[Dict[str, Any]] = []

        self.errors: List[str] = []
        self.warnings: List[str] = []

    def collect_definitions(self):
        if not self.manual_dir.exists():
            self.errors.append(f"User manual path does not exist: {self.manual_dir}")
            return

        # Check if manual_dir is a file or contains a root usermanual.yaml / usermanual.json
        root_doc = None
        if self.manual_dir.is_file():
            try:
                root_doc = load_yaml_or_json(self.manual_dir)
            except Exception as e:
                self.errors.append(f"Failed parsing {self.manual_dir.name}: {e}")
        elif (self.manual_dir / "usermanual.yaml").exists():
            try:
                root_doc = load_yaml_or_json(self.manual_dir / "usermanual.yaml")
            except Exception as e:
                self.errors.append(f"Failed parsing usermanual.yaml: {e}")
        elif (self.manual_dir / "usermanual.json").exists():
            try:
                root_doc = load_yaml_or_json(self.manual_dir / "usermanual.json")
            except Exception as e:
                self.errors.append(f"Failed parsing usermanual.json: {e}")

        if root_doc:
            self.manifest = root_doc
            self._validate_manifest_schema(root_doc)
            if "queries" in root_doc and isinstance(root_doc["queries"], list):
                for q in root_doc["queries"]:
                    q["_file"] = "usermanual"
                    self._validate_query_schema(q)
                    self.queries.append(q)
            if "commands" in root_doc and isinstance(root_doc["commands"], list):
                for c in root_doc["commands"]:
                    c["_file"] = "usermanual"
                    self._validate_command_schema(c)
                    self.commands.append(c)
            if "env_variables" in root_doc and isinstance(root_doc["env_variables"], list):
                for ev in root_doc["env_variables"]:
                    self._validate_env_var_schema(ev, "usermanual")
                    self.env_variables.append(ev)
            if "digital_twin" in root_doc and isinstance(root_doc["digital_twin"], dict):
                self.twin = root_doc["digital_twin"]
                self._validate_twin_schema(self.twin, "usermanual")
            if "processes" in root_doc and isinstance(root_doc["processes"], list):
                self.processes = root_doc["processes"]
            if "dsl" in root_doc and isinstance(root_doc["dsl"], dict):
                self.dsl = root_doc["dsl"]
            if "ui_components" in root_doc and isinstance(root_doc["ui_components"], list):
                self.ui_components = root_doc["ui_components"]
        else:
            manifest_file = self.manual_dir / "manifest.yaml"
            if not manifest_file.exists():
                manifest_file = self.manual_dir / "manifest.json"
            if manifest_file.exists():
                try:
                    self.manifest = load_yaml_or_json(manifest_file)
                    self._validate_manifest_schema(self.manifest)
                except Exception as e:
                    self.errors.append(f"Failed parsing manifest {manifest_file.name}: {e}")

        # 2. Collect Queries
        queries_dir = self.manual_dir / "queries"
        if queries_dir.exists():
            for f in sorted(queries_dir.glob("*.yaml")) + sorted(queries_dir.glob("*.json")):
                try:
                    doc = load_yaml_or_json(f)
                    items = (
                        doc.get("queries", [doc])
                        if isinstance(doc, dict) and "queries" in doc
                        else (doc if isinstance(doc, list) else [doc])
                    )
                    for q in items:
                        q["_file"] = str(f.relative_to(self.manual_dir))
                        self._validate_query_schema(q)
                        self.queries.append(q)
                except Exception as e:
                    self.errors.append(f"Failed parsing query file {f.name}: {e}")

        # 3. Collect Commands
        commands_dir = self.manual_dir / "commands"
        if commands_dir.exists():
            for f in sorted(commands_dir.glob("*.yaml")) + sorted(commands_dir.glob("*.json")):
                try:
                    doc = load_yaml_or_json(f)
                    items = (
                        doc.get("commands", [doc])
                        if isinstance(doc, dict) and "commands" in doc
                        else (doc if isinstance(doc, list) else [doc])
                    )
                    for c in items:
                        c["_file"] = str(f.relative_to(self.manual_dir))
                        self._validate_command_schema(c)
                        self.commands.append(c)
                except Exception as e:
                    self.errors.append(f"Failed parsing command file {f.name}: {e}")

        # 4. Env variables
        env_dir = self.manual_dir / "env"
        if env_dir.exists():
            for f in sorted(env_dir.glob("*.yaml")) + sorted(env_dir.glob("*.json")):
                try:
                    edoc = load_yaml_or_json(f)
                    vars_list = edoc.get("env_variables", [edoc]) if isinstance(edoc, dict) else edoc
                    for ev in vars_list:
                        self._validate_env_var_schema(ev, f.name)
                        self.env_variables.append(ev)
                except Exception as e:
                    self.errors.append(f"Failed parsing env file {f.name}: {e}")

        # 5. Twin
        twin_dir = self.manual_dir / "twin"
        if twin_dir.exists():
            for f in sorted(twin_dir.glob("*.yaml")) + sorted(twin_dir.glob("*.json")):
                try:
                    self.twin = load_yaml_or_json(f)
                    self._validate_twin_schema(self.twin, f.name)
                except Exception as e:
                    self.errors.append(f"Failed parsing twin file {f.name}: {e}")

        # 6. Processes
        proc_dir = self.manual_dir / "processes"
        if proc_dir.exists():
            for f in sorted(proc_dir.glob("*.yaml")) + sorted(proc_dir.glob("*.json")):
                try:
                    pdoc = load_yaml_or_json(f)
                    for p in pdoc.get("processes", []):
                        self.processes.append(p)
                except Exception as e:
                    self.errors.append(f"Failed parsing processes {f.name}: {e}")

        # 7. DSL
        dsl_dir = self.manual_dir / "dsl"
        if dsl_dir.exists():
            for f in sorted(dsl_dir.glob("*.yaml")) + sorted(dsl_dir.glob("*.json")):
                try:
                    self.dsl = load_yaml_or_json(f)
                except Exception as e:
                    self.errors.append(f"Failed parsing dsl {f.name}: {e}")

        # 8. UI components
        ui_dir = self.manual_dir / "ui"
        if ui_dir.exists():
            for f in sorted(ui_dir.glob("*.yaml")) + sorted(ui_dir.glob("*.json")):
                try:
                    udoc = load_yaml_or_json(f)
                    for u in udoc.get("ui_components", []):
                        self.ui_components.append(u)
                except Exception as e:
                    self.errors.append(f"Failed parsing ui {f.name}: {e}")

    def _validate_manifest_schema(self, m: Dict[str, Any]):
        for field in ["schema", "id", "name", "version", "summary"]:
            if not m.get(field):
                self.errors.append(f"[manifest] Missing required field '{field}'")

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

    def _validate_env_var_schema(self, ev: Dict[str, Any], fname: str):
        for field in ["name", "type", "description"]:
            if not ev.get(field):
                self.errors.append(f"[{fname}] Env variable missing required field '{field}'")

    def _validate_twin_schema(self, t: Dict[str, Any], fname: str):
        for field in ["twin_urn", "persona", "role", "capabilities", "autonomous_routines"]:
            if not t.get(field):
                self.errors.append(f"[{fname}] Digital Twin missing required field '{field}'")

    def verify_live_drift(self):
        """Validate whether defined endpoints exist and respond on the running server."""
        if not self.base_url:
            return

        # 1. Verify Queries (GET)
        for q in self.queries:
            raw_endpoint = q.get("endpoint", "")
            # Replace placeholder path variables like {month} or {id} with sample values
            test_path = re.sub(r"\{month\}", "2026.06", raw_endpoint)
            test_path = re.sub(r"\{[a-zA-Z0-9_]+\}", "test", test_path)
            full_url = f"{self.base_url}{test_path}"

            try:
                req = urllib.request.Request(
                    full_url,
                    headers={"User-Agent": "CQRSValidator/1.0", "Accept": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=4.0) as resp:
                    if resp.status not in (200, 204):
                        self.warnings.append(f"[DRIFT-QUERY] Query '{q.get('id')}' at {test_path} returned HTTP {resp.status}")
            except urllib.error.HTTPError as e:
                content_type = e.headers.get("Content-Type", "")
                if e.code == 404 and "application/json" in content_type:
                    # Application logic reached; entity was not found (not a missing route)
                    pass
                elif e.code == 404:
                    self.errors.append(f"[DRIFT-404-QUERY] Declared query '{q.get('id')}' at {test_path} returned 404 Not Found")
                else:
                    self.warnings.append(f"[DRIFT-QUERY] Query '{q.get('id')}' at {test_path} returned HTTP {e.code}")
            except Exception as e:
                self.warnings.append(f"[DRIFT-QUERY-CONN] Could not reach query '{q.get('id')}' at {test_path}: {e}")

        # 2. Verify Commands (read-only OPTIONS probe by default; mutating methods require explicit opt-in)
        for c in self.commands:
            raw_endpoint = c.get("endpoint", "")
            test_path = re.sub(r"\{month\}", "2026.06", raw_endpoint)
            test_path = re.sub(r"\{[a-zA-Z0-9_]+\}", "test", test_path)
            full_url = f"{self.base_url}{test_path}"
            declared_method = str(c.get("method") or "POST").upper()
            probe_method = declared_method if self.allow_mutations else "OPTIONS"
            probe_body = b"{}" if self.allow_mutations else None
            probe_headers = {"User-Agent": "CQRSValidator/1.0", "Accept": "application/json"}
            if self.allow_mutations:
                probe_headers["Content-Type"] = "application/json"

            try:
                req = urllib.request.Request(
                    full_url,
                    data=probe_body,
                    headers=probe_headers,
                    method=probe_method,
                )
                with urllib.request.urlopen(req, timeout=4.0) as resp:
                    pass
            except urllib.error.HTTPError as e:
                content_type = e.headers.get("Content-Type", "")
                if e.code == 404 and "application/json" in content_type:
                    pass
                elif e.code == 404:
                    self.errors.append(f"[DRIFT-404-COMMAND] Declared command '{c.get('id')}' at {test_path} returned 404 Not Found")
                else:
                    # 405 Method Not Allowed (on read-only OPTIONS probe), 400, 422, etc. confirm route existence
                    pass
            except Exception as e:
                self.warnings.append(f"[DRIFT-COMMAND-CONN] Could not reach command '{c.get('id')}' at {test_path}: {e}")

    def run(self) -> Dict[str, Any]:
        self.collect_definitions()
        if self.base_url:
            self.verify_live_drift()

        valid = len(self.errors) == 0
        return {
            "valid": valid,
            "manifest_id": self.manifest.get("id"),
            "allow_mutations": self.allow_mutations,
            "queries_count": len(self.queries),
            "commands_count": len(self.commands),
            "env_vars_count": len(self.env_variables),
            "twin_urn": self.twin.get("twin_urn"),
            "processes_count": len(self.processes),
            "dsl_tokens_count": len(self.dsl.get("capitalize_tokens", [])),
            "ui_components_count": len(self.ui_components),
            "errors": self.errors,
            "warnings": self.warnings,
            "drift_detected": any("DRIFT" in e for e in self.errors),
        }


def main():
    parser = argparse.ArgumentParser(description="Validate CQRS User Manual files and detect live implementation drift.")
    parser.add_argument("manual_dir", type=Path, help="Path to doc/usermanual directory containing queries/ and commands/")
    parser.add_argument("--url", type=str, default=None, help="Base URL of running server to verify live endpoint drift")
    parser.add_argument(
        "--allow-mutations",
        action="store_true",
        help="Explicitly allow mutating POST/PUT/DELETE/PATCH probes instead of read-only OPTIONS checks",
    )
    args = parser.parse_args()

    validator = CQRSValidator(args.manual_dir, args.url, allow_mutations=args.allow_mutations)
    res = validator.run()
    print(json.dumps(res, indent=2, ensure_ascii=False))
    sys.exit(0 if res["valid"] else 1)


if __name__ == "__main__":
    main()
