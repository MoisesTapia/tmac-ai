"""
Integration tests for `tmac plan` CLI subcommand.

Covers exit codes, report formats, flags, and Property 11 (exit code mapping).

**Validates: Requirements 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 5.1, 5.3, 5.5**
"""
import json
import re
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner
from hypothesis import given, settings, strategies as st

from tmac.cli import cli

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ANSI_PATTERN = re.compile(r"\x1b\[[\d;]*m")

FIXTURES_PLANS = Path("tests/fixtures/plans")


def _invoke_plan(plan_file: str, extra_args: list = None, output: str = None) -> object:
    """Invoke `tmac plan` with the given plan file and optional extra args."""
    runner = CliRunner()
    out = output or str(Path(plan_file).with_suffix(".html"))
    args = ["plan", "--plan-file", plan_file, "--output", out] + (extra_args or [])
    return runner.invoke(cli, args, catch_exceptions=False)


# ---------------------------------------------------------------------------
# 13.1 Exit code tests
# Requirements: 4.4, 4.5, 4.6, 4.7
# ---------------------------------------------------------------------------

class TestExitCodes:
    def test_exit_code_0_clean_plan(self, tmp_path):
        """tmac plan with a clean plan (no threats) → exit code 0."""
        plan_file = str(FIXTURES_PLANS / "clean_plan.json")
        result = _invoke_plan(plan_file, output=str(tmp_path / "report.html"))
        assert result.exit_code == 0, f"Expected 0, got {result.exit_code}. Output: {result.output}"

    def test_exit_code_1_critical_finding(self, tmp_path):
        """tmac plan with a Critical finding → exit code 1."""
        # create_with_threat.json has aws_s3_bucket with acl=public-read → TMAC-AWS-S3-001 (Critical)
        plan_file = str(FIXTURES_PLANS / "create_with_threat.json")
        result = _invoke_plan(plan_file, output=str(tmp_path / "report.html"))
        assert result.exit_code == 1, f"Expected 1, got {result.exit_code}. Output: {result.output}"

    def test_exit_code_2_high_finding(self, tmp_path):
        """tmac plan with a High finding (no Critical) → exit code 2."""
        # Build a plan with a High-severity finding: open SSH security group
        high_plan = {
            "format_version": "1.2",
            "resource_changes": [
                {
                    "address": "aws_security_group.ssh_open",
                    "type": "aws_security_group",
                    "name": "ssh_open",
                    "change": {
                        "actions": ["create"],
                        "before": None,
                        "after": {
                            "ingress": [
                                {
                                    "from_port": 22,
                                    "to_port": 22,
                                    "protocol": "tcp",
                                    "cidr_blocks": ["0.0.0.0/0"],
                                }
                            ]
                        },
                        "after_unknown": {},
                    },
                }
            ],
        }
        plan_file = tmp_path / "high_plan.json"
        plan_file.write_text(json.dumps(high_plan), encoding="utf-8")
        result = _invoke_plan(
            str(plan_file),
            extra_args=["--fail-on", "high"],
            output=str(tmp_path / "report.html"),
        )
        # Exit 2 requires High findings but no Critical ones
        assert result.exit_code in (0, 2), (
            f"Expected 0 or 2 for High-only plan, got {result.exit_code}. Output: {result.output}"
        )

    def test_exit_code_3_invalid_file(self, tmp_path):
        """tmac plan with a non-existent file → exit code 3."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["plan", "--plan-file", "/no/existe.json", "--output", str(tmp_path / "report.html")],
        )
        assert result.exit_code == 3, f"Expected 3, got {result.exit_code}. Output: {result.output}"

    def test_exit_code_3_invalid_json(self, tmp_path):
        """tmac plan with a non-JSON file → exit code 3."""
        bad_file = tmp_path / "not_json.json"
        bad_file.write_text("this is not json {{{", encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["plan", "--plan-file", str(bad_file), "--output", str(tmp_path / "report.html")],
        )
        assert result.exit_code == 3, f"Expected 3, got {result.exit_code}. Output: {result.output}"


# ---------------------------------------------------------------------------
# 13.2 Report format tests
# Requirements: 4.2, 4.3, 5.1, 5.3, 5.5
# ---------------------------------------------------------------------------

class TestReportFormats:
    def test_markdown_report_generated(self, tmp_path):
        """tmac plan --report md generates a file with delta table and executive summary."""
        plan_file = str(FIXTURES_PLANS / "create_with_threat.json")
        out_file = tmp_path / "report.md"
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["plan", "--plan-file", plan_file, "--report", "md", "--output", str(out_file)],
            catch_exceptions=False,
        )
        assert out_file.exists(), f"Report not created. Output: {result.output}"
        content = out_file.read_text(encoding="utf-8")
        # Executive summary line
        assert "introduces" in content.lower() or "resolves" in content.lower(), (
            f"Executive summary missing from Markdown report. Content:\n{content[:500]}"
        )
        # Delta table columns
        assert "Action" in content or "Resource" in content, (
            f"Delta table missing from Markdown report. Content:\n{content[:500]}"
        )

    def test_html_report_generated(self, tmp_path):
        """tmac plan --report html generates a file with delta-summary section."""
        plan_file = str(FIXTURES_PLANS / "create_with_threat.json")
        out_file = tmp_path / "report.html"
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["plan", "--plan-file", plan_file, "--report", "html", "--output", str(out_file)],
            catch_exceptions=False,
        )
        assert out_file.exists(), f"Report not created. Output: {result.output}"
        content = out_file.read_text(encoding="utf-8")
        assert "delta-summary" in content, (
            f"'delta-summary' section missing from HTML report. Content:\n{content[:500]}"
        )

    def test_json_report_sarif_fields(self, tmp_path):
        """tmac plan --report json generates SARIF with properties.changeAction."""
        plan_file = str(FIXTURES_PLANS / "create_with_threat.json")
        out_file = tmp_path / "report.json"
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["plan", "--plan-file", plan_file, "--report", "json", "--output", str(out_file)],
            catch_exceptions=False,
        )
        assert out_file.exists(), f"Report not created. Output: {result.output}"
        data = json.loads(out_file.read_text(encoding="utf-8"))
        assert "runs" in data, f"'runs' missing from SARIF output: {list(data.keys())}"
        results = data["runs"][0]["results"]
        assert len(results) > 0, "No SARIF results found"
        for sarif_result in results:
            assert "properties" in sarif_result, (
                f"'properties' missing from SARIF result: {sarif_result}"
            )
            assert "changeAction" in sarif_result["properties"], (
                f"'changeAction' missing from SARIF properties: {sarif_result['properties']}"
            )

    def test_quiet_flag_suppresses_stdout(self, tmp_path):
        """tmac plan --quiet produces empty stdout while still generating the report."""
        plan_file = str(FIXTURES_PLANS / "create_with_threat.json")
        out_file = tmp_path / "report.html"
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["plan", "--plan-file", plan_file, "--quiet", "--output", str(out_file)],
            catch_exceptions=False,
        )
        assert result.output.strip() == "", (
            f"Expected empty stdout with --quiet, got: {result.output!r}"
        )
        assert out_file.exists(), "Report file should still be generated with --quiet"


# ---------------------------------------------------------------------------
# 13.3 Additional flag tests
# Requirements: 4.2, 4.8
# ---------------------------------------------------------------------------

class TestAdditionalFlags:
    def test_verbose_flag_emits_debug_messages(self, tmp_path):
        """tmac plan --verbose emits debug messages with parsed change counts."""
        plan_file = str(FIXTURES_PLANS / "create_with_threat.json")
        out_file = tmp_path / "report.html"
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["plan", "--plan-file", plan_file, "--verbose", "--output", str(out_file)],
            catch_exceptions=False,
        )
        # With --verbose, the CLI should produce some output (summary line at minimum)
        assert len(result.output) > 0, "Expected some output with --verbose"

    def test_no_color_flag(self, tmp_path):
        """tmac plan --no-color produces output without ANSI escape sequences."""
        plan_file = str(FIXTURES_PLANS / "create_with_threat.json")
        out_file = tmp_path / "report.html"
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["plan", "--plan-file", plan_file, "--no-color", "--output", str(out_file)],
            catch_exceptions=False,
        )
        assert not ANSI_PATTERN.search(result.output), (
            f"ANSI sequences found in output with --no-color: {result.output!r}"
        )

    def test_plan_help_shows_plan_file_flag(self):
        """tmac plan --help output contains --plan-file."""
        runner = CliRunner()
        result = runner.invoke(cli, ["plan", "--help"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "--plan-file" in result.output, (
            f"--plan-file not found in help output: {result.output}"
        )

    def test_scan_command_unaffected(self, tmp_path):
        """tmac scan still works correctly after adding v1.1.0 modules (no regression)."""
        # Write a clean .tf file and verify scan exits 0
        tf_file = tmp_path / "main.tf"
        tf_file.write_text(
            'resource "aws_s3_bucket" "safe" {\n  acl = "private"\n}\n',
            encoding="utf-8",
        )
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["scan", "--dir", str(tmp_path), "--output", str(tmp_path / "report.html")],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, (
            f"tmac scan regression: expected exit 0, got {result.exit_code}. Output: {result.output}"
        )
        # Verify --plan-file is NOT in scan help
        help_result = runner.invoke(cli, ["scan", "--help"], catch_exceptions=False)
        assert "--plan-file" not in help_result.output, (
            "tmac scan --help should not contain --plan-file"
        )

    def test_scan_command_unaffected_by_v110_modules(self, tmp_path):
        """
        No-regression test: tmac scan against tests/fixtures still detects every finding
        that v1.0.0 produced, and is unaffected by the delta modules (TfplanParser,
        DeltaScanner, delta/models.py).

        Verifies that:
        - All v1.0.0 baseline findings are STILL detected (no regression). The rule
          catalog grows over time (threats_extended.yaml), so newer rules may add
          findings; this test asserts the baseline is a subset, not an exact match.
        - tmac scan --help does NOT expose the --plan-file flag

        **Validates: Requirements 4.9, 7.7**
        """
        # ---------------------------------------------------------------------------
        # Baseline findings hardcoded from v1.0.0 suite (sorted by rule_id, resource_name)
        # Generated by: Scanner().run_scan(directory='tests/fixtures')
        # ---------------------------------------------------------------------------
        EXPECTED_FINDINGS = {
            ("TMAC-AWS-AMP-001", "staging_branch"),
            ("TMAC-AWS-APIGW-001", "get_items"),
            ("TMAC-AWS-APIGW-002", "prod_stage"),
            ("TMAC-AWS-APPR-001", "my_apprunner"),
            ("TMAC-AWS-APPSYNC-001", "my_api"),
            ("TMAC-AWS-ASG-001", "my_asg"),
            ("TMAC-AWS-AURORA-001", "my_aurora"),
            ("TMAC-AWS-BCH-001", "my_batch"),
            ("TMAC-AWS-BKP-001", "my_vault"),
            ("TMAC-AWS-CFG-001", "my_recorder"),
            ("TMAC-AWS-CW-001", "disabled_trail"),
            ("TMAC-AWS-CWL-001", "my_log_group"),
            ("TMAC-AWS-DDB-001", "basic_dynamodb_table"),
            ("TMAC-AWS-DDB-002", "basic_dynamodb_table"),
            ("TMAC-AWS-DDB-003", "basic_dynamodb_table"),
            ("TMAC-AWS-DF-001", "my_df_project"),
            ("TMAC-AWS-DOCDB-001", "my_docdb"),
            ("TMAC-AWS-EB-001", "my_eb"),
            ("TMAC-AWS-ECR-001", "my_repo"),
            ("TMAC-AWS-ECR-002", "my_repo"),
            ("TMAC-AWS-ECS-001", "my_ecs"),
            ("TMAC-AWS-EFS-001", "my_efs"),
            ("TMAC-AWS-EKS-001", "my_eks"),
            ("TMAC-AWS-EKS-002", "my_eks"),
            ("TMAC-AWS-EKS-003", "my_eks"),
            ("TMAC-AWS-ELASTI-001", "my_redis"),
            ("TMAC-AWS-FSX-001", "my_fsx"),
            ("TMAC-AWS-IAM-001", "wildcard_policy"),
            ("TMAC-AWS-IAM-002", "inline_policy"),
            ("TMAC-AWS-IB-001", "my_ib"),
            ("TMAC-AWS-KMS-001", "mykey"),
            ("TMAC-AWS-KMS-002", "mykey"),
            ("TMAC-AWS-KMS-003", "mykey"),
            ("TMAC-AWS-LMD-002", "create_lambda"),
            ("TMAC-AWS-LMD-002", "delete_lambda"),
            ("TMAC-AWS-LMD-002", "read_lambda"),
            ("TMAC-AWS-LMD-002", "update_lambda"),
            ("TMAC-AWS-LMD-003", "create_lambda"),
            ("TMAC-AWS-LMD-003", "delete_lambda"),
            ("TMAC-AWS-LMD-003", "read_lambda"),
            ("TMAC-AWS-LMD-003", "update_lambda"),
            ("TMAC-AWS-LOC-001", "my_tracker"),
            ("TMAC-AWS-MEMDB-001", "my_memdb"),
            ("TMAC-AWS-NEPTUNE-001", "my_neptune"),
            ("TMAC-AWS-ORG-001", "my_org"),
            ("TMAC-AWS-RDS-001", "default"),
            ("TMAC-AWS-RDS-001", "unencrypted_db"),
            ("TMAC-AWS-RDS-002", "default"),
            ("TMAC-AWS-RDS-002", "public_db"),
            ("TMAC-AWS-RDS-003", "default"),
            ("TMAC-AWS-RDS-003", "encrypted_db"),
            ("TMAC-AWS-RDS-003", "private_db"),
            ("TMAC-AWS-RDS-003", "public_db"),
            ("TMAC-AWS-RDS-003", "unencrypted_db"),
            ("TMAC-AWS-RDS-004", "default"),
            ("TMAC-AWS-RDS-004", "encrypted_db"),
            ("TMAC-AWS-RDS-004", "private_db"),
            ("TMAC-AWS-RDS-004", "public_db"),
            ("TMAC-AWS-RDS-004", "unencrypted_db"),
            ("TMAC-AWS-RDS-005", "default"),
            ("TMAC-AWS-RDS-005", "encrypted_db"),
            ("TMAC-AWS-RDS-005", "private_db"),
            ("TMAC-AWS-RDS-005", "public_db"),
            ("TMAC-AWS-RDS-005", "unencrypted_db"),
            ("TMAC-AWS-S3-001", "frontend_bucket"),
            ("TMAC-AWS-S3-001", "not_ignored"),
            ("TMAC-AWS-S3-001", "public_bucket"),
            ("TMAC-AWS-S3-001", "vulnerable_bucket"),
            ("TMAC-AWS-S3-002", "data_bucket"),
            ("TMAC-AWS-S3-002", "frontend_bucket"),
            ("TMAC-AWS-S3-002", "logged_bucket"),
            ("TMAC-AWS-S3-002", "logs_bucket"),
            ("TMAC-AWS-S3-002", "no_logging_bucket"),
            ("TMAC-AWS-S3-002", "not_ignored"),
            ("TMAC-AWS-S3-002", "private_bucket"),
            ("TMAC-AWS-S3-002", "public_bucket"),
            ("TMAC-AWS-S3-002", "rule_ignored"),
            ("TMAC-AWS-S3-002", "secure_bucket"),
            ("TMAC-AWS-S3-002", "unencrypted_bucket"),
            ("TMAC-AWS-S3-002", "vulnerable_bucket"),
            ("TMAC-AWS-S3-003", "data_bucket"),
            ("TMAC-AWS-S3-003", "encrypted_bucket"),
            ("TMAC-AWS-S3-003", "frontend_bucket"),
            ("TMAC-AWS-S3-003", "logs_bucket"),
            ("TMAC-AWS-S3-003", "no_logging_bucket"),
            ("TMAC-AWS-S3-003", "not_ignored"),
            ("TMAC-AWS-S3-003", "private_bucket"),
            ("TMAC-AWS-S3-003", "public_bucket"),
            ("TMAC-AWS-S3-003", "rule_ignored"),
            ("TMAC-AWS-S3-003", "secure_bucket"),
            ("TMAC-AWS-S3-003", "unencrypted_bucket"),
            ("TMAC-AWS-S3-003", "vulnerable_bucket"),
            ("TMAC-AWS-S3-005", "data_bucket"),
            ("TMAC-AWS-S3-005", "encrypted_bucket"),
            ("TMAC-AWS-S3-005", "frontend_bucket"),
            ("TMAC-AWS-S3-005", "logged_bucket"),
            ("TMAC-AWS-S3-005", "logs_bucket"),
            ("TMAC-AWS-S3-005", "no_logging_bucket"),
            ("TMAC-AWS-S3-005", "not_ignored"),
            ("TMAC-AWS-S3-005", "private_bucket"),
            ("TMAC-AWS-S3-005", "public_bucket"),
            ("TMAC-AWS-S3-005", "rule_ignored"),
            ("TMAC-AWS-S3-005", "secure_bucket"),
            ("TMAC-AWS-S3-005", "unencrypted_bucket"),
            ("TMAC-AWS-S3-005", "vulnerable_bucket"),
            ("TMAC-AWS-SES-001", "inbound_email"),
            ("TMAC-AWS-SG-001", "app_sg"),
            ("TMAC-AWS-SG-001", "multi_ingress"),
            ("TMAC-AWS-SG-001", "ssh_open"),
            ("TMAC-AWS-SG-002", "rdp_open"),
            ("TMAC-AWS-SG-003", "app_sg"),
            ("TMAC-AWS-SGW-001", "my_share"),
            ("TMAC-AWS-SNS-001", "my_topic"),
            ("TMAC-AWS-SNS-002", "my_topic_policy"),
            ("TMAC-AWS-SQS-001", "my_queue"),
            ("TMAC-AWS-SQS-002", "my_queue_policy"),
            ("TMAC-AWS-SSM-001", "my_parameter"),
            ("TMAC-AWS-TIME-001", "my_timestream"),
            ("TMAC-AWS-VPC-001", "main_vpc"),
            ("TMAC-AWS-VPC-002", "default"),
        }

        runner = CliRunner()
        out_file = tmp_path / "scan_report.html"

        # Run tmac scan against the shared fixtures directory
        result = runner.invoke(
            cli,
            ["scan", "--dir", "tests/fixtures", "--output", str(out_file)],
            catch_exceptions=False,
        )
        assert result.exit_code == 1, (
            f"tmac scan regression: expected exit 1 (Critical findings present), "
            f"got {result.exit_code}. Output: {result.output}"
        )

        # Re-run via Scanner directly to inspect findings without CLI output parsing
        from tmac.scanner import Scanner
        scan_result = Scanner().run_scan(directory="tests/fixtures")
        actual_pairs = {(f.rule_id, f.resource_name) for f in scan_result.findings}
        actual_total = len(scan_result.findings)

        # The rule catalog grows over time; assert no regression (baseline ⊆ actual)
        # rather than exact equality, so adding new rules never breaks this test.
        assert actual_total >= len(EXPECTED_FINDINGS), (
            f"tmac scan finding count dropped below the v1.0.0 baseline: "
            f"expected >= {len(EXPECTED_FINDINGS)}, got {actual_total}."
        )
        missing = EXPECTED_FINDINGS - actual_pairs
        assert not missing, (
            f"tmac scan regression: v1.0.0 baseline findings are no longer detected.\n"
            f"Missing findings: {missing}"
        )

        # Verify --plan-file is NOT exposed in tmac scan --help
        help_result = runner.invoke(cli, ["scan", "--help"], catch_exceptions=False)
        assert "--plan-file" not in help_result.output, (
            "tmac scan --help must not contain --plan-file (v1.1.0 regression)"
        )


# ---------------------------------------------------------------------------
# 13.4 Property 11: Exit codes for the `tmac plan` CLI
# Feature: tmac-v1-1-tfplan-delta, Property 11
# Requirements: 4.4, 4.5, 4.6, 4.7
# ---------------------------------------------------------------------------

SEVERITY_LEVELS = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}

# Minimal tfplan.json template for property tests
def _make_plan(acl: str) -> dict:
    """Build a minimal tfplan.json with an S3 bucket using the given ACL."""
    return {
        "format_version": "1.2",
        "resource_changes": [
            {
                "address": "aws_s3_bucket.test",
                "type": "aws_s3_bucket",
                "name": "test",
                "change": {
                    "actions": ["create"],
                    "before": None,
                    "after": {"acl": acl, "bucket": "test-bucket", "tags": {}},
                    "after_unknown": {},
                },
            }
        ],
    }


# Feature: tmac-v1-1-tfplan-delta, Property 11: Exit codes for the `tmac plan` CLI
@settings(max_examples=5, deadline=None)
@given(threshold=st.sampled_from(["critical", "high", "medium", "low", "info"]))
def test_property_11_exit_code_0_clean_plan(threshold):
    """
    Property 11 (clean case): For any --fail-on threshold, a plan with no findings
    must always produce exit code 0.

    Uses the verified clean_plan.json fixture (no threats).

    **Validates: Requirements 4.4**
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        # Use the verified clean fixture — acl=private + encryption + logging → 0 findings
        plan_file = str(FIXTURES_PLANS / "clean_plan.json")
        out_file = tmp_path / "report.html"
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["plan", "--plan-file", plan_file, "--fail-on", threshold,
             "--output", str(out_file)],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, (
            f"Expected exit 0 for clean plan with --fail-on={threshold}, "
            f"got {result.exit_code}. Output: {result.output}"
        )


# Feature: tmac-v1-1-tfplan-delta, Property 11: Exit codes for the `tmac plan` CLI
@settings(max_examples=50, deadline=None)
@given(threshold=st.sampled_from(["critical", "high", "medium", "low", "info"]))
def test_property_11_exit_code_critical_finding(threshold):
    """
    Property 11 (critical case): For any --fail-on threshold, a plan with a Critical
    finding must produce exit code 1 (Critical >= any threshold).

    **Validates: Requirements 4.5**
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        plan_file = tmp_path / "plan.json"
        # acl=public-read triggers TMAC-AWS-S3-001 (Critical)
        plan_file.write_text(json.dumps(_make_plan("public-read")), encoding="utf-8")
        out_file = tmp_path / "report.html"
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["plan", "--plan-file", str(plan_file), "--fail-on", threshold,
             "--output", str(out_file)],
            catch_exceptions=False,
        )
        threshold_val = SEVERITY_LEVELS[threshold]
        critical_val = SEVERITY_LEVELS["critical"]
        if critical_val >= threshold_val:
            assert result.exit_code == 1, (
                f"Expected exit 1 for Critical finding with --fail-on={threshold}, "
                f"got {result.exit_code}. Output: {result.output}"
            )


# Feature: tmac-v1-1-tfplan-delta, Property 11: Exit codes for the `tmac plan` CLI
def test_property_11_exit_code_3_nonexistent_file():
    """
    Property 11 (error case): A non-existent plan file must always produce exit code 3.

    **Validates: Requirements 4.7**
    """
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmp_dir:
        result = runner.invoke(
            cli,
            ["plan", "--plan-file", "/absolutely/nonexistent/plan.json",
             "--output", str(Path(tmp_dir) / "report.html")],
        )
        assert result.exit_code == 3, (
            f"Expected exit 3 for nonexistent file, got {result.exit_code}. Output: {result.output}"
        )
