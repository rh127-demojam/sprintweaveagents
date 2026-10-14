# CPAT — Cloud Platform Automation Tool

Web-based automation platform for deploying **Red Hat cloud infrastructure** on bare metal.
CPAT drives the entire lifecycle — from CIQ (Customer Input Questionnaire) data entry
through manifest generation, review, and automated deployment.

**Supported Products:**

| Product | Versions | Description |
|---------|----------|-------------|
| **OCP** (OpenShift Container Platform) | 4.17, 4.18, 4.19, 4.20 | Bare-metal Kubernetes cluster installation |
| **RHOSO** (Red Hat OpenStack Services on OpenShift) | 18.0 | OpenStack control & data plane on a running OCP cluster |

> **OCP is the platform layer — install it first.**
> RHOSO is deployed on top of a running OCP cluster.

**Version:** `YY.M.W` calendar versioning (e.g. `25.10.1`)

| Documentation | Description |
|---------------|-------------|
| [README-OCP.md](README-OCP.md) | OCP installation — tasks, CIQ schema, templates, API |
| [README-RHOSO.md](README-RHOSO.md) | RHOSO deployment — tasks, CIQ schema, templates, API |
| [USAGE.md](USAGE.md) | Complete combined reference (workflows, troubleshooting, commands) |

---

## Architecture

CPAT runs as a single container (Podman/Docker) on a bastion host with network
access to the target infrastructure.

```
+-------------------------------------------------------------------+
|  Bastion / Jump Host                                              |
|                                                                   |
|  +-------------------------------------------------------------+ |
|  |  CPAT Container (Podman / Docker)                            | |
|  |                                                              | |
|  |  +----------------+  +----------------+  +----------------+  | |
|  |  |  React UI      |  |  Flask API     |  |  Ansible       |  | |
|  |  |  (Nginx :80)   |->|  (Gunicorn     |->|  Playbooks     |  | |
|  |  |  SPA + routes  |  |   :5000)       |  |  2 roles       |  | |
|  |  |                |  |  25+ routes    |  |  (ocp + rhoso)  |  | |
|  |  +----------------+  +----------------+  +-------+--------+  | |
|  |                                                  |           | |
|  +--------------------------------------------------|----------+  |
|                                                     |             |
+-----------------------------------------------------|-------------+
                                                      |
                    +--------------------+    +--------------------+
                    |  OCP Cluster API   |    |  Bare Metal Nodes  |
                    |  (oc / kubectl)    |    |  (BMC / SSH)       |
                    +--------------------+    +--------------------+
```

### Communication Flow

| From | To | Protocol | Purpose |
|------|----|----------|---------|
| Browser | CPAT (Nginx :80) | HTTP | Web UI |
| React UI | Flask API (:5000) | HTTP (proxied) | API calls, NDJSON log streaming |
| Flask API | Ansible | subprocess | Triggers playbook runs |
| Ansible (OCP) | Bare metal nodes | BMC / SSH | Node provisioning, openshift-install |
| Ansible (RHOSO) | OCP API | HTTPS (oc CLI) | Operators, CRs, secrets |
| Ansible (RHOSO) | EDPM nodes | SSH | Data plane configuration |

---

## Application Structure

```
cpat/
├── ansible/
│   └── playbooks/
│       ├── ocp_install.yml                     # OCP playbook entry point
│       ├── main.yml                            # RHOSO playbook entry point
│       └── roles/
│           ├── ocp/                            # OCP installation role
│           │   ├── tasks/         (27 files)   #   11 task groups
│           │   ├── templates/     (12 files)   #   Jinja2 manifests
│           │   ├── defaults/main.yml           #   ~170 default variables
│           │   └── vars/main.yml               #   Derived flags & paths
│           ├── rhoso/                          # RHOSO deployment role
│           │   ├── tasks/         (24 files)   #   18 deployment phases
│           │   ├── templates/     (15 files)   #   Jinja2 manifests
│           │   └── defaults/main.yml           #   ~210 default variables
│           └── register/tasks/                 # Registration tasks
├── backend/
│   ├── app.py                                  # Flask API (25+ routes, NDJSON streaming)
│   ├── models.py                               # SQLAlchemy models (Cluster, Execution)
│   ├── ciq_parser.py                           # Unified CIQ Excel parser (RHOSO + OCP auto-detect)
│   ├── rhoso_ciq_schema.py                     # RHOSO CIQ validation schema (types + regex)
│   ├── ocp_ciq_schema.py                       # OCP CIQ validation schema (types + regex, COPY from ciq-generators/)
│   ├── ansible_runner.py                       # Ansible process runner + log streaming
│   ├── version.py                              # YY.M.W calendar versioning
│   └── requirements.txt                        # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/                         # React components (OCP + RHOSO)
│   │   ├── App.jsx, api.js, main.jsx
│   │   ├── rhosoInputFiles.js                  # RHOSO input file definitions
│   │   └── ocpInputFiles.js                    # OCP input file definitions
│   ├── nginx/default.conf                      # Nginx reverse proxy config
│   └── package.json, vite.config.js
├── Dockerfile                                  # Multi-stage build (auto-downloads OCP binaries)
├── binaries/                                   # Pre-placed OCP binaries (optional — Dockerfile downloads if empty)
├── bringup.sh                                  # Podman build, run, export
├── USAGE.md                                    # Complete product documentation
├── README.md                                   # This file (common)
├── README-OCP.md                               # OCP-specific documentation
└── README-RHOSO.md                             # RHOSO-specific documentation
```

---

## Install Workflow (Both Products)

Both OCP and RHOSO follow the same **Generate → Review → Deploy** pattern:

### 1. Register Cluster

Upload a CIQ Excel workbook (`.xlsx`) through the Web UI or API. The CIQ
contains all site-specific parameters — network CIDRs, node IPs, storage
config, credentials paths, etc.

- **OCP CIQ:** `Type = OCP` in `ocp_details` table → 14 param + 4 row tables, 177 fields
- **RHOSO CIQ:** `Type = RHOSO` in `rhoso_details` table → 16 param + 2 row tables, ~210 params

Both CIQ types are parsed by the unified `ciq_parser.py` which auto-detects cluster
type from Excel table names. A single workbook can contain both RHOSO and OCP registrations.

CIQ workbook templates: `output/ciq-workbooks/ocp/` and `output/ciq-workbooks/rhoso/`

### 2. Generate Manifests for Review

Renders all Jinja2 templates using CIQ data into `artifacts/<cluster>/`
**without applying anything**. Manifests can be reviewed in the UI or
downloaded as a ZIP.

### 3. Deploy

Select deployment tasks from the UI. Tasks execute Ansible playbooks
that apply the generated manifests to the target infrastructure.
Logs stream in real time via NDJSON.

---

## Running CPAT

### Container deployment (recommended)

```bash
chmod +x bringup.sh
./bringup.sh build     # Build image (auto-downloads OCP 4.20 binaries)
./bringup.sh start     # Start container on port 8080
```

Other commands:

```bash
./bringup.sh stop      # Stop and remove container
./bringup.sh restart   # Stop, rebuild, start
./bringup.sh logs      # Tail container logs
./bringup.sh shell     # Open shell inside running container
./bringup.sh export    # Save image as .tar for disconnected transfer
./bringup.sh help      # Show all options
```

Open [http://localhost:8080](http://localhost:8080)

### Disconnected bastion deployment

```bash
# On connected machine — build and export
./bringup.sh build
./bringup.sh export                    # → cpat-25.10.1.tar

# Transfer to bastion
scp -P 2222 cpat-25.10.1.tar pull-secret.json cloud-user@<bastion>:~/

# On bastion — load and start
podman load -i cpat-25.10.1.tar
./bringup.sh start
```

### Local development (without containers)

**Backend:**
```bash
cd backend
python -m venv venv && venv\Scripts\activate    # Windows
pip install -r requirements.txt
python app.py                                   # Flask on :5000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev                                     # Vite on :5173
```

### Default credentials

| Username | Password |
|----------|----------|
| admin | admin |

---

## Versioning (YY.M.W)

Calendar versioning for image tags, API, and environment:

| Part | Meaning |
|------|---------|
| `YY` | Two-digit year |
| `M` | Month (no leading zero for 1–9) |
| `W` | Week of month (days 1–7 → 1, 8–14 → 2, etc.) |

Override: set environment variable `CPAT_VERSION`

---

## Data Storage

All runtime state is stored at `data/` (created dynamically by `paths.py`):

| Content | Local path | Container path |
|---------|------------|----------------|
| SQLite DB | `data/cpat.db` | `/cpat-data/cpat.db` |
| CIQ uploads | `data/uploads/` | `/cpat-data/uploads/` |
| Input secrets | `data/secrets/<cluster-id>/` | `/cpat-data/secrets/<cluster-id>/` |
| Registration logs | `data/logs/registrations/` | `/cpat-data/logs/registrations/` |
| Installation logs | `data/logs/installations/` | `/cpat-data/logs/installations/` |
| Generated manifests | `data/artifacts/<cluster>/` | `/cpat-data/artifacts/<cluster>/` |

Data persists in the `cpat-data` Podman volume, mounted at `/cpat-data` inside the container.
Data survives container restarts but is lost if the volume is removed.

---

## API Reference (Common Endpoints)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/auth/login` | Authentication |
| `POST` | `/api/auth/logout` | Logout |
| `GET` | `/api/auth/me` | Current user info |
| `GET` | `/api/dashboard` | Dashboard summary (RHOSO + OCP counts) |
| `GET` | `/api/clusters` | List clusters (`?type=rhoso\|ocp`) |
| `GET` | `/api/clusters/<id>` | Get cluster details |
| `DELETE` | `/api/clusters/<id>` | Delete cluster and all artifacts |
| `GET` | `/api/clusters/<id>/artifacts` | List generated manifests |
| `GET` | `/api/clusters/<id>/artifacts/<file>` | View/download single manifest |
| `GET` | `/api/clusters/<id>/artifacts/download-all` | Download all manifests as ZIP |
| `GET/POST` | `/api/clusters/<id>/input-files` | Manage input file uploads |
| `GET` | `/api/version` | CPAT version + `supported_types: ["rhoso","ocp"]` |

For product-specific API endpoints, see [README-OCP.md](README-OCP.md) and [README-RHOSO.md](README-RHOSO.md).

---

*CPAT v25.10.1 — OCP 4.17–4.20 + RHOSO 18.0*
