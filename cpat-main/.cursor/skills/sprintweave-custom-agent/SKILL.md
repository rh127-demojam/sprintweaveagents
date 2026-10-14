---
name: sprintweave-custom-agent
description: >-
  Build custom SprintWeave agents for any domain. Generates a complete agent rule
  file following SprintWeave conventions (activation triggers, process steps,
  output format, Excel export, quality summary). Use when the user says "create
  a new agent", "add an agent for X", "build a custom agent", or "I need an
  agent that generates Y".
---

# SprintWeave Custom Agent Builder

Generate new agent rule files that follow SprintWeave's standard architecture. The output is a `.cursor/rules/agent-*.md` file ready to use.

## When to Activate

- "Create a new agent for [domain]"
- "Add an agent that generates [artifact type]"
- "Build a custom agent"
- "I need an agent for [use case]"
- "Create a [role] agent"

## Process

### Step 1: Gather Agent Definition

Ask these questions (use AskQuestion when available). Skip any already answered.

#### Q1: Agent Identity
```
- Agent name/role? (e.g., "Security Analyst", "Database Architect", "Cost Optimizer")
- What artifacts does it produce? (e.g., "threat models", "schema designs", "cost reports")
```

#### Q2: Activation Triggers
```
- What commands should activate this agent? (list 3-6 trigger phrases)
  Example: "Generate threat model from @doc", "Analyze security risks in @doc"
- Any keywords that should trigger it? (e.g., "threat", "vulnerability", "CVE")
```

#### Q3: Input & Analysis
```
- What document types does it work best with? (e.g., architecture docs, API specs, config files)
- What should it look for in the source document? (sections, patterns, data points)
```

#### Q4: Output Structure
```
- What sections should the output contain? (list the main sections)
- Should output be tabular, narrative, or mixed?
- Any specific frameworks or standards to follow? (e.g., STRIDE for threat modeling, OWASP Top 10)
```

#### Q5: Excel Columns
```
- What columns should the Excel export have?
  (e.g., for a Security agent: "Threat ID, Asset, Threat, Severity, Likelihood, Risk, Mitigation, Source")
```

#### Q6: Cross-References
```
- Which existing agents should this agent reference or chain to?
  (e.g., "After threat model, suggest: Generate test cases for security scenarios (QA Architect)")
```

### Step 2: Generate Agent Rule

Use the template below. Fill in all placeholders from user answers.

```markdown
# Agent: {Agent Name}

## When This Activates
Activate when the user asks to:
{activation_triggers as bullet list}

## Process

### 1. Load Context
- Read `@context/team-config.yaml` for team framework, personas, estimation scale
- Load glossary by `team.domain`: telecom → `@context/glossary.yaml` | cloud → `@context/glossary-cloud.yaml` | platform → `@context/glossary-platform.yaml` | generic → `@context/glossary-generic.yaml`
- If team-config is missing, use defaults: Scrum, Fibonacci, markdown output

### 2. Analyze Document
- Read the referenced document fully
- Identify document type ({supported_document_types})
- Report: "Analyzing [title] - [type detected], [X sections/slides]"
- For large docs (100+ pages): offer to process specific sections

### 3. Generate {Primary Artifact}

{Generation instructions — framework/methodology to apply, what to extract, how to structure}

### 4. Output (Default: Markdown)

{Output template with headers, tables, sections — adapted from user's answers}

### 5. Excel Export (Always — Automatic)
After markdown output, generate a real `.xlsx` file:

1. Write artifact data to `sprintweave-output/<doc>-<timestamp>-data.json` using the schema from `00-sprintweave-excel-export.md` (sheets: "{sheet_names}")
2. Run: `python "tools/excel-generator.py" "sprintweave-output/<doc>-<timestamp>-data.json"`
3. Confirm file path to user

This produces a formatted Excel workbook with headers, filters, and color-coded priority rows — no copy-paste needed.

### 6. Quality Summary
```
{Agent Name} Quality:
  Artifacts: {what was generated}
  Source traceability: N/N linked to document sections
  PII: Clean

Next steps:
  - Refine: "{example refinement command}"
  - Export: "Give me JSON" (Excel auto-generated)
  - Related: "{suggest next agent}" ({next agent name})
```

## Iterative Refinement
{List 5-7 example follow-up commands users might ask}

## Rules
- NEVER invent information not found in the source document
- ALWAYS cite source section for each generated item
- ALWAYS apply PII redaction per security rule
- Use personas from team-config.yaml (fall back to generic if not set)
- {Any domain-specific rules}
```

### Step 3: Write the Files

1. Save agent rule to `.cursor/rules/agent-custom-{name-slug}.md` (the `agent-custom-` prefix keeps it out of git — personal agents are not shared with the team)
2. Save output template to `context/templates/custom-{name-slug}.md` (the `custom-` prefix keeps it gitignored — local only)
3. In the agent rule, reference the template as: `context/templates/custom-{name-slug}.md`
4. Show the user a summary of what was created

### Step 4: Update Dashboard (Automatic)

After creating the agent, **always** add it to the canvas dashboard by updating `context/custom-agents.yaml`:

1. **Read** `context/custom-agents.yaml` (create with `version: 1` and `agents: []` if missing)
2. **Append** a new entry to the `agents` array:
   ```yaml
   - id: "{agent-slug}"          # Lowercase kebab-case from agent name
     label: "{Category Label}"    # Dashboard tab label (e.g., "Consulting", "Security")
     color: "{pill-color}"        # One of: blue, purple, cyan, green, orange, yellow, pink, red, gray
     agent_name: "{Agent Name}"   # Exact agent name matching the rule file
     agent_color: "{hex-color}"   # Pipeline stage node color (e.g., "#0891b2")
     artifacts:
       - name: "{Artifact Name}"
         command: "{trigger command}"
       # ... one entry per artifact the agent produces
   ```
3. **If** an entry with the same `id` already exists, update it in-place
4. **Run sync:** `python tools/sync-pipeline-config.py`
5. **Confirm:** "Agent added to dashboard. Canvas updated."

This file is gitignored — custom agents stay local and are never pushed to the shared repo.

After dashboard registration, inform the user about optional additional steps:
- "To include in pipelines: update `agent-orchestrator.md`"
- "To include in consolidated Excel: add an extractor to `tools/consolidate-pipeline.py`"
- "To add to CATALOG.md: add a row with artifact name + command"
- "Update `00-sprintweave-welcome.md` to include in help"

Offer to do any of these automatically.

### Step 5: Update Excel Export Schema

Add the new agent's sheet schema to `00-sprintweave-excel-export.md` and `AGENT_MAP_DEFAULT` in `tools/excel-generator.py`. Use canonical sheet names matching `tools/consolidate-pipeline.py`:

```markdown
### {Agent Name}
\`\`\`json
{
  "sheets": {
    "{Canonical Sheet Name}": {
      "headers": [{column_headers}],
      "rows": [[{example_row}]]
    }
  }
}
\`\`\`
```

## Quick Mode

If user provides a detailed description upfront (e.g., "Create a Security Analyst agent that generates STRIDE threat models with columns: Asset, Threat, Severity, Mitigation"), extract all info and generate directly — only confirm before writing.

## Security Validation

Before writing the agent file, verify these security requirements:

1. **PII Redaction Mandate** — The generated Rules section MUST include: "ALWAYS apply PII redaction per security rule"
2. **No External Calls** — The agent must NOT instruct fetching from URLs, APIs, or external services
3. **No Code Execution** — The agent must NOT generate executable scripts (beyond the standard Excel export flow)
4. **Local Output Only** — All output paths must be within `sprintweave-output/` — never to external locations
5. **Source Citation Required** — Every generated artifact must cite its source section (prevents hallucinated content)
6. **Security Rule Reference** — The agent inherits `00-sprintweave-security.md` — never override or bypass it

If any of these are violated by the user's request, warn them and explain why before proceeding.

## Validation Checklist

Before writing the agent file, verify:
- [ ] Has clear activation triggers (5+ phrases)
- [ ] Follows the 6-step process (Load → Analyze → Generate → Output → Excel → Summary)
- [ ] Output includes source citations
- [ ] Excel export section references `00-sprintweave-excel-export.md`
- [ ] Quality summary includes next-step suggestions
- [ ] Iterative refinement examples are relevant
- [ ] Rules section includes PII redaction and source citation mandates
- [ ] File naming follows `agent-{kebab-case-name}.md` convention
- [ ] Security validation (above) passes

## Examples of Custom Agents Users Might Request

| Request | Agent Name | Primary Artifact |
|---------|-----------|-----------------|
| "Create a security agent" | Security Analyst | Threat models, vulnerability assessments |
| "I need a database designer" | Database Architect | Schema designs, migration scripts, ERDs |
| "Add a cost optimization agent" | Cost Optimizer | Cost reports, optimization recommendations |
| "Create a performance engineer" | Performance Engineer | Load test plans, bottleneck analysis |
| "Add an accessibility reviewer" | Accessibility Auditor | WCAG compliance reports, remediation plans |
| "Build a data pipeline agent" | Data Engineer | Pipeline designs, data flow diagrams |
