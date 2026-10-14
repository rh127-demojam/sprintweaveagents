import json
import uuid
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine

from ciq_parser import CLUSTER_TYPE_LABELS

db = SQLAlchemy()


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, _connection_record):
    if dbapi_connection.__class__.__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


class Cluster(db.Model):
    __tablename__ = "clusters"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    cluster_name = db.Column(db.String(255), nullable=False)
    cluster_type = db.Column(db.String(30), nullable=False)
    description = db.Column(db.Text, default="")
    ciq_filename = db.Column(db.String(255), nullable=False)
    ciq_stored_as = db.Column(db.String(512), nullable=False)
    ciq_parameters = db.Column(db.Text, default="")
    registration_log = db.Column(db.Text, default="")
    status = db.Column(db.String(50), default="registered", nullable=False)
    registered_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    registered_by = db.Column(db.String(100), nullable=False)

    @property
    def cluster_type_label(self) -> str:
        return CLUSTER_TYPE_LABELS.get(self.cluster_type, self.cluster_type)

    def parsed_parameters(self) -> dict:
        if not self.ciq_parameters:
            return {}
        try:
            return json.loads(self.ciq_parameters)
        except json.JSONDecodeError:
            return {}

    def to_dict(self) -> dict:
        registered_at = self.registered_at
        if registered_at.tzinfo is None:
            registered_at = registered_at.replace(tzinfo=timezone.utc)

        return {
            "id": self.id,
            "cluster_name": self.cluster_name,
            "cluster_type": self.cluster_type,
            "cluster_type_label": self.cluster_type_label,
            "description": self.description or "",
            "ciq_filename": self.ciq_filename,
            "ciq_stored_as": self.ciq_stored_as,
            "ciq_parameters": self.parsed_parameters(),
            "has_registration_log": bool(self.registration_log),
            "status": self.status,
            "registered_at": registered_at.isoformat().replace("+00:00", "Z"),
            "registered_by": self.registered_by,
        }


class RhosoInstallationExecution(db.Model):
    __tablename__ = "rhoso_installation_executions"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    cluster_id = db.Column(db.String(36), db.ForeignKey("clusters.id"), nullable=False)
    cluster_name = db.Column(db.String(255), nullable=False)
    rhoso_version = db.Column(db.String(50), nullable=False)
    task_name = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(30), default="in_progress", nullable=False)
    execution_log = db.Column(db.Text, default="")
    started_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    completed_at = db.Column(db.DateTime, nullable=True)
    triggered_by = db.Column(db.String(100), nullable=False)

    cluster = db.relationship(
        "Cluster", backref=db.backref("rhoso_installations", lazy=True)
    )

    def to_dict(self) -> dict:
        started_at = self.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)

        completed_at = self.completed_at
        if completed_at and completed_at.tzinfo is None:
            completed_at = completed_at.replace(tzinfo=timezone.utc)

        return {
            "id": self.id,
            "cluster_id": self.cluster_id,
            "cluster_name": self.cluster_name,
            "rhoso_version": self.rhoso_version,
            "ocp_version": self.rhoso_version,
            "task_name": self.task_name,
            "status": self.status,
            "has_execution_log": bool(self.execution_log),
            "started_at": started_at.isoformat().replace("+00:00", "Z"),
            "completed_at": (
                completed_at.isoformat().replace("+00:00", "Z") if completed_at else None
            ),
            "triggered_by": self.triggered_by,
        }


class OcpInstallationExecution(db.Model):
    __tablename__ = "ocp_installation_executions"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    cluster_id = db.Column(db.String(36), db.ForeignKey("clusters.id"), nullable=False)
    cluster_name = db.Column(db.String(255), nullable=False)
    ocp_version = db.Column(db.String(50), nullable=False)
    task_name = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(30), default="in_progress", nullable=False)
    execution_log = db.Column(db.Text, default="")
    started_at = db.Column(
        db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    completed_at = db.Column(db.DateTime, nullable=True)
    triggered_by = db.Column(db.String(100), nullable=False)

    cluster = db.relationship(
        "Cluster", backref=db.backref("ocp_installations", lazy=True)
    )

    def to_dict(self) -> dict:
        started_at = self.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)

        completed_at = self.completed_at
        if completed_at and completed_at.tzinfo is None:
            completed_at = completed_at.replace(tzinfo=timezone.utc)

        return {
            "id": self.id,
            "cluster_id": self.cluster_id,
            "cluster_name": self.cluster_name,
            "ocp_version": self.ocp_version,
            "task_name": self.task_name,
            "status": self.status,
            "has_execution_log": bool(self.execution_log),
            "started_at": started_at.isoformat().replace("+00:00", "Z"),
            "completed_at": (
                completed_at.isoformat().replace("+00:00", "Z") if completed_at else None
            ),
            "triggered_by": self.triggered_by,
        }
