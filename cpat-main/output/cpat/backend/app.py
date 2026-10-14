import io
import json
import logging
import os
import threading
import uuid
import zipfile
from datetime import datetime, timedelta, timezone

from flask import (
    Flask,
    jsonify,
    request,
    Response,
    send_file,
    session,
    stream_with_context,
)
from flask_cors import CORS
from sqlalchemy import inspect, text
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

from ansible_runner import (
    RHOSO_GENERATE_TASK,
    RHOSO_INSTALLATION_TASK_TAGS,
    OCP_GENERATE_TASK,
    OCP_INSTALLATION_TASK_TAGS,
    stream_register_cluster_playbook,
    stream_register_ocp_playbook,
    stream_rhoso_installation_playbook,
    stream_ocp_installation_playbook,
)
from ciq_parser import CiqParseError, OcpCiqParseError, parse_ciq_xlsx, parse_ocp_ciq_xlsx
from input_files import (
    INPUT_FILE_SPECS,
    PATH_PARAMETER_NAMES,
    cleanup_pending,
    copy_pending_uploads,
    extract_input_files_from_request,
    list_input_file_status,
    path_overrides_from_parameters,
    save_uploaded_input_files,
    stage_uploads_to_pending,
)
from models import (
    Cluster,
    OcpInstallationExecution,
    RhosoInstallationExecution,
    db,
)
from paths import (
    DATA_DIR,
    DATABASE_PATH,
    INSTALLATION_LOGS_DIR,
    REGISTRATION_LOGS_DIR,
    SECRETS_DIR,
    UPLOAD_DIR,
    cluster_artifacts_dir,
    ensure_data_dirs,
    list_cluster_artifacts,
    read_cluster_artifact,
    write_text_log,
)
from version import APP_VERSION

DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin"

ALLOWED_EXTENSIONS = {"xlsx"}

app = Flask(__name__)
app.secret_key = os.environ.get("CPAT_SECRET_KEY", "cpat-dev-secret-key-change-in-production")
app.config["UPLOAD_FOLDER"] = UPLOAD_DIR
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32 MB (CIQ + input files)
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DATABASE_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

_cors_origins = os.environ.get(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
)
if _cors_origins.strip() == "*":
    CORS(app, supports_credentials=True)
else:
    CORS(
        app,
        supports_credentials=True,
        origins=[o.strip() for o in _cors_origins.split(",") if o.strip()],
    )


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def require_auth():
    if not session.get("authenticated"):
        return jsonify({"error": "Unauthorized. Please login."}), 401
    return None


def init_db():
    ensure_data_dirs()
    db.create_all()
    migrate_db()


def migrate_db():
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())
    if "clusters" not in table_names:
        return

    columns = {col["name"] for col in inspector.get_columns("clusters")}
    if "ciq_parameters" not in columns:
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE clusters ADD COLUMN ciq_parameters TEXT"))
            conn.commit()
    if "registration_log" not in columns:
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE clusters ADD COLUMN registration_log TEXT"))
            conn.commit()



def _build_registration_log(
    entry,
    registered_by: str,
    description: str,
    ciq_filename: str,
    log_lines: list[str],
    registered_at: datetime,
) -> str:
    ts = registered_at.isoformat().replace("+00:00", "Z")
    header = [
        "CPAT Registration Log",
        "=" * 50,
        f"Cluster Name   : {entry.cluster_name}",
        f"Cluster Type   : {entry.cluster_type_label}",
        f"Source Table   : {entry.source_table}",
        f"Source Sheet   : {entry.source_sheet}",
        f"Type Parameter : {entry.type_raw_value}",
        f"CIQ File       : {ciq_filename}",
        f"Registered By  : {registered_by}",
        f"Description    : {description or '-'}",
        f"Registered At  : {ts}",
        "=" * 50,
        "",
        "Ansible Execution Log",
        "-" * 50,
    ]
    return "\n".join(header + log_lines) + "\n"


def _build_installation_log(
    cluster_name: str,
    product_version: str,
    task_name: str,
    triggered_by: str,
    log_lines: list[str],
    started_at: datetime,
    completed_at: datetime | None,
    status: str,
    log_title: str = "CPAT RHOSO Installation Execution Log",
    task_label: str = "Task",
    version_label: str = "RHOSO Version",
) -> str:
    ts_start = started_at.isoformat().replace("+00:00", "Z")
    ts_end = completed_at.isoformat().replace("+00:00", "Z") if completed_at else "-"
    header = [
        log_title,
        "=" * 50,
        f"Cluster Name   : {cluster_name}",
        f"{version_label:<15}: {product_version}",
        f"{task_label:<15}: {task_name}",
        f"Status         : {status}",
        f"Triggered By   : {triggered_by}",
        f"Started At     : {ts_start}",
        f"Completed At   : {ts_end}",
        "=" * 50,
        "",
        "Ansible Execution Log",
        "-" * 50,
    ]
    return "\n".join(header + log_lines) + "\n"


RHOSO_INSTALLATION_TASKS = set(RHOSO_INSTALLATION_TASK_TAGS.keys())
OCP_INSTALLATION_TASKS = set(OCP_INSTALLATION_TASK_TAGS.keys())


def _stream_event(event_type: str, payload: dict) -> str:
    return json.dumps({"type": event_type, **payload}) + "\n"


def _stream_playbook_task_executions(
    *,
    cluster_name: str,
    ocp_version: str,
    tasks: list[str],
    triggered_by: str,
    cluster: Cluster,
    ciq_file_path: str,
    execution_model,
    task_field: str,
    stream_playbook_fn,
    log_title: str,
    task_label: str,
    entity_label: str,
    start_message: str,
    success_message: str,
    version_field: str = "ocp_version",
    version_label: str = "OCP Version",
    ciq_parameter_overrides: dict | None = None,
    playbook_kwargs: dict | None = None,
):
    execution_records = []
    playbook_kwargs = playbook_kwargs or {}
    for task_name in tasks:
        started_at = datetime.now(timezone.utc)
        execution_kwargs = {
            "id": str(uuid.uuid4()),
            "cluster_id": cluster.id,
            "cluster_name": cluster_name,
            version_field: ocp_version,
            "status": "in_progress",
            "triggered_by": triggered_by,
            "started_at": started_at,
            task_field: task_name,
        }
        execution = execution_model(**execution_kwargs)
        db.session.add(execution)
        db.session.commit()
        execution_records.append((execution, started_at))

    yield _stream_event(
        "info",
        {
            "message": start_message.format(
                count=len(execution_records),
                cluster_name=cluster_name,
            ),
            "executions": [record[0].to_dict() for record in execution_records],
        },
    )

    completed_executions = []

    for execution, started_at in execution_records:
        task_name = getattr(execution, task_field)
        log_lines = [
            f"Running {entity_label}: {task_name}",
            "",
        ]

        def persist_log(
            status: str = "in_progress",
            completed_at: datetime | None = None,
            current_execution=execution,
            current_task_name=task_name,
        ):
            content = _build_installation_log(
                cluster_name,
                ocp_version,
                current_task_name,
                triggered_by,
                log_lines,
                started_at,
                completed_at,
                status,
                log_title=log_title,
                task_label=task_label,
                version_label=version_label,
            )
            current_execution.execution_log = content
            db.session.commit()
            safe_task = secure_filename(current_task_name.replace(" ", "-")) or "task"
            write_text_log(
                INSTALLATION_LOGS_DIR,
                f"{current_execution.id}-{safe_task}.log",
                content,
            )

        persist_log()
        yield _stream_event(
            "task_start",
            {
                "message": log_lines[0],
                "execution": execution.to_dict(),
            },
        )

        playbook_failed = False
        try:
            for event_type, payload in stream_playbook_fn(
                cluster_name,
                ocp_version,
                task_name,
                ciq_file_path,
                ciq_parameter_overrides,
                **playbook_kwargs,
            ):
                if event_type == "log":
                    log_lines.append(payload["line"])
                    persist_log()
                    yield _stream_event("log", {**payload, "execution_id": execution.id})
                elif event_type == "complete":
                    line = payload.get("message", "Playbook complete.")
                    log_lines.append(line)
                    persist_log()
                    yield _stream_event(
                        "log",
                        {"line": line, "execution_id": execution.id},
                    )
                elif event_type == "error":
                    playbook_failed = True
                    log_lines.append(f"ERROR: {payload.get('message', 'Playbook failed.')}")
                    persist_log()
                    yield _stream_event(
                        "error",
                        {**payload, "execution_id": execution.id, "fatal": False},
                    )
        except GeneratorExit:
            playbook_failed = True
            _stream_aborted = True
            log_lines.append("ERROR: Client disconnected (stream closed).")
        except Exception as exc:
            playbook_failed = True
            _stream_aborted = False
            log_lines.append(f"ERROR: {exc!r}")
        else:
            _stream_aborted = False

        completed_at = datetime.now(timezone.utc)
        final_status = "failed" if playbook_failed else "complete"
        log_lines.append("")
        log_lines.append(
            f"{entity_label} {'failed' if playbook_failed else 'completed successfully'}."
        )

        execution.status = final_status
        execution.completed_at = completed_at
        try:
            persist_log(status=final_status, completed_at=completed_at)
        except Exception:
            pass

        if _stream_aborted:
            return

        completed_executions.append(execution.to_dict())
        yield _stream_event(
            "task_complete",
            {
                "message": (
                    f"{entity_label} '{task_name}' "
                    f"{'failed' if playbook_failed else 'completed'}."
                ),
                "execution": execution.to_dict(),
            },
        )

        if playbook_failed:
            yield _stream_event(
                "error",
                {
                    "message": (
                        f"Execution stopped after {entity_label.lower()} "
                        f"'{task_name}' failed."
                    ),
                    "fatal": True,
                },
            )
            return

    yield _stream_event(
        "success",
        {
            "message": success_message.format(
                count=len(completed_executions),
                cluster_name=cluster_name,
            ),
            "executions": completed_executions,
        },
    )


# ---------------------------------------------------------------------------
# Background task runner — runs Ansible tasks in a thread, polls DB only
# ---------------------------------------------------------------------------

def _run_tasks_in_background(
    flask_app,
    *,
    cluster_name: str,
    ocp_version: str,
    tasks: list[str],
    execution_ids: list[str],
    triggered_by: str,
    cluster_id: str,
    ciq_file_path: str,
    execution_model,
    task_field: str,
    stream_playbook_fn,
    log_title: str,
    task_label: str,
    entity_label: str,
    version_field: str = "ocp_version",
    version_label: str = "OCP Version",
    ciq_parameter_overrides: dict | None = None,
    playbook_kwargs: dict | None = None,
):
    """Run Ansible tasks sequentially in a background thread.

    Updates execution records in the DB as the playbook runs.
    The frontend polls /api/<type>-installations and log endpoints.
    """
    playbook_kwargs = playbook_kwargs or {}

    with flask_app.app_context():
        for exec_id, task_name in zip(execution_ids, tasks):
            execution = execution_model.query.get(exec_id)
            if not execution:
                logger.error("Execution %s not found, skipping.", exec_id)
                continue

            started_at = execution.started_at
            log_lines = [
                f"Running {entity_label}: {task_name}",
                "",
            ]

            def persist_log(
                status="in_progress",
                completed_at=None,
                _exec=execution,
                _task=task_name,
            ):
                content = _build_installation_log(
                    cluster_name,
                    ocp_version,
                    _task,
                    triggered_by,
                    log_lines,
                    started_at,
                    completed_at,
                    status,
                    log_title=log_title,
                    task_label=task_label,
                    version_label=version_label,
                )
                _exec.execution_log = content
                db.session.commit()
                safe_task = secure_filename(_task.replace(" ", "-")) or "task"
                write_text_log(
                    INSTALLATION_LOGS_DIR,
                    f"{_exec.id}-{safe_task}.log",
                    content,
                )

            persist_log()

            playbook_failed = False
            try:
                run_kwargs = {**playbook_kwargs, "execution_uuid": exec_id}
                for event_type, payload in stream_playbook_fn(
                    cluster_name,
                    ocp_version,
                    task_name,
                    ciq_file_path,
                    ciq_parameter_overrides,
                    **run_kwargs,
                ):
                    if event_type == "log":
                        log_lines.append(payload["line"])
                        persist_log()
                    elif event_type == "complete":
                        log_lines.append(
                            payload.get("message", "Playbook complete.")
                        )
                        persist_log()
                    elif event_type == "error":
                        playbook_failed = True
                        log_lines.append(
                            f"ERROR: {payload.get('message', 'Playbook failed.')}"
                        )
                        persist_log()
            except Exception as exc:
                playbook_failed = True
                log_lines.append(f"ERROR: {exc!r}")
                logger.exception(
                    "Background task %s crashed: %s", task_name, exc
                )

            completed_at = datetime.now(timezone.utc)
            final_status = "failed" if playbook_failed else "complete"
            log_lines.append("")
            log_lines.append(
                f"{entity_label} "
                f"{'failed' if playbook_failed else 'completed successfully'}."
            )
            execution.status = final_status
            execution.completed_at = completed_at
            try:
                persist_log(status=final_status, completed_at=completed_at)
            except Exception:
                logger.exception("Failed to persist final log for %s", exec_id)

            if playbook_failed:
                # Mark remaining tasks as cancelled
                remaining_idx = execution_ids.index(exec_id) + 1
                for rem_id in execution_ids[remaining_idx:]:
                    rem_exec = execution_model.query.get(rem_id)
                    if rem_exec and rem_exec.status == "in_progress":
                        rem_exec.status = "cancelled"
                        rem_exec.completed_at = completed_at
                        rem_exec.execution_log = (
                            f"Cancelled: prior task '{task_name}' failed."
                        )
                db.session.commit()
                break

    logger.info(
        "Background execution finished for cluster '%s' (%d tasks).",
        cluster_name, len(tasks),
    )


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "ok",
            "version": APP_VERSION,
            "data_dir": DATA_DIR,
        }
    )


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if username == DEFAULT_USERNAME and password == DEFAULT_PASSWORD:
        session["authenticated"] = True
        session["username"] = username
        session.permanent = True
        app.permanent_session_lifetime = timedelta(hours=8)
        return jsonify(
            {
                "message": "Login successful",
                "username": username,
                "version": APP_VERSION,
            }
        )

    return jsonify({"error": "Invalid username or password"}), 401


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully"})


@app.route("/api/auth/me", methods=["GET"])
def me():
    if not session.get("authenticated"):
        return jsonify({"authenticated": False}), 401
    return jsonify(
        {
            "authenticated": True,
            "username": session.get("username"),
            "version": APP_VERSION,
        }
    )


@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    auth_error = require_auth()
    if auth_error:
        return auth_error

    rhoso_count = Cluster.query.filter_by(cluster_type="rhoso").count()
    ocp_count = Cluster.query.filter_by(cluster_type="ocp").count()
    total_count = rhoso_count + ocp_count
    recent = (
        Cluster.query.order_by(Cluster.registered_at.desc())
        .limit(5)
        .all()
    )

    return jsonify(
        {
            "version": APP_VERSION,
            "summary": {
                "total_clusters": total_count,
                "rhoso_environments": rhoso_count,
                "ocp_clusters": ocp_count,
            },
            "recent_clusters": [cluster.to_dict() for cluster in recent],
        }
    )


@app.route("/api/clusters", methods=["GET"])
def list_clusters():
    auth_error = require_auth()
    if auth_error:
        return auth_error

    query = Cluster.query.order_by(Cluster.registered_at.desc())
    cluster_type = request.args.get("type")
    if cluster_type and cluster_type in ("rhoso", "ocp"):
        query = query.filter_by(cluster_type=cluster_type)
    elif cluster_type:
        return jsonify({"clusters": [], "total": 0})

    clusters = query.all()
    return jsonify(
        {
            "clusters": [cluster.to_dict() for cluster in clusters],
            "total": len(clusters),
        }
    )


@app.route("/api/clusters/register", methods=["POST"])
def register_cluster():
    auth_error = require_auth()
    if auth_error:
        return auth_error

    description = request.form.get("description", "").strip()
    allow_reregister = request.form.get("reregister", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    if "ciq_file" not in request.files:
        return jsonify({"error": "CIQ file is required"}), 400

    file = request.files["ciq_file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "CIQ file must be an .xlsx workbook"}), 400

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(SECRETS_DIR, exist_ok=True)

    original_filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    file.save(file_path)

    input_uploads = extract_input_files_from_request(request.files)
    pending_id = uuid.uuid4().hex
    pending_dir = stage_uploads_to_pending(SECRETS_DIR, pending_id, input_uploads)

    try:
        parsed_batch = parse_ciq_xlsx(file_path)
    except CiqParseError as exc:
        os.remove(file_path)
        cleanup_pending(pending_dir)
        return jsonify({"error": str(exc)}), 400

    existing_by_name: dict[str, Cluster] = {}
    for entry in parsed_batch.clusters:
        if entry.cluster_type not in ("rhoso", "ocp"):
            os.remove(file_path)
            cleanup_pending(pending_dir)
            return jsonify(
                {
                    "error": (
                        f"Unsupported cluster type '{entry.cluster_type_label}'. "
                        "CPAT registers RHOSO and OCP environments."
                    )
                }
            ), 400
        existing = Cluster.query.filter_by(cluster_name=entry.cluster_name).first()
        if existing:
            if not allow_reregister:
                os.remove(file_path)
                cleanup_pending(pending_dir)
                return jsonify(
                    {
                        "error": (
                            f"Cluster '{entry.cluster_name}' is already registered. "
                            "Enable 'Re-register existing cluster' to update the CIQ "
                            "and registration for the same environment."
                        )
                    }
                ), 409
            existing_by_name[entry.cluster_name] = existing

    registered_by = session.get("username", "unknown")

    def generate():
        try:
            reregister_names = sorted(existing_by_name.keys())
            yield _stream_event(
                "info",
                {
                    "message": (
                        f"Parsed {len(parsed_batch.clusters)} cluster(s) from CIQ file."
                        + (
                            f" Re-registering: {', '.join(reregister_names)}."
                            if reregister_names
                            else ""
                        )
                    ),
                    "cluster_count": len(parsed_batch.clusters),
                    "reregister": bool(reregister_names),
                    "reregister_clusters": reregister_names,
                    "clusters": [
                        {
                            "cluster_name": c.cluster_name,
                            "cluster_type": c.cluster_type,
                            "cluster_type_label": c.cluster_type_label,
                            "source_table": c.source_table,
                            "source_sheet": c.source_sheet,
                            "reregister": c.cluster_name in existing_by_name,
                        }
                        for c in parsed_batch.clusters
                    ],
                    "input_files_received": list(input_uploads.keys()),
                },
            )
            if input_uploads:
                labels = ", ".join(
                    INPUT_FILE_SPECS[f][0] for f in input_uploads if f in INPUT_FILE_SPECS
                )
                yield _stream_event(
                    "info",
                    {
                        "message": (
                            f"Input file upload(s) received for: {labels}. "
                            "Paths will be stored under CPAT data/secrets after registration."
                        ),
                    },
                )

            cluster_logs: list[tuple] = []

            for entry in parsed_batch.clusters:
                is_update = entry.cluster_name in existing_by_name
                action = "Re-registering" if is_update else "Registering"
                log_lines = [
                    (
                        f"{action} {entry.cluster_type_label}: {entry.cluster_name} "
                        f"(table '{entry.source_table}' on sheet '{entry.source_sheet}')"
                    ),
                    "",
                ]
                yield _stream_event(
                    "info",
                    {
                        "message": log_lines[0],
                        "cluster_name": entry.cluster_name,
                        "cluster_type": entry.cluster_type,
                        "cluster_type_label": entry.cluster_type_label,
                        "source_table": entry.source_table,
                        "source_sheet": entry.source_sheet,
                        "reregister": is_update,
                    },
                )

                playbook_failed = False
                for event_type, payload in stream_register_cluster_playbook(
                    file_path,
                    description,
                    entry.cluster_type,
                ):
                    if event_type == "log":
                        log_lines.append(payload["line"])
                        yield _stream_event("log", payload)
                    elif event_type == "complete":
                        line = payload.get("message", "Playbook complete.")
                        log_lines.append(line)
                        yield _stream_event("log", {"line": line})
                    elif event_type == "error":
                        playbook_failed = True
                        log_lines.append(
                            f"ERROR: {payload.get('message', 'Playbook failed.')}"
                        )
                        yield _stream_event("error", payload)

                if playbook_failed:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                    return

                log_lines.append("")
                log_lines.append(
                    "Re-registration completed successfully."
                    if is_update
                    else "Registration completed successfully."
                )
                cluster_logs.append((entry, log_lines, is_update))

            saved_clusters = []
            reregistered_count = 0
            for entry, log_lines, is_update in cluster_logs:
                registered_at = datetime.now(timezone.utc)
                existing = existing_by_name.get(entry.cluster_name)
                cluster_id = existing.id if existing else str(uuid.uuid4())
                parameters = dict(entry.parameters)

                # Keep previously stored secret paths when re-registering unless
                # the same input file was uploaded again in this request.
                if existing:
                    old_params = existing.parsed_parameters()
                    for param_name in PATH_PARAMETER_NAMES:
                        old_path = old_params.get(param_name)
                        if (
                            old_path
                            and isinstance(old_path, str)
                            and os.path.isfile(old_path)
                            and param_name not in {
                                INPUT_FILE_SPECS[f][0] for f in input_uploads
                            }
                        ):
                            parameters[param_name] = old_path

                parameters, file_msgs = copy_pending_uploads(
                    SECRETS_DIR, pending_dir, cluster_id, parameters
                )
                for msg in file_msgs:
                    log_lines.append(msg)

                registration_log = _build_registration_log(
                    entry,
                    registered_by,
                    description,
                    original_filename,
                    log_lines,
                    registered_at,
                )

                if existing:
                    old_stored = existing.ciq_stored_as
                    existing.cluster_type = entry.cluster_type
                    existing.description = description
                    existing.ciq_filename = original_filename
                    existing.ciq_stored_as = unique_filename
                    existing.ciq_parameters = json.dumps(parameters)
                    existing.registration_log = registration_log
                    existing.status = "registered"
                    existing.registered_at = registered_at
                    existing.registered_by = registered_by
                    cluster = existing
                    reregistered_count += 1
                    if (
                        old_stored
                        and old_stored != unique_filename
                        and os.path.isfile(os.path.join(UPLOAD_DIR, old_stored))
                    ):
                        try:
                            os.remove(os.path.join(UPLOAD_DIR, old_stored))
                        except OSError:
                            pass
                else:
                    cluster = Cluster(
                        id=cluster_id,
                        cluster_name=entry.cluster_name,
                        cluster_type=entry.cluster_type,
                        description=description,
                        ciq_filename=original_filename,
                        ciq_stored_as=unique_filename,
                        ciq_parameters=json.dumps(parameters),
                        registration_log=registration_log,
                        status="registered",
                        registered_at=registered_at,
                        registered_by=registered_by,
                    )
                    db.session.add(cluster)

                write_text_log(
                    REGISTRATION_LOGS_DIR,
                    f"{cluster_id}-{secure_filename(entry.cluster_name) or 'cluster'}.log",
                    cluster.registration_log,
                )
                saved_clusters.append(cluster)

            db.session.commit()

            cluster_records = [c.to_dict() for c in saved_clusters]
            labels = ", ".join(c["cluster_type_label"] for c in cluster_records)
            if reregistered_count and reregistered_count == len(cluster_records):
                message = (
                    f"Successfully re-registered {len(cluster_records)} "
                    f"cluster(s): {labels}"
                )
            elif reregistered_count:
                message = (
                    f"Successfully registered {len(cluster_records)} cluster(s) "
                    f"({reregistered_count} re-registered): {labels}"
                )
            else:
                message = (
                    f"Successfully registered {len(cluster_records)} cluster(s): {labels}"
                )
            yield _stream_event(
                "success",
                {
                    "message": message,
                    "clusters": cluster_records,
                    "cluster": cluster_records[0] if len(cluster_records) == 1 else None,
                    "reregistered_count": reregistered_count,
                },
            )
        finally:
            cleanup_pending(pending_dir)

    return Response(
        stream_with_context(generate()),
        mimetype="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


def _specs_for_cluster(cluster):
    """Return the correct input file specs based on cluster type."""
    if cluster.cluster_type == "ocp":
        return OCP_INPUT_FILE_SPECS
    return INPUT_FILE_SPECS


def _extract_files_for_specs(request_files, specs):
    """Collect recognized input-file uploads matching the given specs."""
    found = {}
    for field in specs:
        storage = request_files.get(field)
        if storage is not None and storage.filename:
            found[field] = storage
    return found


def _save_files_for_specs(secrets_root, cluster_id, files_by_field, parameters, specs):
    """Save uploaded files using the correct specs and update CIQ path parameters."""
    if not files_by_field:
        return parameters, []
    cluster_dir = os.path.join(secrets_root, cluster_id)
    os.makedirs(cluster_dir, exist_ok=True)
    updated = dict(parameters)
    messages = []
    for field, storage in files_by_field.items():
        if field not in specs:
            continue
        if storage is None or not getattr(storage, "filename", None):
            continue
        param_name, stored_name = specs[field]
        dest = os.path.abspath(os.path.join(cluster_dir, stored_name))
        storage.save(dest)
        try:
            os.chmod(dest, 0o600)
        except OSError:
            pass
        original = os.path.basename(storage.filename)
        updated[param_name] = dest
        messages.append(f"Stored {param_name} → {dest} (from {original})")
    return updated, messages


def _list_files_for_specs(secrets_root, cluster_id, parameters, specs):
    """List input file status for the correct specs."""
    cluster_dir = os.path.join(secrets_root, cluster_id)
    rows = []
    for field, (param_name, stored_name) in specs.items():
        stored_path = os.path.abspath(os.path.join(cluster_dir, stored_name))
        uploaded = os.path.isfile(stored_path)
        rows.append({
            "field": field,
            "parameter": param_name,
            "uploaded": uploaded,
            "stored_path": stored_path if uploaded else None,
            "configured_path": (parameters.get(param_name) or "").strip() or None,
        })
    return rows


@app.route("/api/clusters/<cluster_id>/input-files", methods=["GET"])
def get_cluster_input_files(cluster_id: str):
    auth_error = require_auth()
    if auth_error:
        return auth_error

    cluster = db.session.get(Cluster, cluster_id)
    if not cluster:
        return jsonify({"error": "Cluster not found"}), 404

    specs = _specs_for_cluster(cluster)
    files = _list_files_for_specs(
        SECRETS_DIR, cluster.id, cluster.parsed_parameters(), specs
    )
    return jsonify(
        {
            "cluster_id": cluster.id,
            "cluster_name": cluster.cluster_name,
            "cluster_type": cluster.cluster_type,
            "files": files,
            "accepted_fields": [
                {
                    "field": field,
                    "parameter": param,
                    "stored_filename": stored,
                }
                for field, (param, stored) in specs.items()
            ],
        }
    )


@app.route("/api/clusters/<cluster_id>/input-files", methods=["POST"])
def upload_cluster_input_files(cluster_id: str):
    """Upload or replace path-based input files after registration."""
    auth_error = require_auth()
    if auth_error:
        return auth_error

    cluster = db.session.get(Cluster, cluster_id)
    if not cluster:
        return jsonify({"error": "Cluster not found"}), 404

    specs = _specs_for_cluster(cluster)
    uploads = _extract_files_for_specs(request.files, specs)
    if not uploads:
        return jsonify(
            {
                "error": (
                    "No input files provided. Upload one or more of: "
                    + ", ".join(specs.keys())
                )
            }
        ), 400

    parameters = cluster.parsed_parameters()
    parameters, messages = _save_files_for_specs(
        SECRETS_DIR, cluster.id, uploads, parameters, specs
    )
    cluster.ciq_parameters = json.dumps(parameters)
    db.session.commit()

    return jsonify(
        {
            "message": f"Updated {len(messages)} input file(s).",
            "updates": messages,
            "cluster": cluster.to_dict(),
            "files": _list_files_for_specs(
                SECRETS_DIR, cluster.id, cluster.parsed_parameters(), specs
            ),
        }
    )


@app.route("/api/clusters/<cluster_id>/registration-log", methods=["GET"])
def get_registration_log(cluster_id: str):
    auth_error = require_auth()
    if auth_error:
        return auth_error

    cluster = db.session.get(Cluster, cluster_id)
    if not cluster:
        return jsonify({"error": "Cluster not found"}), 404

    if not cluster.registration_log:
        return jsonify({"error": "Registration log not available for this cluster."}), 404

    if request.args.get("download") == "1":
        safe_name = secure_filename(cluster.cluster_name) or "cluster"
        filename = f"{safe_name}-registration.log"
        return Response(
            cluster.registration_log,
            mimetype="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-store",
            },
        )

    registered_at = cluster.registered_at
    if registered_at.tzinfo is None:
        registered_at = registered_at.replace(tzinfo=timezone.utc)

    content = cluster.registration_log
    return jsonify(
        {
            "cluster_id": cluster.id,
            "cluster_name": cluster.cluster_name,
            "cluster_type_label": cluster.cluster_type_label,
            "content": content,
            "line_count": content.count("\n") + (1 if content else 0),
            "byte_count": len(content.encode("utf-8")),
            "updated_at": registered_at.isoformat().replace("+00:00", "Z"),
        }
    )


@app.route("/api/clusters/<cluster_id>", methods=["GET"])
def get_cluster(cluster_id: str):
    auth_error = require_auth()
    if auth_error:
        return auth_error

    cluster = db.session.get(Cluster, cluster_id)
    if not cluster:
        return jsonify({"error": "Cluster not found"}), 404

    return jsonify({"cluster": cluster.to_dict()})


@app.route("/api/clusters/<cluster_id>", methods=["DELETE"])
def delete_cluster(cluster_id: str):
    auth_error = require_auth()
    if auth_error:
        return auth_error

    cluster = db.session.get(Cluster, cluster_id)
    if not cluster:
        return jsonify({"error": "Cluster not found"}), 404

    cluster_name = cluster.cluster_name

    # Remove stored CIQ workbook
    if cluster.ciq_stored_as:
        ciq_path = os.path.join(UPLOAD_DIR, cluster.ciq_stored_as)
        if os.path.isfile(ciq_path):
            try:
                os.remove(ciq_path)
            except OSError:
                pass

    # Remove cluster secrets directory
    secrets_cluster_dir = os.path.join(SECRETS_DIR, str(cluster.id))
    if os.path.isdir(secrets_cluster_dir):
        import shutil
        shutil.rmtree(secrets_cluster_dir, ignore_errors=True)

    # Remove installation execution records
    RhosoInstallationExecution.query.filter_by(cluster_id=cluster.id).delete()
    OcpInstallationExecution.query.filter_by(cluster_id=cluster.id).delete()

    db.session.delete(cluster)
    db.session.commit()

    return jsonify({
        "message": f"Cluster '{cluster_name}' deleted successfully.",
        "cluster_id": cluster_id,
    })


@app.route("/api/rhoso-installations/run", methods=["POST"])
def run_rhoso_installation():
    auth_error = require_auth()
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    cluster_name = data.get("cluster_name", "").strip()
    rhoso_version = data.get("rhoso_version", "").strip()
    tasks = data.get("tasks") or []
    # execution_mode: generate | deploy | full
    #   generate — render templates only (Generate Manifests for Review)
    #   deploy   — apply using reviewed artifacts (skip re-render by default)
    #   full     — re-render then apply (legacy one-shot)
    execution_mode = (data.get("execution_mode") or "deploy").strip().lower()
    re_render = bool(data.get("re_render_manifests", False))

    if not cluster_name:
        return jsonify({"error": "cluster_name is required"}), 400
    if not rhoso_version:
        return jsonify({"error": "rhoso_version is required"}), 400
    if not isinstance(tasks, list) or not tasks:
        return jsonify({"error": "At least one task is required"}), 400
    if execution_mode not in ("generate", "deploy", "full"):
        return jsonify(
            {"error": "execution_mode must be generate, deploy, or full"}
        ), 400

    invalid_tasks = [task for task in tasks if task not in RHOSO_INSTALLATION_TASKS]
    if invalid_tasks:
        return jsonify({"error": f"Invalid task(s): {', '.join(invalid_tasks)}"}), 400

    if execution_mode == "generate":
        if tasks != [RHOSO_GENERATE_TASK]:
            return jsonify(
                {
                    "error": (
                        f"Generate mode must run only '{RHOSO_GENERATE_TASK}'."
                    )
                }
            ), 400
        playbook_kwargs = {
            "rhoso_apply_manifests": False,
            "rhoso_skip_generation": False,
        }
        start_message = (
            "Generating manifests for review on environment '{cluster_name}' "
            "({count} task)."
        )
        success_message = (
            "Manifest generation complete for '{cluster_name}'. "
            "Review artifacts, then run deployment tasks."
        )
    elif execution_mode == "full":
        if RHOSO_GENERATE_TASK in tasks:
            return jsonify(
                {
                    "error": (
                        f"Do not include '{RHOSO_GENERATE_TASK}' in full/deploy runs; "
                        "use generate mode first."
                    )
                }
            ), 400
        playbook_kwargs = {
            "rhoso_apply_manifests": True,
            "rhoso_skip_generation": False,
        }
        start_message = (
            "Starting {count} RHOSO installation task(s) "
            "on environment '{cluster_name}' (re-render + apply)."
        )
        success_message = (
            "Successfully completed {count} RHOSO installation task(s) "
            "on environment '{cluster_name}'."
        )
    else:
        # deploy — use reviewed files unless engineer opts into re-render
        if RHOSO_GENERATE_TASK in tasks:
            return jsonify(
                {
                    "error": (
                        f"Do not include '{RHOSO_GENERATE_TASK}' in deploy runs; "
                        "use the Generate button for that."
                    )
                }
            ), 400
        playbook_kwargs = {
            "rhoso_apply_manifests": True,
            "rhoso_skip_generation": not re_render,
        }
        if re_render:
            start_message = (
                "Starting {count} RHOSO deployment task(s) "
                "on environment '{cluster_name}' (re-render then apply)."
            )
        else:
            start_message = (
                "Starting {count} RHOSO deployment task(s) "
                "on environment '{cluster_name}' (using reviewed manifests)."
            )
        success_message = (
            "Successfully completed {count} RHOSO deployment task(s) "
            "on environment '{cluster_name}'."
        )

    cluster = Cluster.query.filter_by(
        cluster_name=cluster_name, cluster_type="rhoso"
    ).first()
    if not cluster:
        return jsonify(
            {"error": f"RHOSO environment '{cluster_name}' is not registered."}
        ), 404

    triggered_by = session.get("username", "unknown")
    ciq_file_path = os.path.join(app.config["UPLOAD_FOLDER"], cluster.ciq_stored_as)
    ciq_parameter_overrides = path_overrides_from_parameters(cluster.parsed_parameters())

    def generate():
        yield from _stream_playbook_task_executions(
            cluster_name=cluster_name,
            ocp_version=rhoso_version,
            tasks=tasks,
            triggered_by=triggered_by,
            cluster=cluster,
            ciq_file_path=ciq_file_path,
            execution_model=RhosoInstallationExecution,
            task_field="task_name",
            stream_playbook_fn=stream_rhoso_installation_playbook,
            log_title="CPAT RHOSO Installation Execution Log",
            task_label="Task",
            entity_label="RHOSO installation task",
            start_message=start_message,
            success_message=success_message,
            version_field="rhoso_version",
            version_label="RHOSO Version",
            ciq_parameter_overrides=ciq_parameter_overrides or None,
            playbook_kwargs=playbook_kwargs,
        )

    return Response(
        stream_with_context(generate()),
        mimetype="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/api/clusters/<cluster_id>/artifacts", methods=["GET"])
def list_cluster_manifest_artifacts(cluster_id):
    auth_error = require_auth()
    if auth_error:
        return auth_error

    cluster = db.session.get(Cluster, cluster_id)
    if not cluster:
        return jsonify({"error": "Cluster not found"}), 404

    artifacts = list_cluster_artifacts(cluster.cluster_name)
    return jsonify(
        {
            "cluster_id": cluster.id,
            "cluster_name": cluster.cluster_name,
            "cluster_type": cluster.cluster_type,
            "artifacts_dir": cluster_artifacts_dir(cluster.cluster_name),
            "artifacts": artifacts,
            "total": len(artifacts),
        }
    )


@app.route("/api/clusters/<cluster_id>/artifacts/download-all", methods=["GET"])
def download_all_cluster_artifacts(cluster_id):
    auth_error = require_auth()
    if auth_error:
        return auth_error

    cluster = db.session.get(Cluster, cluster_id)
    if not cluster:
        return jsonify({"error": "Cluster not found"}), 404

    artifacts = list_cluster_artifacts(cluster.cluster_name)
    if not artifacts:
        return jsonify({"error": "No manifest artifacts to download"}), 404

    art_dir = cluster_artifacts_dir(cluster.cluster_name)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in artifacts:
            file_path = os.path.join(art_dir, item["name"])
            if os.path.isfile(file_path):
                zf.write(file_path, item["name"])

    buf.seek(0)
    safe_name = secure_filename(cluster.cluster_name) or cluster.cluster_type
    return send_file(
        buf,
        as_attachment=True,
        download_name=f"{safe_name}-manifests.zip",
        mimetype="application/zip",
    )


@app.route("/api/clusters/<cluster_id>/artifacts/<path:filename>", methods=["GET"])
def get_cluster_manifest_artifact(cluster_id, filename):
    auth_error = require_auth()
    if auth_error:
        return auth_error

    cluster = db.session.get(Cluster, cluster_id)
    if not cluster:
        return jsonify({"error": "Cluster not found"}), 404

    try:
        path, text = read_cluster_artifact(cluster.cluster_name, filename)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except FileNotFoundError:
        return jsonify({"error": f"Artifact '{filename}' not found"}), 404

    if request.args.get("download") == "1":
        return send_file(
            path,
            as_attachment=True,
            download_name=os.path.basename(path),
            mimetype="text/plain; charset=utf-8",
        )

    # Use "text" (not "content") — some clients/proxies mishandle a top-level
    # JSON key named "content".
    return jsonify(
        {
            "cluster_id": cluster.id,
            "cluster_name": cluster.cluster_name,
            "name": os.path.basename(path),
            "text": text,
            "content": text,  # backward compatible
            "size": len(text),
        }
    )


@app.route("/api/rhoso-installations", methods=["GET"])
def list_rhoso_installations():
    auth_error = require_auth()
    if auth_error:
        return auth_error

    cluster_name = request.args.get("cluster_name", "").strip()
    status = request.args.get("status", "").strip()
    query = RhosoInstallationExecution.query.order_by(
        RhosoInstallationExecution.started_at.desc()
    )
    if cluster_name:
        query = query.filter_by(cluster_name=cluster_name)
    if status:
        query = query.filter_by(status=status)

    executions = query.all()
    return jsonify(
        {
            "executions": [execution.to_dict() for execution in executions],
            "total": len(executions),
        }
    )


@app.route("/api/rhoso-installations/<execution_id>", methods=["GET"])
def get_rhoso_installation_status(execution_id: str):
    """Return status and metadata for a single RHOSO installation task execution."""
    auth_error = require_auth()
    if auth_error:
        return auth_error

    execution = db.session.get(RhosoInstallationExecution, execution_id)
    if not execution:
        return jsonify({"error": "Installation execution not found"}), 404

    return jsonify({"execution": execution.to_dict()})


@app.route("/api/rhoso-installations/<execution_id>/log", methods=["GET"])
def get_rhoso_installation_log(execution_id: str):
    auth_error = require_auth()
    if auth_error:
        return auth_error

    execution = db.session.get(RhosoInstallationExecution, execution_id)
    if not execution:
        return jsonify({"error": "Installation execution not found"}), 404

    if not execution.execution_log:
        return jsonify({"error": "Execution log not available yet."}), 404

    if request.args.get("download") == "1":
        safe_cluster = secure_filename(execution.cluster_name) or "cluster"
        safe_task = secure_filename(execution.task_name.replace(" ", "-")) or "task"
        filename = f"{safe_cluster}-{safe_task}-rhoso-installation.log"
        return Response(
            execution.execution_log,
            mimetype="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-store",
            },
        )

    started_at = execution.started_at
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)

    content = execution.execution_log
    return jsonify(
        {
            "execution_id": execution.id,
            "cluster_name": execution.cluster_name,
            "rhoso_version": execution.rhoso_version,
            "ocp_version": execution.rhoso_version,
            "task_name": execution.task_name,
            "status": execution.status,
            "content": content,
            "line_count": content.count("\n") + (1 if content else 0),
            "byte_count": len(content.encode("utf-8")),
            "updated_at": started_at.isoformat().replace("+00:00", "Z"),
        }
    )


# =========================================================================
# OCP Installation API
# =========================================================================

OCP_INPUT_FILE_SPECS: dict[str, tuple[str, str]] = {
    "ocp_pull_secret": ("Pull Secret Path", "pull-secret.json"),
    "ocp_ssh_public_key": ("SSH Public Key Path", "ssh-public-key"),
    "ocp_bastion_ssh_key": ("Bastion SSH Private Key Path", "bastion-ssh-key"),
    "ocp_mirror_ca": ("Mirror Registry CA Path", "mirror-ca.crt"),
    "ocp_mirror_pull_secret": ("Mirror Pull Secret Path", "mirror-pull-secret.json"),
}


@app.route("/api/ocp/clusters/register", methods=["POST"])
def register_ocp_cluster():
    """Register an OCP cluster from an OCP CIQ workbook.

    Streams Ansible validation logs (like RHOSO registration) so the user
    sees live schema-based validation of every parameter, BMC host,
    NMState interface, and DNS record.
    """
    auth_error = require_auth()
    if auth_error:
        return auth_error

    description = request.form.get("description", "").strip()
    allow_reregister = request.form.get("reregister", "").strip().lower() in {
        "1", "true", "yes", "on",
    }

    if "ciq_file" not in request.files:
        return jsonify({"error": "OCP CIQ file is required"}), 400

    file = request.files["ciq_file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "CIQ file must be an .xlsx workbook"}), 400

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(SECRETS_DIR, exist_ok=True)

    original_filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    file.save(file_path)

    try:
        parsed = parse_ocp_ciq_xlsx(file_path)
    except OcpCiqParseError as exc:
        os.remove(file_path)
        return jsonify({"error": str(exc)}), 400

    existing = Cluster.query.filter_by(cluster_name=parsed.cluster_name).first()
    if existing and not allow_reregister:
        os.remove(file_path)
        return jsonify(
            {
                "error": (
                    f"Cluster '{parsed.cluster_name}' is already registered. "
                    "Enable 'Re-register existing cluster' to update."
                )
            }
        ), 409

    registered_by = session.get("username", "unknown")
    is_update = existing is not None

    def generate():
        try:
            action = "Re-registering" if is_update else "Registering"
            log_lines = [
                f"{action} OCP cluster: {parsed.cluster_name}",
                f"CIQ file: {original_filename}",
                f"Install Method: {parsed.parameters.get('Install Method', 'unknown')}",
                f"Deployment Mode: {parsed.parameters.get('Deployment Mode', 'unknown')}",
                f"OCP Version: {parsed.parameters.get('OCP Version', 'unknown')}",
                "",
                f"Parameters parsed: {len(parsed.parameters)}",
                f"BMC hosts:         {len(parsed.bmc_hosts)}",
                f"NMState interfaces:{len(parsed.nmstate_interfaces)}",
                f"DNS records:       {len(parsed.dns_records)}",
                "",
            ]

            yield _stream_event(
                "info",
                {
                    "message": (
                        f"Parsed OCP CIQ: {parsed.cluster_name} "
                        f"({len(parsed.parameters)} parameters, "
                        f"{len(parsed.bmc_hosts)} BMC hosts, "
                        f"{len(parsed.nmstate_interfaces)} NMState interfaces, "
                        f"{len(parsed.dns_records)} DNS records)"
                    ),
                    "cluster_name": parsed.cluster_name,
                    "cluster_type": "ocp",
                },
            )

            yield _stream_event(
                "info",
                {"message": "Running Ansible schema-based CIQ validation..."},
            )

            # Run Ansible validation playbook with live streaming
            playbook_failed = False
            parsed_data = {
                "cluster_name": parsed.cluster_name,
                "parameters": dict(parsed.parameters),
                "bmc_hosts": parsed.bmc_hosts,
                "nmstate_interfaces": parsed.nmstate_interfaces,
                "compute_nodes": parsed.compute_nodes,
                "dns_records": parsed.dns_records,
            }
            for event_type, payload in stream_register_ocp_playbook(parsed_data):
                if event_type == "log":
                    log_lines.append(payload["line"])
                    yield _stream_event("log", payload)
                elif event_type == "complete":
                    line = payload.get("message", "Validation complete.")
                    log_lines.append(line)
                    yield _stream_event("log", {"line": line})
                elif event_type == "error":
                    playbook_failed = True
                    log_lines.append(
                        f"VALIDATION FAILED: {payload.get('message', 'Playbook failed.')}"
                    )
                    yield _stream_event("error", payload)

            if playbook_failed:
                log_lines.append("")
                log_lines.append("OCP CIQ validation FAILED. Fix the errors above and re-register.")
                # Still save the cluster with validation_failed status so user can see log
                registered_at = datetime.now(timezone.utc)
                cluster_id = existing.id if is_update else str(uuid.uuid4())

                parameters = dict(parsed.parameters)
                if parsed.bmc_hosts:
                    parameters["_ocp_bmc_hosts_json"] = json.dumps(parsed.bmc_hosts)
                if parsed.nmstate_interfaces:
                    parameters["_ocp_nmstate_interfaces_json"] = json.dumps(parsed.nmstate_interfaces)
                if parsed.compute_nodes:
                    parameters["_ocp_compute_nodes_json"] = json.dumps(parsed.compute_nodes)
                if parsed.dns_records:
                    parameters["_ocp_dns_records_json"] = json.dumps(parsed.dns_records)

                registration_log = _build_registration_log(
                    parsed, registered_by, description, original_filename,
                    log_lines, registered_at,
                )

                if is_update:
                    existing.cluster_type = "ocp"
                    existing.description = description
                    existing.ciq_filename = original_filename
                    existing.ciq_stored_as = unique_filename
                    existing.ciq_parameters = json.dumps(parameters)
                    existing.registration_log = registration_log
                    existing.status = "validation_failed"
                    existing.registered_at = registered_at
                    existing.registered_by = registered_by
                    cluster = existing
                else:
                    cluster = Cluster(
                        id=cluster_id,
                        cluster_name=parsed.cluster_name,
                        cluster_type="ocp",
                        description=description,
                        ciq_filename=original_filename,
                        ciq_stored_as=unique_filename,
                        ciq_parameters=json.dumps(parameters),
                        registration_log=registration_log,
                        status="validation_failed",
                        registered_at=registered_at,
                        registered_by=registered_by,
                    )
                    db.session.add(cluster)
                db.session.commit()

                yield _stream_event(
                    "error",
                    {
                        "message": (
                            f"OCP CIQ validation failed for '{parsed.cluster_name}'. "
                            "Fix the errors in the CIQ and re-register."
                        ),
                        "fatal": True,
                    },
                )
                return

            # Validation passed — read back enriched row tables (MACs, etc.)
            _enriched_bmc_hosts = parsed.bmc_hosts
            _enriched_nmstate = parsed.nmstate_interfaces
            _enriched_compute = parsed.compute_nodes
            _enriched_dns = parsed.dns_records
            _enriched_path = "/tmp/cpat_enriched_ciq.json"
            try:
                if os.path.isfile(_enriched_path):
                    with open(_enriched_path) as _ef:
                        _enriched = json.load(_ef)
                    _enriched_bmc_hosts = _enriched.get("ocp_bmc_hosts", _enriched_bmc_hosts)
                    _enriched_nmstate = _enriched.get("ocp_nmstate_interfaces", _enriched_nmstate)
                    _enriched_compute = _enriched.get("ocp_compute_nodes", _enriched_compute)
                    _enriched_dns = _enriched.get("ocp_dns_records", _enriched_dns)
                    os.remove(_enriched_path)
                    log_lines.append("Enriched CIQ data loaded (Redfish MAC auto-discovery applied).")
            except Exception as _enr_err:
                log_lines.append(f"Note: Could not load enriched CIQ: {_enr_err}")

            # Save cluster
            log_lines.append("")
            log_lines.append(
                "Re-registration completed successfully."
                if is_update
                else "Registration completed successfully."
            )
            registered_at = datetime.now(timezone.utc)
            cluster_id = existing.id if is_update else str(uuid.uuid4())

            parameters = dict(parsed.parameters)
            if _enriched_bmc_hosts:
                parameters["_ocp_bmc_hosts_json"] = json.dumps(_enriched_bmc_hosts)
            if _enriched_nmstate:
                parameters["_ocp_nmstate_interfaces_json"] = json.dumps(_enriched_nmstate)
            if _enriched_compute:
                parameters["_ocp_compute_nodes_json"] = json.dumps(_enriched_compute)
            if _enriched_dns:
                parameters["_ocp_dns_records_json"] = json.dumps(_enriched_dns)

            registration_log = _build_registration_log(
                parsed, registered_by, description, original_filename,
                log_lines, registered_at,
            )

            if is_update:
                old_stored = existing.ciq_stored_as
                existing.cluster_type = "ocp"
                existing.description = description
                existing.ciq_filename = original_filename
                existing.ciq_stored_as = unique_filename
                existing.ciq_parameters = json.dumps(parameters)
                existing.registration_log = registration_log
                existing.status = "registered"
                existing.registered_at = registered_at
                existing.registered_by = registered_by
                cluster = existing
                if (
                    old_stored
                    and old_stored != unique_filename
                    and os.path.isfile(os.path.join(UPLOAD_DIR, old_stored))
                ):
                    try:
                        os.remove(os.path.join(UPLOAD_DIR, old_stored))
                    except OSError:
                        pass
            else:
                cluster = Cluster(
                    id=cluster_id,
                    cluster_name=parsed.cluster_name,
                    cluster_type="ocp",
                    description=description,
                    ciq_filename=original_filename,
                    ciq_stored_as=unique_filename,
                    ciq_parameters=json.dumps(parameters),
                    registration_log=registration_log,
                    status="registered",
                    registered_at=registered_at,
                    registered_by=registered_by,
                )
                db.session.add(cluster)

            db.session.commit()

            yield _stream_event(
                "success",
                {
                    "message": (
                        f"OCP cluster '{parsed.cluster_name}' "
                        f"{'re-registered' if is_update else 'registered'} successfully. "
                        "All CIQ validations passed."
                    ),
                    "cluster": cluster.to_dict(),
                    "parsed_summary": {
                        "cluster_name": parsed.cluster_name,
                        "source_table": parsed.source_table,
                        "source_sheet": parsed.source_sheet,
                        "parameter_count": len(parsed.parameters),
                        "bmc_host_count": len(parsed.bmc_hosts),
                        "nmstate_interface_count": len(parsed.nmstate_interfaces),
                        "compute_node_count": len(parsed.compute_nodes),
                        "dns_record_count": len(parsed.dns_records),
                    },
                },
            )

        except Exception as exc:
            yield _stream_event(
                "error",
                {"message": f"Registration failed: {exc}", "fatal": True},
            )

    return Response(
        stream_with_context(generate()),
        mimetype="application/x-ndjson",
    )


@app.route("/api/ocp-installations/tasks", methods=["GET"])
def list_ocp_installation_tasks():
    """Return the list of available OCP installation tasks."""
    auth_error = require_auth()
    if auth_error:
        return auth_error

    return jsonify(
        {
            "tasks": list(OCP_INSTALLATION_TASK_TAGS.keys()),
            "generate_task": OCP_GENERATE_TASK,
            "total": len(OCP_INSTALLATION_TASK_TAGS),
        }
    )


@app.route("/api/ocp-installations/run", methods=["POST"])
def run_ocp_installation():
    """Run OCP installation task(s) on a registered OCP cluster."""
    auth_error = require_auth()
    if auth_error:
        return auth_error

    data = request.get_json(silent=True) or {}
    cluster_name = data.get("cluster_name", "").strip()
    ocp_version = data.get("ocp_version", "").strip()
    tasks = data.get("tasks") or []
    execution_mode = (data.get("execution_mode") or "deploy").strip().lower()
    re_render = bool(data.get("re_render_manifests", False))

    if not cluster_name:
        return jsonify({"error": "cluster_name is required"}), 400
    if not ocp_version:
        return jsonify({"error": "ocp_version is required"}), 400
    if not isinstance(tasks, list) or not tasks:
        return jsonify({"error": "At least one task is required"}), 400
    if execution_mode not in ("generate", "deploy", "full"):
        return jsonify(
            {"error": "execution_mode must be generate, deploy, or full"}
        ), 400

    invalid_tasks = [task for task in tasks if task not in OCP_INSTALLATION_TASKS]
    if invalid_tasks:
        return jsonify({"error": f"Invalid OCP task(s): {', '.join(invalid_tasks)}"}), 400

    if execution_mode == "generate":
        if tasks != [OCP_GENERATE_TASK]:
            return jsonify(
                {"error": f"Generate mode must run only '{OCP_GENERATE_TASK}'."}
            ), 400
        playbook_kwargs = {
            "ocp_apply_manifests": False,
            "ocp_skip_generation": False,
        }
        start_message = (
            "Generating OCP manifests for review on cluster '{cluster_name}' "
            "({count} task)."
        )
        success_message = (
            "OCP manifest generation complete for '{cluster_name}'. "
            "Review artifacts, then run deployment tasks."
        )
    elif execution_mode == "full":
        if OCP_GENERATE_TASK in tasks:
            return jsonify(
                {
                    "error": (
                        f"Do not include '{OCP_GENERATE_TASK}' in full/deploy runs; "
                        "use generate mode first."
                    )
                }
            ), 400
        playbook_kwargs = {
            "ocp_apply_manifests": True,
            "ocp_skip_generation": False,
        }
        start_message = (
            "Starting {count} OCP installation task(s) "
            "on cluster '{cluster_name}' (re-render + apply)."
        )
        success_message = (
            "Successfully completed {count} OCP installation task(s) "
            "on cluster '{cluster_name}'."
        )
    else:
        if OCP_GENERATE_TASK in tasks:
            return jsonify(
                {
                    "error": (
                        f"Do not include '{OCP_GENERATE_TASK}' in deploy runs; "
                        "use the Generate button for that."
                    )
                }
            ), 400
        playbook_kwargs = {
            "ocp_apply_manifests": True,
            "ocp_skip_generation": not re_render,
        }
        if re_render:
            start_message = (
                "Starting {count} OCP deployment task(s) "
                "on cluster '{cluster_name}' (re-render then apply)."
            )
        else:
            start_message = (
                "Starting {count} OCP deployment task(s) "
                "on cluster '{cluster_name}' (using reviewed manifests)."
            )
        success_message = (
            "Successfully completed {count} OCP deployment task(s) "
            "on cluster '{cluster_name}'."
        )

    cluster = Cluster.query.filter_by(
        cluster_name=cluster_name, cluster_type="ocp"
    ).first()
    if not cluster:
        return jsonify(
            {"error": f"OCP cluster '{cluster_name}' is not registered."}
        ), 404

    triggered_by = session.get("username", "unknown")
    ciq_file_path = os.path.join(app.config["UPLOAD_FOLDER"], cluster.ciq_stored_as)

    # Build CIQ parameter overrides from stored parameters
    stored_params = cluster.parsed_parameters()
    ciq_parameter_overrides: dict[str, Any] = {}

    # Pass the full CIQ parameters dict so Ansible _validate_ciq.yml can
    # perform schema-based validation during installation tasks too.
    ocp_ciq_dict: dict[str, str] = {}
    for param_name, param_value in stored_params.items():
        if param_name.startswith("_ocp_") and param_name.endswith("_json"):
            # Row tables — pass as structured data
            # e.g. "_ocp_bmc_hosts_json" → "ocp_bmc_hosts"
            var_name = param_name.removeprefix("_").removesuffix("_json")
            try:
                ciq_parameter_overrides[var_name] = json.loads(param_value)
            except (json.JSONDecodeError, TypeError):
                pass
        else:
            # All parameters (including path params like Pull Secret Path)
            # go into ocp_ciq_dict so _load_ciq_context.yml can resolve them
            ocp_ciq_dict[param_name] = param_value

    ciq_parameter_overrides["ocp_ciq"] = ocp_ciq_dict

    # Create execution records up-front so we can return them immediately
    execution_records = []
    execution_ids = []
    for task_name in tasks:
        started_at = datetime.now(timezone.utc)
        exec_id = str(uuid.uuid4())
        execution = OcpInstallationExecution(
            id=exec_id,
            cluster_id=cluster.id,
            cluster_name=cluster_name,
            ocp_version=ocp_version,
            status="in_progress",
            triggered_by=triggered_by,
            started_at=started_at,
            task_name=task_name,
        )
        db.session.add(execution)
        db.session.commit()
        execution_records.append(execution.to_dict())
        execution_ids.append(exec_id)

    # Run tasks in a background thread — no long-lived HTTP connection
    thread = threading.Thread(
        target=_run_tasks_in_background,
        args=(app,),
        kwargs=dict(
            cluster_name=cluster_name,
            ocp_version=ocp_version,
            tasks=tasks,
            execution_ids=execution_ids,
            triggered_by=triggered_by,
            cluster_id=cluster.id,
            ciq_file_path=ciq_file_path,
            execution_model=OcpInstallationExecution,
            task_field="task_name",
            stream_playbook_fn=stream_ocp_installation_playbook,
            log_title="CPAT OCP Installation Execution Log",
            task_label="OCP Task",
            entity_label="OCP installation task",
            version_field="ocp_version",
            version_label="OCP Version",
            ciq_parameter_overrides=ciq_parameter_overrides or None,
            playbook_kwargs=playbook_kwargs,
        ),
        daemon=True,
    )
    thread.start()

    return jsonify({
        "message": start_message.format(
            count=len(execution_records),
            cluster_name=cluster_name,
        ),
        "executions": execution_records,
    }), 202


@app.route("/api/ocp-installations", methods=["GET"])
def list_ocp_installations():
    """List OCP installation execution records."""
    auth_error = require_auth()
    if auth_error:
        return auth_error

    cluster_name = request.args.get("cluster_name", "").strip()
    status = request.args.get("status", "").strip()
    query = OcpInstallationExecution.query.order_by(
        OcpInstallationExecution.started_at.desc()
    )
    if cluster_name:
        query = query.filter_by(cluster_name=cluster_name)
    if status:
        query = query.filter_by(status=status)

    executions = query.all()
    result_list = []
    for execution in executions:
        d = execution.to_dict()
        d["has_command_log"] = execution.task_name in OCP_TASK_COMMAND_LOGS
        result_list.append(d)
    return jsonify(
        {
            "executions": result_list,
            "total": len(result_list),
        }
    )


@app.route("/api/ocp-installations/<execution_id>", methods=["GET"])
def get_ocp_installation_status(execution_id: str):
    """Return status and metadata for a single OCP installation task execution."""
    auth_error = require_auth()
    if auth_error:
        return auth_error

    execution = db.session.get(OcpInstallationExecution, execution_id)
    if not execution:
        return jsonify({"error": "OCP installation execution not found"}), 404

    return jsonify({"execution": execution.to_dict()})


@app.route("/api/ocp-installations/<execution_id>/log", methods=["GET"])
def get_ocp_installation_log(execution_id: str):
    """Return the execution log for an OCP installation task."""
    auth_error = require_auth()
    if auth_error:
        return auth_error

    execution = db.session.get(OcpInstallationExecution, execution_id)
    if not execution:
        return jsonify({"error": "OCP installation execution not found"}), 404

    if not execution.execution_log:
        return jsonify({"error": "Execution log not available yet."}), 404

    if request.args.get("download") == "1":
        safe_cluster = secure_filename(execution.cluster_name) or "cluster"
        safe_task = secure_filename(execution.task_name.replace(" ", "-")) or "task"
        filename = f"{safe_cluster}-{safe_task}-ocp-installation.log"
        return Response(
            execution.execution_log,
            mimetype="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-store",
            },
        )

    started_at = execution.started_at
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)

    content = execution.execution_log
    return jsonify(
        {
            "execution_id": execution.id,
            "cluster_name": execution.cluster_name,
            "ocp_version": execution.ocp_version,
            "task_name": execution.task_name,
            "status": execution.status,
            "content": content,
            "line_count": content.count("\n") + (1 if content else 0),
            "byte_count": len(content.encode("utf-8")),
            "updated_at": started_at.isoformat().replace("+00:00", "Z"),
        }
    )


# ---------------------------------------------------------------------------
# OCP Command Log API — serve log files from long-running bastion commands
# ---------------------------------------------------------------------------

# Maps OCP task name → log filename on bastion (under ocp_install_dir)
OCP_TASK_COMMAND_LOGS: dict[str, tuple[str, str]] = {
    # task_name → (label, bastion_log_filename)
    "OCP Mirror Registry Install": ("Mirror Registry Install", "mirror-registry-install.log"),
    "OCP OC Mirror Execution": ("OC Mirror Execution", "oc-mirror.log"),
    "OCP Uninstall Mirror Registry": ("Mirror Registry Uninstall", "mirror-registry-uninstall.log"),
    "OCP Destroy Cluster": ("Cluster Destroy", "cluster-destroy.log"),
    "OCP Create Agent ISO": ("Agent ISO Creation", "agent-create-image.log"),
    "OCP Bootstrap Cluster": ("Bootstrap Complete", "bootstrap-complete.log"),
    "OCP Wait Install Complete": ("Install Complete", "install-complete.log"),
}


def _read_remote_log_via_ssh(
    bastion_ip: str,
    bastion_user: str,
    bastion_key: str,
    remote_path: str,
) -> str | None:
    """SSH to bastion and read a log file.  Returns content or None on failure."""
    import subprocess as _sp

    cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10"]
    if bastion_key and os.path.isfile(bastion_key):
        cmd.extend(["-i", bastion_key])
    cmd.extend([f"{bastion_user}@{bastion_ip}", f"cat {remote_path} 2>/dev/null"])
    try:
        result = _sp.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout:
            return result.stdout
    except Exception:
        pass
    return None


@app.route("/api/ocp-installations/<execution_id>/command-log", methods=["GET"])
def get_ocp_command_log(execution_id: str):
    """Return the command-specific log for a long-running OCP task.

    - If the execution is complete, reads the fetched log from local disk.
    - If the execution is in_progress, SSHes to bastion to read the live log.
    """
    auth_error = require_auth()
    if auth_error:
        return auth_error

    execution = db.session.get(OcpInstallationExecution, execution_id)
    if not execution:
        return jsonify({"error": "Execution not found"}), 404

    task_log_info = OCP_TASK_COMMAND_LOGS.get(execution.task_name)
    if not task_log_info:
        return jsonify({"error": "This task does not produce a command log"}), 404

    label, bastion_log_filename = task_log_info

    # Try local file first (fetched by Ansible after completion)
    local_path = os.path.join(
        INSTALLATION_LOGS_DIR,
        f"{execution_id}-{bastion_log_filename}",
    )
    content = ""
    if os.path.isfile(local_path):
        with open(local_path, encoding="utf-8", errors="replace") as fh:
            content = fh.read()

    # If in_progress and no local file (or stale), try SSH to bastion
    if execution.status == "in_progress" and not content:
        cluster = Cluster.query.get(execution.cluster_id)
        if cluster:
            params = cluster.parsed_parameters()
            bastion_ip = params.get("Bastion IP", "")
            bastion_user = params.get("Bastion SSH User", "root")
            bastion_key = params.get("Bastion SSH Private Key Path", "")
            if bastion_ip:
                ocp_install_dir = f"/home/{bastion_user}/ocp-install"
                remote_path = f"{ocp_install_dir}/{bastion_log_filename}"
                live_content = _read_remote_log_via_ssh(
                    bastion_ip, bastion_user, bastion_key, remote_path
                )
                if live_content:
                    content = live_content

    if not content:
        return jsonify({"error": "Command log not available yet."}), 404

    if request.args.get("download") == "1":
        filename = f"{execution.cluster_name}-{bastion_log_filename}"
        return Response(
            content,
            mimetype="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-store",
            },
        )

    return jsonify({
        "execution_id": execution_id,
        "label": label,
        "task_name": execution.task_name,
        "status": execution.status,
        "content": content,
        "line_count": content.count("\n") + (1 if content else 0),
    })


@app.route("/api/version", methods=["GET"])
def get_version():
    return jsonify({
        "version": APP_VERSION,
        "schema_version": "1.5",
        "product": "CPAT",
        "supported_types": ["rhoso", "ocp"],
    })


with app.app_context():
    init_db()

    # Clean up stale executions left as "in_progress" from prior crashes
    # (gunicorn worker timeout, container restart, etc.)
    _stale_ts = datetime.now(timezone.utc)
    for _model in (RhosoInstallationExecution, OcpInstallationExecution):
        _stale = _model.query.filter_by(status="in_progress").all()
        for _exec in _stale:
            _exec.status = "failed"
            _exec.completed_at = _stale_ts
            if _exec.execution_log:
                _exec.execution_log += (
                    "\n\n--- CPAT: Marked as failed on restart "
                    "(worker timeout or container restart) ---\n"
                )
        if _stale:
            db.session.commit()
            app.logger.warning(
                "Cleaned up %d stale '%s' executions stuck in 'in_progress'.",
                len(_stale), _model.__tablename__,
            )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
