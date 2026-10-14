"""Deploy generated CPAT from a SprintWeave job.

Modes (SPRINTWEAVE_CPAT_DEPLOY_MODE / UI override / PVC settings):
  openshift  — binary BuildConfig + Deployment via ``oc`` (preferred on OCP)
  bringup    — run ``./bringup.sh start`` with podman/docker (bastion / privileged)
  manifests  — write YAML + helper script only (always safe fallback)

Default: PVC settings → env → openshift if ``oc`` works, else manifests.
User preference is stored at ``/data/settings.json`` (no rebuild).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from api.job_store import save_job

DATA_DIR = Path(os.environ.get("SPRINTWEAVE_DATA_DIR", "/data"))
SETTINGS_PATH = DATA_DIR / "settings.json"
DEPLOY_MODE = os.environ.get("SPRINTWEAVE_CPAT_DEPLOY_MODE", "").strip().lower()
CPAT_HOST_PORT = os.environ.get("SPRINTWEAVE_CPAT_PORT", "8088")
CPAT_NAMESPACE = os.environ.get(
    "SPRINTWEAVE_CPAT_NAMESPACE",
    os.environ.get("POD_NAMESPACE", "sprintweave"),
)
VALID_MODES = frozenset({"openshift", "bringup", "manifests"})
_SA_DIR = Path("/var/run/secrets/kubernetes.io/serviceaccount")

_lock = threading.Lock()
_threads: dict[str, threading.Thread] = {}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_settings() -> dict[str, Any]:
    """PVC-backed defaults (survive restart, no image rebuild)."""
    defaults = {
        "cpat_deploy_mode": DEPLOY_MODE or "",
        "cpat_namespace": CPAT_NAMESPACE,
    }
    try:
        if SETTINGS_PATH.is_file():
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                defaults.update({k: data[k] for k in defaults if k in data})
    except (OSError, json.JSONDecodeError):
        pass
    return defaults


def save_settings(
    *,
    cpat_deploy_mode: str | None = None,
    cpat_namespace: str | None = None,
) -> dict[str, Any]:
    cur = load_settings()
    if cpat_deploy_mode is not None:
        mode = cpat_deploy_mode.strip().lower()
        if mode and mode not in VALID_MODES:
            raise ValueError(f"mode must be one of {sorted(VALID_MODES)}")
        cur["cpat_deploy_mode"] = mode
    if cpat_namespace is not None:
        ns = cpat_namespace.strip()
        if not ns or len(ns) > 63:
            raise ValueError("namespace must be 1–63 characters")
        cur["cpat_namespace"] = ns
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(cur, indent=2) + "\n", encoding="utf-8")
    return cur


def _job_dirs(job: dict, data_root: Path | None = None) -> tuple[Path, Path]:
    root = data_root or DATA_DIR
    job_dir = root / "jobs" / job["id"]
    out = Path(job.get("output_path") or (job_dir / "output"))
    ws_out = Path(job.get("workspace_path") or (job_dir / "workspace")) / "output"
    return out, ws_out


def find_cpat_root(job: dict, data_root: Path | None = None) -> Path | None:
    out, ws_out = _job_dirs(job, data_root)
    for base in (out, ws_out):
        cpat = base / "cpat"
        if (cpat / "Dockerfile").is_file():
            return cpat
    return None


def cpat_ready(job: dict, data_root: Path | None = None) -> dict[str, Any]:
    cpat = find_cpat_root(job, data_root)
    if cpat is None:
        return {"ready": False, "reason": "no cpat/Dockerfile in job artifacts"}
    checks = {
        "Dockerfile": (cpat / "Dockerfile").is_file(),
        "bringup.sh": (cpat / "bringup.sh").is_file(),
        "backend/app.py": (cpat / "backend" / "app.py").is_file(),
        "frontend/package.json": (cpat / "frontend" / "package.json").is_file(),
        "ansible/playbooks/main.yml": (
            cpat / "ansible" / "playbooks" / "main.yml"
        ).is_file(),
    }
    missing = [k for k, ok in checks.items() if not ok]
    return {
        "ready": not missing,
        "cpat_path": str(cpat),
        "checks": checks,
        "missing": missing,
        "reason": ("missing: " + ", ".join(missing)) if missing else "",
    }


def _oc_available() -> bool:
    return shutil.which("oc") is not None


def _runtime_available() -> str | None:
    if shutil.which("podman"):
        return "podman"
    if shutil.which("docker"):
        return "docker"
    return None


def resolve_mode(override: str | None = None) -> str:
    """Resolve deploy mode: explicit override → PVC settings → env → auto."""
    if override:
        mode = override.strip().lower()
        if mode not in VALID_MODES:
            raise ValueError(f"mode must be one of {sorted(VALID_MODES)}")
        return mode
    pref = (load_settings().get("cpat_deploy_mode") or "").strip().lower()
    if pref in VALID_MODES:
        return pref
    if DEPLOY_MODE in VALID_MODES:
        return DEPLOY_MODE
    if _oc_available():
        return "openshift"
    if _runtime_available():
        return "bringup"
    return "manifests"


def resolve_namespace(override: str | None = None) -> str:
    if override and override.strip():
        return override.strip()
    pref = (load_settings().get("cpat_namespace") or "").strip()
    return pref or CPAT_NAMESPACE


def _in_cluster_oc_args() -> list[str]:
    """Auth flags so ``oc`` works from the API pod without a kubeconfig file."""
    token = _SA_DIR / "token"
    ca = _SA_DIR / "ca.crt"
    if not token.is_file() or not ca.is_file():
        return []
    host = os.environ.get("KUBERNETES_SERVICE_HOST", "kubernetes.default.svc")
    port = os.environ.get("KUBERNETES_SERVICE_PORT", "443")
    return [
        "--token",
        token.read_text(encoding="utf-8").strip(),
        "--server",
        f"https://{host}:{port}",
        "--certificate-authority",
        str(ca),
    ]


def _set_deploy(job: dict, **fields: Any) -> None:
    dep = dict(job.get("cpat_deploy") or {})
    dep.update(fields)
    dep["updated_at"] = _utc()
    job["cpat_deploy"] = dep
    logs = list(job.get("logs") or [])
    msg = fields.get("log_line")
    if msg:
        logs.append(msg)
        job["logs"] = logs
        dep.pop("log_line", None)
        job["cpat_deploy"] = dep
    save_job(job)


def _write_manifests(cpat: Path, job_id: str, namespace: str) -> Path:
    deploy_dir = cpat.parent / "cpat-openshift"
    deploy_dir.mkdir(parents=True, exist_ok=True)
    name = f"cpat-{job_id}"[:63].rstrip("-")
    image = f"image-registry.openshift-image-registry.svc:5000/{namespace}/{name}:latest"
    yaml_text = f"""# Generated by SprintWeave for job {job_id}
# Apply after image build, or use deploy-cpat.sh
---
apiVersion: image.openshift.io/v1
kind: ImageStream
metadata:
  name: {name}
  namespace: {namespace}
---
apiVersion: build.openshift.io/v1
kind: BuildConfig
metadata:
  name: {name}
  namespace: {namespace}
spec:
  source:
    type: Binary
  strategy:
    type: Docker
    dockerStrategy:
      dockerfilePath: Dockerfile
  output:
    to:
      kind: ImageStreamTag
      name: {name}:latest
  runPolicy: Serial
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {name}
  namespace: {namespace}
  labels:
    app: {name}
    sprintweave-job: "{job_id}"
spec:
  replicas: 1
  selector:
    matchLabels:
      app: {name}
  template:
    metadata:
      labels:
        app: {name}
        sprintweave-job: "{job_id}"
    spec:
      containers:
        - name: cpat
          image: {image}
          imagePullPolicy: Always
          ports:
            - containerPort: 8080
              name: http
          volumeMounts:
            - name: cpat-data
              mountPath: /cpat-data
          resources:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: "1"
              memory: 1Gi
      volumes:
        - name: cpat-data
          emptyDir: {{}}
---
apiVersion: v1
kind: Service
metadata:
  name: {name}
  namespace: {namespace}
spec:
  selector:
    app: {name}
  ports:
    - name: http
      port: 8080
      targetPort: http
---
apiVersion: route.openshift.io/v1
kind: Route
metadata:
  name: {name}
  namespace: {namespace}
spec:
  to:
    kind: Service
    name: {name}
  port:
    targetPort: http
  tls:
    termination: edge
    insecureEdgeTerminationPolicy: Redirect
"""
    (deploy_dir / "cpat-app.yaml").write_text(yaml_text, encoding="utf-8")
    script = f"""#!/usr/bin/env bash
# SprintWeave helper — build + deploy CPAT for job {job_id}
set -euo pipefail
NS="{namespace}"
NAME="{name}"
CPAT_DIR="$(cd "$(dirname "$0")/../cpat" && pwd)"
oc project "$NS"
oc apply -f "$(dirname "$0")/cpat-app.yaml"
oc start-build "$NAME" --from-dir="$CPAT_DIR" --follow
oc rollout status "deployment/$NAME" -n "$NS"
echo "Route:"
oc get route "$NAME" -n "$NS" -o jsonpath='{{.spec.host}}{{"\\n"}}'
"""
    script_path = deploy_dir / "deploy-cpat.sh"
    script_path.write_text(script, encoding="utf-8")
    try:
        script_path.chmod(0o755)
    except OSError:
        pass
    return deploy_dir


def _run_oc(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["oc", *_in_cluster_oc_args(), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _sanitize_dockerfile(cpat: Path, log: Callable[[str], None]) -> None:
    """Fix common LLM-generated Dockerfile issues before binary build.

    1. COPY with shell redirects (``2>/dev/null || true``) — invalid Docker syntax.
       Remove ``2>/dev/null || true`` and skip COPY if source dir doesn't exist.
    2. COPY of non-existent directories — comment them out.
    3. OpenShift permissions — ensure all runtime-writable dirs are chmod'd
       so non-root random UIDs can write to them.
    """
    dockerfile = cpat / "Dockerfile"
    if not dockerfile.is_file():
        return
    import re as _re

    original = dockerfile.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)
    patched: list[str] = []
    fixes = 0
    has_chmod_fix = False

    # Collect all mkdir paths to ensure they get chmod'd
    mkdir_paths: list[str] = []

    for line in lines:
        stripped = line.strip()

        # Track mkdir -p paths
        if "mkdir" in stripped and "-p" in stripped:
            parts = stripped.split()
            for i, p in enumerate(parts):
                if p.startswith("/") and not p.startswith("/dev"):
                    mkdir_paths.append(p)

        # Fix: COPY ... 2>/dev/null || true  →  COPY ... (or skip if missing)
        if stripped.upper().startswith("COPY") and ("2>/dev/null" in stripped or "|| true" in stripped):
            clean = _re.sub(r"\s*2>/dev/null.*", "", stripped).rstrip()
            parts = clean.split()
            if len(parts) >= 3:
                src = parts[1].rstrip("/")
                src_path = cpat / src
                if not src_path.exists():
                    patched.append(f"# SKIPPED (source missing): {stripped}\n")
                    fixes += 1
                    continue
            patched.append(clean + "\n")
            fixes += 1
            continue

        # Fix: COPY of non-existent directory
        if stripped.upper().startswith("COPY") and not stripped.startswith("#"):
            parts = stripped.split()
            if len(parts) >= 3:
                src = parts[1].rstrip("/")
                src_path = cpat / src
                if not src_path.exists() and not src.startswith("--"):
                    patched.append(f"# SKIPPED (source missing): {stripped}\n")
                    fixes += 1
                    continue

        patched.append(line)

    # Nginx / schema / entrypoint sanitizers (LLM drift)
    _sanitize_nginx_configs(cpat, log)
    _sanitize_schema_shim(cpat, log)

    # --- Fix EXPOSE 80 → 8080 and HEALTHCHECK port ---
    final_patched: list[str] = []
    for line in patched:
        s = line.strip()
        # EXPOSE 80 → EXPOSE 8080
        if s == "EXPOSE 80":
            final_patched.append("EXPOSE 8080\n")
            fixes += 1
        # HEALTHCHECK curl hitting port 80 (default) → 8080
        elif "curl" in line and "127.0.0.1/" in line and "8080" not in line:
            final_patched.append(line.replace("http://127.0.0.1/", "http://127.0.0.1:8080/"))
            fixes += 1
        else:
            final_patched.append(line)
    patched = final_patched
    # --- OpenShift permission fix ---
    # Append chmod for all writable dirs + common patterns before the last
    # CMD/ENTRYPOINT so the random UID can write at runtime.
    writable_dirs = set(mkdir_paths)
    # Common CPAT writable paths
    for d in ["/cpat-data", "/app/data", "/tmp", "/app/uploads", "/app/instance"]:
        writable_dirs.add(d)

    chmod_line = (
        "RUN chmod -R 777 " + " ".join(sorted(writable_dirs))
        + " 2>/dev/null || true\n"
    )

    # Insert before the last CMD or ENTRYPOINT
    insert_idx = len(patched)
    for i in range(len(patched) - 1, -1, -1):
        s = patched[i].strip().upper()
        if s.startswith("CMD") or s.startswith("ENTRYPOINT"):
            insert_idx = i
            break

    # OpenShift: nginx needs writable dirs under /var/lib/nginx + /run
    nginx_chmod = (
        "RUN mkdir -p /var/lib/nginx/body /var/lib/nginx/proxy /var/lib/nginx/fastcgi "
        "/var/lib/nginx/uwsgi /var/lib/nginx/scgi /var/log/nginx /run "
        "&& chmod -R 777 /var/lib/nginx /var/log/nginx /run /tmp "
        "/cpat-data /app/data /app/instance /app/uploads 2>/dev/null || true\n"
    )
    if not any("chmod -R 777" in l and "/var/lib/nginx" in l for l in patched):
        patched.insert(insert_idx, nginx_chmod)
        has_chmod_fix = True
        fixes += 1
    elif not any("chmod" in l and "777" in l for l in patched):
        patched.insert(insert_idx, chmod_line)
        has_chmod_fix = True
        fixes += 1

    if fixes:
        dockerfile.write_text("".join(patched), encoding="utf-8")
        msgs = []
        if has_chmod_fix:
            msgs.append("OpenShift permission fix")
        msgs.append(f"{fixes} total fix(es)")
        log(f"[cpat-deploy] patched Dockerfile ({', '.join(msgs)})")

    _sanitize_entrypoint(cpat, log)


_SCHEMA_SHIM = '''\
"""Backend shim — load canonical schema by file path (avoids circular import).

Re-exports ALL public symbols from ansible/module_utils/rhoso_ciq_schema.py
plus common LLM alias names (RHOSO_CIQ_PARAMS, RHOSO_CIQ_SCHEMA, …).
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_here = Path(__file__).resolve().parent
_candidates = [
    _here / "ansible" / "module_utils" / "rhoso_ciq_schema.py",
    _here.parent / "ansible" / "module_utils" / "rhoso_ciq_schema.py",
]
_CANONICAL = next((p for p in _candidates if p.is_file()), None)
if _CANONICAL is None:
    raise ImportError(
        "canonical rhoso_ciq_schema.py not found; tried: "
        + ", ".join(str(p) for p in _candidates)
    )
_spec = importlib.util.spec_from_file_location("_rhoso_ciq_schema_canonical", _CANONICAL)
_canonical = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_canonical)

# Re-export every public name from the canonical module
for _name in dir(_canonical):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_canonical, _name)

# Parameter-table aliases (LLM / backend naming drift)
_params = getattr(
    _canonical,
    "RHOSO_PARAMETER_SCHEMA",
    getattr(
        _canonical,
        "RHOSO_CIQ_SCHEMA",
        getattr(_canonical, "RHOSO_CIQ_PARAMS", getattr(_canonical, "RHOSO_CIQ_PARAMETERS", {})),
    ),
)
RHOSO_PARAMETER_SCHEMA = _params
RHOSO_CIQ_SCHEMA = getattr(_canonical, "RHOSO_CIQ_SCHEMA", _params)
RHOSO_CIQ_PARAMS = getattr(_canonical, "RHOSO_CIQ_PARAMS", _params)
RHOSO_CIQ_PARAMETERS = getattr(_canonical, "RHOSO_CIQ_PARAMETERS", _params)

# Network / node column aliases
_net = getattr(
    _canonical,
    "RHOSO_NETWORK_FIELD_SCHEMA",
    getattr(_canonical, "RHOSO_NETWORK_COLUMNS", []),
)
_node = getattr(
    _canonical,
    "RHOSO_NODE_FIELD_SCHEMA",
    getattr(_canonical, "RHOSO_NODE_COLUMNS", []),
)
RHOSO_NETWORK_FIELD_SCHEMA = _net
RHOSO_NETWORK_COLUMNS = getattr(_canonical, "RHOSO_NETWORK_COLUMNS", _net)
RHOSO_NODE_FIELD_SCHEMA = _node
RHOSO_NODE_COLUMNS = getattr(_canonical, "RHOSO_NODE_COLUMNS", _node)

SCHEMA_VERSION = getattr(_canonical, "SCHEMA_VERSION", "1.4")
RHOSO_SUPPLEMENTAL_PARAM_TABLES = getattr(
    _canonical, "RHOSO_SUPPLEMENTAL_PARAM_TABLES", []
)

__all__ = [n for n in globals() if not n.startswith("_") and n[0].isupper()]
'''


def _sanitize_schema_shim(cpat: Path, log: Callable[[str], None]) -> None:
    """Always rewrite backend schema shim — LLM naming/import drift is fatal at runtime."""
    shim = cpat / "backend" / "rhoso_ciq_schema.py"
    canonical = cpat / "ansible" / "module_utils" / "rhoso_ciq_schema.py"
    if not canonical.is_file():
        return
    shim.parent.mkdir(parents=True, exist_ok=True)
    shim.write_text(_SCHEMA_SHIM, encoding="utf-8")
    log("[cpat-deploy] rewrote backend/rhoso_ciq_schema.py (safe shim + symbol aliases)")


def _sanitize_nginx_configs(cpat: Path, log: Callable[[str], None]) -> None:
    """Force listen 8080 + /tmp temp paths for OpenShift non-root nginx."""
    import re as _re

    conf_dirs = [
        cpat / "frontend" / "nginx",
        cpat / "nginx",
        cpat / "docker" / "nginx",
    ]
    for conf_dir in conf_dirs:
        if not conf_dir.is_dir():
            continue
        for conf in conf_dir.rglob("*.conf"):
            text = conf.read_text(encoding="utf-8", errors="replace")
            original = text
            text = _re.sub(r"listen\s+80\s*;", "listen 8080;", text)
            if "client_body_temp_path" not in text and "server {" in text:
                text = text.replace(
                    "server {",
                    "server {\n"
                    "    client_body_temp_path /tmp/nginx_client_body;\n"
                    "    proxy_temp_path       /tmp/nginx_proxy;\n"
                    "    fastcgi_temp_path     /tmp/nginx_fastcgi;\n"
                    "    uwsgi_temp_path       /tmp/nginx_uwsgi;\n"
                    "    scgi_temp_path        /tmp/nginx_scgi;\n",
                    1,
                )
            if text != original:
                conf.write_text(text, encoding="utf-8")
                log(f"[cpat-deploy] patched nginx config {conf.name} (8080 + /tmp temps)")


def _sanitize_entrypoint(cpat: Path, log: Callable[[str], None]) -> None:
    """Make entrypoint OpenShift-safe: no fatal chmod on mounts; nginx /tmp dirs."""
    entry = cpat / "docker" / "entrypoint.sh"
    if not entry.is_file():
        for alt in (cpat / "entrypoint.sh", cpat / "docker-entrypoint.sh"):
            if alt.is_file():
                entry = alt
                break
        else:
            return

    text = entry.read_text(encoding="utf-8")
    original = text
    import re as _re

    # Remove or soften chmod on data-dir mount root (emptyDir rejects chmod)
    text = _re.sub(
        r'^[ \t]*chmod\s+\d+\s+["\']?\$\{?CPAT_DATA_DIR\}?[^;\n]*$',
        lambda m: (
            m.group(0)
            if "|| true" in m.group(0)
            else m.group(0).rstrip() + " 2>/dev/null || true\n"
        ),
        text,
        flags=_re.MULTILINE,
    )
    text = _re.sub(
        r'^[ \t]*chmod\s+\d+\s+["\']?/cpat-data[^;\n]*$',
        lambda m: (
            m.group(0)
            if "|| true" in m.group(0)
            else m.group(0).rstrip() + " 2>/dev/null || true\n"
        ),
        text,
        flags=_re.MULTILINE,
    )

    if "nginx_client_body" not in text:
        block = (
            "\n# OpenShift: non-root cannot write /var/lib/nginx — use /tmp\n"
            "mkdir -p /tmp/nginx_client_body /tmp/nginx_proxy /tmp/nginx_fastcgi "
            "/tmp/nginx_uwsgi /tmp/nginx_scgi /tmp/nginx_logs /tmp/nginx_run\n"
            "sed -i 's|^pid .*|pid /tmp/nginx.pid;|' /etc/nginx/nginx.conf 2>/dev/null || true\n"
            "sed -i 's|error_log .*|error_log /tmp/nginx_logs/error.log warn;|' /etc/nginx/nginx.conf 2>/dev/null || true\n"
            "sed -i 's|access_log .*|access_log /tmp/nginx_logs/access.log;|' /etc/nginx/nginx.conf 2>/dev/null || true\n"
        )
        # Insert before nginx start (or append before end)
        m = _re.search(r'^.*[Nn]ginx.*$', text, flags=_re.MULTILINE)
        if m:
            text = text[: m.start()] + block + text[m.start() :]
        else:
            text = text.rstrip() + block + "\n"

    text = text.replace("Starting Nginx on port 80", "Starting Nginx on port 8080")

    if text != original:
        entry.write_text(text, encoding="utf-8")
        log("[cpat-deploy] patched entrypoint.sh (OpenShift-safe chmod + nginx /tmp)")


def _validate_cpat_package(cpat: Path, log: Callable[[str], None]) -> list[str]:
    """Pre-build validation gate — returns error list (empty = pass).

    Runs AFTER the sanitizer so we're checking the final state.
    Catches issues that would cause build failures or runtime crashes.
    """
    import ast as _ast

    errors: list[str] = []
    be = cpat / "backend"
    dockerfile = cpat / "Dockerfile"

    # 1. All Python files must parse
    if be.is_dir():
        for py in sorted(be.glob("*.py")):
            text = py.read_text(encoding="utf-8", errors="replace").rstrip()
            if not text:
                continue
            try:
                _ast.parse(text)
            except SyntaxError as exc:
                errors.append(f"SyntaxError in backend/{py.name}: {exc}")

    # 2. Schema shim must not use circular-import pattern
    shim = be / "rhoso_ciq_schema.py" if be.is_dir() else None
    if shim and shim.is_file():
        st = shim.read_text(encoding="utf-8", errors="replace")
        if 'import_module("rhoso_ciq_schema")' in st or "import_module('rhoso_ciq_schema')" in st:
            errors.append(
                "backend/rhoso_ciq_schema.py circular import "
                "(import_module of same name)"
            )

    # 3. Import/export match — names imported in ciq_parser/app must exist in shim
    if shim and shim.is_file():
        import re as _re

        shim_text = shim.read_text(encoding="utf-8", errors="replace")
        for consumer_name in ("ciq_parser.py", "app.py"):
            consumer = be / consumer_name
            if not consumer.is_file():
                continue
            ct = consumer.read_text(encoding="utf-8", errors="replace")
            for m in _re.finditer(
                r"from\s+rhoso_ciq_schema\s+import\s+\(([^)]+)\)", ct, _re.DOTALL
            ):
                for sym in _re.findall(r"\b([A-Z][A-Z_0-9]+)\b", m.group(1)):
                    if sym not in shim_text:
                        errors.append(
                            f"backend/{consumer_name} imports '{sym}' "
                            f"not defined in rhoso_ciq_schema shim"
                        )

    # 4. Dockerfile must have ENTRYPOINT/CMD and no bad COPY lines
    if dockerfile.is_file():
        dt = dockerfile.read_text(encoding="utf-8", errors="replace")
        if "ENTRYPOINT" not in dt and "CMD" not in dt:
            errors.append("Dockerfile has no ENTRYPOINT or CMD")
        for line in dt.splitlines():
            s = line.strip()
            if s.upper().startswith("COPY") and ("2>/dev/null" in s or "|| true" in s):
                errors.append(f"Dockerfile bad COPY: {s[:80]}")
    else:
        errors.append("No Dockerfile found")

    # 5. nginx config must exist and have listen directive
    nginx_found = False
    for d in (cpat / "frontend" / "nginx", cpat / "nginx", cpat / "docker" / "nginx"):
        if d.is_dir():
            for conf in d.rglob("*.conf"):
                nginx_found = True
    if not nginx_found:
        errors.append("No nginx config found")

    # 6. Frontend JSX truncation check
    fe_src = cpat / "frontend" / "src"
    if fe_src.is_dir():
        for ext in ("*.jsx", "*.js"):
            for f in fe_src.rglob(ext):
                text = f.read_text(encoding="utf-8", errors="replace").rstrip()
                if not text:
                    continue
                opens = text.count("{") + text.count("(")
                closes = text.count("}") + text.count(")")
                if abs(opens - closes) > 5:
                    errors.append(
                        f"Truncated frontend/{f.relative_to(fe_src)}: "
                        f"brace imbalance {opens}/{closes}"
                    )

    # Log results
    if errors:
        log(f"[cpat-validate] FAILED — {len(errors)} issue(s):")
        for e in errors[:10]:
            log(f"[cpat-validate]   {e}")
    else:
        log("[cpat-validate] PASSED — package looks good")

    return errors


def _deploy_openshift(
    job: dict,
    cpat: Path,
    log: Callable[[str], None],
    *,
    namespace: str,
) -> dict[str, Any]:
    ns = namespace
    job_id = job["id"]
    name = f"cpat-{job_id}"[:63].rstrip("-")
    deploy_dir = _write_manifests(cpat, job_id, ns)
    log(f"[cpat-deploy] wrote manifests → {deploy_dir} (ns={ns})")

    # Patch LLM-generated Dockerfile before build
    _sanitize_dockerfile(cpat, log)

    # Pre-build validation gate — block doomed builds
    gate_errors = _validate_cpat_package(cpat, log)
    if gate_errors:
        error_msg = "; ".join(gate_errors[:5])
        raise RuntimeError(
            f"Pre-build validation failed ({len(gate_errors)} issue(s)): {error_msg}"
        )

    if not _oc_available():
        return {
            "status": "prepared",
            "mode": "manifests",
            "message": (
                "oc not in PATH — manifests written; run deploy-cpat.sh from bastion, "
                "or rebuild the API image with the OpenShift client."
            ),
            "manifests_dir": str(deploy_dir),
            "app_name": name,
            "namespace": ns,
        }

    apply = _run_oc(["apply", "-f", str(deploy_dir / "cpat-app.yaml"), "-n", ns])
    log(f"[cpat-deploy] oc apply exit={apply.returncode}")
    if apply.stdout:
        log(apply.stdout.strip()[:500])
    if apply.returncode != 0:
        err = (apply.stderr or apply.stdout or "oc apply failed")[:800]
        raise RuntimeError(err)

    log(f"[cpat-deploy] starting binary build {name} (this can take several minutes)…")
    build = _run_oc(
        ["start-build", name, "--from-dir", str(cpat), "--follow", "-n", ns],
        timeout=1800,
    )
    if build.stdout:
        for line in build.stdout.splitlines()[-20:]:
            log(f"[cpat-build] {line}")
    if build.returncode != 0:
        err = (build.stderr or build.stdout or "build failed")[:800]
        raise RuntimeError(err)

    _run_oc(["rollout", "status", f"deployment/{name}", "-n", ns], timeout=600)
    route = _run_oc(
        ["get", "route", name, "-n", ns, "-o", "jsonpath={.spec.host}"],
        timeout=60,
    )
    host = (route.stdout or "").strip()
    url = f"https://{host}" if host else ""
    log(f"[cpat-deploy] ready {url or name}")
    return {
        "status": "running",
        "mode": "openshift",
        "message": "CPAT built and deployed on OpenShift",
        "manifests_dir": str(deploy_dir),
        "app_name": name,
        "namespace": ns,
        "url": url,
        "host": host,
    }


def _deploy_bringup(job: dict, cpat: Path, log: Callable[[str], None]) -> dict[str, Any]:
    runtime = _runtime_available()
    if not runtime:
        raise RuntimeError("neither podman nor docker found for bringup mode")
    bringup = cpat / "bringup.sh"
    if not bringup.is_file():
        raise RuntimeError("bringup.sh missing")
    try:
        bringup.chmod(0o755)
    except OSError:
        pass
    env = os.environ.copy()
    env["CPAT_PORT"] = CPAT_HOST_PORT
    env["CPAT_CONTAINER"] = f"cpat-{job['id']}"
    log(f"[cpat-deploy] {runtime} bringup restart (port {CPAT_HOST_PORT})…")
    proc = subprocess.run(
        ["bash", str(bringup), "restart"],
        cwd=str(cpat),
        capture_output=True,
        text=True,
        timeout=1800,
        env=env,
        check=False,
    )
    if proc.stdout:
        for line in proc.stdout.splitlines()[-30:]:
            log(f"[bringup] {line}")
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "bringup failed")[:800])
    url = f"http://localhost:{CPAT_HOST_PORT}"
    return {
        "status": "running",
        "mode": "bringup",
        "message": f"CPAT container started via {runtime}",
        "url": url,
        "port": CPAT_HOST_PORT,
        "runtime": runtime,
    }


def get_deploy_status(job: dict) -> dict[str, Any]:
    ready = cpat_ready(job)
    dep = dict(job.get("cpat_deploy") or {})
    settings = load_settings()
    return {
        "job_id": job["id"],
        "mode": resolve_mode(),
        "namespace": resolve_namespace(),
        "settings": settings,
        "cpat": ready,
        "deploy": dep,
        "oc_available": _oc_available(),
        "in_cluster": (_SA_DIR / "token").is_file(),
        "runtime": _runtime_available(),
        "modes": sorted(VALID_MODES),
    }


def start_deploy(
    job: dict,
    data_root: Path | None = None,
    *,
    mode: str | None = None,
    namespace: str | None = None,
    save_as_default: bool = False,
) -> dict[str, Any]:
    """Queue a background deploy. Returns current deploy status dict."""
    ready = cpat_ready(job, data_root)
    if not ready.get("ready"):
        raise ValueError(ready.get("reason") or "CPAT artifacts not ready")

    resolved_mode = resolve_mode(mode)
    resolved_ns = resolve_namespace(namespace)
    if save_as_default:
        save_settings(
            cpat_deploy_mode=resolved_mode,
            cpat_namespace=resolved_ns,
        )

    with _lock:
        t = _threads.get(job["id"])
        if t is not None and t.is_alive():
            raise ValueError("CPAT deploy already in progress for this job")
        cur = (job.get("cpat_deploy") or {}).get("status")
        if cur == "deploying":
            raise ValueError("CPAT deploy already in progress for this job")

        _set_deploy(
            job,
            status="deploying",
            mode=resolved_mode,
            namespace=resolved_ns,
            started_at=_utc(),
            finished_at="",
            url="",
            error="",
            message=f"Deploy starting ({resolved_mode} → {resolved_ns})",
            log_line=(
                f"[cpat-deploy] queued mode={resolved_mode} namespace={resolved_ns}"
            ),
        )

        def _worker() -> None:
            def log(line: str) -> None:
                _set_deploy(job, log_line=line)

            try:
                cpat = find_cpat_root(job, data_root)
                assert cpat is not None
                if resolved_mode == "bringup":
                    result = _deploy_bringup(job, cpat, log)
                elif resolved_mode == "openshift":
                    result = _deploy_openshift(
                        job, cpat, log, namespace=resolved_ns
                    )
                else:
                    deploy_dir = _write_manifests(cpat, job["id"], resolved_ns)
                    log(f"[cpat-deploy] manifests only → {deploy_dir}")
                    result = {
                        "status": "prepared",
                        "mode": "manifests",
                        "message": (
                            "Wrote OpenShift manifests + deploy-cpat.sh. "
                            "Run that script with oc, or choose "
                            "'This OpenShift cluster' with oc + SA RBAC."
                        ),
                        "manifests_dir": str(deploy_dir),
                        "app_name": f"cpat-{job['id']}"[:63].rstrip("-"),
                        "namespace": resolved_ns,
                    }
                _set_deploy(
                    job,
                    status=result.get("status", "running"),
                    mode=result.get("mode", resolved_mode),
                    message=result.get("message", ""),
                    url=result.get("url", ""),
                    host=result.get("host", ""),
                    manifests_dir=result.get("manifests_dir", ""),
                    app_name=result.get("app_name", ""),
                    namespace=result.get("namespace", resolved_ns),
                    finished_at=_utc(),
                    error="",
                )
            except Exception as exc:
                _set_deploy(
                    job,
                    status="failed",
                    error=str(exc)[:1000],
                    message="CPAT deploy failed",
                    finished_at=_utc(),
                    log_line=f"[cpat-deploy] FAILED: {exc}",
                )
            finally:
                with _lock:
                    _threads.pop(job["id"], None)

        thread = threading.Thread(
            target=_worker, name=f"cpat-deploy-{job['id']}", daemon=True
        )
        _threads[job["id"]] = thread
        thread.start()

    # brief yield so status is saved
    time.sleep(0.05)
    return get_deploy_status(job)
