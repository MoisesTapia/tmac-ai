"""
Unit tests for TMAC data models: Finding, ScanResult, ResourceModel.

Validates: Requirements 9.1, 9.2, 9.3, 20.2, 20.3
"""
from typing import Any, Dict

import pytest
from hypothesis import given, settings, strategies as st

from tmac.models.finding import Finding, ScanMetadata, ScanResult, ScanStatistics
from tmac.models.resource import ResourceModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_finding(**kwargs) -> Finding:
    defaults: Dict[str, Any] = dict(
        rule_id="TMAC-AWS-S3-001",
        rule_name="S3 Public ACL",
        severity="Critical",
        stride="Information Disclosure",
        resource_type="aws_s3_bucket",
        resource_name="test_bucket",
        file_path="test.tf",
        line_number=5,
        matched_attribute="acl",
        description="Bucket is public",
        mitigation="Set acl to private",
    )
    defaults.update(kwargs)
    return Finding(**defaults)


def _make_scan_result(**kwargs) -> ScanResult:
    defaults: Dict[str, Any] = dict(
        metadata=ScanMetadata(scanned_directory="/tmp/test"),
        statistics=ScanStatistics(total_resources=1, total_findings=1, critical=1),
        findings=[_make_finding()],
    )
    defaults.update(kwargs)
    return ScanResult(**defaults)


def _make_resource(**kwargs) -> ResourceModel:
    defaults: Dict[str, Any] = dict(
        resource_type="aws_s3_bucket",
        name="test_bucket",
        attributes={"acl": "public-read"},
        source_file="test.tf",
        line_number=5,
    )
    defaults.update(kwargs)
    return ResourceModel(**defaults)


# ---------------------------------------------------------------------------
# Finding tests — Requirement 9.1
# ---------------------------------------------------------------------------

class TestFinding:
    def test_tags_defaults_to_empty_list(self):
        """Finding.tags has a default value of empty list."""
        finding = _make_finding()
        assert finding.tags == []

    def test_tags_accepts_list_of_strings(self):
        """Finding accepts tags as a list of strings."""
        finding = _make_finding(tags=["s3", "public-access", "pci"])
        assert finding.tags == ["s3", "public-access", "pci"]

    def test_tags_accepts_empty_list_explicitly(self):
        """Finding accepts an explicitly provided empty list for tags."""
        finding = _make_finding(tags=[])
        assert finding.tags == []

    def test_tags_are_independent_between_instances(self):
        """Two Finding instances do not share the same tags list."""
        f1 = _make_finding()
        f2 = _make_finding()
        f1.tags.append("mutated")
        assert f2.tags == []


# ---------------------------------------------------------------------------
# ScanResult tests — Requirements 9.2, 9.3
# ---------------------------------------------------------------------------

class TestScanResult:
    def test_files_scanned_defaults_to_zero(self):
        """ScanResult.files_scanned defaults to 0."""
        result = _make_scan_result()
        assert result.files_scanned == 0

    def test_rules_loaded_defaults_to_zero(self):
        """ScanResult.rules_loaded defaults to 0."""
        result = _make_scan_result()
        assert result.rules_loaded == 0

    def test_files_scanned_accepts_positive_int(self):
        """ScanResult accepts files_scanned as a positive integer."""
        result = _make_scan_result(files_scanned=42)
        assert result.files_scanned == 42

    def test_rules_loaded_accepts_positive_int(self):
        """ScanResult accepts rules_loaded as a positive integer."""
        result = _make_scan_result(rules_loaded=10)
        assert result.rules_loaded == 10

    def test_both_fields_set_together(self):
        """ScanResult accepts both files_scanned and rules_loaded simultaneously."""
        result = _make_scan_result(files_scanned=7, rules_loaded=15)
        assert result.files_scanned == 7
        assert result.rules_loaded == 15


# ---------------------------------------------------------------------------
# ResourceModel.to_dict() round-trip — Requirements 20.2, 20.3
# ---------------------------------------------------------------------------

class TestResourceModelToDict:
    def test_to_dict_returns_dict(self):
        """to_dict() returns a plain dict."""
        resource = _make_resource()
        assert isinstance(resource.to_dict(), dict)

    def test_to_dict_contains_all_fields(self):
        """to_dict() includes all required fields."""
        resource = _make_resource()
        data = resource.to_dict()
        for field in ("resource_type", "name", "attributes", "source_file", "line_number"):
            assert field in data, f"Missing field: {field}"

    def test_round_trip_produces_equivalent_object(self):
        """Serializing with to_dict() and reconstructing produces an equivalent ResourceModel."""
        original = _make_resource()
        data = original.to_dict()
        reconstructed = ResourceModel(**data)

        assert reconstructed.resource_type == original.resource_type
        assert reconstructed.name == original.name
        assert reconstructed.attributes == original.attributes
        assert reconstructed.source_file == original.source_file
        assert reconstructed.line_number == original.line_number

    def test_round_trip_with_nested_attributes(self):
        """Round-trip preserves nested attribute structures."""
        original = _make_resource(
            attributes={"tags": {"env": "prod"}, "acl": "private", "count": 3}
        )
        reconstructed = ResourceModel(**original.to_dict())
        assert reconstructed.attributes == original.attributes

    def test_round_trip_with_zero_line_number(self):
        """Round-trip works when line_number is 0 (default)."""
        original = _make_resource(line_number=0)
        reconstructed = ResourceModel(**original.to_dict())
        assert reconstructed.line_number == 0


# ---------------------------------------------------------------------------
# Property 19: ResourceModel serialization round-trip
# Validates: Requirements 20.2, 20.3
# ---------------------------------------------------------------------------

# Strategies for generating ResourceModel fields
_resource_type_st = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="_"),
    min_size=1,
    max_size=50,
)
_name_st = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="_-"),
    min_size=1,
    max_size=50,
)
_source_file_st = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="/_-."),
    min_size=1,
    max_size=100,
)
_attributes_st = st.dictionaries(
    keys=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("Ll",), whitelist_characters="_")),
    values=st.one_of(
        st.text(max_size=50),
        st.integers(),
        st.booleans(),
        st.none(),
    ),
    max_size=10,
)


@settings(max_examples=100)
@given(
    resource_type=_resource_type_st,
    name=_name_st,
    attributes=_attributes_st,
    source_file=_source_file_st,
    line_number=st.integers(min_value=0, max_value=100_000),
)
def test_property_19_resource_model_round_trip(
    resource_type: str,
    name: str,
    attributes: Dict[str, Any],
    source_file: str,
    line_number: int,
):
    """
    **Property 19: ResourceModel serialization round-trip**

    For any ResourceModel, calling to_dict() and reconstructing with
    ResourceModel(**data) must produce an equivalent object with all fields
    preserved (resource_type, name, attributes, source_file, line_number).

    **Validates: Requirements 20.2, 20.3**
    """
    original = ResourceModel(
        resource_type=resource_type,
        name=name,
        attributes=attributes,
        source_file=source_file,
        line_number=line_number,
    )
    data = original.to_dict()
    reconstructed = ResourceModel(**data)

    assert reconstructed.resource_type == original.resource_type
    assert reconstructed.name == original.name
    assert reconstructed.attributes == original.attributes
    assert reconstructed.source_file == original.source_file
    assert reconstructed.line_number == original.line_number
