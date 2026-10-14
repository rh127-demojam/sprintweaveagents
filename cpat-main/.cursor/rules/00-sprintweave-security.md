---
alwaysApply: true
---
# SprintWeave Security (Always Active)

## Scope
This rule activates for ALL SprintWeave interactions. It enforces data safety at every stage: input handling, processing, output redaction, and storage.

---

## 1. Input Safety — Before Processing Any Document

### Data Handling Disclosure (Show on First Use)
When a user first interacts with SprintWeave agents, ALWAYS display:

```
⚠️ DATA HANDLING NOTICE:
• Document content referenced with @ is sent to the AI model for processing
• With Privacy Mode ON: content is NOT stored, NOT used for training
• Content transmitted over encrypted connection (same as code in Cursor)
• Generated output stays LOCAL unless YOU share/commit it
• REQUIREMENT: Enable Privacy Mode in Cursor Settings for any sensitive document
```

### Document Classification (Automatic)

BEFORE processing any referenced document, assess its sensitivity level:

| Sensitivity | Indicators | Action |
|-------------|-----------|--------|
| **PUBLIC** | Published docs, official product guides, open-source docs | Process normally |
| **INTERNAL** | Company procedures, internal guides, process docs | Process with PII redaction |
| **CONFIDENTIAL** | Customer names, infrastructure details, contracts, SLAs | WARN before processing |
| **RESTRICTED** | Credentials, API keys, passwords, HR/financial data | BLOCK — refuse to process |

### Classification Guard

If a document appears CONFIDENTIAL or RESTRICTED, display BEFORE processing:

```
⚠️ SECURITY CHECK:
This document appears to contain: [sensitive data type detected]

Sensitivity level: [CONFIDENTIAL / RESTRICTED]

For CONFIDENTIAL documents:
  ✅ Proceeding — all output will have PII auto-redacted
  ⚠️  Recommendation: Ensure Privacy Mode is ON in Cursor Settings
  ⚠️  Recommendation: Review output before sharing with anyone

For RESTRICTED documents:
  ❌ BLOCKED — This document contains [credentials/passwords/financial data]
  → Create a SANITIZED COPY first (remove secrets, replace real values with placeholders)
  → Then re-run with the sanitized version
```

### What Users Should NOT Feed In
Educate users (show in help/first-use):
- Raw credentials files (.env, secrets.yaml, vault files)
- Customer contracts with commercial terms
- HR documents, performance reviews, salary data
- Unredacted audit logs with user activity
- Documents marked "Company Confidential" or higher classification

### What IS Safe to Feed In
- Product documentation (install guides, upgrade procedures, admin guides)
- Architecture documents and design specs
- Requirements specifications
- Process documents and runbooks (even internal ones — PII gets redacted in output)
- Meeting notes and decision logs
- Public API documentation

---

## 2. Processing Safety — During Generation

### PII Redaction (Mandatory - All Output)

BEFORE delivering any generated artifact, scan and replace:

| Pattern | Replacement |
|---------|-------------|
| IPv4/IPv6 addresses | `[REDACTED-IP]` |
| MAC addresses | `[REDACTED-MAC]` |
| Internal hostnames, FQDNs (*.internal, *.corp, *.local) | `[INTERNAL-HOST]` |
| Email addresses | `[EMAIL-REDACTED]` |
| API keys, tokens, passwords, secrets | `[CREDENTIAL-REDACTED]` |
| Internal URLs (intranet, wiki, jira, git) | `[INTERNAL-URL]` |
| Employee IDs, badge numbers | `[ID-REDACTED]` |
| Customer names in infrastructure contexts | `[CUSTOMER-ENV]` |
| Database connection strings | `[CONNECTION-REDACTED]` |
| License keys, serial numbers | `[LICENSE-REDACTED]` |

**PRESERVE** (safe to include in output): Generic role names, process descriptions, architecture patterns, technology names, standard port numbers, product names, version numbers.

**Example transformations:**
- Input: "SSH to 10.45.23.100 as admin@netact-prod-01.nokia.internal"
- Output: "SSH to [REDACTED-IP] as [ROLE]@[INTERNAL-HOST]"

- Input: "Connect to postgres://admin:s3cret@db.acme-corp.internal:5432/production"
- Output: "Connect to [CONNECTION-REDACTED]"

- Input: "Customer ACME Corp's OCP cluster at ocp.acme.internal"
- Output: "[CUSTOMER-ENV] OCP cluster at [INTERNAL-HOST]"

### No Memorization
- Do NOT reference specific document content in suggestions for OTHER documents
- Each chat session is isolated — artifacts from one document do not leak to another
- Never suggest "based on the last customer document I saw..."

---

## 3. Output Safety — AI-Generated Labeling, Traceability & Storage

### AI-Generated Label (Mandatory - All Output) [TR-01]

Every generated artifact — markdown, JSON data file, and Excel — MUST carry a visible "AI-Generated" label:

**Markdown output header (first lines of every artifact file):**
```
> **AI-Generated Content** — This artifact was produced by SprintWeave AI agents.
> Always review AI-generated output prior to use. Source citations provided for traceability.
```

**Excel output:** The `excel-generator.py` Summary sheet includes an "AI-Generated" notice row automatically.

**In-chat output:** Every agent's final output block MUST begin with this single-line banner before the content:
```
AI-Generated | Agent: [Agent Name] | Source: [Document Name] | Review before use
```

This labeling is persistent and visible at every point of delivery.

### Traceability (Mandatory - All Output)

Every generated artifact MUST include a source citation:
- **Single document:** `[Source: Section X.Y - Title]` or `[Source: Slide N]` or `[Source: Row N]`
- **Multiple documents:** `[Source: filename.ext § Section X.Y]` (always include filename when 2+ docs)
- If content cannot be traced to the source document, flag it: `[UNVERIFIED]`
- Never fabricate requirements that are not in the source document

### Output File Guidance

When delivering final output, remind users:
- Save to `sprintweave-output/` folder (already in .gitignore)
- **NEVER** commit generated artifacts to a shared repo without manual review
- Review all output for any PII that may have slipped through before sharing
- JSON exports are for local use only, not for external sharing
- If sharing output externally: do a final pass to verify no sensitive data remains

### Sharing Safety Checklist
Before sharing any SprintWeave output with others, verify:
- [ ] No real IP addresses, hostnames, or URLs remain
- [ ] No customer names tied to specific infrastructure
- [ ] No credentials, tokens, or connection strings
- [ ] No employee names or IDs
- [ ] Document classification allows sharing at this level
- [ ] Privacy Mode was ON during generation

---

## 4. Compliance Reminders

- SprintWeave does NOT store documents — Cursor's AI processes them in-session only
- With Privacy Mode OFF: content MAY be used for model training — NEVER process sensitive docs without Privacy Mode
- Generated artifacts inherit the classification of the source document — treat them accordingly
- When in doubt: ask your security team before processing a document through any AI tool
