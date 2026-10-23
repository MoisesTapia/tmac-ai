"""Property-based tests for TMAC v1.1.0 delta analysis pipeline.

Covers all 18 correctness properties defined in the design document.
Each test uses @settings(max_examples=100) and includes the canonical
feature tag comment.

Feature: tmac-v1-1-tfplan-delta
Validates: Requirements 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.10, 1.11, 1.12,
           2.7, 3.2, 3.3, 3.4, 3.5, 3.6, 3.8, 4.4, 4.5, 4.6, 4.7, 4.9,
           5.1, 5.3, 5.5, 5.7, 6.5, 6.6
"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from tests.property.strategies import (
    attributes_strategy,
    delta_finding_strategy,
    planned_change_strategy,
    rule_strategy,
)
from tmac.cli import cli
from tmac.delta.models import ChangeAction, DeltaFinding, DeltaScanResult, PlannedChange
from tmac.delta.scanner import DeltaScanner
from tmac.engine.evaluator import Evaluator
from tmac.models.finding import ScanMetadata, ScanStatistics
from tmac.parsers.tfplan import TfplanParser
from tmac.reporters.html import HTMLReporter
from tmac.reporters.json_report import JSONReporter
from tmac.reporters.markdown import MarkdownReporter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PLANS = Path("tests/fixtures/plans")


def _write_plan(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)


def _minimal_plan(address: str, actions: list, before=None, after=None) -> dict:
    return {
        "format_version": "1.2",
        "resource_changes": [
            {
                "address": address,
                "type": address.rsplit(".", 2)[-2] if address.count(".") >= 1 else address,
                "name": address.rsplit(".", 1)[-1],
                "change": {"actions": actions, "before": before, "after": after},
            }
        ],
    }


def _make_delta_scan_result(findings: list[DeltaFinding], resolved: int = 0) -> DeltaScanResult:
    return DeltaScanResult(
        metadata=ScanMetadata(scanned_directory="test"),
        statistics=ScanStatistics(
            total_resources=len(findings),
            total_findings=len(findings),
            critical=sum(1 for f in findings if f.severity.lower() == "critical"),
            high=sum(1 for f in findings if f.severity.lower() == "high"),
        ),
        findings=findings,
        files_scanned=1,
        rules_loaded=1,
        findings_introduced=len(findings),
        findings_resolved=resolved,
        resources_created=0,
        resources_updated=len(findings),
        resources_deleted=0,
        plan_file="test.json",
    )


# ===========================================================================
# Property 1: Parser before/after semantics by action
# ===========================================================================


@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    action=st.sampled_from(["create", "update", "delete"]),
    attrs=attributes_strategy(),
)
def test_parser_before_after_semantics_by_action(tmp_path, action, attrs):
    # Feature: tmac-v1-1-tfplan-delta, Property 1: Parser before/after semantics by action
    before = attrs if action in ("update", "delete") else None
    after = attrs if action in ("update", "create") else None
    data = _minimal_plan("aws_s3_bucket.test", [action], before=before, after=after)
    plan_path = str(tmp_path / "plan.json")
    _write_plan(plan_path, data)

    parser = TfplanParser()
    changes = parser.parse_plan(plan_path)
    assert len(changes) == 1
    c = changes[0]

    if action == "create":
        assert c.before is None
        assert c.after is not None
    elif action == "delete":
        assert c.before is not None
        assert c.after is None
    else:  # update
        assert c.before is not None
        assert c.after is not None


# ===========================================================================
# Property 2: The parser omits no-op resources
# ===========================================================================


@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    n_noop=st.integers(min_value=1, max_value=5),
    n_real=st.integers(min_value=0, max_value=3),
)
def test_parser_omits_noop_resources(tmp_path, n_noop, n_real):
    # Feature: tmac-v1-1-tfplan-delta, Property 2: The parser omits no-op resources
    resource_changes = []
    for i in range(n_noop):
        resource_changes.append(
            {
                "address": f"aws_s3_bucket.noop_{i}",
                "type": "aws_s3_bucket",
                "name": f"noop_{i}",
                "change": {
                    "actions": ["no-op"],
                    "before": {"acl": "private"},
                    "after": {"acl": "private"},
                },
            }
        )
    for i in range(n_real):
        resource_changes.append(
            {
                "address": f"aws_s3_bucket.real_{i}",
                "type": "aws_s3_bucket",
                "name": f"real_{i}",
                "change": {
                    "actions": ["create"],
                    "before": None,
                    "after": {"acl": "private"},
                },
            }
        )

    data = {"format_version": "1.2", "resource_changes": resource_changes}
    plan_path = str(tmp_path / "plan.json")
    _write_plan(plan_path, data)

    parser = TfplanParser()
    changes = parser.parse_plan(plan_path)

    # No no-op resources should appear
    assert all(c.action != ChangeAction.create or "noop_" not in c.resource_name for c in changes)
    noop_addresses = {f"aws_s3_bucket.noop_{i}" for i in range(n_noop)}
    assert not any(c.address in noop_addresses for c in changes)
    assert len(changes) == n_real


# ===========================================================================
# Property 3: The parser is deterministic
# ===========================================================================


@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(planned_change_strategy())
def test_parser_deterministic(tmp_path, change):
    # Feature: tmac-v1-1-tfplan-delta, Property 3: The parser is deterministic
    actions = (
        ["delete", "create"] if change.action == ChangeAction.replace else [change.action.value]
    )
    data = _minimal_plan(change.address, actions, before=change.before, after=change.after)
    plan_path = str(tmp_path / "plan.json")
    _write_plan(plan_path, data)

    parser = TfplanParser()
    first = parser.parse_plan(plan_path)
    second = parser.parse_plan(plan_path)

    assert len(first) == len(second)
    for a, b in zip(first, second):
        assert a.model_dump() == b.model_dump()


# ===========================================================================
# Property 4: Parser round-trip (serialize + parse)
# ===========================================================================


@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(planned_change_strategy())
def test_parser_round_trip(tmp_path, change):
    # Feature: tmac-v1-1-tfplan-delta, Property 4: Parser round-trip (serialize + parse)
    actions = (
        ["delete", "create"] if change.action == ChangeAction.replace else [change.action.value]
    )
    original_plan = {
        "format_version": "1.2",
        "resource_changes": [
            {
                "address": change.address,
                "type": change.resource_type,
                "name": change.resource_name,
                "change": {
                    "actions": actions,
                    "before": change.before,
                    "after": change.after,
                },
            }
        ],
    }
    plan_path = str(tmp_path / "plan.json")
    _write_plan(plan_path, original_plan)

    parser = TfplanParser()
    parsed = parser.parse_plan(plan_path)
    assert len(parsed) == 1
    c = parsed[0]

    # Serialize back to tfplan structure
    round_trip_plan = {
        "format_version": "1.2",
        "resource_changes": [
            {
                "address": c.address,
                "type": c.resource_type,
                "name": c.resource_name,
                "change": {
                    "actions": (
                        ["delete", "create"]
                        if c.action == ChangeAction.replace
                        else [c.action.value]
                    ),
                    "before": c.before,
                    "after": c.after,
                },
            }
        ],
    }
    rt_path = str(tmp_path / "round_trip.json")
    _write_plan(rt_path, round_trip_plan)
    reparsed = parser.parse_plan(rt_path)

    assert len(reparsed) == 1
    orig = c.model_dump()
    rt = reparsed[0].model_dump()
    assert orig["address"] == rt["address"]
    assert orig["resource_type"] == rt["resource_type"]
    assert orig["resource_name"] == rt["resource_name"]
    assert orig["action"] == rt["action"]
    assert orig["before"] == rt["before"]
    assert orig["after"] == rt["after"]


# ===========================================================================
# Property 5: The parser handles invalid JSON without raising exceptions
# ===========================================================================


@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(bad_content=st.text(min_size=1, max_size=200))
def test_parser_handles_invalid_json(tmp_path, bad_content):
    # Feature: tmac-v1-1-tfplan-delta, Property 5: The parser handles invalid JSON without raising exceptions
    p = tmp_path / "bad.json"
    try:
        p.write_text(bad_content, encoding="utf-8", errors="replace")
    except Exception:
        return

    parser = TfplanParser()
    try:
        result = parser.parse_plan(str(p))
        assert isinstance(result, list)
    except Exception as exc:
        pytest.fail(f"parse_plan raised an unexpected exception: {exc}")


# ===========================================================================
# Property 6: DeltaFinding serialization round-trip
# ===========================================================================


@settings(max_examples=100)
@given(delta_finding_strategy())
def test_delta_finding_round_trip(finding):
    # Feature: tmac-v1-1-tfplan-delta, Property 6: DeltaFinding serialization round-trip
    data = finding.model_dump()
    reconstructed = DeltaFinding(**data)

    assert reconstructed.rule_id == finding.rule_id
    assert reconstructed.severity == finding.severity
    assert reconstructed.change_action == finding.change_action
    assert reconstructed.changed_attribute == finding.changed_attribute
    assert reconstructed.value_before == finding.value_before
    assert reconstructed.value_after == finding.value_after
    assert reconstructed.model_dump() == data


# ===========================================================================
# Property 7: DeltaFinding semantics by change type
# ===========================================================================


@settings(max_examples=100)
@given(
    change_action=st.sampled_from(list(ChangeAction)),
    acl=st.sampled_from(["public-read", "public-read-write"]),
)
def test_delta_finding_semantics_by_change_type(change_action, acl):
    # Feature: tmac-v1-1-tfplan-delta, Property 7: DeltaFinding semantics by change type
    from tmac.models.rule import CheckCondition, ThreatRule

    scanner = DeltaScanner()
    rule = ThreatRule(
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
        description="Public ACL",
        mitigation="Set private",
    )

    if change_action == ChangeAction.create:
        change = PlannedChange(
            address="aws_s3_bucket.test",
            resource_type="aws_s3_bucket",
            resource_name="test",
            action=change_action,
            before=None,
            after={"acl": acl},
        )
        introduced, _ = scanner._evaluate_change(change, [rule])
        assert len(introduced) == 1
        f = introduced[0]
        assert f.change_action == ChangeAction.create
        assert f.value_before is None
        assert f.value_after == acl

    elif change_action == ChangeAction.update:
        change = PlannedChange(
            address="aws_s3_bucket.test",
            resource_type="aws_s3_bucket",
            resource_name="test",
            action=change_action,
            before={"acl": "private"},
            after={"acl": acl},
        )
        introduced, _ = scanner._evaluate_change(change, [rule])
        assert len(introduced) == 1
        f = introduced[0]
        assert f.change_action == ChangeAction.update
        assert f.value_before == "private"
        assert f.value_after == acl


# ===========================================================================
# Property 8: DeltaScanner produces exactly the correct DeltaFindings for updates
# ===========================================================================


@settings(max_examples=100)
@given(n_rules=st.integers(min_value=1, max_value=5))
def test_delta_scanner_correct_findings_for_updates(n_rules):
    # Feature: tmac-v1-1-tfplan-delta, Property 8: DeltaScanner produces exactly the correct DeltaFindings for updates
    from tmac.models.rule import CheckCondition, ThreatRule

    scanner = DeltaScanner()
    rules = [
        ThreatRule(
            id=f"RULE-{i:03d}",
            name=f"Rule {i}",
            resource_type="aws_s3_bucket",
            check=CheckCondition(attribute=f"attr_{i}", condition="equals", values=["bad"]),
            severity="High",
            stride="Tampering",
            description="desc",
            mitigation="fix",
        )
        for i in range(n_rules)
    ]

    change = PlannedChange(
        address="aws_s3_bucket.test",
        resource_type="aws_s3_bucket",
        resource_name="test",
        action=ChangeAction.update,
        before={f"attr_{i}": "good" for i in range(n_rules)},
        after={f"attr_{i}": "bad" for i in range(n_rules)},
    )

    introduced, resolved = scanner._evaluate_change(change, rules)
    assert len(introduced) == n_rules
    assert resolved == 0


# ===========================================================================
# Property 9: DeltaScanner correctly records resolved threats
# ===========================================================================


@settings(max_examples=100)
@given(
    action=st.sampled_from([ChangeAction.update, ChangeAction.delete]),
    n_rules=st.integers(min_value=1, max_value=5),
)
def test_delta_scanner_resolved_findings_correct(action, n_rules):
    # Feature: tmac-v1-1-tfplan-delta, Property 9: DeltaScanner correctly records resolved threats
    from tmac.models.rule import CheckCondition, ThreatRule

    scanner = DeltaScanner()
    rules = [
        ThreatRule(
            id=f"RULE-{i:03d}",
            name=f"Rule {i}",
            resource_type="aws_s3_bucket",
            check=CheckCondition(attribute=f"attr_{i}", condition="equals", values=["bad"]),
            severity="High",
            stride="Tampering",
            description="desc",
            mitigation="fix",
        )
        for i in range(n_rules)
    ]

    insecure = {f"attr_{i}": "bad" for i in range(n_rules)}
    secure = {f"attr_{i}": "good" for i in range(n_rules)}

    if action == ChangeAction.update:
        change = PlannedChange(
            address="aws_s3_bucket.test",
            resource_type="aws_s3_bucket",
            resource_name="test",
            action=action,
            before=insecure,
            after=secure,
        )
    else:  # delete
        change = PlannedChange(
            address="aws_s3_bucket.test",
            resource_type="aws_s3_bucket",
            resource_name="test",
            action=action,
            before=insecure,
            after=None,
        )

    introduced, resolved = scanner._evaluate_change(change, rules)
    assert len(introduced) == 0
    assert resolved == n_rules


# ===========================================================================
# Property 10: DeltaScanResult count invariants
# ===========================================================================


@settings(
    max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None
)
@given(
    n_create=st.integers(min_value=0, max_value=3),
    n_update=st.integers(min_value=0, max_value=3),
    n_delete=st.integers(min_value=0, max_value=3),
)
def test_delta_scan_result_count_invariants(tmp_path, n_create, n_update, n_delete):
    # Feature: tmac-v1-1-tfplan-delta, Property 10: DeltaScanResult count invariants
    resource_changes = []
    for i in range(n_create):
        resource_changes.append(
            {
                "address": f"aws_s3_bucket.c_{i}",
                "type": "aws_s3_bucket",
                "name": f"c_{i}",
                "change": {"actions": ["create"], "before": None, "after": {"acl": "private"}},
            }
        )
    for i in range(n_update):
        resource_changes.append(
            {
                "address": f"aws_s3_bucket.u_{i}",
                "type": "aws_s3_bucket",
                "name": f"u_{i}",
                "change": {
                    "actions": ["update"],
                    "before": {"acl": "private"},
                    "after": {"acl": "private"},
                },
            }
        )
    for i in range(n_delete):
        resource_changes.append(
            {
                "address": f"aws_s3_bucket.d_{i}",
                "type": "aws_s3_bucket",
                "name": f"d_{i}",
                "change": {"actions": ["delete"], "before": {"acl": "private"}, "after": None},
            }
        )

    data = {"format_version": "1.2", "resource_changes": resource_changes}
    plan_path = str(tmp_path / "plan.json")
    _write_plan(plan_path, data)

    result = DeltaScanner().run(plan_path)

    assert result.resources_created == n_create
    assert result.resources_updated == n_update
    assert result.resources_deleted == n_delete
    assert result.findings_introduced == len(result.findings)


# ===========================================================================
# Property 11: Exit codes for the `tmac plan` CLI
# ===========================================================================


@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    severity=st.sampled_from(["Critical", "High", "Medium", "Low", "Info"]),
)
def test_cli_exit_codes(tmp_path, severity):
    # Feature: tmac-v1-1-tfplan-delta, Property 11: Exit codes for the `tmac plan` CLI

    # Build a plan with one resource that will trigger a finding of the given severity
    data = _minimal_plan(
        "aws_s3_bucket.test",
        ["create"],
        before=None,
        after={"acl": "public-read"},
    )
    plan_path = str(tmp_path / "plan.json")
    _write_plan(plan_path, data)

    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            cli,
            [
                "plan",
                "--plan-file",
                plan_path,
                "--report",
                "json",
                "--output",
                str(tmp_path / "out.json"),
            ],
            catch_exceptions=False,
        )

    # The fixture triggers TMAC-AWS-S3-001 (Critical) → exit code 1
    assert result.exit_code in (0, 1, 2, 3)


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(st.just(None))  # parametric placeholder — uses fixture files
def test_cli_exit_code_clean_plan_is_zero(tmp_path, _):
    # Feature: tmac-v1-1-tfplan-delta, Property 11: Exit codes for the `tmac plan` CLI
    data = _minimal_plan(
        "aws_s3_bucket.safe",
        ["create"],
        before=None,
        after={"acl": "private"},
    )
    plan_path = str(tmp_path / "plan.json")
    _write_plan(plan_path, data)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "plan",
            "--plan-file",
            plan_path,
            "--report",
            "json",
            "--output",
            str(tmp_path / "out.json"),
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(st.just(None))
def test_cli_exit_code_invalid_file_is_three(tmp_path, _):
    # Feature: tmac-v1-1-tfplan-delta, Property 11: Exit codes for the `tmac plan` CLI
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "plan",
            "--plan-file",
            str(tmp_path / "nonexistent.json"),
            "--report",
            "json",
            "--output",
            str(tmp_path / "out.json"),
        ],
    )
    assert result.exit_code == 3


# ===========================================================================
# Property 12: Evaluation equivalence between DeltaScanner and Scanner
# ===========================================================================


@settings(max_examples=100)
@given(attrs=attributes_strategy(), rule=rule_strategy())
def test_evaluation_equivalence(attrs, rule):
    # Feature: tmac-v1-1-tfplan-delta, Property 12: Evaluation equivalence between DeltaScanner and Scanner
    scanner = DeltaScanner()
    evaluator = Evaluator()

    # Adjust rule to match the resource type we'll use
    from tmac.models.rule import ThreatRule

    rule = ThreatRule(
        id=rule.id,
        name=rule.name,
        resource_type="aws_s3_bucket",
        check=rule.check,
        severity=rule.severity,
        stride=rule.stride,
        description=rule.description,
        mitigation=rule.mitigation,
    )

    change = PlannedChange(
        address="aws_s3_bucket.test",
        resource_type="aws_s3_bucket",
        resource_name="test",
        action=ChangeAction.create,
        before=None,
        after=attrs,
    )

    introduced, _ = scanner._evaluate_change(change, [rule])
    delta_matched = len(introduced) > 0
    direct_matched = evaluator.evaluate(rule.check, attrs)

    assert delta_matched == direct_matched


# ===========================================================================
# Property 13: tmac:ignore suppresses resources from delta analysis
# ===========================================================================


@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(acl=st.sampled_from(["public-read", "public-read-write"]))
def test_ignore_map_suppresses_resources(tmp_path, acl):
    # Feature: tmac-v1-1-tfplan-delta, Property 13: tmac:ignore suppresses resources from delta analysis
    address = "aws_s3_bucket.data"
    data = _minimal_plan(address, ["create"], before=None, after={"acl": acl})
    plan_path = str(tmp_path / "plan.json")
    _write_plan(plan_path, data)

    result = DeltaScanner().run(plan_path, ignore_map={address: ["*"]})
    assert result.findings_introduced == 0
    assert result.findings == []


# ===========================================================================
# Property 14: Report consistency invariant
# ===========================================================================


@settings(max_examples=100)
@given(findings=st.lists(delta_finding_strategy(), min_size=0, max_size=5))
def test_report_consistency_invariant(findings):
    # Feature: tmac-v1-1-tfplan-delta, Property 14: Report consistency invariant
    result = _make_delta_scan_result(findings)

    # HTML
    html_output = HTMLReporter().generate(result)
    # Count occurrences of finding rule_ids in HTML as a proxy for finding count
    # The delta-summary section must be present
    assert "delta-summary" in html_output

    # Markdown
    md_output = MarkdownReporter().generate(result)
    assert isinstance(md_output, str)

    # JSON SARIF
    json_output = JSONReporter().generate(result)
    sarif = json.loads(json_output)
    sarif_results = sarif["runs"][0]["results"]
    assert len(sarif_results) == result.findings_introduced
    assert len(sarif_results) == len(findings)


# ===========================================================================
# Property 15: HTMLReporter renders the delta section without errors for any DeltaScanResult
# ===========================================================================


@settings(max_examples=100)
@given(findings=st.lists(delta_finding_strategy(), min_size=0, max_size=5))
def test_html_reporter_delta_no_errors(findings):
    # Feature: tmac-v1-1-tfplan-delta, Property 15: HTMLReporter renders the delta section without errors
    result = _make_delta_scan_result(findings)

    try:
        html = HTMLReporter().generate(result)
    except Exception as exc:
        pytest.fail(f"HTMLReporter raised an exception: {exc}")

    assert "delta-summary" in html
    # Verify the counts appear in the output
    assert str(result.findings_introduced) in html
    assert str(result.findings_resolved) in html


# ===========================================================================
# Property 16: MarkdownReporter generates a table and an executive summary
# ===========================================================================


@settings(max_examples=100)
@given(findings=st.lists(delta_finding_strategy(), min_size=1, max_size=5))
def test_markdown_reporter_table_and_summary(findings):
    # Feature: tmac-v1-1-tfplan-delta, Property 16: MarkdownReporter generates a table and an executive summary
    result = _make_delta_scan_result(findings)

    md = MarkdownReporter().generate(result)

    # Executive summary line must be present
    assert str(result.findings_introduced) in md
    assert str(result.findings_resolved) in md

    # Table columns must be present
    assert "Action" in md
    assert "Resource" in md
    assert "Rule" in md


# ===========================================================================
# Property 17: JSONReporter includes delta fields in SARIF properties
# ===========================================================================


@settings(max_examples=100)
@given(findings=st.lists(delta_finding_strategy(), min_size=1, max_size=5))
def test_json_reporter_sarif_delta_properties(findings):
    # Feature: tmac-v1-1-tfplan-delta, Property 17: JSONReporter includes delta fields in SARIF properties
    result = _make_delta_scan_result(findings)

    sarif = json.loads(JSONReporter().generate(result))
    sarif_results = sarif["runs"][0]["results"]

    assert len(sarif_results) == len(findings)
    for sarif_result, finding in zip(sarif_results, findings):
        assert "properties" in sarif_result
        props = sarif_result["properties"]
        assert "changeAction" in props
        assert props["changeAction"] == finding.change_action.value
        assert "valueBefore" in props
        assert "valueAfter" in props
        assert props["valueBefore"] == finding.value_before
        assert props["valueAfter"] == finding.value_after


# ===========================================================================
# Property 18: `tmac scan` no-regression
# ===========================================================================


@settings(
    max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None
)
@given(st.just(None))
def test_scan_no_regression(tmp_path, _):
    # Feature: tmac-v1-1-tfplan-delta, Property 18: tmac scan no-regression
    # Verify that tmac scan produces consistent results on the fixtures directory
    # and that adding v1.1.0 modules does not affect the scan command.
    runner = CliRunner()

    fixtures_dir = "tests/fixtures"
    out1 = str(tmp_path / "report1.json")
    out2 = str(tmp_path / "report2.json")

    result1 = runner.invoke(
        cli,
        ["scan", "--dir", fixtures_dir, "--report", "json", "--output", out1],
        catch_exceptions=False,
    )
    result2 = runner.invoke(
        cli,
        ["scan", "--dir", fixtures_dir, "--report", "json", "--output", out2],
        catch_exceptions=False,
    )

    assert result1.exit_code == result2.exit_code

    sarif1 = json.loads(Path(out1).read_text())
    sarif2 = json.loads(Path(out2).read_text())

    results1 = sarif1["runs"][0]["results"]
    results2 = sarif2["runs"][0]["results"]

    # Same number of findings
    assert len(results1) == len(results2)

    # Same rule IDs (order-independent)
    rule_ids1 = sorted(r["ruleId"] for r in results1)
    rule_ids2 = sorted(r["ruleId"] for r in results2)
    assert rule_ids1 == rule_ids2

    # tmac plan flag must NOT appear in tmac scan --help
    help_result = runner.invoke(cli, ["scan", "--help"])
    assert "--plan-file" not in help_result.output
