"""
OpenTofu support: .tofu sources in `tmac scan`, `tofu show -json` plans in `tmac plan`,
plus the directories every scan skips by default.

Validates: OpenTofu-1, OpenTofu-2 (tmac-v1-2-cloudformation tasks 13.x)
"""

import json
import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from tmac.cli import cli
from tmac.delta.scanner import DeltaScanner
from tmac.scanner import DEFAULT_EXCLUDED_DIRS, Scanner

FIXTURES = Path(__file__).parent.parent / "fixtures"
PUBLIC_TF = (FIXTURES / "s3_public_acl.tf").read_text(encoding="utf-8")
PRIVATE_TF = (FIXTURES / "s3_private.tf").read_text(encoding="utf-8")


def _findings(directory: Path, **kwargs) -> set[tuple[str, str]]:
    result = Scanner().run_scan(str(directory), **kwargs)
    return {(Path(f.file_path).name, f.rule_id) for f in result.findings}


def test_tofu_files_are_scanned(tmp_path):
    (tmp_path / "main.tofu").write_text(PUBLIC_TF, encoding="utf-8")
    assert ("main.tofu", "TMAC-AWS-S3-001") in _findings(tmp_path)


def test_mixed_tf_and_tofu_are_both_scanned(tmp_path):
    (tmp_path / "a.tf").write_text(PUBLIC_TF, encoding="utf-8")
    (tmp_path / "b.tofu").write_text(PUBLIC_TF, encoding="utf-8")
    files = {name for name, _ in _findings(tmp_path)}
    assert files == {"a.tf", "b.tofu"}


def test_tofu_file_overrides_tf_file_with_same_name(tmp_path):
    # OpenTofu loads main.tofu instead of main.tf when both exist.
    (tmp_path / "main.tf").write_text(PUBLIC_TF, encoding="utf-8")
    (tmp_path / "main.tofu").write_text(PRIVATE_TF, encoding="utf-8")
    result = Scanner().run_scan(str(tmp_path))
    assert result.files_scanned == 1
    assert not any(f.rule_id == "TMAC-AWS-S3-001" for f in result.findings)


def test_tofu_files_respect_exclude_patterns(tmp_path):
    (tmp_path / "main.tofu").write_text(PUBLIC_TF, encoding="utf-8")
    assert _findings(tmp_path, exclude_patterns=["*.tofu"]) == set()


def test_tofu_plan_matches_terraform_plan():
    terraform = DeltaScanner().run(str(FIXTURES / "plans" / "create_with_threat.json"))
    tofu = DeltaScanner().run(str(FIXTURES / "plans" / "tofu_create_with_threat.json"))
    key = lambda r: sorted((f.rule_id, f.resource_name) for f in r.findings)
    assert key(tofu) == key(terraform) != []


def test_plan_source_dir_reads_tofu_ignores(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.tofu").write_text(
        '# tmac:ignore\nresource "aws_s3_bucket" "data" {\n  acl = "public-read"\n}\n',
        encoding="utf-8",
    )
    out = tmp_path / "d.json"
    result = CliRunner().invoke(
        cli,
        [
            "plan", "-p", str(FIXTURES / "plans" / "tofu_create_with_threat.json"),
            "--source-dir", str(src), "-r", "json", "-o", str(out),
        ],
    )  # fmt: skip
    assert result.exit_code == 0
    assert json.loads(out.read_text())["runs"][0]["results"] == []


# ---------------------------------------------------------------------------
# Default excluded directories (vendored code is never scanned)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("vendored", [".terraform", "node_modules", ".git", "venv"])
def test_default_excluded_dirs_are_not_scanned(tmp_path, vendored):
    nested = tmp_path / vendored / "modules" / "x"
    nested.mkdir(parents=True)
    (nested / "main.tf").write_text(PUBLIC_TF, encoding="utf-8")
    shutil.copy(FIXTURES / "s3_private.tf", tmp_path / "root.tf")
    assert vendored in DEFAULT_EXCLUDED_DIRS
    result = Scanner().run_scan(str(tmp_path))
    assert result.files_scanned == 1


def test_scan_root_inside_excluded_name_is_still_scanned(tmp_path):
    root = tmp_path / ".terraform"
    root.mkdir()
    (root / "main.tf").write_text(PUBLIC_TF, encoding="utf-8")
    # config={} so the repo's own .tmac.yaml (which excludes .terraform) doesn't apply.
    assert Scanner().run_scan(str(root), config={}).files_scanned == 1
