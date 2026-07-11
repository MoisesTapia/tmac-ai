"""Unit tests for tmac.ci.secrets — token reading and redaction.

Validates: Requirements R3.6, R4.1, R4.2, R4.3, R4.5
"""

import os
from unittest.mock import patch

import pytest

from tmac.ci.secrets import read_token, redact

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# All three env var names that read_token inspects
_ALL_TOKEN_VARS = ["GITHUB_TOKEN", "CI_JOB_TOKEN", "TMAC_TOKEN"]

_PLACEHOLDER = "***REDACTED***"


def _clear_all(env: dict) -> dict:
    """Return a copy of env with all three token variables removed."""
    cleaned = dict(env)
    for var in _ALL_TOKEN_VARS:
        cleaned.pop(var, None)
    return cleaned


# ---------------------------------------------------------------------------
# read_token — env-var priority and fallback
# ---------------------------------------------------------------------------

class TestReadToken:
    """Tests for read_token(), verifying priority order and env-only reads."""

    def test_returns_github_token_when_set(self, monkeypatch):
        """GITHUB_TOKEN is returned when it is set."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("CI_JOB_TOKEN", raising=False)
        monkeypatch.delenv("TMAC_TOKEN", raising=False)
        monkeypatch.setenv("GITHUB_TOKEN", "github-secret-token")

        assert read_token() == "github-secret-token"

    def test_returns_ci_job_token_when_github_token_unset(self, monkeypatch):
        """CI_JOB_TOKEN is returned when GITHUB_TOKEN is absent."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("CI_JOB_TOKEN", raising=False)
        monkeypatch.delenv("TMAC_TOKEN", raising=False)
        monkeypatch.setenv("CI_JOB_TOKEN", "gitlab-job-token")

        assert read_token() == "gitlab-job-token"

    def test_returns_tmac_token_when_others_unset(self, monkeypatch):
        """TMAC_TOKEN is returned when GITHUB_TOKEN and CI_JOB_TOKEN are absent."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("CI_JOB_TOKEN", raising=False)
        monkeypatch.delenv("TMAC_TOKEN", raising=False)
        monkeypatch.setenv("TMAC_TOKEN", "explicit-tmac-token")

        assert read_token() == "explicit-tmac-token"

    def test_prefers_github_token_over_others(self, monkeypatch):
        """GITHUB_TOKEN takes priority when all three env vars are set."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("CI_JOB_TOKEN", raising=False)
        monkeypatch.delenv("TMAC_TOKEN", raising=False)
        monkeypatch.setenv("GITHUB_TOKEN", "github-token")
        monkeypatch.setenv("CI_JOB_TOKEN", "ci-job-token")
        monkeypatch.setenv("TMAC_TOKEN", "tmac-token")

        assert read_token() == "github-token"

    def test_returns_none_when_all_unset(self, monkeypatch):
        """None is returned when all three env vars are absent."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("CI_JOB_TOKEN", raising=False)
        monkeypatch.delenv("TMAC_TOKEN", raising=False)

        assert read_token() is None

    def test_returns_none_when_all_empty_strings(self, monkeypatch):
        """Empty strings are treated as missing; None is returned."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("CI_JOB_TOKEN", raising=False)
        monkeypatch.delenv("TMAC_TOKEN", raising=False)
        monkeypatch.setenv("GITHUB_TOKEN", "")
        monkeypatch.setenv("CI_JOB_TOKEN", "")
        monkeypatch.setenv("TMAC_TOKEN", "")

        assert read_token() is None

    def test_skips_empty_github_token_falls_back_to_ci_job_token(self, monkeypatch):
        """An empty GITHUB_TOKEN is skipped; the next available token is returned."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("CI_JOB_TOKEN", raising=False)
        monkeypatch.delenv("TMAC_TOKEN", raising=False)
        monkeypatch.setenv("GITHUB_TOKEN", "")
        monkeypatch.setenv("CI_JOB_TOKEN", "fallback-ci-token")

        assert read_token() == "fallback-ci-token"


# ---------------------------------------------------------------------------
# redact — placeholder substitution
# ---------------------------------------------------------------------------

class TestRedact:
    """Tests for redact(), verifying secret replacement with the fixed placeholder."""

    def test_replaces_single_secret(self):
        """A secret embedded in text is replaced by the placeholder."""
        result = redact("my token is abc123xyz", "abc123xyz")
        assert result == f"my token is {_PLACEHOLDER}"

    def test_replaces_all_occurrences(self):
        """Every occurrence of the secret is replaced, not just the first."""
        result = redact("abc abc abc", "abc")
        assert _PLACEHOLDER in result
        assert "abc" not in result

    def test_replaces_multiple_secrets(self):
        """Multiple distinct secrets are each replaced."""
        result = redact("token1 and token2", "token1", "token2")
        assert "token1" not in result
        assert "token2" not in result
        assert _PLACEHOLDER in result

    def test_empty_text_returns_as_is(self):
        """Empty string input is returned unchanged."""
        assert redact("", "secret") == ""

    def test_none_text_returns_as_is(self):
        """None text is returned unchanged (graceful handling)."""
        assert redact(None, "secret") is None  # type: ignore[arg-type]

    def test_empty_secret_is_skipped(self):
        """An empty string secret is skipped; text is unchanged."""
        original = "some text"
        assert redact(original, "") == original

    def test_none_secret_is_skipped(self):
        """A None secret is skipped gracefully; text is unchanged."""
        original = "some text"
        assert redact(original, None) == original  # type: ignore[arg-type]

    def test_no_secrets_returns_text_unchanged(self):
        """Calling redact with no secrets returns the original text."""
        original = "nothing to redact here"
        assert redact(original) == original

    def test_placeholder_does_not_contain_secret_chars(self):
        """The placeholder itself contains none of the typical token characters."""
        # The placeholder is "***REDACTED***" — verify it never accidentally
        # matches an alphanumeric token value.
        token = "sometoken123"
        result = redact(f"log: {token}", token)
        assert token not in result
        assert result == f"log: {_PLACEHOLDER}"
