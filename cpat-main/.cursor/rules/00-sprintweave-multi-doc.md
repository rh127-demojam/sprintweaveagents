---
description: "Multiple documents referenced, compare, combine, complement documents, multi-document input"
alwaysApply: false
---
# Multi-Document Input Handling

## When This Activates
Always active. Apply these rules whenever the user references **multiple documents** in a single request, such as:
- `"Generate stories from @requirements.pdf and @architecture.docx"`
- `"Generate test cases from @spec.pdf @api-guide.md @meeting-notes.txt"`
- `"Run pipeline on @doc1.pdf @doc2.pdf @doc3.pptx"`
- `"Compare @old-spec.pdf with @new-spec.pdf and generate change request"`

## Supported Multi-Document Patterns

### Pattern 1: Combined Input (merge into single output)
**Trigger:** Multiple docs referenced as sources for the SAME artifact type
**Example:** `"Generate user stories from @requirements.pdf and @install-guide.docx"`

**Behavior:**
1. Analyze each document separately first
2. Identify overlaps and unique content across documents
3. Merge into a single unified output
4. Tag each item with its source document:
   - `[Source: requirements.pdf § Section 3.2]`
   - `[Source: install-guide.docx § Step 5]`
5. Flag cross-document conflicts: `[CONFLICT: requirements.pdf says X, install-guide.docx says Y]`

**Report at start:**
```
Analyzing 2 documents:
  1. requirements.pdf — [type detected], [X sections]
  2. install-guide.docx — [type detected], [Y sections]
  
Cross-referencing for unified output...
```

### Pattern 2: Comparative Input (diff/delta analysis)
**Trigger:** User says "compare", "diff", "what changed", "delta between"
**Example:** `"Compare @old-spec.pdf with @new-spec.pdf and generate impact analysis"`

**Behavior:**
1. Identify the baseline document and the updated document
2. Extract differences: new content, removed content, modified content
3. Generate artifacts focused on the DELTA only
4. Mark items clearly:
   - `[NEW in new-spec.pdf]`
   - `[CHANGED from old-spec § 3.1]`
   - `[REMOVED from old-spec § 4.2]`

### Pattern 3: Complementary Input (different perspectives on same system)
**Trigger:** Documents of different types that describe the same system
**Example:** `"Generate runbook from @architecture.pdf @network-diagram.pptx @config-guide.md"`

**Behavior:**
1. Identify the role of each document (design, operations, configuration, etc.)
2. Cross-reference information across documents for completeness
3. Generate richer output by combining perspectives
4. Cite the specific document for each piece of information:
   - `[Source: architecture.pdf § Component X]`
   - `[Source: network-diagram.pptx § Slide 3]`
   - `[Source: config-guide.md § Parameters]`

### Pattern 4: Iterative Input (add more context to existing generation)
**Trigger:** User provides additional documents AFTER initial generation
**Example:** First: `"Generate stories from @spec.pdf"` → Then: `"Also consider @meeting-notes.md"`

**Behavior:**
1. Keep previously generated artifacts
2. Analyze the new document
3. Show what's NEW or MODIFIED based on the additional input:
   - New stories discovered
   - Existing stories that need updates
   - Conflicts with previous output
4. Present as a diff/supplement, not regenerate everything

## Output Requirements for Multi-Document

### Source Citation Format
When multiple documents are in context, ALWAYS use the full citation format:
```
[Source: filename.ext § Section/Slide/Page reference]
```

Never use just `[Source: Section X.Y]` when multiple docs are involved — always include the filename.

### Document Summary Table
Start every multi-document generation with:
```
Documents analyzed:
| # | File | Type | Sections | Key Content |
|---|------|------|----------|-------------|
| 1 | requirements.pdf | Requirements Spec | 12 sections | Functional requirements |
| 2 | architecture.docx | Design Document | 8 sections | System components |
| 3 | notes.md | Meeting Notes | 5 items | Decisions & action items |

Cross-references found: N items referenced across multiple documents
Conflicts detected: N (listed below if any)
```

### Conflict Resolution
When documents contradict each other:
```
⚠️ CONFLICT DETECTED:
  - requirements.pdf § 3.1: "System must support 1000 concurrent users"
  - architecture.docx § 2.4: "Designed for 500 concurrent users"
  → [REQUIRES CLARIFICATION: Which target is correct?]
```

### Deduplication
When the same requirement/procedure appears in multiple documents:
- Generate the artifact ONCE
- Cite ALL sources: `[Source: doc1.pdf § 3.1, doc2.docx § 2.4]`
- Note if descriptions differ slightly between documents

## Excel Export for Multi-Document
When multiple documents are used, the auto-generated `.xlsx` file includes a "Source File" column alongside the "Source" (section) column in every sheet, enabling filtering by document origin.

## Limits & Guidance
- **Recommended:** Up to 5 documents per request for best quality
- **Large sets (5+):** Suggest processing in batches or ask which are highest priority
- **Mixed relevance:** If a document seems unrelated, ask: "I see @notes.md — should I include this in the analysis or is it just for reference?"
- **Very large combined input:** Offer section-by-section processing: "These 3 documents total ~200 pages. Process all, or focus on specific sections?"
