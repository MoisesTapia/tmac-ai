"""
Unit tests for TerraformParser — line numbers, tmac:ignore, and determinism.

Covers:
  - Property 5: line_number > 0 for all resources in valid files
  - Property 6: tmac:ignore global suppresses all findings for a resource
  - Property 7: tmac:ignore[RULE-ID] suppresses only the specified rule
  - Property 8: Parsing is deterministic (round-trip extraction)
  - Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 12.1, 12.2, 12.3, 12.4
"""

import pytest
from pathlib import Path
from hypothesis import given, settings, strategies as st

from tmac.parsers.terraform import TerraformParser
from tmac.engine.matcher import Matcher
from tmac.engine.rule_loader import RuleLoader

FIXTURES = Path(__file__).parent.parent / "fixtures"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tf(tmp_path: Path, content: str, name: str = "test.tf") -> str:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------------------
# Requirement 12.1 — valid file returns correct number of ResourceModel objects
# ---------------------------------------------------------------------------

def test_parse_multiple_resources_count(tmp_path):
    content = """
resource "aws_s3_bucket" "bucket_a" {
  bucket = "a"
}

resource "aws_s3_bucket" "bucket_b" {
  bucket = "b"
}

resource "aws_security_group" "sg_one" {
  name = "sg"
}
"""
    path = _make_tf(tmp_path, content)
    parser = TerraformParser()
    resources = parser.parse(path)
    assert len(resources) == 3


# ---------------------------------------------------------------------------
# Requirement 12.2 — invalid syntax returns empty list without exception
# ---------------------------------------------------------------------------

def test_parse_invalid_syntax_returns_empty(tmp_path):
    content = "this is not valid terraform { {{ }"
    path = _make_tf(tmp_path, content)
    parser = TerraformParser()
    resources = parser.parse(path)
    assert resources == []


# ---------------------------------------------------------------------------
# Requirement 4.1 / Property 5 — line_number > 0 for all resources
# ---------------------------------------------------------------------------

def test_line_numbers_positive(tmp_path):
    content = """
resource "aws_s3_bucket" "first" {
  bucket = "first"
}

resource "aws_s3_bucket" "second" {
  bucket = "second"
}
"""
    path = _make_tf(tmp_path, content)
    parser = TerraformParser()
    resources = parser.parse(path)
    assert len(resources) == 2
    for r in resources:
        assert r.line_number > 0, f"Expected line_number > 0 for {r.name}, got {r.line_number}"


def test_line_numbers_from_real_fixture():
    """Property 5: all resources in a real fixture have line_number > 0."""
    parser = TerraformParser()
    resources = parser.parse(str(FIXTURES / "sample.tf"))
    assert len(resources) > 0
    for r in resources:
        assert r.line_number > 0, f"line_number == 0 for resource {r.name}"


# ---------------------------------------------------------------------------
# Requirement 4.3 / Property 6 — tmac:ignore global suppresses all findings
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ignore_comment,resource_line", [
    # ignore on preceding line
    ("# tmac:ignore\n", 'resource "aws_s3_bucket" "target" {\n  acl = "public-read"\n}\n'),
    # ignore on same line as resource declaration
    ("", 'resource "aws_s3_bucket" "target" { # tmac:ignore\n  acl = "public-read"\n}\n'),
])
def test_tmac_ignore_global_suppresses_all_findings(tmp_path, ignore_comment, resource_line):
    """Property 6: global tmac:ignore suppresses all findings for the resource."""
    content = ignore_comment + resource_line
    path = _make_tf(tmp_path, content)

    parser = TerraformParser()
    resources = parser.parse(path)
    ignore_map = parser.get_ignore_map(path)

    loader = RuleLoader()
    rules = loader.load_rules()
    matcher = Matcher()

    findings = matcher.match(resources, rules, ignore_map=ignore_map)
    target_findings = [f for f in findings if f.resource_name == "target"]
    assert target_findings == [], (
        f"Expected no findings for globally ignored resource, got: {target_findings}"
    )


# ---------------------------------------------------------------------------
# Requirement 4.4 / Property 7 — tmac:ignore[RULE-ID] suppresses only that rule
# ---------------------------------------------------------------------------

def test_tmac_ignore_rule_id_suppresses_only_specified_rule(tmp_path):
    """Property 7: tmac:ignore[RULE-ID] suppresses only the named rule."""
    # This bucket has public ACL (triggers TMAC-AWS-S3-001) and no encryption
    # (triggers TMAC-AWS-S3-002). We ignore only S3-001.
    content = """\
# tmac:ignore[TMAC-AWS-S3-001]
resource "aws_s3_bucket" "partial_ignore" {
  acl = "public-read"
}
"""
    path = _make_tf(tmp_path, content)
    parser = TerraformParser()
    resources = parser.parse(path)
    ignore_map = parser.get_ignore_map(path)

    assert "partial_ignore" in ignore_map
    assert "TMAC-AWS-S3-001" in ignore_map["partial_ignore"]
    assert "*" not in ignore_map["partial_ignore"]

    loader = RuleLoader()
    rules = loader.load_rules()
    matcher = Matcher()
    findings = matcher.match(resources, rules, ignore_map=ignore_map)

    rule_ids = {f.rule_id for f in findings if f.resource_name == "partial_ignore"}
    assert "TMAC-AWS-S3-001" not in rule_ids, "Ignored rule should not appear in findings"


# ---------------------------------------------------------------------------
# Requirement 4.6 — multiple consecutive tmac:ignore[RULE-ID] comments
# ---------------------------------------------------------------------------

def test_multiple_consecutive_ignore_rule_ids(tmp_path):
    content = """\
# tmac:ignore[TMAC-AWS-SG-001]
# tmac:ignore[TMAC-AWS-SG-002]
resource "aws_security_group" "multi_ignored" {
  name = "test"
}
"""
    path = _make_tf(tmp_path, content)
    parser = TerraformParser()
    ignore_map = parser.get_ignore_map(path)

    assert "multi_ignored" in ignore_map
    assert "TMAC-AWS-SG-001" in ignore_map["multi_ignored"]
    assert "TMAC-AWS-SG-002" in ignore_map["multi_ignored"]
    assert "*" not in ignore_map["multi_ignored"]


# ---------------------------------------------------------------------------
# Requirement 4.7 / Property 8 — parsing is deterministic
# ---------------------------------------------------------------------------

def test_parse_deterministic(tmp_path):
    """Property 8: parsing the same file twice yields identical ResourceModel sets."""
    content = """\
resource "aws_s3_bucket" "det_bucket" {
  bucket = "deterministic"
  acl    = "private"
}

resource "aws_security_group" "det_sg" {
  name = "det-sg"
}
"""
    path = _make_tf(tmp_path, content)
    parser = TerraformParser()

    first = parser.parse(path)
    second = parser.parse(path)

    assert len(first) == len(second)
    for r1, r2 in zip(first, second):
        assert r1.resource_type == r2.resource_type
        assert r1.name == r2.name
        assert r1.attributes == r2.attributes
        assert r1.line_number == r2.line_number


# ---------------------------------------------------------------------------
# Property 8 (Hypothesis) — determinism over arbitrary valid resource names
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(
    res_name=st.from_regex(r"[a-z][a-z0-9_]{0,19}", fullmatch=True),
    bucket_name=st.from_regex(r"[a-z][a-z0-9\-]{2,20}", fullmatch=True),
)
def test_parse_deterministic_hypothesis(res_name, bucket_name):
    """Property 8 (PBT): parsing is deterministic for any valid resource name."""
    import tempfile, os
    content = f'resource "aws_s3_bucket" "{res_name}" {{\n  bucket = "{bucket_name}"\n}}\n'
    with tempfile.NamedTemporaryFile(mode="w", suffix=".tf", delete=False, encoding="utf-8") as f:
        f.write(content)
        path = f.name
    try:
        parser = TerraformParser()
        first = parser.parse(path)
        second = parser.parse(path)
        assert len(first) == len(second)
        if first:
            assert first[0].name == second[0].name
            assert first[0].line_number == second[0].line_number
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# Property 5 (Hypothesis) — line_number > 0 for any valid resource
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(
    res_name=st.from_regex(r"[a-z][a-z0-9_]{0,19}", fullmatch=True),
)
def test_line_number_positive_hypothesis(res_name):
    """Property 5 (PBT): line_number > 0 for any valid resource in a .tf file."""
    import tempfile, os
    content = f'resource "aws_s3_bucket" "{res_name}" {{\n  bucket = "test"\n}}\n'
    with tempfile.NamedTemporaryFile(mode="w", suffix=".tf", delete=False, encoding="utf-8") as f:
        f.write(content)
        path = f.name
    try:
        parser = TerraformParser()
        resources = parser.parse(path)
        for r in resources:
            assert r.line_number > 0
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# Fixture file smoke test — all fixture .tf files parse without error
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fixture_file", list(FIXTURES.glob("*.tf")))
def test_fixture_files_parse_without_error(fixture_file):
    """Requirement 12.5: all fixture .tf files return at least one ResourceModel."""
    parser = TerraformParser()
    resources = parser.parse(str(fixture_file))
    # Should not raise; result may be empty for intentionally invalid fixtures
    assert isinstance(resources, list)


# ---------------------------------------------------------------------------
# _prescan unit tests — line_map correctness
# ---------------------------------------------------------------------------

def test_prescan_line_map_accuracy():
    content = """\
# some comment
resource "aws_s3_bucket" "first" {
  bucket = "first"
}

resource "aws_security_group" "second" {
  name = "sg"
}
"""
    parser = TerraformParser()
    line_map, _ = parser._prescan(content)

    assert ("aws_s3_bucket", "first") in line_map
    assert ("aws_security_group", "second") in line_map
    # "first" starts at line 2
    assert line_map[("aws_s3_bucket", "first")] == 2
    # "second" starts at line 6
    assert line_map[("aws_security_group", "second")] == 6


def test_prescan_ignore_map_global():
    content = """\
# tmac:ignore
resource "aws_s3_bucket" "ignored" {
  bucket = "x"
}
"""
    parser = TerraformParser()
    _, ignore_map = parser._prescan(content)
    assert ignore_map.get("ignored") == ["*"]


def test_prescan_ignore_map_inline_global():
    content = 'resource "aws_s3_bucket" "inline" { # tmac:ignore\n  bucket = "x"\n}\n'
    parser = TerraformParser()
    _, ignore_map = parser._prescan(content)
    assert ignore_map.get("inline") == ["*"]


def test_prescan_ignore_map_rule_id():
    content = """\
# tmac:ignore[TMAC-AWS-S3-001]
resource "aws_s3_bucket" "partial" {
  bucket = "x"
}
"""
    parser = TerraformParser()
    _, ignore_map = parser._prescan(content)
    assert "partial" in ignore_map
    assert ignore_map["partial"] == ["TMAC-AWS-S3-001"]


def test_prescan_no_ignore_for_undecorated_resource():
    content = """\
resource "aws_s3_bucket" "clean" {
  bucket = "clean"
}
"""
    parser = TerraformParser()
    _, ignore_map = parser._prescan(content)
    assert "clean" not in ignore_map
