from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from alerting.router import COMPONENT_SEVERITY_MAP
from app.dependencies import (
    get_alert_router,
    get_incident_store,
    get_mongo_signal_store,
    get_pipeline,
    get_signal_store,
)
from incident_pipeline.db.store import IncidentStore
from incident_pipeline.models import Incident, IncidentState, RcaCategory
from incident_pipeline.pipeline import IncidentPipeline
from observability.prometheus import (
    incident_state_transitions_total,
    mttr_seconds,
    rca_submissions_total,
    rca_validation_failures_total,
)
from signals.store import SignalStore
from workflow.state_machine import InvalidTransitionError, transition_or_raise

router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])


class StatePatch(BaseModel):
    state: IncidentState


class RcaPayload(BaseModel):
    root_cause: str
    rca_category: RcaCategory
    incident_start_at: datetime
    incident_end_at: datetime
    fix_applied: str
    prevention_steps: str
    rca_verified_by: str | None = None


@router.post("")
async def create_incident(
    incident: Incident,
    pipeline: IncidentPipeline = Depends(get_pipeline)
) -> dict:
    incident.severity = COMPONENT_SEVERITY_MAP.get(incident.component, incident.severity)
    result = pipeline.process(incident)
    if result.status != 201 or result.incident is None:
        raise HTTPException(status_code=result.status, detail=result.reason or result.errors)
    return result.incident.model_dump(mode="json")


@router.get("")
async def list_incidents(
    pipeline: IncidentPipeline = Depends(get_pipeline)
) -> list[dict]:
    store = pipeline.store.__self__
    if isinstance(store, IncidentStore):
        return [i.model_dump(mode="json") for i in store.list_all()]
    records = getattr(store, "_records", {})
    return [i.model_dump(mode="json") for i in records.values()]


@router.get("/{incident_id}")
async def get_incident(
    incident_id: UUID,
    include_signals: bool = False,
    incident_store: IncidentStore = Depends(get_incident_store),
    signal_store: SignalStore = Depends(get_mongo_signal_store),
) -> dict:
    incident = incident_store.get_by_id(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="incident not found")
    payload = incident.model_dump(mode="json")
    if include_signals:
        signals = await signal_store.find_by_work_item(incident_id)
        payload["signals"] = [s.model_dump(mode="json") for s in signals]
    return payload


@router.patch("/{incident_id}/state")
async def transition_state(
    incident_id: UUID,
    body: StatePatch,
    incident_store: IncidentStore = Depends(get_incident_store),
    alert_router=Depends(get_alert_router),
) -> dict:
    incident = incident_store.get_by_id(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="incident not found")
    from_state = incident.state
    try:
        target_state = transition_or_raise(incident.state, body.state, incident)
    except InvalidTransitionError as exc:
        incident_state_transitions_total.labels(
            from_state=from_state.value,
            to_state=body.state.value,
            result="blocked",
        ).inc()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    incident = incident_store.transition_state(incident_id, target_state)
    if incident is None:
        raise HTTPException(status_code=404, detail="incident not found")
    incident_state_transitions_total.labels(
        from_state=from_state.value,
        to_state=target_state.value,
        result="ok",
    ).inc()
    await alert_router.dispatch(incident)
    return incident.model_dump(mode="json")


@router.post("/{incident_id}/rca")
async def submit_rca(
    incident_id: UUID,
    body: RcaPayload,
    pipeline: IncidentPipeline = Depends(get_pipeline),
    incident_store: IncidentStore = Depends(get_incident_store),
) -> dict:
    incident = incident_store.get_by_id(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="incident not found")
    merged_description = f"Fix Applied:\n{body.fix_applied}\n\nPrevention Steps:\n{body.prevention_steps}"
    errors = pipeline.rca.validate(body.root_cause, merged_description)
    if errors:
        rca_validation_failures_total.inc()
        raise HTTPException(status_code=422, detail=errors)
    if body.incident_end_at < body.incident_start_at:
        rca_validation_failures_total.inc()
        raise HTTPException(status_code=422, detail="incident_end_at must be >= incident_start_at")
    updated = incident_store.update_rca(
        incident_id,
        root_cause=body.root_cause,
        rca_category=body.rca_category,
        rca_description=merged_description,
        rca_verified_by=body.rca_verified_by,
        incident_start_at=body.incident_start_at,
        incident_end_at=body.incident_end_at,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="incident not found")
    rca_submissions_total.inc()
    if updated.mttr_seconds is not None:
        mttr_seconds.observe(updated.mttr_seconds)
    return updated.model_dump(mode="json")


@router.get("/aggregations/throughput")
async def incident_throughput(
    bucket_minutes: int = Query(default=5, ge=1, le=60),
    lookback_hours: int = Query(default=24, ge=1, le=168),
    incident_store: IncidentStore = Depends(get_incident_store),
) -> dict:
    return {
        "bucket_minutes": bucket_minutes,
        "lookback_hours": lookback_hours,
        "series": incident_store.throughput_timeseries(
            bucket_minutes=bucket_minutes,
            lookback_hours=lookback_hours,
        ),
    }