from __future__ import annotations

import html
import time
from pathlib import Path

import requests
import streamlit as st

from job_client import (
    API_URL,
    api_reachable,
    approve_job,
    cancel_job,
    create_custom_agent,
    create_job,
    delete_custom_agent,
    delete_input_file,
    delete_input_set,
    fetch_artifact_bytes,
    fetch_artifacts_zip_bytes,
    get_job,
    list_artifacts,
    list_custom_agents,
    list_inputs,
    list_jobs,
    list_pipelines,
    reject_job,
    resolve_pipeline,
    resume_job,
    skip_job,
    get_cpat_deploy,
    start_cpat_deploy,
    upload_inputs,
    using_api,
)
from pipelines import default_command

# ── Page config ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="SprintWeave",
    page_icon="🔷",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
/* Global */
[data-testid="stAppViewContainer"] { background: linear-gradient(175deg, #0d1117 0%, #161b22 100%); }
[data-testid="stSidebar"] { background: #0d1117; border-right: 1px solid #21262d; }

/* Cards */
.sw-card {
    background: linear-gradient(135deg, #161b22 0%, #1c2333 100%);
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 16px;
    transition: border-color 0.2s, box-shadow 0.2s;
}
.sw-card:hover {
    border-color: #58a6ff;
    box-shadow: 0 0 20px rgba(88, 166, 255, 0.1);
}
.sw-card h3 { color: #e6edf3; margin: 0 0 8px 0; font-size: 1.25rem; }
.sw-card .desc { color: #8b949e; font-size: 0.9rem; margin-bottom: 12px; }
.sw-card .badge {
    display: inline-block;
    background: #21262d;
    color: #58a6ff;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.8rem;
    margin-right: 6px;
}
.sw-card .badge-agent {
    background: #1a1e2e;
    color: #a5d6ff;
}

/* Hero */
.sw-hero {
    background: linear-gradient(135deg, #0d1117 0%, #0d2137 50%, #0d1117 100%);
    border: 1px solid #21262d;
    border-radius: 16px;
    padding: 48px 32px;
    text-align: center;
    margin-bottom: 32px;
}
.sw-hero h1 {
    background: linear-gradient(90deg, #58a6ff, #a371f7, #f778ba);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 2.5rem;
    margin-bottom: 8px;
}
.sw-hero p { color: #8b949e; font-size: 1.1rem; }

/* Status chips */
.status-running { color: #f0883e; font-weight: 600; }
.status-succeeded { color: #3fb950; font-weight: 600; }
.status-failed { color: #f85149; font-weight: 600; }
.status-queued { color: #8b949e; font-weight: 600; }
.status-awaiting_approval { color: #d29922; font-weight: 600; }
.status-rejected { color: #f85149; font-weight: 600; }
.status-cancelled { color: #f85149; font-weight: 600; }

/* Stage progress */
.stage-done { color: #3fb950; }
.stage-running { color: #f0883e; }
.stage-gate { color: #d29922; }
.stage-pending { color: #484f58; }

/* Sidebar branding */
.sw-brand {
    background: linear-gradient(90deg, #58a6ff, #a371f7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 1.5rem;
    font-weight: 700;
}
.sw-subtitle { color: #484f58; font-size: 0.8rem; }

/* Pipeline selector cards */
.pipe-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }

/* Log block */
.sw-log {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 16px;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 0.85rem;
    line-height: 1.6;
    color: #c9d1d9;
}

/* Job table */
.sw-job-row {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 8px;
}
</style>
""", unsafe_allow_html=True)

# ── Session state ────────────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "Home"
if "selected_pipeline" not in st.session_state:
    st.session_state.selected_pipeline = "lab-requirements"
if "active_job_id" not in st.session_state:
    st.session_state.active_job_id = None


def go(page: str) -> None:
    st.session_state.page = page


# ── Sidebar ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sw-brand">🔷 SprintWeave</div>', unsafe_allow_html=True)
    st.markdown('<div class="sw-subtitle">AI Delivery Platform on OpenShift</div>', unsafe_allow_html=True)
    st.markdown("---")

    pages = {
        "🏠 Home": "Home",
        "📁 Inputs": "Inputs",
        "🤖 Agents": "Agents",
        "🚀 Run": "Run",
        "📋 Job": "Job",
        "📦 Outputs": "Outputs",
    }
    for label, key in pages.items():
        if st.sidebar.button(
            label,
            key=f"nav-{key}",
            use_container_width=True,
            type="primary" if st.session_state.page == key else "secondary",
        ):
            go(key)
            st.rerun()

    st.markdown("---")
    if using_api():
        ok, msg = api_reachable()
        if ok:
            st.success("API connected", icon="✅")
        else:
            st.error(f"API error: {msg}", icon="❌")
        st.caption(API_URL)
    else:
        st.warning("Demo mode (fake jobs)", icon="⚠️")
        st.caption("Set SPRINTWEAVE_API_URL for real runs.")


# ── Helpers ──────────────────────────────────────────────────────────
PIPELINE_ICONS = {
    "standard": "📋",
    "lab-requirements": "🔬",
    "rhoso": "🏗️",
    "nrho": "🌐",
    "nrho-delivery": "📦",
    "governance": "🛡️",
}


def status_html(status: str) -> str:
    known = {
        "running",
        "succeeded",
        "failed",
        "queued",
        "awaiting_approval",
        "rejected",
        "cancelled",
    }
    cls = f"status-{status}" if status in known else ""
    icon = {
        "running": "⏳",
        "succeeded": "✅",
        "failed": "❌",
        "queued": "🕐",
        "awaiting_approval": "🛂",
        "rejected": "🚫",
        "cancelled": "⏹️",
    }.get(status, "❓")
    label = status.replace("_", " ").upper()
    return f'<span class="{cls}">{icon} {label}</span>'


def _job_clock(job: dict) -> str:
    started = job.get("started_at") or job.get("created_at") or ""
    finished = job.get("finished_at") or ""
    duration = job.get("duration") or ""
    if not duration and started and finished:
        duration = f"{started} → {finished}"
    if started and duration:
        return f"{started} · {duration}"
    if started:
        return started
    return "—"


def _timing_for(job: dict, abbrev: str) -> dict:
    for item in job.get("stage_timings") or []:
        if item.get("abbrev") == abbrev:
            return item
    return {}


def _completed_log_lines(logs: list[str]) -> list[str]:
    keep = []
    for line in logs:
        if any(
            token in line
            for token in (
                "[parsed]",
                "[done]",
                "[rda-single-shot] success",
                "[rda-single-shot] wrote",
                "[rde-single-shot]",
                "[rde-pass]",
                "[skip]",
            )
        ) and "waiting for worker" not in line:
            keep.append(line)
    return keep[-20:]


# ── PAGE: Home ───────────────────────────────────────────────────────
def page_home() -> None:
    st.markdown("""
    <div class="sw-hero">
        <h1>SprintWeave</h1>
        <p>AI agents that turn documents into delivery-ready artifacts.<br>
        Upload → Pick a pipeline → Download results.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Choose a pipeline")

    try:
        pipelines = list_pipelines(st.session_state)
    except Exception as exc:
        st.error(f"Could not load pipelines: {exc}")
        return

    cols = st.columns(2)
    for i, pipeline in enumerate(pipelines):
        icon = "✨" if pipeline.get("custom") else PIPELINE_ICONS.get(pipeline["id"], "⚡")
        with cols[i % 2]:
            agents = sorted({s["agent"] for s in pipeline["stages"]})
            badges = "".join(f'<span class="badge">{s["abbrev"]}</span>' for s in pipeline["stages"])
            agent_badges = "".join(f'<span class="badge badge-agent">{a}</span>' for a in agents)
            custom_tag = '<span class="badge badge-agent">custom</span>' if pipeline.get("custom") else ""
            st.markdown(f"""
            <div class="sw-card">
                <h3>{icon} {pipeline['name']} {custom_tag}</h3>
                <div class="desc">{pipeline['blurb']}</div>
                <div style="margin-bottom:8px">{badges}</div>
                <div>{agent_badges}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"▶ Run {pipeline['name']}", key=f"use-{pipeline['id']}", use_container_width=True):
                st.session_state.selected_pipeline = pipeline["id"]
                go("Run")
                st.rerun()


# ── PAGE: Agents ─────────────────────────────────────────────────────
def page_agents() -> None:
    st.markdown("### 🤖 Custom agents")
    st.caption(
        "Create agents on the PVC (`/data/custom-agents/`). "
        "They appear as pipelines immediately — **no image rebuild**. "
        "Form create is free; optional LLM draft is ~$0.50–2."
    )

    if not using_api():
        st.warning("API mode required (`SPRINTWEAVE_API_URL`).")
        return

    with st.expander("➕ Create agent", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Agent name", placeholder="Site Survey Analyst", key="ca-name")
            abbrev = st.text_input("Abbrev", placeholder="SSA", max_chars=12, key="ca-abbrev")
            agent_id = st.text_input(
                "Agent id (optional)",
                placeholder="auto from name",
                key="ca-id",
                help="Lowercase slug used in PVC paths and pipeline id custom-<id>",
            )
        with c2:
            blurb = st.text_input(
                "Short blurb",
                placeholder="Extract site survey findings",
                key="ca-blurb",
            )
            output_hint = st.text_input(
                "Output hint",
                placeholder="output/site-survey/report.md + checklist.xlsx",
                key="ca-output",
            )
            mode = st.radio(
                "Default stage mode",
                options=["tool_loop", "single_shot"],
                format_func=lambda m: (
                    "Tool loop (like Ansible — many files via tools)"
                    if m == "tool_loop"
                    else "Single-shot (### FILE bundle — cheaper, fewer files)"
                ),
                index=0,
                key="ca-mode",
            )
            gate = st.checkbox("Approval gate (default)", value=True, key="ca-gate")

        goal = st.text_area(
            "Goal / instructions",
            placeholder="Read parsed docs and produce a site survey pack under output/...",
            height=120,
            key="ca-goal",
        )
        rule_paste = st.text_area(
            "Optional: paste full agent rule markdown",
            height=100,
            key="ca-rule",
            help="If set, used as-is (free). Otherwise a template is written from the form.",
        )
        generate_llm = st.checkbox(
            "Generate richer rule with LLM (~$0.50–2)",
            value=False,
            key="ca-llm",
            help="Ignored if you paste a rule above.",
        )

        st.markdown("**Multi-stage pipeline (optional)** — like RDE Ansible + Backend")
        st.caption(
            'JSON list; each stage sets its own mode. Example: '
            '`[{"abbrev":"ANS","mode":"tool_loop","output":"ansible under output/…","gate":true},'
            '{"abbrev":"BE","mode":"single_shot","output":"backend files","gate":false}]`'
        )
        stages_raw = st.text_area(
            "stages_json",
            height=90,
            key="ca-stages",
            placeholder='Leave empty for a single stage using the defaults above.',
        )

        st.markdown("**Output verification (optional, Cursor parity)**")
        st.caption(
            "JSON list of relative paths that MUST exist after the agent finishes. "
            "If missing → automatic repair pass (like Cursor validate+fix)."
        )
        verify_paths_raw = st.text_area(
            "verify_paths",
            height=60,
            key="ca-verify",
            placeholder='["output/myagent/report.md", "output/myagent/data.csv"]',
        )
        repair_prompt_val = st.text_area(
            "Repair prompt (optional)",
            height=60,
            key="ca-repair",
            placeholder="Extra instructions for the repair pass if files are missing...",
        )

        if st.button("Create agent", type="primary", key="ca-create"):
            if not name.strip() or not abbrev.strip() or not goal.strip():
                st.error("Name, abbrev, and goal are required.")
            else:
                stages = None
                stages_ok = True
                if stages_raw.strip():
                    import json as _json

                    try:
                        stages = _json.loads(stages_raw)
                        if not isinstance(stages, list):
                            raise ValueError("stages_json must be a JSON list")
                    except (ValueError, _json.JSONDecodeError) as exc:
                        st.error(f"Invalid stages_json: {exc}")
                        stages_ok = False
                verify_paths = None
                if verify_paths_raw.strip():
                    import json as _json2

                    try:
                        verify_paths = _json2.loads(verify_paths_raw)
                        if not isinstance(verify_paths, list):
                            raise ValueError("verify_paths must be a JSON list")
                    except (ValueError, _json2.JSONDecodeError) as exc:
                        st.error(f"Invalid verify_paths: {exc}")
                        stages_ok = False
                if stages_ok:
                    try:
                        with st.spinner("Creating agent on PVC…"):
                            result = create_custom_agent(
                                st.session_state,
                                name=name.strip(),
                                abbrev=abbrev.strip(),
                                goal=goal.strip(),
                                output_hint=output_hint.strip(),
                                blurb=blurb.strip(),
                                agent_id=agent_id.strip(),
                                mode=mode,
                                gate=gate,
                                generate_llm=generate_llm and not rule_paste.strip(),
                                rule_markdown=rule_paste,
                                stages=stages,
                                verify_paths=verify_paths,
                                repair_prompt=repair_prompt_val.strip(),
                            )
                    except (requests.RequestException, RuntimeError) as exc:
                        st.error(f"Create failed: {exc}")
                    else:
                        pipe = (result.get("pipeline") or {}).get("id", "")
                        stage_modes = ", ".join(
                            f"{s.get('abbrev')}={s.get('mode')}"
                            for s in (result.get("pipeline") or {}).get("stages") or []
                        )
                        st.success(
                            f"Created `{result.get('agent', {}).get('id')}` "
                            f"(rule: {result.get('generated')}) — pipeline `{pipe}` "
                            f"[{stage_modes}]"
                        )
                        st.session_state.selected_pipeline = pipe
                        st.rerun()

    st.markdown("---")
    try:
        agents = list_custom_agents(st.session_state)
    except requests.RequestException as exc:
        st.error(f"Could not list agents: {exc}")
        return

    if not agents:
        st.info("No custom agents yet. Create one above.")
        return

    st.markdown(f"**{len(agents)} custom agent(s) on PVC**")
    for agent in agents:
        aid = agent.get("id", "")
        name = html.escape(str(agent.get("name") or ""))
        abbrev = html.escape(str(agent.get("abbrev") or ""))
        blurb = html.escape(str(agent.get("blurb") or ""))
        rule = html.escape(str(agent.get("rule_file") or ""))
        generated = html.escape(str(agent.get("generated") or ""))
        st.markdown(
            f"""
            <div class="sw-card" style="padding:16px; margin-bottom:8px">
              <h3 style="margin:0 0 6px 0; font-size:1.1rem">✨ {name}
              (<code>{abbrev}</code>)</h3>
              <div class="desc" style="margin:0">{blurb}</div>
              <div class="desc" style="margin:4px 0 0 0">
                id=<code>{html.escape(aid)}</code> ·
                pipeline=<code>custom-{html.escape(aid)}</code> ·
                rule=<code>{rule}</code> · mode={html.escape(str(agent.get('mode') or ''))} ·
                generated={generated}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        b1, b2, b3 = st.columns([2, 1, 1])
        stage_summary = ", ".join(
            f"{s.get('abbrev')}={s.get('mode')}"
            for s in (agent.get("stages") or [])
        ) or agent.get("output") or ""
        b1.caption(stage_summary)
        if b2.button("▶ Run", key=f"run-ca-{aid}", use_container_width=True):
            st.session_state.selected_pipeline = f"custom-{aid}"
            go("Run")
            st.rerun()
        if b3.button("🗑️ Delete", key=f"del-ca-{aid}", use_container_width=True):
            try:
                delete_custom_agent(st.session_state, aid)
            except (requests.RequestException, RuntimeError) as exc:
                st.error(f"Delete failed: {exc}")
            else:
                st.rerun()


# ── PAGE: Run ────────────────────────────────────────────────────────
def page_run() -> None:
    st.markdown("### 🚀 Run a pipeline")

    try:
        pipelines = list_pipelines(st.session_state)
    except Exception as exc:
        st.error(f"Could not load pipelines: {exc}")
        return
    if not pipelines:
        st.warning("No pipelines available.")
        return

    ids = [p["id"] for p in pipelines]
    labels = {
        p["id"]: (
            f"{'✨' if p.get('custom') else PIPELINE_ICONS.get(p['id'], '⚡')} {p['name']}"
        )
        for p in pipelines
    }
    current = st.session_state.selected_pipeline
    if current not in ids:
        current = ids[0]

    col1, col2 = st.columns([2, 3])
    with col1:
        pipeline_id = st.selectbox(
            "Pipeline",
            ids,
            index=ids.index(current),
            format_func=lambda pid: labels[pid],
        )
        st.session_state.selected_pipeline = pipeline_id

    try:
        pipeline = resolve_pipeline(pipeline_id, st.session_state)
    except KeyError as exc:
        st.error(str(exc))
        return

    with col2:
        st.markdown(f"**{pipeline['name']}** — {pipeline['blurb']}")

    st.markdown("---")

    # Stage preview
    st.markdown("**Pipeline stages:** *(stages marked 🛂 pause for approval)*")
    stage_cols = st.columns(min(len(pipeline["stages"]), 6))
    for j, stage in enumerate(pipeline["stages"]):
        with stage_cols[j % len(stage_cols)]:
            gate_label = "🛂 gate" if stage.get("gate") else ""
            if "tool_loop" in stage or stage.get("mode"):
                mode_lbl = (
                    "🔧 tool_loop"
                    if stage.get("tool_loop", stage.get("mode") == "tool_loop")
                    else "📄 single_shot"
                )
            else:
                mode_lbl = ""
            border = "#d29922" if stage.get("gate") else "#30363d"
            vp_count = len(stage.get("verify_paths") or [])
            verify_lbl = f"✅ {vp_count} verify" if vp_count else ""
            st.markdown(f"""
            <div style="background:#161b22; border:1px solid {border}; border-radius:8px;
                        padding:12px; text-align:center; min-height:90px">
                <div style="color:#58a6ff; font-weight:600; font-size:1.1rem">{stage['abbrev']}</div>
                <div style="color:#8b949e; font-size:0.8rem; margin-top:4px">{stage['agent']}</div>
                <div style="color:#8b949e; font-size:0.7rem; margin-top:4px">{mode_lbl}</div>
                <div style="color:#3fb950; font-size:0.7rem; margin-top:2px">{verify_lbl}</div>
                <div style="color:#d29922; font-size:0.75rem; margin-top:6px">{gate_label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # Input set ID — reusable file bundle on the PVC
    st.markdown("**Input set**")
    st.caption(
        "Files are stored under `/data/inputs/<input_id>/`. "
        "Reuse the same ID for another pipeline run, or pick a new ID for a different file set. "
        "Multiple files per set are supported."
    )

    existing_inputs: list[dict] = []
    try:
        existing_inputs = list_inputs(st.session_state)
    except requests.RequestException:
        existing_inputs = []

    existing_ids = [i.get("input_id", "") for i in existing_inputs if i.get("input_id")]
    mode = st.radio(
        "Files",
        ["Upload new / add files", "Reuse existing input set"],
        horizontal=True,
        label_visibility="collapsed",
    )

    col_id, col_pick = st.columns([2, 2])
    with col_id:
        default_id = st.session_state.get("last_input_id", "")
        input_id = st.text_input(
            "Input set ID",
            value=default_id,
            placeholder="Leave blank to auto-generate (e.g. site-a-ciq)",
            help="Letters, digits, dot, underscore, hyphen. Same ID = same files on PVC.",
        )
    with col_pick:
        if existing_ids:
            picked = st.selectbox(
                "Or pick an existing set",
                options=[""] + existing_ids,
                format_func=lambda x: "(select…)" if not x else x,
            )
            if picked:
                input_id = picked
                for item in existing_inputs:
                    if item.get("input_id") == picked:
                        st.caption(
                            f"Files: {', '.join(item.get('filenames') or []) or '(none)'}"
                        )
                        break

    uploads = None
    if mode.startswith("Upload"):
        uploads = st.file_uploader(
            "📄 Source documents (one or many)",
            accept_multiple_files=True,
            type=["pdf", "docx", "md", "txt", "xlsx", "pptx", "yaml", "yml"],
        )
    else:
        if not input_id.strip():
            st.info("Select or type an existing **Input set ID** to reuse its files.")
        elif input_id.strip() in existing_ids:
            st.success(f"Will reuse input set `{input_id.strip()}` (no re-upload).")

    # Cursor-style prompt: statement + @ mentions (like dashboard "Run … on @cpat")
    st.markdown("**Prompt** *(Cursor-style)*")
    st.caption(
        "Same idea as Cursor chat: a natural-language command plus `@` references. "
        "`@cpat` = generate under `output/cpat/`, `@input` = your uploaded docs, "
        "`@context` = templates/glossary, `@filename` = a specific input file."
    )

    prompt_key = "run_cursor_prompt"
    pipe_track = "run_cursor_prompt_pipeline"
    suggested = default_command(pipeline, input_id.strip())
    if st.session_state.get(pipe_track) != pipeline_id:
        st.session_state[prompt_key] = suggested
        st.session_state[pipe_track] = pipeline_id

    # Collect @ insert targets from current files
    file_names: list[str] = []
    if uploads:
        file_names = [f.name for f in uploads if getattr(f, "name", None)]
    elif input_id.strip():
        for item in existing_inputs:
            if item.get("input_id") == input_id.strip():
                file_names = list(item.get("filenames") or [])
                break

    ref_chips = ["@cpat", "@input", "@context"]
    if input_id.strip():
        ref_chips.append(f"@input:{input_id.strip()}")
    for name in file_names[:12]:
        ref_chips.append(f"@{name}")

    chip_cols = st.columns(min(len(ref_chips), 6))
    for i, ref in enumerate(ref_chips):
        with chip_cols[i % len(chip_cols)]:
            if st.button(ref, key=f"at-ref-{pipeline_id}-{i}-{ref}", use_container_width=True):
                cur = (st.session_state.get(prompt_key) or "").rstrip()
                st.session_state[prompt_key] = f"{cur} {ref}".strip()
                st.rerun()

    c_reset, _ = st.columns([1, 3])
    with c_reset:
        if st.button("↺ Reset to default command", key=f"reset-prompt-{pipeline_id}"):
            st.session_state[prompt_key] = suggested
            st.rerun()

    instructions = st.text_area(
        "Cursor prompt",
        height=120,
        key=prompt_key,
        placeholder=suggested,
        help="Example: Run RHOSO delivery pipeline on @cpat using @input:site-a",
        label_visibility="collapsed",
    )
    st.code(instructions or suggested, language=None)

    gates_enabled = st.toggle(
        "Enable approval gates",
        value=True,
        help="When off, the pipeline runs all stages without pausing for review.",
    )
    if not gates_enabled:
        st.caption("Gates off — stages will run straight through.")

    st.markdown("")
    if st.button("🚀 Run pipeline", type="primary", use_container_width=True):
        names = [f.name for f in uploads] if uploads else []
        if mode.startswith("Upload") and not names and not input_id.strip():
            st.error("Upload at least one file, or provide an existing Input set ID.")
            return
        if mode.startswith("Reuse") and not input_id.strip():
            st.error("Choose an Input set ID to reuse.")
            return
        prompt_text = (instructions or "").strip() or suggested
        with st.spinner("Creating job…"):
            try:
                job = create_job(
                    st.session_state,
                    pipeline_id,
                    names,
                    prompt_text,
                    uploads=uploads,
                    gates_enabled=gates_enabled,
                    input_id=input_id.strip(),
                )
            except (requests.RequestException, ValueError) as exc:
                st.error(f"Could not create job: {exc}")
                return
        st.session_state.active_job_id = job["id"]
        st.session_state.last_input_id = job.get("input_id") or input_id.strip()
        go("Job")
        st.rerun()


# ── PAGE: Job ────────────────────────────────────────────────────────
def page_job() -> None:
    st.markdown("### 📋 Job details")

    job_id = st.text_input("Job ID", value=st.session_state.active_job_id or "", label_visibility="collapsed",
                           placeholder="Enter job ID or start a run…")
    if not job_id:
        st.info("Start a run from the **Run** page, or paste a job ID above.")
        return

    try:
        job = get_job(st.session_state, job_id)
    except requests.RequestException as exc:
        st.error(f"Could not load job: {exc}")
        return
    if not job:
        st.warning("Job not found.")
        return

    st.session_state.active_job_id = job["id"]
    status = job.get("status", "unknown")

    # Header row
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"**Status:** {status_html(status)}", unsafe_allow_html=True)
    c2.markdown(f"**Pipeline:** {job.get('pipeline_name', job.get('pipeline_id'))}")
    c3.markdown(f"**Input set:** `{job.get('input_id') or '—'}`")
    gates_label = "on" if job.get("gates_enabled", True) else "off"
    c4.markdown(f"**Gates:** {gates_label}")

    files = job.get("filenames") or []
    st.markdown(f"**Files:** {', '.join(files) if files else '(none)'}")
    prompt = (job.get("instructions") or "").strip()
    if prompt:
        st.markdown("**Prompt:**")
        st.code(prompt, language=None)
    if job.get("input_path"):
        st.caption(f"📂 Input set path: `{job['input_path']}`")
    if job.get("output_path"):
        st.caption(f"📁 Job output: `{job['output_path']}`")
    st.caption(f"Job ID: `{job.get('id')}` (execution) · Input set ID: `{job.get('input_id') or '—'}` (files)")
    st.caption(f"⏱️ {_job_clock(job)}")

    st.markdown("---")

    # Stage progress
    st.markdown("**Stage progress:**")
    stages = job.get("stages") or []
    current = int(job.get("current_index") or 0)
    gate_idx = job.get("gate_stage_index")
    prog_cols = st.columns(max(len(stages), 1))
    for i, stage in enumerate(stages):
        with prog_cols[i] if i < len(prog_cols) else prog_cols[-1]:
            if status == "awaiting_approval" and gate_idx is not None and i == int(gate_idx):
                icon, cls = "🛂", "stage-gate"
            elif i < current:
                icon, cls = "✅", "stage-done"
            elif i == current and status == "running":
                icon, cls = "⏳", "stage-running"
            else:
                icon, cls = "⬜", "stage-pending"
            gate_mark = " · gate" if stage.get("gate") else ""
            timing = _timing_for(job, stage.get("abbrev", ""))
            dur = timing.get("duration") or ""
            if not dur and timing.get("started_at") and status == "running" and i == current:
                dur = "in progress"
            time_line = f'<div style="color:#8b949e; font-size:0.65rem">{dur or "—"}</div>'
            st.markdown(f"""
            <div style="text-align:center">
                <div style="font-size:1.5rem">{icon}</div>
                <div class="{cls}" style="font-size:0.85rem; font-weight:600">{stage.get('abbrev', '')}</div>
                <div style="color:#484f58; font-size:0.7rem">{stage.get('agent', '')}{gate_mark}</div>
                {time_line}
            </div>
            """, unsafe_allow_html=True)

    # Progress bar
    total = len(stages)
    if total:
        progress = min(current / total, 1.0) if status != "succeeded" else 1.0
        st.progress(progress)

    # Gate approval panel
    if status == "awaiting_approval":
        st.markdown("---")
        abbrev = job.get("gate_abbrev") or "?"
        st.warning(
            f"**Gate: {abbrev}** — review output, optionally add a follow-up prompt "
            "(like Cursor chat), then approve or reject.",
            icon="🛂",
        )
        pending = job.get("pending_artifact") or ""
        edit_key = f"gate-edit-{job['id']}-{abbrev}"
        sync_key = f"gate-sync-{job['id']}-{abbrev}"
        # Refresh editor when the server sends a new stage artifact
        if st.session_state.get(sync_key) != pending:
            st.session_state[edit_key] = pending
            st.session_state[sync_key] = pending

        prev_tab, edit_tab = st.tabs(["📖 Preview", "✏️ Edit raw"])
        with prev_tab:
            preview_body = st.session_state.get(edit_key, pending) or ""
            if preview_body.strip():
                st.markdown(preview_body)
            else:
                st.caption("(empty stage output)")
            st.download_button(
                "⬇️ Download this stage (.md)",
                data=preview_body,
                file_name=f"sprintweave-{job['id']}-{abbrev}.md",
                mime="text/markdown",
                key=f"dl-gate-{job['id']}-{abbrev}",
            )
        with edit_tab:
            st.text_area(
                "Stage output (editable markdown)",
                height=360,
                key=edit_key,
            )
            st.caption("Edit tables/text here; Preview renders markdown. Approve saves this version.")
        edited = st.session_state.get(edit_key, pending)
        follow_up = st.text_area(
            "💬 Follow-up prompt for next stage (optional)",
            placeholder=(
                "e.g. Focus on lab sizing tables only. Skip Ansible. "
                "Use Red Hat product names. Expand the gap analysis."
            ),
            height=120,
            key=f"gate-followup-{job['id']}-{abbrev}",
            help="Sent to the next agent only — like an extra Cursor message before continuing.",
        )
        reason = st.text_input(
            "Reject reason (optional)",
            key=f"gate-reason-{job['id']}-{abbrev}",
            placeholder="Why this stage is rejected…",
        )
        col_a, col_sk, col_r, col_s = st.columns(4)
        with col_a:
            if st.button("✅ Approve & continue", type="primary", use_container_width=True):
                try:
                    approve_job(
                        st.session_state,
                        job["id"],
                        edited_text=edited if (edited or "") != pending else None,
                        follow_up=follow_up,
                    )
                except (requests.RequestException, ValueError, LookupError) as exc:
                    st.error(f"Approve failed: {exc}")
                else:
                    st.rerun()
        with col_sk:
            if st.button(
                f"⏭️ Skip {abbrev}",
                use_container_width=True,
                help="Skip this agent and continue to the next stage",
            ):
                try:
                    skip_job(st.session_state, job["id"], skip_rest=False)
                except (requests.RequestException, ValueError, RuntimeError) as exc:
                    st.error(f"Skip failed: {exc}")
                else:
                    st.rerun()
        with col_r:
            if st.button("🚫 Reject", use_container_width=True):
                try:
                    reject_job(st.session_state, job["id"], reason=reason)
                except (requests.RequestException, ValueError, LookupError) as exc:
                    st.error(f"Reject failed: {exc}")
                else:
                    st.rerun()
        with col_s:
            if st.button("⏹️ Stop pipeline", use_container_width=True):
                try:
                    cancel_job(st.session_state, job["id"])
                except (requests.RequestException, ValueError, LookupError) as exc:
                    st.error(f"Stop failed: {exc}")
                else:
                    st.rerun()
        if st.button(
            "⏭️ Skip remaining agents & finish",
            key=f"skip-rest-{job['id']}-{abbrev}",
            help="Skip this gate and all later stages, then mark job succeeded",
        ):
            try:
                skip_job(st.session_state, job["id"], skip_rest=True)
            except (requests.RequestException, ValueError, RuntimeError) as exc:
                st.error(f"Skip remaining failed: {exc}")
            else:
                st.rerun()

    # Stop (Cursor-like) while queued / running
    if status in {"queued", "running"}:
        stopping = bool(job.get("cancel_requested"))
        st.markdown("---")
        col_stop, col_hint = st.columns([1, 3])
        with col_stop:
            if stopping:
                st.button(
                    "⏹️ Stopping…",
                    disabled=True,
                    use_container_width=True,
                    key=f"stop-busy-{job['id']}",
                )
            elif st.button(
                "⏹️ Stop",
                type="primary",
                use_container_width=True,
                key=f"stop-{job['id']}",
                help="Like Cursor Stop — halts after the current LLM/tool step",
            ):
                try:
                    cancel_job(st.session_state, job["id"])
                except (requests.RequestException, ValueError, LookupError) as exc:
                    st.error(f"Stop failed: {exc}")
                else:
                    st.rerun()
        with col_hint:
            if stopping:
                st.caption(
                    "Stop requested — waiting for the current model call/tool to finish, "
                    "then the job will show CANCELLED. Partial files under output/ are kept."
                )
            else:
                st.caption(
                    "Stop the agent like Cursor Stop. Cannot abort an in-flight LLM HTTP call; "
                    "halts before the next step."
                )

    # Completed work so far (visible while current stage is still running)
    done_lines = _completed_log_lines(job.get("logs") or [])
    if done_lines and status in {"queued", "running", "awaiting_approval"}:
        st.markdown("**Completed so far:**")
        st.markdown(
            f'<div class="sw-log" style="white-space:pre-wrap">{html.escape(chr(10).join(done_lines))}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("**Generated artifacts**")
    st.caption(
        "RHOSO DA/RDE use a tool-calling agent loop (like Cursor): real files under "
        "`output/` (CIQ generators, Excel, CPAT). Not a full IDE — gates/follow-up only for mid-run chat. "
        "Runs can take a long time and use many tokens."
    )
    try:
        artifact_files = list_artifacts(st.session_state, job["id"])
    except requests.RequestException:
        artifact_files = list(job.get("artifacts") or [])
    if artifact_files:
        if using_api():
            st.caption(
                "Downloads go through the UI pod (cluster-internal API). "
                "Click **Prepare**, then **Save** — browser links to `sprintweave-api` do not work."
            )
            zip_key = f"zip-bytes-{job['id']}"
            if st.button(
                "⬇️ Prepare all artifacts (.zip)",
                key=f"prep-zip-{job['id']}",
                use_container_width=True,
            ):
                try:
                    with st.spinner("Fetching zip from API…"):
                        st.session_state[zip_key] = fetch_artifacts_zip_bytes(job["id"])
                except requests.RequestException as exc:
                    st.error(f"Zip failed: {exc}")
            if zip_key in st.session_state and st.session_state[zip_key]:
                st.download_button(
                    "⬇️ Save artifacts.zip",
                    data=st.session_state[zip_key],
                    file_name=f"sprintweave-{job['id']}-artifacts.zip",
                    mime="application/zip",
                    key=f"save-zip-{job['id']}",
                    use_container_width=True,
                )
        shown = artifact_files[:100]
        for rel in shown:
            c_a, c_b = st.columns([4, 1])
            c_a.code(rel, language=None)
            if using_api():
                file_key = f"art-bytes-{job['id']}-{rel}"
                safe_key = rel.replace("/", "_").replace(".", "_")
                if c_b.button("Get", key=f"get-{job['id']}-{safe_key}"):
                    try:
                        st.session_state[file_key] = fetch_artifact_bytes(job["id"], rel)
                    except requests.RequestException as exc:
                        st.error(f"Download failed for {rel}: {exc}")
                if file_key in st.session_state and st.session_state[file_key] is not None:
                    c_b.download_button(
                        "Save",
                        data=st.session_state[file_key],
                        file_name=Path(rel).name,
                        key=f"save-{job['id']}-{safe_key}",
                    )
        if len(artifact_files) > 100:
            st.caption(f"… and {len(artifact_files) - 100} more files")
    else:
        st.caption("No generated files yet (waiting for agent tools to write under output/).")

    # Logs
    logs = job.get("logs") or []
    if logs:
        st.markdown("**Logs:**")
        log_text = html.escape("\n".join(logs[-80:]))
        st.markdown(
            f'<div class="sw-log" style="white-space:pre-wrap">{log_text}</div>',
            unsafe_allow_html=True,
        )

    # Download markdown summary
    artifact = job.get("artifact_md") or job.get("pending_artifact") or ""
    if status == "succeeded" and artifact:
        st.markdown("---")
        st.success("Pipeline completed successfully!", icon="🎉")
        col_dl, col_preview = st.columns([1, 2])
        with col_dl:
            st.download_button(
                "⬇️ Download summary.md",
                data=artifact,
                file_name=f"sprintweave-{job['id']}-summary.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with col_preview:
            with st.expander("Preview summary", expanded=False):
                st.markdown(artifact)
    elif status in {"queued", "running"}:
        st.caption(
            "⏳ Agent running — refreshing every 5 seconds "
            "(Docling + tool loops can take minutes). Use **Stop** to cancel."
        )
        time.sleep(5)
        st.rerun()
    elif status == "failed":
        st.error("Pipeline failed. Check logs above.")
    elif status == "rejected":
        st.error("Pipeline rejected at a gate.")
    elif status == "cancelled":
        st.warning(
            "Pipeline stopped by user. Any files already written under **Generated artifacts** "
            "are still available to download.",
            icon="⏹️",
        )

    # Per-agent Skip / Resume controls (when job is not actively running)
    if status in {"rejected", "failed", "cancelled", "succeeded", "awaiting_approval"}:
        st.markdown("---")
        st.markdown("**Agent controls**")
        st.caption(
            "Resume re-runs from that agent (skips Docling + earlier stages). "
            "Skip is available at a gate (see buttons above)."
        )
        if stages:
            btn_cols = st.columns(min(len(stages), 6))
            for i, stage in enumerate(stages):
                ab = stage.get("abbrev", f"S{i}")
                with btn_cols[i % len(btn_cols)]:
                    disabled = status == "awaiting_approval"
                    label = f"▶️ Resume {ab}"
                    if st.button(
                        label,
                        key=f"resume-{ab}-{job['id']}",
                        use_container_width=True,
                        disabled=disabled,
                        help=(
                            f"Start from {ab} ({stage.get('agent', '')}). "
                            "Requires parsed PDFs; earlier stage output if not first."
                            if not disabled
                            else "Reject or Stop first, then Resume"
                        ),
                    ):
                        try:
                            resume_job(st.session_state, job["id"], stage=ab)
                            st.success(f"Resumed from {ab}")
                            st.rerun()
                        except (requests.RequestException, ValueError, RuntimeError) as exc:
                            st.error(f"Resume {ab} failed: {exc}")
            if status == "awaiting_approval":
                st.caption(
                    "At a gate: use **Skip** above, or Reject/Stop first then use Resume."
                )

    # Package delivery: (1) download zip  (2) install on this OpenShift cluster — UI only
    if using_api() and status in {
        "succeeded",
        "awaiting_approval",
        "cancelled",
        "failed",
    }:
        st.markdown("---")
        st.markdown("**Package**")
        st.caption(
            "Two ways to use the generated build — both from this UI. "
            "No OpenShift CLI or bastion access required."
        )
        try:
            deploy_info = get_cpat_deploy(st.session_state, job["id"])
        except requests.RequestException as exc:
            st.warning(f"Could not check package status: {exc}")
            deploy_info = None

        ready = bool(deploy_info and (deploy_info.get("cpat") or {}).get("ready"))
        dep = (deploy_info or {}).get("deploy") or job.get("cpat_deploy") or {}
        dep_status = dep.get("status") or "idle"
        pkg_ns = (
            ((deploy_info or {}).get("settings") or {}).get("cpat_namespace")
            or (deploy_info or {}).get("namespace")
            or "sprintweave"
        )

        col_dl, col_inst = st.columns(2)
        with col_dl:
            st.markdown("**1. Download the package**")
            st.caption("Zip of generated artifacts (CIQ, CPAT tree, reports).")
            zip_key = f"zip-bytes-{job['id']}"
            if st.button(
                "⬇️ Download package (.zip)",
                key=f"pkg-prep-zip-{job['id']}",
                use_container_width=True,
            ):
                try:
                    with st.spinner("Preparing package…"):
                        st.session_state[zip_key] = fetch_artifacts_zip_bytes(job["id"])
                except requests.RequestException as exc:
                    st.error(f"Download failed: {exc}")
            if zip_key in st.session_state and st.session_state[zip_key]:
                st.download_button(
                    "⬇️ Save package.zip",
                    data=st.session_state[zip_key],
                    file_name=f"sprintweave-{job['id']}-package.zip",
                    mime="application/zip",
                    key=f"pkg-save-zip-{job['id']}",
                    use_container_width=True,
                    type="primary",
                )

        with col_inst:
            st.markdown("**2. Install on this OpenShift cluster**")
            st.caption(
                "Builds and runs CPAT here and opens a Route URL. "
                "Controlled only from this screen."
            )
            if not ready:
                st.info(
                    "Install available after the job produces a full CPAT tree "
                    f"(`cpat/Dockerfile`). "
                    f"{((deploy_info or {}).get('cpat') or {}).get('reason') or ''}"
                )
            else:
                if dep.get("url"):
                    st.success(f"Installed — open: {dep['url']}")
                elif dep_status == "deploying":
                    st.warning("Installing… image build can take several minutes.")
                elif dep_status == "failed":
                    st.error(dep.get("error") or dep.get("message") or "Install failed")
                elif dep_status == "prepared":
                    st.warning(
                        "Install could not run in-cluster yet (platform setup incomplete). "
                        "Use **Download package** for now, or ask an admin to enable "
                        "CPAT install on SprintWeave."
                    )

                if st.button(
                    "🚀 Install on OpenShift",
                    key=f"deploy-cpat-{job['id']}",
                    type="primary",
                    use_container_width=True,
                    disabled=dep_status == "deploying",
                ):
                    try:
                        with st.spinner("Installing CPAT on OpenShift…"):
                            start_cpat_deploy(
                                st.session_state,
                                job["id"],
                                mode="openshift",
                                namespace=pkg_ns,
                                save_as_default=True,
                            )
                        st.success("Install started — watch logs for `[cpat-deploy]`")
                        st.rerun()
                    except (requests.RequestException, RuntimeError) as exc:
                        st.error(f"Install failed: {exc}")

        if ready and dep_status == "deploying":
            time.sleep(5)
            st.rerun()


# ── PAGE: Outputs ────────────────────────────────────────────────────
def page_outputs() -> None:
    st.markdown("### 📦 All jobs")

    try:
        jobs = list_jobs(st.session_state)
    except requests.RequestException as exc:
        st.error(f"Could not list jobs: {exc}")
        return
    if not jobs:
        st.info("No jobs yet. Go to **Run** to start one.")
        return

    # Header
    hc = st.columns([1, 2, 2, 2, 2, 2, 1])
    hc[0].markdown("**#**")
    hc[1].markdown("**Job ID**")
    hc[2].markdown("**Input set**")
    hc[3].markdown("**Pipeline**")
    hc[4].markdown("**Status**")
    hc[5].markdown("**Time**")
    hc[6].markdown("")

    for idx, job in enumerate(jobs):
        cols = st.columns([1, 2, 2, 2, 2, 2, 1])
        cols[0].write(idx + 1)
        cols[1].code(job.get("id", ""), language=None)
        cols[2].code(job.get("input_id", "") or "—", language=None)
        cols[3].write(job.get("pipeline_name", job.get("pipeline_id", "")))
        cols[4].markdown(status_html(job.get("status", "")), unsafe_allow_html=True)
        cols[5].caption(_job_clock(job))
        if cols[6].button("Open", key=f"open-{job.get('id')}"):
            st.session_state.active_job_id = job["id"]
            st.session_state.last_input_id = job.get("input_id") or ""
            go("Job")
            st.rerun()

    st.caption("Manage file sets on the **Inputs** page.")


# ── PAGE: Inputs ─────────────────────────────────────────────────────
def page_inputs() -> None:
    st.markdown("### 📁 Input sets")
    st.caption(
        "Each **input set ID** is a folder on the PVC (`/data/inputs/<id>/`). "
        "Upload multiple files into a set, reuse it on Run, or delete files/sets here."
    )

    with st.expander("➕ Upload or add files", expanded=True):
        col_a, col_b = st.columns(2)
        with col_a:
            new_id = st.text_input(
                "Input set ID",
                placeholder="Leave blank to auto-generate (e.g. site-a)",
                key="inputs-new-id",
            )
        with col_b:
            add_files = st.file_uploader(
                "Files (one or many)",
                accept_multiple_files=True,
                type=["pdf", "docx", "md", "txt", "xlsx", "pptx", "yaml", "yml"],
                key="inputs-uploader",
            )
        if st.button("Save to PVC", type="primary", key="inputs-save"):
            if not add_files:
                st.error("Choose at least one file.")
            else:
                try:
                    result = upload_inputs(
                        st.session_state,
                        input_id=new_id.strip(),
                        uploads=add_files,
                    )
                except (requests.RequestException, ValueError) as exc:
                    st.error(f"Upload failed: {exc}")
                else:
                    st.session_state.last_input_id = result.get("input_id", "")
                    st.success(
                        f"Saved to input set `{result.get('input_id')}` — "
                        f"files: {', '.join(result.get('filenames') or [])}"
                    )
                    st.rerun()

    st.markdown("---")

    try:
        inputs = list_inputs(st.session_state)
    except requests.RequestException as exc:
        st.error(f"Could not list inputs: {exc}")
        return

    if not inputs:
        st.info("No input sets yet. Upload files above, or start a run with uploads.")
        return

    st.markdown(f"**{len(inputs)} input set(s) on PVC**")

    for item in inputs:
        iid = item.get("input_id", "")
        files = item.get("filenames") or []
        path = item.get("path", "")
        job_ids = item.get("job_ids") or []

        st.markdown(
            f"""
            <div class="sw-card" style="padding:16px; margin-bottom:8px">
              <h3 style="margin:0 0 6px 0; font-size:1.1rem">📁 {iid}</h3>
              <div class="desc" style="margin:0">Path: <code>{path}</code></div>
              <div class="desc" style="margin:4px 0 0 0">
                {len(files)} file(s)
                {" · linked jobs: " + ", ".join(job_ids) if job_ids else " · no active jobs in memory"}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not files:
            st.caption("(empty set)")
        else:
            for fname in files:
                fc1, fc2 = st.columns([5, 1])
                fc1.code(fname, language=None)
                if fc2.button("Remove", key=f"rm-file-{iid}-{fname}"):
                    try:
                        delete_input_file(st.session_state, iid, fname)
                    except (requests.RequestException, LookupError) as exc:
                        st.error(f"Remove failed: {exc}")
                    else:
                        st.rerun()

        b1, b2, _ = st.columns([1, 1, 2])
        with b1:
            if st.button("▶ Use on Run", key=f"use-input-{iid}", use_container_width=True):
                st.session_state.last_input_id = iid
                go("Run")
                st.rerun()
        with b2:
            if st.button("🗑️ Delete set", key=f"rm-set-{iid}", use_container_width=True):
                try:
                    delete_input_set(st.session_state, iid)
                except (requests.RequestException, LookupError) as exc:
                    st.error(f"Delete failed: {exc}")
                else:
                    st.rerun()
        st.markdown("")


# ── Router ───────────────────────────────────────────────────────────
if st.session_state.page == "Home":
    page_home()
elif st.session_state.page == "Inputs":
    page_inputs()
elif st.session_state.page == "Agents":
    page_agents()
elif st.session_state.page == "Run":
    page_run()
elif st.session_state.page == "Job":
    page_job()
else:
    page_outputs()
