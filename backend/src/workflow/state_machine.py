from __future__ import annotations

from abc import ABC, abstractmethod

from incident_pipeline.models import Incident, IncidentState as IncidentStateEnum
from workflow.rca_guard import RcaGuard


class InvalidTransitionError(ValueError):
    pass


class IncidentState(ABC):
    @property
    @abstractmethod
    def value(self) -> IncidentStateEnum: ...

    @abstractmethod
    def transition_to(self, new_state: IncidentStateEnum, incident: Incident) -> "IncidentState": ...


class OpenState(IncidentState):
    value = IncidentStateEnum.open

    def transition_to(self, new_state: IncidentStateEnum, incident: Incident) -> IncidentState:
        if new_state == IncidentStateEnum.investigating:
            return InvestigatingState()
        raise InvalidTransitionError(f"invalid transition: {self.value.value} -> {new_state.value}")


class InvestigatingState(IncidentState):
    value = IncidentStateEnum.investigating

    def transition_to(self, new_state: IncidentStateEnum, incident: Incident) -> IncidentState:
        if new_state == IncidentStateEnum.resolved:
            return ResolvedState()
        raise InvalidTransitionError(f"invalid transition: {self.value.value} -> {new_state.value}")


class ResolvedState(IncidentState):
    value = IncidentStateEnum.resolved

    def transition_to(self, new_state: IncidentStateEnum, incident: Incident) -> IncidentState:
        if new_state == IncidentStateEnum.investigating:
            return InvestigatingState()
        if new_state == IncidentStateEnum.closed:
            if not RcaGuard.can_close(incident):
                raise InvalidTransitionError("cannot close without complete RCA")
            return ClosedState()
        raise InvalidTransitionError(f"invalid transition: {self.value.value} -> {new_state.value}")


class ClosedState(IncidentState):
    value = IncidentStateEnum.closed

    def transition_to(self, new_state: IncidentStateEnum, incident: Incident) -> IncidentState:
        raise InvalidTransitionError(f"invalid transition: {self.value.value} -> {new_state.value}")


STATES: dict[IncidentStateEnum, IncidentState] = {
    IncidentStateEnum.open: OpenState(),
    IncidentStateEnum.investigating: InvestigatingState(),
    IncidentStateEnum.resolved: ResolvedState(),
    IncidentStateEnum.closed: ClosedState(),
}


def transition_or_raise(
    from_state: IncidentStateEnum,
    to_state: IncidentStateEnum,
    incident: Incident,
) -> IncidentStateEnum:
    current = STATES[from_state]
    next_state = current.transition_to(to_state, incident)
    return next_state.value


def validate_transition(from_state: IncidentStateEnum, to_state: IncidentStateEnum) -> bool:
    allowed: dict[IncidentStateEnum, set[IncidentStateEnum]] = {
        IncidentStateEnum.open: {IncidentStateEnum.investigating},
        IncidentStateEnum.investigating: {IncidentStateEnum.resolved},
        IncidentStateEnum.resolved: {IncidentStateEnum.investigating, IncidentStateEnum.closed},
        IncidentStateEnum.closed: set(),
    }
    return to_state in allowed[from_state]
