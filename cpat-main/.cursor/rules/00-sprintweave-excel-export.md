---
alwaysApply: true
---
# SprintWeave Excel Export — Real .xlsx Generation

## When This Activates

This rule applies to ALL artifact generation. After producing markdown output, ALWAYS generate a real Excel file.

## Excel Generation Flow

After every artifact generation, perform these steps automatically:

### Step 1: Write JSON Data File

Write the structured artifact data to `sprintweave-output/<document>-<timestamp>-data.json` using this schema:

```json
{
  "document": "<source document name>",
  "generated_at": "<ISO timestamp>",
  "agent": "<agent name that generated this>",
  "agent_map": {
    "<Sheet Name>": {
      "agent": "<agent that produced this sheet>",
      "purpose": "<one-line description of what this sheet contains>"
    }
  },
  "sheets": {
    "<Sheet Name>": {
      "headers": ["Column1", "Column2", "..."],
      "rows": [
        ["value1", "value2", "..."],
        ["value1", "value2", "..."]
      ]
    }
  }
}
```

The `agent_map` is optional — the generator has built-in defaults for all standard sheets. Include it when running custom agents or when you want to override the default attribution.

### Step 2: Run the Generator

Execute:
```
python "tools/excel-generator.py" "sprintweave-output/<document>-<timestamp>-data.json"
```

If `openpyxl` is not installed, run `pip install openpyxl` first.

### Step 3: Confirm to User

Report the file path:
```
Excel exported: sprintweave-output/<document>-<timestamp>-artifacts.xlsx
  Sheets: N | Total rows: M
```

## Sheet Schemas Per Agent

Each agent maps its artifacts to specific sheet structures:

### Requirements Analyst
```json
{
  "sheets": {
    "User Stories": {
      "headers": ["ID", "Phase", "Title", "Persona", "Action", "Benefit", "Acceptance Criteria", "Priority", "SP", "T-Shirt", "Epic", "Source", "Verification Story"],
      "rows": [["PRE-01", "Prerequisites", "Validate DNS records", "Deployment Engineer", "validate all DNS records", "confirm DNS readiness before deployment", "1. All FQDNs resolve via nslookup\n2. Reverse PTR records resolve\n3. VIP DNS entries verified", "P1-Critical", "3", "S", "Pre-Deployment Validation", "[Doc Title]: § 2.1 - Deployment Prerequisites", "VAL-01"]]
    },
    "NFRs": {
      "headers": ["NFR#", "Category", "Requirement", "Priority", "Target Metric", "Verification", "Source"],
      "rows": [["NFR-1", "Performance", "...", "High", "...", "...", "[Doc Title]: § X.Y"]]
    },
    "Epic Summary": {
      "headers": ["Epic", "Title", "Stories", "Total SP"],
      "rows": [["EPIC-1", "Foundation & Platform Setup", "12", "39"]]
    }
  }
}
```

**Notes:**
- **Acceptance Criteria** is now a single column in the User Stories sheet — each cell contains a numbered list (`1. condition\n2. condition\n3. condition`). No separate AC sheet.
- **ID** uses phase-prefixed format for MoP/deployment docs (e.g., `PRE-01`, `SETUP-01`, `CFG-01`, `VAL-01` — derived from the document's own section titles) and standard `US-01` for other document types.
- **Phase** is the deployment lifecycle phase derived from the document's section structure.
- **Source** uses the full reference format: `[Doc Title]: § [X.Y] - [Section Title]`.
- **Verification Story** links action stories to their paired verification story ID (or `—` if not applicable).
- For MoP/ops documents, acceptance criteria should include actual CLI commands from the source document.

### Solution Architect
```json
{
  "sheets": {
    "ADRs": {
      "headers": ["ADR#", "Title", "Status", "Context", "Decision", "Consequences", "Source"],
      "rows": [["ADR-1", "...", "Proposed", "...", "...", "...", "[Doc Title]: § X.Y"]]
    },
    "API Endpoints": {
      "headers": ["Method", "Path", "Description", "Auth", "Request Params", "Response", "Source"],
      "rows": [["GET", "/api/v1/...", "...", "Required", "...", "...", "[Doc Title]: § X.Y"]]
    },
    "Data Model": {
      "headers": ["Entity", "Attribute", "Type", "Constraints", "Description"],
      "rows": [["User", "id", "UUID", "PK", "Unique identifier"]]
    },
    "System Design": {
      "headers": ["Type", "Name", "Detail", "Pattern/Technology", "Source"],
      "rows": [["Component", "API Gateway", "Routes external requests", "REST/gRPC", "[Doc Title]: § X.Y"]]
    }
  }
}
```

### Technical Lead
```json
{
  "sheets": {
    "Technical Tasks": {
      "headers": ["Task#", "Title", "Type", "Effort", "Priority", "Depends On", "Story", "Source"],
      "rows": [["TT-1", "...", "Backend", "2d", "P1", "-", "US-1", "[Doc Title]: § X.Y"]]
    },
    "Implementation Plan": {
      "headers": ["Phase", "Task", "Owner Role", "Duration", "Dependencies", "Deliverable"],
      "rows": [["1", "...", "Backend Dev", "3d", "None", "..."]]
    }
  }
}
```

### QA Architect
```json
{
  "sheets": {
    "Test Cases": {
      "headers": ["TC ID", "Title", "Type", "Priority", "Story ID", "Preconditions", "Steps", "Expected Result", "Source"],
      "rows": [["TC-1", "...", "Functional", "High", "PRE-01", "...", "...", "...", "[Doc Title]: § 2.1 - [Section Title]"]]
    },
    "BDD Scenarios": {
      "headers": ["Feature", "Scenario", "Given", "When", "Then", "Source"],
      "rows": [["...", "...", "...", "...", "...", "[Doc Title]: § X.Y"]]
    }
  }
}
```

### DevOps Engineer
```json
{
  "sheets": {
    "Deployment Runbook": {
      "headers": ["Step", "Title", "Duration", "Has Rollback", "Verification"],
      "rows": [["Step 1", "Create Namespace", "2 min", "Yes", "oc get project openstack"]]
    },
    "Day-2 Operations": {
      "headers": ["ID", "Procedure", "Trigger", "Steps"],
      "rows": [["D2-1", "Scale Out — Add Nodes", "Adding compute capacity", "5 steps"]]
    },
    "Release Notes": {
      "headers": ["Category", "Item", "Impact", "Version", "Source"],
      "rows": [["Feature", "...", "High", "v1.0", "[Doc Title]: § X.Y"]]
    }
  }
}
```

### Automation Engineer
```json
{
  "sheets": {
    "Playbook Tasks": {
      "headers": ["Play", "Task", "Module", "Variables", "Handler", "Tags", "Source Step"],
      "rows": [["Deploy App", "...", "template", "...", "restart_service", "deploy", "Step 3"]]
    },
    "Variables": {
      "headers": ["Variable", "Default Value", "Description", "Override Required"],
      "rows": [["app_version", "latest", "...", "Yes"]]
    }
  }
}
```

### SRE Engineer
```json
{
  "sheets": {
    "Monitoring Metrics": {
      "headers": ["Metric", "Type", "Source", "Alert Threshold", "Dashboard", "Source"],
      "rows": [["cpu_usage", "gauge", "node_exporter", ">80%", "Infrastructure", "[Doc Title]: § X.Y"]]
    },
    "Alerting Rules": {
      "headers": ["Alert", "Severity", "Condition", "Duration", "Response Time", "Escalation", "Source"],
      "rows": [["HighCPU", "Warning", "cpu > 80%", "5m", "15 min", "L1 → L2", "[Doc Title]: § X.Y"]]
    },
    "SLOs": {
      "headers": ["SLO", "Objective", "Target", "Window", "Error Budget", "Source"],
      "rows": [["SLO-1", "Availability", "99.9%", "30d", "43.2 min/month", "[Doc Title]: § X.Y"]]
    },
    "SRE Troubleshooting": {
      "headers": ["ID", "Scenario", "Symptom", "Root Cause", "Resolution"],
      "rows": [["TS01", "Operator install failure", "Pod CrashLoopBackOff", "Image pull failure", "Verify registry connectivity"]]
    }
  }
}
```

### Technical Writer
```json
{
  "sheets": {
    "Documentation Sections": {
      "headers": ["Doc Type", "Section", "Title", "Content Summary", "Audience", "Source"],
      "rows": [["Admin Guide", "1.1", "Installation", "...", "System Admins", "[Doc Title]: § 1.1 - Installation"]]
    },
    "FAQ": {
      "headers": ["FAQ#", "Category", "Question", "Answer", "Source"],
      "rows": [["1", "Installation", "How to...?", "...", "[Doc Title]: § 1.1"]]
    },
    "SOPs": {
      "headers": ["ID", "Procedure", "Steps"],
      "rows": [["SOP-1", "Emergency Shutdown", "12 steps"]]
    },
    "Operational Procedures": {
      "headers": ["Procedure#", "Name", "Source", "Duration", "Risk Level", "Pre-checks", "Steps Summary", "Post-checks", "Known Issues"],
      "rows": [["SOP-1", "Emergency Shutdown", "Admin Guide Part 2", "30 min", "High", "Verify access", "12 steps: Notify, Stop VMs...", "Verify shutdown", ""]]
    }
  }
}
```

### Governance Specialist
```json
{
  "sheets": {
    "Risk Assessment": {
      "headers": ["Risk#", "Title", "Category", "Likelihood", "Impact", "Level", "Mitigation", "Owner", "Source"],
      "rows": [["RISK-1", "...", "Technical", "High", "High", "Critical", "...", "...", "[Doc Title]: § X.Y"]]
    },
    "Compliance Checklist": {
      "headers": ["Item#", "Standard", "Requirement", "Status", "Evidence", "Gap", "Source"],
      "rows": [["1", "ISO 27001", "...", "Partial", "...", "...", "[Doc Title]: § X.Y"]]
    },
    "Impact Analysis": {
      "headers": ["Area", "Impact", "Severity", "Affected Systems", "Mitigation", "Source"],
      "rows": [["Performance", "...", "Medium", "...", "...", "[Doc Title]: § X.Y"]]
    }
  }
}
```

### Cloud Deployment Engineer
```json
{
  "sheets": {
    "Method of Procedure": {
      "headers": ["Step", "Action", "Command/API", "Expected Result", "Duration", "Rollback Trigger", "Rollback Action", "Verification", "Source"],
      "rows": [["1", "...", "...", "...", "5 min", "...", "...", "...", "[Doc Title]: § X.Y"]]
    },
    "Cloud Troubleshooting": {
      "headers": ["ID", "Scenario", "Severity", "Symptom"],
      "rows": [["TS-1", "...", "Critical", "..."]]
    },
    "Input Validation": {
      "headers": ["#", "Section", "Validation Item", "Check", "Result", "Notes"],
      "rows": [["1", "NodeSet", "Node count matches spec", "Syntax", "Pass", ""]]
    },
    "Deployment Input Files": {
      "headers": ["File", "Description", "Location", "Validated"],
      "rows": [["node-set.yaml", "NodeSet definition", "input/", "[ ]"]]
    }
  }
}
```

### Project Manager
```json
{
  "sheets": {
    "Stakeholder Update": {
      "headers": ["Category", "Item", "Status", "Owner", "Due Date", "Notes"],
      "rows": [["Milestone", "...", "On Track", "...", "...", "..."]]
    },
    "Key Decisions": {
      "headers": ["#", "Decision", "Options", "Owner", "Deadline", "Impact if Delayed"],
      "rows": [["1", "Choose deployment strategy", "Blue-green / Rolling", "Tech Lead", "Sprint 2", "Delays deployment"]]
    },
    "Next Actions": {
      "headers": ["#", "Action", "Owner", "Target Date"],
      "rows": [["1", "Finalize network topology", "Network Engineer", "Week 1"]]
    },
    "Project Metrics": {
      "headers": ["Metric", "Current", "Target", "Trend"],
      "rows": [["Velocity", "38 SP", "40 SP", "Improving"]]
    },
    "Source Documents": {
      "headers": ["#", "Document", "Type", "Sections Analyzed"],
      "rows": [["1", "Deploying RHOSO 18.0", "Installation Guide", "All chapters"]]
    }
  }
}
```

### Proposal Writer
```json
{
  "sheets": {
    "Proposal Outline": {
      "headers": ["#", "Section", "RFx Reference", "Page Limit", "Status", "Owner", "Notes"],
      "rows": [["1", "Cover Letter", "Section A.1", "1 page", "Draft", "...", "..."]]
    },
    "Compliance Matrix": {
      "headers": ["Req #", "Section", "Requirement", "Type", "Compliance", "Response Reference", "Gap / Notes", "Source"],
      "rows": [["R-1", "3.1", "...", "Mandatory", "Compliant", "[RFP Title]: § 3.1", "...", "[RFP Title]: § 3.1"]]
    },
    "Win Themes": {
      "headers": ["#", "Theme", "Maps to Criteria", "Weight", "Ghost Against", "Proof Points", "Integration"],
      "rows": [["1", "...", "Technical Approach", "40%", "...", "...", "Exec Summary, Tech Section"]]
    },
    "Clarification Requests": {
      "headers": ["#", "RFx Section", "Question", "Priority", "Rationale", "Impact if Unresolved"],
      "rows": [["1", "3.2.1", "...", "Critical", "...", "..."]]
    }
  }
}
```

### Sprint Coach
```json
{
  "sheets": {
    "Sprint Plan": {
      "headers": ["Sprint", "Story", "SP", "Status", "Priority", "Assignee Role", "Dependencies", "Risk"],
      "rows": [
        ["Sprint 1", "US-1: Install Operator", "3", "Committed", "High", "Deployment Engineer", "None", "Low"],
        ["Sprint 2", "US-9: Create Control Plane", "8", "Committed", "High", "Deployment Engineer", "Sprint 1", "Medium"],
        ["Sprint 3", "US-13: Add Nodes to Data Plane", "5", "Committed", "Medium", "Operations Engineer", "Sprint 2", "Low"]
      ]
    },
    "Velocity": {
      "headers": ["Sprint", "Theme", "Committed SP", "Stretch SP", "Total Stories", "Sprint Goal"],
      "rows": [["Sprint 1", "Foundation & Networking", "38", "6", "10", "Deploy operator and configure all networks"]]
    }
  }
}
```

**Important:** The Sprint Plan sheet MUST contain ALL stories from ALL sprints in one table. The "Sprint" column allows filtering by sprint. No story from the backlog should be missing.

### RHOSO DA
```json
{
  "sheets": {
    "CIQ Parameters": {
      "headers": ["Table", "Parameter", "Type", "Required", "Required When", "Default", "Description", "Source"],
      "rows": [["rhoso_details", "Cluster Name", "string", "Yes", "always", "", "Unique cluster identifier", "Schema: cluster_name"]]
    },
    "CIQ Required-When": {
      "headers": ["Parameter", "Table", "Condition", "Depends On", "Notes"],
      "rows": [["EDPM NIC2 Name", "rhoso_edpm_network_config", "Topology = dual_nic_bond | ovs_bond | linux_bond", "EDPM Network Config Topology", "Only bonded topologies"]]
    },
    "Registration Inputs": {
      "headers": ["#", "File", "CIQ Parameter", "Format", "Purpose", "Required When"],
      "rows": [["1", "kubeconfig", "Kubeconfig Path", "YAML", "RHOCP cluster-admin access", "always"]]
    },
    "EDPM Topology Guide": {
      "headers": ["Topology", "NICs", "Bond", "Bridge", "Use Case", "Required Params", "Optional Params"],
      "rows": [["single_nic_vlans", "1", "No", "ovs_bridge", "Lab / simple environments", "NIC1, Bridge Type", ""]]
    },
    "RHOSO PDF Gap Matrix": {
      "headers": ["Area", "PDF", "Chapter", "In CIQ", "Reason", "Propose Adding"],
      "rows": [["Service enable/disable", "Customizing", "Ch 3.10-3.11", "No", "CPAT does not have service-toggle Ansible", "Only when CPAT adds service-toggle"]]
    },
    "CIQ Workbook Files": {
      "headers": ["File", "Size", "Description", "Layer", "Pattern"],
      "rows": [["rhoso_ciq_schema.py", "12 KB", "CIQ type and parameter schema (source of truth)", "CIQTemplates", "Pattern A: CIQ Schema"]]
    }
  }
}
```

### RHOSO Deployment Engineer
```json
{
  "sheets": {
    "CPAT Workflow": {
      "headers": ["#", "Phase", "CPAT Action", "execution_mode", "Ansible Tags", "Key Manifests", "Verification", "Source"],
      "rows": [["1", "Register", "Upload CIQ + files", "—", "register", "—", "Cluster in sidebar", "USAGE.md § Registration"]]
    },
    "Manifest Catalog": {
      "headers": ["#", "File", "CR Kind", "Source CIQ Tables", "Applied Phase", "oc Verify Command"],
      "rows": [["1", "openstack_nncp.yaml", "NodeNetworkConfigurationPolicy", "control_plane + networks", "Network Preparation", "oc get nncp"]]
    },
    "Deploy Tasks": {
      "headers": ["#", "Task", "Audience", "Role", "Duration", "Depends On", "Source"],
      "rows": [["1", "Upload CIQ workbook and input files", "End user", "Deployer", "10 min", "CIQ complete", "USAGE.md"]]
    },
    "Cluster Commands": {
      "headers": ["Phase", "Command", "Purpose", "Expected Output"],
      "rows": [["Pre-check", "oc get nodes", "Verify RHOCP cluster access", "Nodes listed in Ready state"]]
    },
    "CPAT Source Files": {
      "headers": ["File", "Layer", "Purpose", "Pattern", "Sync With"],
      "rows": [["ansible/playbooks/roles/rhoso/tasks/main.yml", "Ansible", "Task dispatcher — loads CIQ context, includes installation_task.yml", "Pattern H", "ansible_runner.py RHOSO_INSTALLATION_TASK_TAGS"]]
    }
  }
}
```

## Pipeline / Consolidated Excel

When running a pipeline (multiple agents), create ONE consolidated workbook:
- Each agent contributes its sheets to the same JSON
- File naming: `sprintweave-output/<document>-pipeline-<timestamp>-artifacts.xlsx`
- The Summary sheet lists all agents that contributed

Build the consolidated JSON incrementally:
```json
{
  "document": "<source document>",
  "generated_at": "<timestamp>",
  "agent": "Pipeline (Full)",
  "agent_map": {
    "User Stories": {"agent": "Requirements Analyst", "purpose": "User stories with acceptance criteria"},
    "NFRs": {"agent": "Requirements Analyst", "purpose": "Non-functional requirements"},
    "Epic Summary": {"agent": "Requirements Analyst", "purpose": "Epic groupings with story point totals"},
    "ADRs": {"agent": "Solution Architect", "purpose": "Architecture Decision Records"},
    "Data Model": {"agent": "Solution Architect", "purpose": "Entity-attribute model"},
    "System Design": {"agent": "Solution Architect", "purpose": "Architecture components and communication patterns"},
    "Technical Tasks": {"agent": "Technical Lead", "purpose": "Implementation tasks broken from stories"},
    "Implementation Plan": {"agent": "Technical Lead", "purpose": "Work area phases with effort"},
    "Test Cases": {"agent": "QA Architect", "purpose": "Test cases with traceability"},
    "BDD Scenarios": {"agent": "QA Architect", "purpose": "Given/When/Then test scenarios"},
    "Deployment Runbook": {"agent": "DevOps Engineer", "purpose": "Step-by-step deployment procedure"},
    "Day-2 Operations": {"agent": "DevOps Engineer", "purpose": "Day-2 operational procedures"},
    "Method of Procedure": {"agent": "Cloud Deployment Engineer", "purpose": "Cloud deployment MoP"},
    "Cloud Troubleshooting": {"agent": "Cloud Deployment Engineer", "purpose": "Deployment troubleshooting scenarios"},
    "Input Validation": {"agent": "Cloud Deployment Engineer", "purpose": "Input file validation checklist"},
    "Deployment Input Files": {"agent": "Cloud Deployment Engineer", "purpose": "Configuration files required"},
    "Playbook Tasks": {"agent": "Automation Engineer", "purpose": "Ansible automation tasks"},
    "Variables": {"agent": "Automation Engineer", "purpose": "Key deployment configuration variables"},
    "SLOs": {"agent": "SRE Engineer", "purpose": "Service Level Objectives"},
    "Monitoring Metrics": {"agent": "SRE Engineer", "purpose": "Prometheus metrics and thresholds"},
    "Alerting Rules": {"agent": "SRE Engineer", "purpose": "Alert definitions with severity"},
    "SRE Troubleshooting": {"agent": "SRE Engineer", "purpose": "SRE troubleshooting scenarios"},
    "Documentation Sections": {"agent": "Technical Writer", "purpose": "Documentation structure index"},
    "FAQ": {"agent": "Technical Writer", "purpose": "Frequently asked questions"},
    "SOPs": {"agent": "Technical Writer", "purpose": "Standard Operating Procedures"},
    "Operational Procedures": {"agent": "Technical Writer", "purpose": "SOP details with pre-checks"},
    "Risk Assessment": {"agent": "Governance Specialist", "purpose": "Risk register with mitigations"},
    "Compliance Checklist": {"agent": "Governance Specialist", "purpose": "Compliance requirements and status"},
    "Impact Analysis": {"agent": "Governance Specialist", "purpose": "Deployment impact analysis"},
    "Stakeholder Update": {"agent": "Project Manager", "purpose": "Stakeholder deliverables summary"},
    "Key Decisions": {"agent": "Project Manager", "purpose": "Pending decisions with deadlines"},
    "Next Actions": {"agent": "Project Manager", "purpose": "Immediate action items"},
    "Project Metrics": {"agent": "Project Manager", "purpose": "Key project health metrics"},
    "Source Documents": {"agent": "Project Manager", "purpose": "Input documents analyzed"},
    "Sprint Plan": {"agent": "Sprint Coach", "purpose": "Sprint-by-sprint delivery plan"},
    "Velocity": {"agent": "Sprint Coach", "purpose": "Sprint velocity and utilization"},
    "Proposal Outline": {"agent": "Proposal Writer", "purpose": "Proposal structure with section guidance"},
    "Compliance Matrix": {"agent": "Proposal Writer", "purpose": "RFx compliance requirements mapping"},
    "Win Themes": {"agent": "Proposal Writer", "purpose": "Competitive differentiators"},
    "Clarification Requests": {"agent": "Proposal Writer", "purpose": "Questions to clarify RFP/RFQ ambiguities"},
    "CIQ Parameters": {"agent": "RHOSO DA", "purpose": "RHOSO CIQ parameter catalog with required-when"},
    "CIQ Required-When": {"agent": "RHOSO DA", "purpose": "Conditional parameter requirements matrix"},
    "Registration Inputs": {"agent": "RHOSO DA", "purpose": "Registration input files and paths"},
    "EDPM Topology Guide": {"agent": "RHOSO DA", "purpose": "EDPM topology parameters and conditions"},
    "RHOSO PDF Gap Matrix": {"agent": "RHOSO DA", "purpose": "PDF-vs-CIQ coverage gap analysis"},
    "CIQ Workbook Files": {"agent": "RHOSO DA", "purpose": "Generated CIQ workbook files inventory"},
    "CPAT Workflow": {"agent": "RHOSO Deployment Engineer", "purpose": "Generate-review-deploy workflow phases"},
    "Manifest Catalog": {"agent": "RHOSO Deployment Engineer", "purpose": "Generated manifest files and CR kinds"},
    "Deploy Tasks": {"agent": "RHOSO Deployment Engineer", "purpose": "Deployment task brief steps"},
    "Cluster Commands": {"agent": "RHOSO Deployment Engineer", "purpose": "oc/openstack verification commands by phase"},
    "CPAT Source Files": {"agent": "RHOSO Deployment Engineer", "purpose": "Generated CPAT source files inventory with layer and pattern"}
  },
  "sheets": {
    "User Stories": { "..." : "..." },
    "NFRs": { "..." : "..." },
    "Epic Summary": { "..." : "..." },
    "ADRs": { "..." : "..." },
    "Data Model": { "..." : "..." },
    "System Design": { "..." : "..." },
    "Technical Tasks": { "..." : "..." },
    "Implementation Plan": { "..." : "..." },
    "Test Cases": { "..." : "..." },
    "BDD Scenarios": { "..." : "..." },
    "Deployment Runbook": { "..." : "..." },
    "Day-2 Operations": { "..." : "..." },
    "Method of Procedure": { "..." : "..." },
    "Cloud Troubleshooting": { "..." : "..." },
    "Input Validation": { "..." : "..." },
    "Deployment Input Files": { "..." : "..." },
    "Playbook Tasks": { "..." : "..." },
    "Variables": { "..." : "..." },
    "SLOs": { "..." : "..." },
    "Monitoring Metrics": { "..." : "..." },
    "Alerting Rules": { "..." : "..." },
    "SRE Troubleshooting": { "..." : "..." },
    "Documentation Sections": { "..." : "..." },
    "FAQ": { "..." : "..." },
    "SOPs": { "..." : "..." },
    "Operational Procedures": { "..." : "..." },
    "Risk Assessment": { "..." : "..." },
    "Compliance Checklist": { "..." : "..." },
    "Impact Analysis": { "..." : "..." },
    "Stakeholder Update": { "..." : "..." },
    "Key Decisions": { "..." : "..." },
    "Next Actions": { "..." : "..." },
    "Project Metrics": { "..." : "..." },
    "Source Documents": { "..." : "..." },
    "Sprint Plan": { "..." : "..." },
    "Velocity": { "..." : "..." }
  }
}
```

## Rules

1. **Always generate Excel** — Do not wait for user to ask. Every generation produces .xlsx automatically.
2. **JSON first, then script** — Write the JSON file, then run the Python generator.
3. **One file per generation** — Single agent = single workbook. Pipeline = consolidated workbook.
4. **Never overwrite previous runs** — Every output file includes a timestamp to preserve history. Previous runs remain accessible for comparison.
5. **Preserve markdown** — Still show markdown in chat for immediate reading. Excel is the exportable artifact.
6. **Handle errors gracefully** — If Python/openpyxl unavailable, fall back to writing the JSON file and instruct user to run manually.
7. **PII applies** — The same PII redaction rules apply to Excel content. Redact before writing JSON.

## Fallback (No Python Available)

If Python is not available or openpyxl install fails:
1. Still write the JSON data file
2. Tell user: "JSON data saved to `sprintweave-output/<doc>-<timestamp>-data.json`. To generate Excel: `pip install openpyxl && python 'tools/excel-generator.py' 'sprintweave-output/<doc>-<timestamp>-data.json'`"

## File Naming Convention

**All output files include a timestamp (`YYYYMMDD-HHmmss`) to prevent overwriting previous runs.**

| Scenario | JSON File | Excel File |
|----------|-----------|------------|
| Single agent | `<doc>-<timestamp>-data.json` | `<doc>-<timestamp>-artifacts.xlsx` |
| Pipeline | `<doc>-pipeline-<timestamp>-data.json` | `<doc>-pipeline-<timestamp>-artifacts.xlsx` |
| Specific agent re-run | `<doc>-<agent>-<timestamp>-data.json` | `<doc>-<agent>-<timestamp>-artifacts.xlsx` |

Where:
- `<doc>` is the source document filename without extension, lowercased, spaces replaced with hyphens
- `<timestamp>` is the generation time in `YYYYMMDD-HHmmss` format (e.g., `20260707-143000`)

**Examples:**
```
sprintweave-output/rhoso-18-deploying-20260707-143000-data.json
sprintweave-output/rhoso-18-deploying-20260707-143000-artifacts.xlsx
sprintweave-output/rhoso-18-deploying-pipeline-20260707-150000-data.json
sprintweave-output/rhoso-18-deploying-pipeline-20260707-150000-artifacts.xlsx
```

**Markdown output files** also follow this convention:
```
sprintweave-output/<doc>-<timestamp>-stories.md
sprintweave-output/<doc>-<timestamp>-architecture.md
sprintweave-output/<doc>-<timestamp>-runbook.md
```
