"""
CloudFormation rules: each insecure fixture triggers exactly its service's rules and
the secure counterpart triggers none.

Validates: Requirements 5-16, 24 (tmac-v1-2-cloudformation)
"""

import re
from pathlib import Path

import pytest

from tmac.engine.matcher import Matcher
from tmac.engine.rule_loader import RuleLoader
from tmac.models.resource import ResourceModel
from tmac.parsers.cloudformation import CloudFormationParser

SERVICES = Path(__file__).parent.parent / "fixtures" / "cfn" / "services"

EXPECTED = {
    "s3": {"S3-001", "S3-002", "S3-003", "S3-004", "S3-005"},
    "iam": {f"IAM-00{i}" for i in range(1, 10)},
    "sg": {"SG-001", "SG-002", "SG-003"},
    "vpc": {"VPC-001"},
    "ec2": {"EC2-001", "EC2-002", "EC2-003", "EC2-004"},
    "rds": {"RDS-001", "RDS-002", "RDS-003", "RDS-004", "RDS-005"},
    "ddb": {"DDB-001", "DDB-002", "DDB-003"},
    "kms": {"KMS-001", "KMS-002", "KMS-003"},
    "lambda": {"LMD-001", "LMD-002", "LMD-003"},
    "cloudtrail": {"CW-001", "CW-002", "CW-003"},
    "apigw": {"APIGW-001", "APIGW-002", "APIGW-003"},
    "stack": {"STACK-001"},
}


@pytest.fixture(scope="module")
def rules():
    return [r for r in RuleLoader().load_rules() if r.id.startswith("TMAC-CFN-")]


def _rule_ids(path: Path, rules) -> set[str]:
    resources = CloudFormationParser().parse_strict(str(path))
    return {f.rule_id.removeprefix("TMAC-CFN-") for f in Matcher().match(resources, rules)}


@pytest.mark.parametrize("service", sorted(EXPECTED))
def test_insecure_fixture_triggers_all_service_rules(service, rules):
    assert _rule_ids(SERVICES / f"{service}_insecure.yaml", rules) == EXPECTED[service]


@pytest.mark.parametrize("service", sorted(EXPECTED))
def test_secure_fixture_triggers_nothing(service, rules):
    assert _rule_ids(SERVICES / f"{service}_secure.yaml", rules) == set()


def test_every_cfn_rule_is_covered_by_a_fixture(rules):
    covered = set().union(*EXPECTED.values())
    assert {r.id.removeprefix("TMAC-CFN-") for r in rules} == covered


def test_rule_catalog_conventions(rules):
    assert len(rules) >= 30
    for rule in rules:
        assert re.fullmatch(r"TMAC-CFN-[A-Z0-9]+-\d{3}", rule.id), rule.id
        assert rule.resource_type.startswith("AWS::"), rule.id
        assert all(ref.startswith("https://") for ref in rule.references), rule.id


# ---------------------------------------------------------------------------
# Targeted cases for the trickier conditions
# ---------------------------------------------------------------------------


def _match(resource_type: str, attributes: dict, rules) -> set[str]:
    resource = ResourceModel(
        resource_type=resource_type, name="R", attributes=attributes, source_file="t.yaml"
    )
    return {f.rule_id.removeprefix("TMAC-CFN-") for f in Matcher().match([resource], rules)}


@pytest.mark.parametrize(
    "action, fires",
    [("*", True), (["s3:GetObject", "*"], True), ("s3:*", False), (["s3:*", "ec2:*"], False)],
)
def test_wildcard_action_detection(action, fires, rules):
    doc = {"Statement": [{"Effect": "Allow", "Action": action, "Resource": "arn:aws:s3:::b"}]}
    assert ("IAM-002" in _match("AWS::IAM::Policy", {"PolicyDocument": doc}, rules)) is fires


def test_single_statement_object_is_supported(rules):
    doc = {"Statement": {"Effect": "Allow", "Action": "*", "Resource": "*"}}
    assert {"IAM-001", "IAM-002"} <= _match("AWS::IAM::Policy", {"PolicyDocument": doc}, rules)


@pytest.mark.parametrize(
    "variables, fires",
    [
        ({"DB_PASSWORD": "hunter2"}, True),
        ({"api_key": "abc"}, True),
        ({"DB_PASSWORD": "{{resolve:ssm-secure:db-pass:1}}"}, False),
        ({"DB_PASSWORD": {"Ref": "DbPassword"}}, False),
        ({"LOG_LEVEL": "debug"}, False),
    ],
)
def test_lambda_secret_detection(variables, fires, rules):
    attrs = {"Environment": {"Variables": variables}, "TracingConfig": {"Mode": "Active"}}
    assert ("LMD-001" in _match("AWS::Lambda::Function", attrs, rules)) is fires


def test_options_method_without_auth_is_allowed(rules):
    attrs = {"HttpMethod": "OPTIONS", "AuthorizationType": "NONE"}
    assert "APIGW-001" not in _match("AWS::ApiGateway::Method", attrs, rules)


def test_cfn_rules_never_apply_to_terraform_resources(rules):
    assert _match("aws_s3_bucket", {"AccessControl": "PublicRead"}, rules) == set()
