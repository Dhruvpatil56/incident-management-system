from __future__ import annotations

import re

from incident_pipeline.config import settings


class RcaPolicy:
    """Semantic validation of root cause analysis fields.

    Enforced at the service layer — catches empty strings, placeholders,
    and semantically empty text before it reaches the database.
    """

    _PLACEHOLDER_PATTERNS = {
        "tbd", "n/a", "na", "unknown", "none",
        "to be determined", "to be decided",
        "not applicable", "not yet known",
        "will update later", "investigating",
    }

    def __init__(
        self,
        min_length: int = settings.rca_min_length,
        max_length: int = settings.rca_max_length,
    ):
        self.min_length = min_length
        self.max_length = max_length
        self._blocked_re = re.compile(
            r"\b(?:"
            + "|".join(re.escape(p) for p in self._PLACEHOLDER_PATTERNS)
            + r")\b",
            re.IGNORECASE,
        )

    def validate(self, root_cause: str, rca_description: str) -> list[str]:
        """Returns a list of validation errors. Empty list means valid."""
        errors: list[str] = []

        errors.extend(self._check_field("root_cause", root_cause))
        errors.extend(self._check_field("rca_description", rca_description))

        return errors

    def _check_field(self, field_name: str, value: str) -> list[str]:
        errors: list[str] = []
        stripped = value.strip()

        if len(stripped) < self.min_length:
            errors.append(
                f"{field_name} too short ({len(stripped)} < {self.min_length} chars)"
            )
        if len(stripped) > self.max_length:
            errors.append(
                f"{field_name} too long ({len(stripped)} > {self.max_length} chars)"
            )
        if self._blocked_re.search(stripped):
            errors.append(f"{field_name} contains placeholder text")

        return errors