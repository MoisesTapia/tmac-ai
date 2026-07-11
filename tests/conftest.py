"""
Shared pytest fixtures for TMAC test suite.

Validates: Requirements 11.1
"""
from pathlib import Path

import pytest

from tmac.delta.models import ChangeAction, DeltaFinding, DeltaScanResult, PlannedChange
from tmac.models.finding import Finding, ScanMetadata, ScanResult, ScanStatistics
from tmac.models.resource import ResourceModel
from tmac.models.rule import CheckCondition, ThreatRule


@pytest.fixture
def sample_finding() -> Finding:
    return Finding(
        rule_id="TMAC-AWS-S3-001",
        rule_name="S3 Public ACL",
        severity="Critical",
        stride="Information Disclosure",
        resource_type="aws_s3_bucket",
        resource_name="test_bucket",
        file_path="test.tf",
        line_number=5,
        matched_attribute="acl",
        description="Bucket is publicly accessible via ACL.",
        mitigation="Set acl to private.",
        tags=["s3", "public-access"],
    )


@pytest.fixture
def sample_scan_result(sample_finding: Finding) -> ScanResult:
    return ScanResult(
        metadata=ScanMetadata(scanned_directory="/tmp/test"),
        statistics=ScanStatistics(
            total_resources=1,
            total_findings=1,
            critical=1,
        ),
        findings=[sample_finding],
        files_scanned=1,
        rules_loaded=10,
    )


@pytest.fixture
def sample_rule() -> ThreatRule:
    return ThreatRule(
        id="TMAC-AWS-S3-001",
        name="S3 Public ACL",
        resource_type="aws_s3_bucket",
        check=CheckCondition(
            attribute="acl",
            condition="in",
            values=["public-read", "public-read-write"],
        ),
        severity="Critical",
        stride="Information Disclosure",
        description="Bucket is publicly accessible via ACL.",
        mitigation="Set acl to private.",
        tags=["s3", "public-access"],
    )


@pytest.fixture
def sample_resource() -> ResourceModel:
    return ResourceModel(
        resource_type="aws_s3_bucket",
        name="test_bucket",
        attributes={"acl": "public-read"},
        source_file="test.tf",
        line_number=5,
    )


@pytest.fixture
def fixtures_path() -> Path:
    return Path("tests/fixtures")


@pytest.fixture
def fixtures_plans_path() -> Path:
    return Path("tests/fixtures/plans")


@pytest.fixture
def sample_planned_change() -> PlannedChange:
    return PlannedChange(
        address="aws_s3_bucket.data",
        resource_type="aws_s3_bucket",
        resource_name="data",
        action=ChangeAction.update,
        before={"acl": "private", "bucket": "my-data-bucket"},
        after={"acl": "public-read", "bucket": "my-data-bucket"},
    )


@pytest.fixture
def sample_delta_finding() -> DeltaFinding:
    return DeltaFinding(
        rule_id="TMAC-AWS-S3-001",
        rule_name="S3 Public ACL",
        severity="Critical",
        stride="Information Disclosure",
        resource_type="aws_s3_bucket",
        resource_name="data",
        file_path="aws_s3_bucket.data",
        line_number=0,
        matched_attribute="acl",
        description="Bucket is publicly accessible via ACL.",
        mitigation="Set acl to private.",
        change_action=ChangeAction.update,
        changed_attribute="acl",
        value_before="private",
        value_after="public-read",
    )


@pytest.fixture
def sample_delta_scan_result(sample_delta_finding: DeltaFinding) -> DeltaScanResult:
    return DeltaScanResult(
        metadata=ScanMetadata(scanned_directory="aws_s3_bucket.data"),
        statistics=ScanStatistics(total_resources=1, total_findings=1, critical=1),
        findings=[sample_delta_finding],
        files_scanned=1,
        rules_loaded=10,
        findings_introduced=1,
        findings_resolved=0,
        resources_created=0,
        resources_updated=1,
        resources_deleted=0,
        plan_file="tests/fixtures/plans/update_secure_to_insecure.json",
    )
