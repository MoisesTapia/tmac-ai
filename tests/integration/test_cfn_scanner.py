"""
Integration tests: Scanner(parser=CloudFormationParser()) over fixture directories.

Validates: Requirements 18, 19, 20 (tmac-v1-2-cloudformation; CfnScanner is replaced by
the format-agnostic Scanner with a pluggable parser).
"""

import shutil
from pathlib import Path

import pytest

from tmac.parsers.cloudformation import CloudFormationParser
from tmac.reporters import get_reporter
from tmac.scanner import Scanner

FIXTURES = Path(__file__).parent.parent / "fixtures"
CFN = FIXTURES / "cfn"


def _scan(directory, **kwargs):
    return Scanner(parser=CloudFormationParser()).run_scan(str(directory), **kwargs)


def test_services_directory(tmp_path):
    result = _scan(CFN / "services")
    assert result.files_scanned == 24
    assert result.issues == []
    assert all(f.rule_id.startswith("TMAC-CFN-") for f in result.findings)
    assert result.statistics.total_findings == len(result.findings) > 0
    assert result.rules_loaded >= 101 + 43


def test_only_cloudformation_files_are_processed(tmp_path):
    shutil.copy(CFN / "services" / "s3_insecure.yaml", tmp_path / "s3.yaml")
    shutil.copy(FIXTURES / "s3_public_acl.tf", tmp_path / "main.tf")
    shutil.copytree(CFN / "not_cfn", tmp_path / "not_cfn")
    result = _scan(tmp_path)
    assert result.files_scanned == 1
    assert all(f.rule_id.startswith("TMAC-CFN-") for f in result.findings)


def test_directory_without_templates(tmp_path):
    (tmp_path / "README.md").write_text("nothing here", encoding="utf-8")
    result = _scan(tmp_path)
    assert (result.files_scanned, result.findings, result.issues) == (0, [], [])


def test_invalid_templates_are_reported_as_issues():
    result = _scan(CFN / "invalid")
    assert sorted(Path(i.file_path).name for i in result.issues) == [
        "invalid_json.json",
        "invalid_yaml.yaml",
    ]


def test_exclude_patterns_and_ignores(tmp_path):
    shutil.copy(CFN / "tmac_ignore.yaml", tmp_path / "ignored.yaml")
    shutil.copy(CFN / "services" / "s3_insecure.yaml", tmp_path / "skip_me.yaml")
    result = _scan(tmp_path, exclude_patterns=["skip_*"])
    assert result.files_scanned == 1
    by_resource = {(f.resource_name, f.rule_id) for f in result.findings}
    assert not any(name == "IgnoredBucket" for name, _ in by_resource)
    assert ("PartialBucket", "TMAC-CFN-S3-001") not in by_resource
    assert ("PartialBucket", "TMAC-CFN-S3-003") in by_resource


@pytest.mark.parametrize("min_severity", ["critical", "high", "medium"])
def test_min_severity_filter(min_severity):
    full = _scan(CFN / "services")
    filtered = _scan(CFN / "services", min_severity=min_severity)
    order = ["info", "low", "medium", "high", "critical"]
    assert len(filtered.findings) <= len(full.findings)
    assert all(
        order.index(f.severity.lower()) >= order.index(min_severity) for f in filtered.findings
    )


@pytest.mark.parametrize("fmt", ["html", "md", "json"])
def test_reporters_render_cfn_results(fmt):
    result = _scan(CFN / "services")
    content = get_reporter(fmt).generate(result)
    assert "TMAC-CFN-S3-001" in content


@pytest.mark.parametrize("fmt", ["html", "md", "json"])
def test_reporters_render_empty_cfn_results(fmt, tmp_path):
    content = get_reporter(fmt).generate(_scan(tmp_path))
    assert content
