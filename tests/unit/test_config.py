"""
Tests unitarios para src/tmac/config.py

Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5
"""

import textwrap
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from tmac.config import ALLOWED_TOP_KEYS, ConfigError, load_config

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def write_yaml(tmp_path: Path, content: str) -> str:
    cfg = tmp_path / ".tmac.yaml"
    cfg.write_text(textwrap.dedent(content), encoding="utf-8")
    return str(cfg)


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def test_unknown_top_keys_emits_warning_and_returns_valid_only(tmp_path, caplog):
    """Unknown top-level keys trigger a warning; only valid keys are returned."""
    cfg_path = write_yaml(
        tmp_path,
        """\
        scan:
          dir: ./infra
        unknown_key: some_value
        another_bad: 123
        """,
    )
    import logging

    with caplog.at_level(logging.WARNING, logger="tmac.config"):
        result = load_config(cfg_path)

    assert "scan" in result
    assert "unknown_key" not in result
    assert "another_bad" not in result
    assert any("unknown_key" in msg or "another_bad" in msg for msg in caplog.messages)


def test_scan_exclude_non_list_emits_warning_and_is_ignored(tmp_path, caplog):
    """scan.exclude that is not a list triggers a warning and is absent from result."""
    cfg_path = write_yaml(
        tmp_path,
        """\
        scan:
          dir: ./infra
          exclude: "not-a-list"
        """,
    )
    import logging

    with caplog.at_level(logging.WARNING, logger="tmac.config"):
        result = load_config(cfg_path)

    assert "exclude" not in result.get("scan", {})
    assert any("exclude" in msg for msg in caplog.messages)


def test_scan_exclude_non_string_items_emits_warning_and_is_ignored(tmp_path, caplog):
    """scan.exclude list with non-string items triggers a warning and is absent."""
    cfg_path = write_yaml(
        tmp_path,
        """\
        scan:
          dir: ./infra
          exclude:
            - 123
            - 456
        """,
    )
    import logging

    with caplog.at_level(logging.WARNING, logger="tmac.config"):
        result = load_config(cfg_path)

    assert "exclude" not in result.get("scan", {})
    assert any("exclude" in msg for msg in caplog.messages)


def test_report_format_invalid_emits_warning_and_is_absent(tmp_path, caplog):
    """report.format with an invalid value triggers a warning and is absent from result."""
    cfg_path = write_yaml(
        tmp_path,
        """\
        report:
          format: xml
        """,
    )
    import logging

    with caplog.at_level(logging.WARNING, logger="tmac.config"):
        result = load_config(cfg_path)

    assert "format" not in result.get("report", {})
    assert any("format" in msg or "xml" in msg for msg in caplog.messages)


def test_yaml_syntax_error_raises_config_error(tmp_path):
    """A YAML file with syntax errors raises ConfigError."""
    cfg = tmp_path / ".tmac.yaml"
    cfg.write_text("scan:\n  dir: [\nbad yaml here", encoding="utf-8")

    with pytest.raises(ConfigError):
        load_config(str(cfg))


def test_valid_config_returns_all_valid_keys(tmp_path):
    """A fully valid config is returned unchanged."""
    cfg_path = write_yaml(
        tmp_path,
        """\
        scan:
          dir: ./infra
          exclude:
            - .terraform
          rules_dir: ./rules
        report:
          format: json
          fail_on: high
          severity: medium
        """,
    )
    result = load_config(cfg_path)
    assert result["scan"]["dir"] == "./infra"
    assert result["scan"]["exclude"] == [".terraform"]
    assert result["report"]["format"] == "json"


def test_missing_config_file_returns_empty_dict(tmp_path):
    """If the config file does not exist, an empty dict is returned."""
    result = load_config(str(tmp_path / "nonexistent.yaml"))
    assert result == {}


def test_empty_config_file_returns_empty_dict(tmp_path):
    """An empty YAML file returns an empty dict."""
    cfg = tmp_path / ".tmac.yaml"
    cfg.write_text("", encoding="utf-8")
    result = load_config(str(cfg))
    assert result == {}


def test_valid_report_formats_are_accepted(tmp_path):
    """All three valid report formats are accepted without warnings."""
    for fmt in ("html", "json", "md"):
        cfg_path = write_yaml(tmp_path, f"report:\n  format: {fmt}\n")
        result = load_config(cfg_path)
        assert result["report"]["format"] == fmt


# ---------------------------------------------------------------------------
# Property 18: Config validates unknown keys in .tmac.yaml
# Validates: Requirements 10.1, 10.2
# ---------------------------------------------------------------------------

# Strategy: generate dicts that may contain unknown top-level keys mixed with valid ones
_unknown_key_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="_"),
    min_size=1,
    max_size=20,
).filter(lambda k: k not in ALLOWED_TOP_KEYS and k.isidentifier())

_valid_top_key_strategy = st.sampled_from(sorted(ALLOWED_TOP_KEYS))


@settings(max_examples=100)
@given(
    unknown_keys=st.lists(_unknown_key_strategy, min_size=1, max_size=5, unique=True),
    include_valid=st.booleans(),
)
def test_property_18_unknown_keys_always_filtered(unknown_keys, include_valid):
    """
    Property 18: Config validates unknown keys in .tmac.yaml

    For any .tmac.yaml that contains top-level keys outside of ALLOWED_TOP_KEYS,
    load_config() must return only valid keys (scan, report).

    Validates: Requirements 10.1, 10.2
    """
    import os
    import tempfile

    import yaml  # type: ignore

    data: dict = {k: "value" for k in unknown_keys}
    if include_valid:
        data["scan"] = {"dir": "./infra"}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write(yaml.dump(data))
        cfg_path = f.name

    try:
        result = load_config(cfg_path)

        # All returned keys must be in ALLOWED_TOP_KEYS
        for key in result:
            assert (
                key in ALLOWED_TOP_KEYS
            ), f"load_config() returned unexpected key '{key}' — only {ALLOWED_TOP_KEYS} are allowed"

        # None of the unknown keys should appear in the result
        for key in unknown_keys:
            assert (
                key not in result
            ), f"Unknown key '{key}' should have been filtered out but was present in result"
    finally:
        os.unlink(cfg_path)


# ---------------------------------------------------------------------------
# report.fail_on / report.severity validation
# ---------------------------------------------------------------------------


def test_report_fail_on_and_severity_are_normalized(tmp_path):
    cfg = tmp_path / ".tmac.yaml"
    cfg.write_text("report:\n  fail_on: HIGH\n  severity: Medium\n", encoding="utf-8")
    assert load_config(str(cfg))["report"] == {"fail_on": "high", "severity": "medium"}


def test_invalid_report_fail_on_and_severity_are_dropped(tmp_path, caplog):
    import logging

    cfg = tmp_path / ".tmac.yaml"
    cfg.write_text("report:\n  fail_on: everything\n  severity: 3\n", encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        result = load_config(str(cfg))
    assert result["report"] == {}
    assert "report.fail_on" in caplog.text and "report.severity" in caplog.text
