---
description: "Batch processing, folder reference, input folder, multiple files in directory"
alwaysApply: false
---
# Input Folder: Batch Document Processing

> **Shared rule** — All agents inherit this behavior when a folder path is referenced.

## When This Applies

This rule activates when the user references a **folder** instead of a single file:
- `@input/` (the standard input folder)
- Any folder path (e.g., `@docs/`, `@source-documents/`)

## Supported File Types

Only process files with these extensions (skip all others silently):
`.pdf`, `.doc`, `.docx`, `.pptx`, `.xlsx`, `.csv`, `.md`, `.txt`, `.html`, `.yaml`, `.yml`, `.json`

## Process

### Step 1: Discover Files (MANDATORY — DO NOT SKIP)

> **HARD GATE**: No agent may begin processing until this step is complete and ALL files are accounted for.

When a folder is referenced:

1. **Run the discovery script** (preferred — deterministic, no files missed):
   ```
   python tools/discover-inputs.py <folder-path>
   ```
   If the script is not available, fall back to a shell listing:
   - Windows: `Get-ChildItem <folder> | Format-Table Name, Length`
   - Linux/Mac: `ls -la <folder>`

2. **Display the FULL discovery output** to the user — every file must be visible, including unsupported and skipped files. Never abbreviate or omit files.

3. **Confirm the file count**: Display "Proceeding with N supported files" and list them. In pipeline mode, proceed after displaying. In standalone mode, wait for user confirmation if the count seems unexpected.

4. If folder is empty or has no supported files: "No supported documents found in [folder]. Supported types: .pdf, .doc, .docx, .pptx, .xlsx, .csv, .md, .txt, .html, .yaml, .yml, .json"

### Step 2: Determine Processing Mode

**Combined mode (default):**
- Triggers: `"from @input/"`, `"on @input/"`, or any folder reference without "separately"/"each file"/"individually"
- All files are read and treated as a single logical document
- Produce one unified set of artifacts
- In the output, cite sources as `[filename.pdf § Section Name]` to distinguish which file each item came from

**Individual mode:**
- Triggers: user says "each file", "separately", "individually", "per file", "one by one"
- Process each file independently through the full agent logic
- Produce separate output per file
- Name output files with the source doc prefix: `<source-doc>-stories.md`, `<source-doc>-testcases.md`, etc.
- Report progress between files: "Processing file 2/3: upgrade-guide.docx..."

### Step 3: Handle Large Sets

If the folder contains more than 5 documents in combined mode:
- Warn: "This folder contains N documents. Combined processing may produce very large output."
- Offer: "Process all combined, process individually, or select specific files?"

If the folder contains more than 10 documents in individual mode:
- Warn: "Processing 10+ files individually will take time."
- Offer to process in batches or let user select a subset

## Output Naming

| Mode | JSON Data File | Excel File |
|------|---------------|------------|
| Combined | `sprintweave-output/input-<timestamp>-data.json` | `sprintweave-output/input-<timestamp>-artifacts.xlsx` |
| Individual | `sprintweave-output/<filename>-<timestamp>-data.json` | `sprintweave-output/<filename>-<timestamp>-artifacts.xlsx` |

Where `<timestamp>` is in `YYYYMMDD-HHmmss` format to avoid overwriting previous runs.

For combined mode, use the folder name as the document identifier (e.g., "input" for the `input/` folder).

## Source Citation in Combined Mode

When multiple documents are merged, every generated artifact MUST include which source file it came from:
- Stories: add a "Source File" field
- Test cases: cite "Derived from: [filename.pdf § section]"
- Runbook steps: note which document each step references

This ensures traceability across multiple source documents.

## Critical Rules

- **NEVER begin processing without completing Step 1 discovery** — this is a hard gate, not a suggestion
- **NEVER assume folder contents** — always list files explicitly using the discovery script or shell command
- **ALWAYS show ALL files** including unsupported and skipped, so the user can verify nothing was missed or convert files if needed
- NEVER skip files silently without reporting them in the discovery step
- ALWAYS report the total file count before processing
- Combined mode is the DEFAULT — only use individual mode when explicitly requested
- Single file references still work: `@input/specific-file.pdf` processes just that file
- Apply all standard agent rules (PII redaction, source citation, etc.) to every file
- For individual mode, generate a consolidated Excel at the end containing all per-file sheets
