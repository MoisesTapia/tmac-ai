"""Targeted checks for rules in threats_extended.yaml whose conditions are easy to get wrong."""

import pytest

from tmac.engine.matcher import Matcher
from tmac.engine.rule_loader import RuleLoader
from tmac.models.resource import ResourceModel


@pytest.mark.parametrize(
    "types, fires",
    [
        (["PLAINTEXT"], True),
        (["SECRETS_MANAGER", "PLAINTEXT"], True),
        (["SECRETS_MANAGER"], False),
        ([], False),
    ],
)
def test_codebuild_plaintext_variables_rule(types, fires):
    rule = next(r for r in RuleLoader().load_rules() if r.id == "TMAC-AWS-CB-003")
    env = {
        "environment": [
            {"environment_variable": [{"name": f"V{i}", "type": t} for i, t in enumerate(types)]}
        ]
    }
    resource = ResourceModel(
        resource_type="aws_codebuild_project", name="p", attributes=env, source_file="m.tf"
    )
    assert bool(Matcher().match([resource], [rule])) is fires
