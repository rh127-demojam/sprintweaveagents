# CPAT Container Golden Templates

These are **pre-tested infrastructure files** that are seeded into the workspace
**before** the LLM runs. The LLM never generates these — it only generates the
application-specific code (routes, components, playbooks, schemas).

## Files

| File | Purpose | OpenShift-Safe |
|------|---------|---------------|
| `Dockerfile` | Multi-stage Node→Python→Nginx, OCP binary bundling | ✅ Port 8080, non-root, chmod 777 |
| `docker/entrypoint.sh` | Gunicorn + Nginx startup | ✅ No chmod on mount root, /tmp nginx dirs |
| `.dockerignore` | Excludes node_modules, __pycache__, .git | ✅ |
| `bringup.sh` | Podman/Docker lifecycle (build/start/stop/export) | ✅ Port 8080 default |

## Why Golden Templates?

These files are **identical for every CPAT deployment**. LLM-generating them wastes
tokens and introduces bugs:

- `chmod /cpat-data` under `set -e` → container crash on OpenShift
- `COPY 2>/dev/null` → invalid Docker syntax
- `listen 80` → blocked by OpenShift for non-root
- `importlib.import_module("rhoso_ciq_schema")` → circular import

Golden templates eliminate these **entirely**. The LLM budget goes to application
logic where it actually matters.

## Used By

`cpat-main/context/pipelines.yaml` references these via `golden_templates`:

```yaml
golden_templates:
  - { src: "context/templates/nrho-cpat-container/Dockerfile",         dest: "output/cpat/Dockerfile" }
  - { src: "context/templates/nrho-cpat-container/docker/entrypoint.sh", dest: "output/cpat/docker/entrypoint.sh" }
  - { src: "context/templates/nrho-cpat-container/.dockerignore",      dest: "output/cpat/.dockerignore" }
```

`worker.py` copies them into the workspace before the Docker sub-stage runs.
The LLM sees them as existing files and only generates `USAGE.md` and `binaries/README.md`.
