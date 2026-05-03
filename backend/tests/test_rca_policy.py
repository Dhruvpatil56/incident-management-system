import pytest

from incident_pipeline.rca.policy import RcaPolicy


class TestRcaPolicy:
    """Tests for the RCA enforcement policy."""

    @pytest.fixture
    def policy(self):
        return RcaPolicy(min_length=10, max_length=500)

    def test_valid_rca(self, policy):
        errors = policy.validate(
            "Deploy of v2.3.1 introduced a null pointer in the payment handler",
            "Rolled back to v2.3.0, added null check, deployed v2.3.2",
        )
        assert errors == []

    def test_empty_root_cause(self, policy):
        errors = policy.validate("", "some description")
        assert any("root_cause" in e for e in errors)

    def test_placeholder_text(self, policy):
        errors = policy.validate("TBD", "N/A")
        assert any("placeholder" in e for e in errors)
        assert any("placeholder" in e for e in errors)

    def test_case_insensitive_placeholder(self, policy):
        errors = policy.validate("To Be Determined", "real description here")
        assert any("placeholder" in e for e in errors)

    def test_too_short(self, policy):
        errors = policy.validate("short", "also short")
        assert any("too short" in e for e in errors)
        assert any("too short" in e for e in errors)

    def test_too_long(self, policy):
        long = "a" * 600
        errors = policy.validate(long, long)
        assert any("too long" in e for e in errors)

    def test_valid_with_verified_by(self, policy):
        errors = policy.validate(
            "Configuration change in proxy caused 502 errors",
            "Reverted proxy config, added canary deployment step",
        )
        assert errors == []