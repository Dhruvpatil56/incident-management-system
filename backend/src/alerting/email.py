from __future__ import annotations

try:
    import aiosmtplib
except ModuleNotFoundError:  # pragma: no cover
    aiosmtplib = None

from incident_pipeline.models import Incident


class EmailAlert:
    def __init__(self, host: str, port: int, sender: str, recipient: str):
        self.host = host
        self.port = port
        self.sender = sender
        self.recipient = recipient

    async def send(self, incident: Incident) -> bool:
        message = (
            f"From: {self.sender}\r\n"
            f"To: {self.recipient}\r\n"
            f"Subject: Incident {incident.severity.value} - {incident.title}\r\n\r\n"
            f"Component: {incident.component}\r\n"
            f"State: {incident.state.value}\r\n"
            f"Source: {incident.source}\r\n"
        )
        result = await aiosmtplib.send(
            message,
            hostname=self.host,
            port=self.port,
            sender=self.sender,
            recipients=[self.recipient],
        ) if aiosmtplib is not None else {}
        return bool(result)
