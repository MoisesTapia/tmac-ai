"""Secret and token handling for TMAC CI.

Provides safe token reading from environment variables and redaction of
secret values from output strings.

Feature: tmac-v1-6-pr-agent
Requirements: R3.6, R4.1, R4.2, R4.3, R4.5
"""

import os

# The fixed redaction placeholder. It contains no alphanumeric characters from
# any typical token, satisfying R4.1 (placeholder contains none of the original
# secret's characters for any printable non-asterisk/dash token value).
_REDACTED_PLACEHOLDER = "***REDACTED***"

# Priority-ordered list of environment variable names to search for the CI token.
_TOKEN_ENV_VARS = ["GITHUB_TOKEN", "CI_JOB_TOKEN", "TMAC_TOKEN"]


def read_token() -> str | None:
    """Read the CI token from environment variables in priority order.

    Checks the following environment variables in order:
      1. GITHUB_TOKEN
      2. CI_JOB_TOKEN
      3. TMAC_TOKEN

    Returns the first non-empty value found, or None if all are missing or empty.
    Never reads from sys.argv or any command-line source (R4.2, R4.3, R3.6).

    Returns:
        The token string if found, or None.
    """
    for var_name in _TOKEN_ENV_VARS:
        value = os.environ.get(var_name, "")
        if value:  # non-empty string
            return value
    return None


def redact(text: str, *secrets: str | None) -> str:
    """Replace every occurrence of each secret in text with the redaction placeholder.

    The placeholder is the fixed string "***REDACTED***", which contains none of
    the typical alphanumeric characters found in CI tokens (R4.1, R4.5).

    Args:
        text:    The string to sanitize. If empty or None, returned as-is.
        *secrets: Zero or more secret values to redact. Empty or None values
                  are skipped gracefully.

    Returns:
        The sanitized string with all secret occurrences replaced by the placeholder.
    """
    if not text:
        return text

    result = text
    for secret in secrets:
        # Skip empty/None secrets gracefully
        if not secret:
            continue
        result = result.replace(secret, _REDACTED_PLACEHOLDER)

    return result
