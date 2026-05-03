from incident_pipeline.models import Incident


class RcaGuard:
    @staticmethod
    def can_close(incident: Incident) -> bool:
        return bool(
            incident.root_cause.strip()
            and incident.rca_description.strip()
            and incident.rca_verified_by
        )
