from __future__ import annotations

import hashlib
import json
from datetime import datetime
from uuid import UUID

from incident_pipeline.db.retry import with_retry
from incident_pipeline.models import Incident, IncidentState, RcaCategory, Severity
from observability.prometheus import db_timing


def compute_hash(incident: Incident) -> str:
    """Deterministic hash for dedup key. Matches debounce normalization."""
    normalized = {
        "source": incident.source.strip().lower(),
        "title": incident.title.strip().lower(),
        "description": incident.description.strip().lower(),
    }
    raw = json.dumps(normalized, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()[:16]


class IncidentStore:
    """Production store that reads/writes incidents in PostgreSQL."""

    def __init__(self, db_conn):
        self.db = db_conn

    @staticmethod
    def _from_row(row: tuple) -> Incident:
        return Incident(
            id=row[0],
            title=row[1],
            description=row[2],
            source=row[3],
            root_cause=row[4],
            rca_category=RcaCategory(row[5]),
            rca_description=row[6],
            rca_verified_by=row[7],
            state=IncidentState(row[8]),
            severity=Severity(row[9]),
            component=row[10],
            first_signal_at=row[11],
            rca_submitted_at=row[12],
            mttr_seconds=row[13],
            hash=row[14],
            metadata=row[15] or {},
            created_at=row[16],
            updated_at=row[17],
        )

    def create(self, incident: Incident) -> Incident:
        incident_hash = compute_hash(incident)

        def _write() -> Incident:
            with db_timing("postgres", "insert_incident"):
                cursor = self.db.cursor()
                try:
                    cursor.execute(
                    """INSERT INTO incidents
                       (id, title, description, source, root_cause, rca_category,
                        rca_description, rca_verified_by, state, severity, component,
                        first_signal_at, rca_submitted_at, mttr_seconds, hash, metadata)
                       VALUES
                       (%s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s)
                       RETURNING id, title, description, source, root_cause, rca_category,
                                 rca_description, rca_verified_by, state, severity, component,
                                 first_signal_at, rca_submitted_at, mttr_seconds, hash, metadata,
                                 created_at, updated_at""",
                    (
                        str(incident.id),
                        incident.title,
                        incident.description,
                        incident.source,
                        incident.root_cause,
                        incident.rca_category.value,
                        incident.rca_description,
                        incident.rca_verified_by,
                        incident.state.value,
                        incident.severity.value,
                        incident.component,
                        incident.first_signal_at,
                        incident.rca_submitted_at,
                        incident.mttr_seconds,
                        incident_hash,
                        json.dumps(incident.metadata),
                    ),
                )
                    row = cursor.fetchone()
                    self.db.commit()
                    return self._from_row(row)
                except Exception:
                    self.db.rollback()
                    raise
                finally:
                    cursor.close()

        return with_retry(_write, db="postgres", operation="insert_incident")

    def list_all(self) -> list[Incident]:
        with db_timing("postgres", "list_incidents"):
            cursor = self.db.cursor()
            try:
                cursor.execute(
                """SELECT id, title, description, source, root_cause, rca_category,
                          rca_description, rca_verified_by, state, severity, component,
                          first_signal_at, rca_submitted_at, mttr_seconds, hash, metadata,
                          created_at, updated_at
                   FROM incidents
                   ORDER BY created_at DESC"""
            )
                return [self._from_row(row) for row in cursor.fetchall()]
            finally:
                cursor.close()

    def get_by_id(self, incident_id: UUID) -> Incident | None:
        with db_timing("postgres", "get_incident"):
            cursor = self.db.cursor()
            try:
                cursor.execute(
                """SELECT id, title, description, source, root_cause, rca_category,
                          rca_description, rca_verified_by, state, severity, component,
                          first_signal_at, rca_submitted_at, mttr_seconds, hash, metadata,
                          created_at, updated_at
                   FROM incidents WHERE id = %s""",
                (str(incident_id),),
            )
                row = cursor.fetchone()
                return self._from_row(row) if row else None
            finally:
                cursor.close()

    def transition_state(self, incident_id: UUID, new_state: IncidentState) -> Incident | None:
        with db_timing("postgres", "transition_state"):
            cursor = self.db.cursor()
            try:
                cursor.execute(
                """SELECT id, title, description, source, root_cause, rca_category,
                          rca_description, rca_verified_by, state, severity, component,
                          first_signal_at, rca_submitted_at, mttr_seconds, hash, metadata,
                          created_at, updated_at
                   FROM incidents WHERE id = %s FOR UPDATE""",
                (str(incident_id),),
            )
                locked = cursor.fetchone()
                if not locked:
                    self.db.rollback()
                    return None
                cursor.execute(
                "UPDATE incidents SET state=%s, updated_at=NOW() WHERE id=%s",
                (new_state.value, str(incident_id)),
                )
                cursor.execute(
                """SELECT id, title, description, source, root_cause, rca_category,
                          rca_description, rca_verified_by, state, severity, component,
                          first_signal_at, rca_submitted_at, mttr_seconds, hash, metadata,
                          created_at, updated_at
                   FROM incidents WHERE id=%s""",
                (str(incident_id),),
            )
                row = cursor.fetchone()
                self.db.commit()
                return self._from_row(row)
            except Exception:
                self.db.rollback()
                raise
            finally:
                cursor.close()

    def update_rca(
        self,
        incident_id: UUID,
        *,
        root_cause: str,
        rca_category: RcaCategory,
        rca_description: str,
        rca_verified_by: str | None,
        incident_start_at: datetime,
        incident_end_at: datetime,
    ) -> Incident | None:
        mttr = int((incident_end_at - incident_start_at).total_seconds())
        with db_timing("postgres", "update_rca"):
            cursor = self.db.cursor()
            try:
                cursor.execute("SELECT id FROM incidents WHERE id = %s FOR UPDATE", (str(incident_id),))
                if cursor.fetchone() is None:
                    self.db.rollback()
                    return None
                cursor.execute(
                """UPDATE incidents
                   SET root_cause=%s,
                       rca_category=%s,
                       rca_description=%s,
                       rca_verified_by=%s,
                       first_signal_at=%s,
                       rca_submitted_at=%s,
                       mttr_seconds=%s,
                       updated_at=NOW()
                   WHERE id=%s""",
                (
                    root_cause,
                    rca_category.value,
                    rca_description,
                    rca_verified_by,
                    incident_start_at,
                    incident_end_at,
                    mttr,
                    str(incident_id),
                ),
                )
                cursor.execute(
                """SELECT id, title, description, source, root_cause, rca_category,
                          rca_description, rca_verified_by, state, severity, component,
                          first_signal_at, rca_submitted_at, mttr_seconds, hash, metadata,
                          created_at, updated_at
                   FROM incidents WHERE id=%s""",
                (str(incident_id),),
            )
                row = cursor.fetchone()
                self.db.commit()
                return self._from_row(row)
            except Exception:
                self.db.rollback()
                raise
            finally:
                cursor.close()

    def throughput_timeseries(self, *, bucket_minutes: int = 5, lookback_hours: int = 24) -> list[dict]:
        bucket = max(bucket_minutes, 1)
        lookback = max(lookback_hours, 1)
        with db_timing("postgres", "throughput_timeseries"):
            cursor = self.db.cursor()
            try:
                cursor.execute(
                """
                SELECT
                  date_trunc('minute', created_at)
                  - ((EXTRACT(MINUTE FROM created_at)::int %% %s) * INTERVAL '1 minute') AS bucket_start,
                  count(*)::int AS incident_count
                FROM incidents
                WHERE created_at >= NOW() - (%s * INTERVAL '1 hour')
                GROUP BY bucket_start
                ORDER BY bucket_start ASC
                """,
                (bucket, lookback),
            )
                return [
                    {"bucket_start": row[0].isoformat(), "incident_count": row[1]}
                    for row in cursor.fetchall()
                ]
            finally:
                cursor.close()


class InMemoryStore:
    """In-memory store for development / testing."""

    def __init__(self):
        self._records: dict[str, Incident] = {}

    def create(self, incident: Incident) -> Incident:
        record = incident.model_copy()
        record.hash = compute_hash(incident)
        self._records[str(record.id)] = record
        return record
