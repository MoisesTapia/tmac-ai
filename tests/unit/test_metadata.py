"""Tests for extracting configuration metadata from resources."""

import json

from tmac.graph.metadata import (
    MetadataExtractor,
    render_metadata,
    render_metadata_json,
)
from tmac.models.resource import ResourceModel


def _resources():
    return [
        ResourceModel(
            resource_type="aws_vpc",
            name="main",
            attributes={"cidr_block": "10.0.0.0/16"},
            source_file="main.tf",
            line_number=1,
        ),
        ResourceModel(
            resource_type="aws_flow_log",
            name="vpc_flow",
            attributes={"vpc_id": "${aws_vpc.main.id}", "traffic_type": "ALL"},
            source_file="main.tf",
            line_number=5,
        ),
        ResourceModel(
            resource_type="aws_db_instance",
            name="prod",
            attributes={
                "engine": "postgres",
                "instance_class": "db.t3.micro",
                "vpc_security_group_ids": ["${aws_security_group.sg.id}"],
            },
            source_file="main.tf",
            line_number=10,
        ),
    ]


def test_extracts_metadata_per_resource():
    md = MetadataExtractor().extract(_resources())
    assert len(md) == 3
    ids = {m.id for m in md}
    assert "aws_vpc.main" in ids


def test_classifies_config_connections_blocks():
    md = {m.id: m for m in MetadataExtractor().extract(_resources())}
    db = md["aws_db_instance.prod"]
    # engine is scalar configuration
    assert "engine" in db.config
    # vpc_security_group_ids is a connection (reference)
    assert "vpc_security_group_ids" in db.connections


def test_instance_class_not_treated_as_reference():
    # 'db.t3.micro' must not be classified as a connection
    md = {m.id: m for m in MetadataExtractor().extract(_resources())}
    db = md["aws_db_instance.prod"]
    assert "instance_class" in db.config
    assert "instance_class" not in db.connections


def test_security_attrs_marks_missing():
    md = {m.id: m for m in MetadataExtractor().extract(_resources())}
    db = md["aws_db_instance.prod"]
    # storage_encrypted is not defined → it must be marked as undefined
    assert db.security_attrs.get("storage_encrypted") == "<not defined>"


def test_satellite_enrichment_links_flow_log_to_vpc():
    md = {m.id: m for m in MetadataExtractor().extract(_resources())}
    vpc = md["aws_vpc.main"]
    assert "VPC Flow Logs" in vpc.enrichments


def test_render_markdown_contains_sections():
    md = MetadataExtractor().extract(_resources())
    out = render_metadata(md, "md")
    assert "# TMAC" in out
    assert "aws_vpc.main" in out
    assert "VPC Flow Logs" in out


def test_render_json_is_valid_and_roundtrips():
    md = MetadataExtractor().extract(_resources())
    out = render_metadata_json(md)
    payload = json.loads(out)
    assert payload["total_resources"] == 3
    assert len(payload["resources"]) == 3


def test_security_config_loaded_from_yaml():
    # The external YAML adds types that were not in the defaults (e.g. dynamodb).
    from tmac.graph.metadata import SATELLITE_RESOURCES, SECURITY_ATTRS

    assert "aws_dynamodb_table" in SECURITY_ATTRS
    assert "aws_flow_log" in SATELLITE_RESOURCES


def test_security_config_fallback_on_missing_file(monkeypatch, tmp_path):
    from tmac.graph import metadata as m

    monkeypatch.setattr(m, "_SECURITY_ATTRS_YAML", tmp_path / "nope.yaml")
    sec, sat = m._load_security_config()
    # Falls back to the defaults without raising an exception
    assert "aws_s3_bucket" in sec
    assert "aws_flow_log" in sat
