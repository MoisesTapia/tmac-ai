"""
Unit tests for CloudFormationParser.

Validates: Requirements 1, 2, 3, 4, 21 (tmac-v1-2-cloudformation)
"""

import logging
from pathlib import Path

import pytest

from tmac.engine.evaluator import Evaluator
from tmac.models.rule import CheckCondition
from tmac.parsers.base import ParseError
from tmac.parsers.cloudformation import MAX_TEMPLATE_BYTES, CloudFormationParser

CFN = Path(__file__).parent.parent / "fixtures" / "cfn"


@pytest.fixture
def parser() -> CloudFormationParser:
    return CloudFormationParser()


def _by_name(resources):
    return {r.name: r for r in resources}


# ---------------------------------------------------------------------------
# Requisitos 1 y 2 — YAML y JSON
# ---------------------------------------------------------------------------


class TestParsing:
    def test_yaml_maps_logical_id_type_properties_and_line(self, parser):
        path = str(CFN / "valid_multi_resource.yaml")
        resources = _by_name(parser.parse(path))
        assert set(resources) == {"Bucket", "Queue", "Sg"}
        bucket = resources["Bucket"]
        assert bucket.resource_type == "AWS::S3::Bucket"
        assert bucket.attributes["AccessControl"] == "PublicRead"
        assert bucket.source_file == path
        assert bucket.line_number == 4  # line of "  Bucket:"
        assert resources["Queue"].attributes == {}  # no Properties

    def test_json_produces_same_resources_as_equivalent_yaml(self, parser):
        yaml_res = parser.parse(str(CFN / "valid_multi_resource.yaml"))
        json_res = parser.parse(str(CFN / "valid_template.json"))
        key = lambda r: (r.name, r.resource_type, r.attributes)
        assert sorted(map(key, yaml_res), key=str) == sorted(map(key, json_res), key=str)

    def test_json_line_numbers(self, parser):
        resources = _by_name(parser.parse(str(CFN / "valid_template.json")))
        assert resources["Bucket"].line_number == 5
        assert resources["Queue"].line_number == 12

    def test_format_is_detected_by_content_not_extension(self, parser, tmp_path):
        disguised = tmp_path / "template.yaml"
        disguised.write_text((CFN / "valid_template.json").read_text(), encoding="utf-8")
        assert len(parser.parse(str(disguised))) == 3

    def test_parsing_is_deterministic(self, parser):
        path = str(CFN / "intrinsic_functions.yaml")
        assert parser.parse(path) == parser.parse(path)

    def test_dates_stay_strings(self, parser, tmp_path):
        f = tmp_path / "t.yaml"
        f.write_text(
            "Resources:\n  B:\n    Type: AWS::S3::Bucket\n    Properties: {Created: 2024-01-01}\n"
        )
        assert parser.parse(str(f))[0].attributes["Created"] == "2024-01-01"


class TestEdgeCases:
    def test_empty_resources_returns_empty_list(self, parser, caplog):
        with caplog.at_level(logging.WARNING):
            assert parser.parse_strict(str(CFN / "empty_resources.yaml")) == []
        assert caplog.text == ""

    def test_missing_resources_warns_and_returns_empty(self, parser, caplog):
        with caplog.at_level(logging.WARNING):
            assert parser.parse_strict(str(CFN / "no_resources.yaml")) == []
        assert "No 'Resources' section" in caplog.text

    @pytest.mark.parametrize("name", ["invalid/invalid_yaml.yaml", "invalid/invalid_json.json"])
    def test_invalid_syntax_raises_parse_error_in_strict_mode(self, parser, name):
        with pytest.raises(ParseError, match="Failed to parse"):
            parser.parse_strict(str(CFN / name))

    @pytest.mark.parametrize("name", ["invalid/invalid_yaml.yaml", "invalid/invalid_json.json"])
    def test_invalid_syntax_returns_empty_in_lenient_mode(self, parser, name, caplog):
        with caplog.at_level(logging.WARNING):
            assert parser.parse(str(CFN / name)) == []
        assert "Failed to parse" in caplog.text

    def test_missing_file(self, parser, tmp_path):
        assert parser.parse(str(tmp_path / "nope.yaml")) == []
        with pytest.raises(ParseError):
            parser.parse_strict(str(tmp_path / "nope.yaml"))

    @pytest.mark.parametrize(
        "body, message",
        [
            ("Resources:\n  B: {Properties: {}}\n", "has no 'Type'"),
            ("Resources:\n  B: {Type: AWS::S3::Bucket, Properties: [1]}\n", "not a mapping"),
            ("Resources: [1, 2]\n", "'Resources' is not a mapping"),
            ("- just\n- a list\n", "template is not a mapping"),
        ],
    )
    def test_malformed_templates_raise(self, parser, tmp_path, body, message):
        f = tmp_path / "t.yaml"
        f.write_text(body, encoding="utf-8")
        with pytest.raises(ParseError, match=message):
            parser.parse_strict(str(f))

    def test_oversized_file_is_rejected(self, parser, tmp_path):
        f = tmp_path / "big.yaml"
        f.write_bytes(b"#" * (MAX_TEMPLATE_BYTES + 1))
        with pytest.raises(ParseError, match="larger than"):
            parser.parse_strict(str(f))

    def test_yaml_alias_bomb_is_rejected_quickly(self, parser, tmp_path):
        lines = ['a: &a ["x","x","x","x","x","x","x","x","x"]']
        for prev, cur in zip("abcdef", "bcdefg"):
            lines.append(f"{cur}: &{cur} [{','.join(['*' + prev] * 9)}]")
        lines += ["Resources:", "  B:", "    Type: AWS::S3::Bucket", "    Properties: {X: *g}"]
        f = tmp_path / "bomb.yaml"
        f.write_text("\n".join(lines) + "\n", encoding="utf-8")
        with pytest.raises(ParseError, match="alias expansion"):
            parser.parse_strict(str(f))

    def test_global_safe_loader_is_not_modified(self):
        import yaml

        with pytest.raises(yaml.constructor.ConstructorError):
            yaml.safe_load("x: !Ref Foo")


class TestCanParse:
    @pytest.mark.parametrize(
        "name", ["valid_multi_resource.yaml", "valid_template.json", "invalid/invalid_yaml.yaml"]
    )
    def test_cloudformation_files_are_accepted(self, parser, name):
        assert parser.can_parse(str(CFN / name))

    @pytest.mark.parametrize("name", ["deployment.yaml", "package.json", "helm_template.yaml"])
    def test_other_yaml_and_json_are_skipped(self, parser, name):
        assert not parser.can_parse(str(CFN / "not_cfn" / name))

    def test_unreadable_path_is_skipped(self, parser, tmp_path):
        assert not parser.can_parse(str(tmp_path / "missing.yaml"))


# ---------------------------------------------------------------------------
# Requisito 3 — Intrinsic functions
# ---------------------------------------------------------------------------


class TestIntrinsicFunctions:
    @pytest.fixture
    def resources(self, parser):
        return _by_name(parser.parse(str(CFN / "intrinsic_functions.yaml")))

    def test_short_form_tags_become_sentinels(self, resources):
        attrs = resources["Bucket"].attributes
        assert attrs["BucketName"] == {"Sub": "${Env}-data"}
        assert attrs["AccessControl"] == {"If": ["IsProd", "Private", "PublicRead"]}
        assert attrs["Tags"][0]["Value"] == {
            "Join": [":", [{"Ref": "AWS::Region"}, {"GetAtt": "Role.Arn"}]]
        }

    def test_long_form_is_normalized_like_short_form(self, resources):
        attrs = resources["Role"].attributes
        assert attrs["RoleName"] == {"Sub": "${Env}-role"}
        assert attrs["Path"] == {"Select": [0, ["/", "/app/"]]}
        assert attrs["PermissionsBoundary"] == {"GetAtt": "Boundary.Arn"}
        principal = attrs["AssumeRolePolicyDocument"]["Statement"][0]["Principal"]
        assert principal == {"Service": {"FindInMap": ["Services", "Lambda", "Principal"]}}

    @pytest.mark.parametrize(
        "condition, values, expected",
        [
            ("exists", [], True),
            ("not_exists", [], False),
            ("equals", ["PublicRead"], False),
            ("not_equals", ["Private"], False),
            ("in", ["PublicRead"], False),
            ("not_in", ["Private"], False),
            ("regex", ["Public"], False),
        ],
    )
    def test_evaluator_treats_sentinel_as_present_but_unknown(
        self, resources, condition, values, expected
    ):
        check = CheckCondition(attribute="AccessControl", condition=condition, values=values)
        assert Evaluator().evaluate(check, resources["Bucket"].attributes) is expected


# ---------------------------------------------------------------------------
# Requisito 4 — tmac:ignore
# ---------------------------------------------------------------------------


class TestIgnores:
    @pytest.fixture
    def resources(self, parser):
        return _by_name(parser.parse(str(CFN / "tmac_ignore.yaml")))

    def test_comment_above_logical_id_is_global(self, resources):
        assert resources["IgnoredBucket"].ignored_rules == ["*"]

    def test_consecutive_rule_comments_accumulate(self, resources):
        assert sorted(resources["PartialBucket"].ignored_rules) == [
            "TMAC-CFN-S3-001",
            "TMAC-CFN-S3-002",
        ]

    def test_inline_comment(self, resources):
        assert resources["InlineBucket"].ignored_rules == ["TMAC-CFN-S3-003"]

    def test_metadata_ignore(self, resources):
        assert resources["MetadataBucket"].ignored_rules == ["TMAC-CFN-S3-005"]

    def test_comment_does_not_leak_past_a_resource(self, resources):
        assert resources["PlainBucket"].ignored_rules == []

    def test_get_ignore_map(self, parser):
        path = str(CFN / "tmac_ignore.yaml")
        ignore_map = parser.get_ignore_map(path)
        assert ignore_map["IgnoredBucket"] == ["*"]
        assert "PlainBucket" not in ignore_map
        assert ignore_map == parser.get_ignore_map(path)

    def test_get_ignore_map_of_invalid_file_is_empty(self, parser):
        assert parser.get_ignore_map(str(CFN / "invalid" / "invalid_yaml.yaml")) == {}

    def test_metadata_ignore_works_in_json(self, parser, tmp_path):
        f = tmp_path / "t.json"
        f.write_text(
            '{"Resources": {"B": {"Type": "AWS::S3::Bucket", '
            '"Metadata": {"tmac": {"ignore": "*"}}}}}',
            encoding="utf-8",
        )
        assert parser.parse(str(f))[0].ignored_rules == ["*"]


# ---------------------------------------------------------------------------
# Requisito 21 — Pretty printer / round-trip
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_serialize_structure(self, parser):
        resources = parser.parse(str(CFN / "valid_multi_resource.yaml"))
        data = parser.serialize(resources)
        assert data["Resources"]["Bucket"]["Type"] == "AWS::S3::Bucket"
        assert data["Resources"]["Bucket"]["Properties"]["AccessControl"] == "PublicRead"

    def test_serialize_writes_intrinsics_in_long_form(self, parser):
        resources = _by_name(parser.parse(str(CFN / "intrinsic_functions.yaml")))
        props = parser.serialize([resources["Bucket"]])["Resources"]["Bucket"]["Properties"]
        assert props["BucketName"] == {"Fn::Sub": "${Env}-data"}

    @pytest.mark.parametrize("name", ["valid_multi_resource.yaml", "intrinsic_functions.yaml"])
    def test_yaml_round_trip(self, parser, tmp_path, name):
        original = parser.parse(str(CFN / name))
        f = tmp_path / "round.yaml"
        f.write_text(parser.serialize_to_yaml(original), encoding="utf-8")
        again = parser.parse(str(f))
        assert [(r.name, r.resource_type, r.attributes) for r in again] == [
            (r.name, r.resource_type, r.attributes) for r in original
        ]

    def test_dict_round_trip(self, parser):
        original = parser.parse(str(CFN / "valid_template.json"))
        again = parser.parse_template(parser.serialize(original))
        assert [(r.name, r.attributes) for r in again] == [(r.name, r.attributes) for r in original]
