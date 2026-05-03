from __future__ import annotations

from incident_pipeline.models import Incident, Severity

from alerting.base import AlertStrategy

COMPONENT_SEVERITY_MAP: dict[str, Severity] = {
    "rdbms": Severity.p0,
    "api": Severity.p1,
    "mcp_host": Severity.p1,
    "cache": Severity.p2,
}

SEVERITY_STRATEGIES: dict[Severity, list[str]] = {
    Severity.p0: ["pagerduty", "slack"],
    Severity.p1: ["slack"],
    Severity.p2: ["email"],
    Severity.p3: ["email"],
}


class AlertRouter:
    def __init__(self, strategy_map: dict[Severity, list[AlertStrategy]]):
        self.strategy_map = strategy_map

    async def dispatch(self, incident: Incident) -> list[bool]:
        results: list[bool] = []
        for strategy in self.strategy_map.get(incident.severity, []):
            results.append(await strategy.send(incident))
        return results
