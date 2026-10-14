---
description: "Auto-sync canvas dashboard after edits to tools/sprintweave-dashboard.canvas.tsx"
globs:
  - "tools/sprintweave-dashboard.canvas.tsx"
---
# SprintWeave Canvas Sync Rule

## Purpose
Ensures the deployed canvas runtime copy stays in sync whenever the source dashboard is modified.

## When This Activates
Automatically applies when any edit is made to `tools/sprintweave-dashboard.canvas.tsx` — whether adding categories, agents, colors, UI changes, or any structural modification.

## Required Action
After **every** edit to `tools/sprintweave-dashboard.canvas.tsx`, run the sync script:

```
python tools/sync-pipeline-config.py
```

This script:
1. Merges built-in + custom pipeline definitions into the source canvas
2. Injects local custom agents from `context/custom-agents.yaml` into the **runtime** canvas only (markers stay empty in source)
3. Writes the runtime canvas to `~/.cursor/projects/.../canvases/`

**Do NOT skip this step.** Without it, the live canvas preview will show stale content.

## Custom Agents (Local Only)
- Custom dashboard categories live in `context/custom-agents.yaml` (gitignored)
- Never hardcode custom agent categories into the source canvas
- Source markers `CUSTOM_CATEGORIES_*` / `CUSTOM_AGENT_COLORS_*` must remain empty in committed code

## What NOT to Do
- Do not manually copy the canvas file to the runtime location — the sync script handles it
- Do not edit the runtime canvas directly (`~/.cursor/projects/.../canvases/`) — always edit the source in `tools/`
- Do not put personal custom agents into shared files (dashboard source, CATALOG.md, welcome rule)
