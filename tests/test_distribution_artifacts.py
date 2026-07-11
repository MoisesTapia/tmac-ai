"""
Smoke / config tests for TMAC v1.6.0 distribution artifacts.

Validates the declarative configuration files — not runtime behaviour — by
parsing them and asserting structural and value invariants.

Requirements covered:
  R4.7  – GitHub Action permissions limited to pull-requests:write, contents:read
  R5.1  – action.yml entrypoint exists
  R5.2  – dir input with default '.'
  R5.3  – fail-on input with default 'high'
  R5.4  – delta-only input with default 'true'
  R5.5  – comment input with default 'true'
  R5.6  – report-format input with default 'Markdown'
  R5.7  – output input with default ''
  R6.1  – GitLab template defines at least one runnable job
  R6.3  – GitLab template exposes TMAC_DIR, TMAC_FAIL_ON variables
  R6.4  – GitLab variable defaults match Action defaults
  R6.7  – GitLab artifacts.when == always
  R8.4  – runtime deps declared in pyproject.toml
  R8.7  – pyproject.toml version == "1.6.0"
"""

import sys
from pathlib import Path

import yaml
import pytest

# Python 3.11+ ships tomllib in stdlib; fall back to the tomli back-port.
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib  # type: ignore[no-redef]
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]

# ---------------------------------------------------------------------------
# Repo root relative to this test file (tests/ → project root)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).parent.parent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
NON_JOB_KEYS = frozenset(
    {"variables", "stages", "include", "workflow", "default", "image", "services", "cache"}
)


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _load_toml(path: Path) -> dict:
    with path.open("rb") as fh:
        return tomllib.load(fh)


# ===========================================================================
# action.yml tests  (R4.7, R5.1–5.7)
# ===========================================================================


class TestActionYml:
    """Smoke tests for the GitHub Action definition at <repo-root>/action.yml."""

    @pytest.fixture(scope="class")
    def action(self) -> dict:
        return _load_yaml(REPO_ROOT / "action.yml")

    # --- inputs and defaults -----------------------------------------------

    def test_has_required_input_keys(self, action: dict) -> None:
        """R5.2–5.7: action.yml must declare all six expected inputs."""
        expected = {"dir", "fail-on", "delta-only", "comment", "report-format", "output"}
        assert expected.issubset(set(action["inputs"].keys())), (
            f"Missing inputs: {expected - set(action['inputs'].keys())}"
        )

    def test_input_default_dir(self, action: dict) -> None:
        """R5.2: dir default is '.'."""
        assert action["inputs"]["dir"]["default"] == ".", (
            f"Expected dir default '.', got {action['inputs']['dir']['default']!r}"
        )

    def test_input_default_fail_on(self, action: dict) -> None:
        """R5.3: fail-on default is 'high'."""
        assert action["inputs"]["fail-on"]["default"] == "high", (
            f"Expected fail-on default 'high', got {action['inputs']['fail-on']['default']!r}"
        )

    def test_input_default_delta_only(self, action: dict) -> None:
        """R5.4: delta-only default is 'true'."""
        assert action["inputs"]["delta-only"]["default"] == "true", (
            f"Expected delta-only default 'true', got {action['inputs']['delta-only']['default']!r}"
        )

    def test_input_default_comment(self, action: dict) -> None:
        """R5.5: comment default is 'true'."""
        assert action["inputs"]["comment"]["default"] == "true", (
            f"Expected comment default 'true', got {action['inputs']['comment']['default']!r}"
        )

    def test_input_default_report_format(self, action: dict) -> None:
        """R5.6: report-format default is 'Markdown'."""
        assert action["inputs"]["report-format"]["default"] == "Markdown", (
            f"Expected report-format default 'Markdown', "
            f"got {action['inputs']['report-format']['default']!r}"
        )

    def test_input_default_output(self, action: dict) -> None:
        """R5.7: output default is '' (empty string)."""
        assert action["inputs"]["output"]["default"] == "", (
            f"Expected output default '', got {action['inputs']['output']['default']!r}"
        )

    # --- permissions block (R4.7) -------------------------------------------

    def test_permissions_block_exists(self, action: dict) -> None:
        """R4.7: action.yml must define a top-level permissions block."""
        assert "permissions" in action, "No top-level 'permissions' key in action.yml"

    def test_permissions_only_allowed_scopes(self, action: dict) -> None:
        """R4.7: permissions block must contain ONLY pull-requests and contents."""
        allowed_scopes = {"pull-requests", "contents"}
        actual_scopes = set(action["permissions"].keys())
        assert actual_scopes == allowed_scopes, (
            f"Unexpected permission scopes: {actual_scopes - allowed_scopes}; "
            f"missing: {allowed_scopes - actual_scopes}"
        )

    def test_permissions_pull_requests_write(self, action: dict) -> None:
        """R4.7: pull-requests permission must be 'write'."""
        assert action["permissions"]["pull-requests"] == "write", (
            f"Expected pull-requests: write, got {action['permissions']['pull-requests']!r}"
        )

    def test_permissions_contents_read(self, action: dict) -> None:
        """R4.7: contents permission must be 'read'."""
        assert action["permissions"]["contents"] == "read", (
            f"Expected contents: read, got {action['permissions']['contents']!r}"
        )

    # --- runs block (R5.1) --------------------------------------------------

    def test_runs_using_composite(self, action: dict) -> None:
        """R5.1: action.yml must use the 'composite' runner type."""
        assert action["runs"]["using"] == "composite", (
            f"Expected runs.using == 'composite', got {action['runs']['using']!r}"
        )


# ===========================================================================
# GitLab CI template tests  (R6.1, R6.3, R6.4, R6.7)
# ===========================================================================


class TestGitLabTemplate:
    """Smoke tests for ci/gitlab/tmac.gitlab-ci.yml."""

    @pytest.fixture(scope="class")
    def gitlab_ci(self) -> dict:
        return _load_yaml(REPO_ROOT / "ci" / "gitlab" / "tmac.gitlab-ci.yml")

    # --- top-level variables (R6.3, R6.4) -----------------------------------

    def test_variables_block_exists(self, gitlab_ci: dict) -> None:
        """R6.3: template must have a top-level 'variables' block."""
        assert "variables" in gitlab_ci, "No top-level 'variables' key in GitLab template"

    def test_variable_tmac_dir_default(self, gitlab_ci: dict) -> None:
        """R6.4: TMAC_DIR default must match Action default ('.')."""
        assert gitlab_ci["variables"]["TMAC_DIR"] == ".", (
            f"Expected TMAC_DIR '.', got {gitlab_ci['variables']['TMAC_DIR']!r}"
        )

    def test_variable_tmac_fail_on_default(self, gitlab_ci: dict) -> None:
        """R6.4: TMAC_FAIL_ON default must match Action default ('high')."""
        assert gitlab_ci["variables"]["TMAC_FAIL_ON"] == "high", (
            f"Expected TMAC_FAIL_ON 'high', got {gitlab_ci['variables']['TMAC_FAIL_ON']!r}"
        )

    def test_variable_tmac_delta_only_default(self, gitlab_ci: dict) -> None:
        """R6.4: TMAC_DELTA_ONLY default must match Action default ('true')."""
        assert gitlab_ci["variables"]["TMAC_DELTA_ONLY"] == "true", (
            f"Expected TMAC_DELTA_ONLY 'true', got {gitlab_ci['variables']['TMAC_DELTA_ONLY']!r}"
        )

    def test_variable_tmac_comment_default(self, gitlab_ci: dict) -> None:
        """R6.4: TMAC_COMMENT default must match Action default ('true')."""
        assert gitlab_ci["variables"]["TMAC_COMMENT"] == "true", (
            f"Expected TMAC_COMMENT 'true', got {gitlab_ci['variables']['TMAC_COMMENT']!r}"
        )

    # --- at least one runnable job (R6.1) ------------------------------------

    def test_at_least_one_runnable_job(self, gitlab_ci: dict) -> None:
        """R6.1: template must define at least one runnable job."""
        job_keys = [k for k in gitlab_ci if k not in NON_JOB_KEYS]
        assert job_keys, (
            "No runnable jobs found in GitLab template "
            f"(all keys were: {list(gitlab_ci.keys())})"
        )

    # --- tmac job artifacts (R6.7) ------------------------------------------

    def test_tmac_job_artifacts_when_always(self, gitlab_ci: dict) -> None:
        """R6.7: tmac job must set artifacts.when == 'always'."""
        assert "tmac" in gitlab_ci, "Expected a 'tmac' job key in the GitLab template"
        tmac_job = gitlab_ci["tmac"]
        assert "artifacts" in tmac_job, "'tmac' job has no 'artifacts' section"
        assert tmac_job["artifacts"]["when"] == "always", (
            f"Expected artifacts.when == 'always', "
            f"got {tmac_job['artifacts']['when']!r}"
        )

    # --- tmac job rules -------------------------------------------------

    def test_tmac_job_has_rules(self, gitlab_ci: dict) -> None:
        """R6.5/R6.9: tmac job must define rules (at least 2 entries)."""
        assert "tmac" in gitlab_ci, "Expected a 'tmac' job key in the GitLab template"
        tmac_job = gitlab_ci["tmac"]
        assert "rules" in tmac_job, "'tmac' job has no 'rules' section"
        assert len(tmac_job["rules"]) >= 2, (
            f"Expected at least 2 rules entries, got {len(tmac_job['rules'])}"
        )


# ===========================================================================
# pyproject.toml tests  (R8.4, R8.7)
# ===========================================================================


class TestPyprojectToml:
    """Smoke tests for pyproject.toml at the repo root."""

    @pytest.fixture(scope="class")
    def pyproject(self) -> dict:
        return _load_toml(REPO_ROOT / "pyproject.toml")

    # --- version (R8.7) -----------------------------------------------------

    def test_version_is_1_6_0(self, pyproject: dict) -> None:
        """R8.7: package version must be exactly '1.6.0'."""
        # Support both [tool.poetry] and [project] layouts.
        version = (
            pyproject.get("tool", {}).get("poetry", {}).get("version")
            or pyproject.get("project", {}).get("version")
        )
        assert version == "1.6.0", f"Expected version '1.6.0', got {version!r}"

    # --- runtime deps (R8.4) ------------------------------------------------

    def test_runtime_dependencies_declared(self, pyproject: dict) -> None:
        """R8.4: runtime dependencies must be declared and non-empty."""
        # [tool.poetry.dependencies] (exclude the 'python' key itself)
        poetry_deps = {
            k: v
            for k, v in pyproject.get("tool", {})
            .get("poetry", {})
            .get("dependencies", {})
            .items()
            if k.lower() != "python"
        }
        # [project] PEP 621 style
        pep621_deps = pyproject.get("project", {}).get("dependencies", [])

        assert poetry_deps or pep621_deps, (
            "No runtime dependencies found in [tool.poetry.dependencies] or [project.dependencies]"
        )

    # --- console script (R8.7 / task requirement) ---------------------------

    def test_tmac_console_script_present(self, pyproject: dict) -> None:
        """R8.7: 'tmac' console script must point to tmac.cli:cli."""
        # [tool.poetry.scripts]
        poetry_scripts = pyproject.get("tool", {}).get("poetry", {}).get("scripts", {})
        # [project.scripts] (PEP 621)
        pep621_scripts = pyproject.get("project", {}).get("scripts", {})

        scripts = {**pep621_scripts, **poetry_scripts}
        assert "tmac" in scripts, (
            f"'tmac' console script not found. Declared scripts: {list(scripts.keys())}"
        )
        assert scripts["tmac"] == "tmac.cli:cli", (
            f"Expected 'tmac' script entry to be 'tmac.cli:cli', got {scripts['tmac']!r}"
        )


# ===========================================================================
# Bonus: Dockerfile smoke checks (R9.1)
# ===========================================================================


class TestDockerfile:
    """Basic structural checks on the Dockerfile (bonus)."""

    @pytest.fixture(scope="class")
    def dockerfile_text(self) -> str:
        return (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")

    def test_entrypoint_is_tmac(self, dockerfile_text: str) -> None:
        """R9.1: Dockerfile ENTRYPOINT must be the 'tmac' command."""
        assert 'ENTRYPOINT ["tmac"]' in dockerfile_text, (
            "Dockerfile does not contain: ENTRYPOINT [\"tmac\"]"
        )

    def test_pip_install_present(self, dockerfile_text: str) -> None:
        """R9.1: Dockerfile must install the package (pip install .)."""
        assert "pip install" in dockerfile_text, (
            "Dockerfile does not contain a pip install step"
        )


# ===========================================================================
# Bonus: .pre-commit-hooks.yaml smoke checks (R10.1, R10.4)
# ===========================================================================


class TestPreCommitHooks:
    """Basic structural checks on .pre-commit-hooks.yaml (bonus)."""

    @pytest.fixture(scope="class")
    def hooks(self) -> list:
        return _load_yaml(REPO_ROOT / ".pre-commit-hooks.yaml")

    def test_tmac_hook_id_present(self, hooks: list) -> None:
        """R10.1: .pre-commit-hooks.yaml must define a hook with id 'tmac'."""
        ids = [h.get("id") for h in hooks]
        assert "tmac" in ids, f"Hook id 'tmac' not found. Found ids: {ids}"

    def test_tmac_hook_targets_tf_files(self, hooks: list) -> None:
        """R10.4: tmac hook must scope to .tf files via 'files' pattern."""
        tmac_hook = next(h for h in hooks if h.get("id") == "tmac")
        files_pattern = tmac_hook.get("files", "")
        assert r"\.tf" in files_pattern, (
            f"Expected tmac hook 'files' to match .tf; got {files_pattern!r}"
        )

    def test_tmac_hook_entry_is_tmac_scan(self, hooks: list) -> None:
        """R10.1: tmac hook entry must invoke 'tmac scan'."""
        tmac_hook = next(h for h in hooks if h.get("id") == "tmac")
        assert tmac_hook.get("entry", "").startswith("tmac"), (
            f"Expected hook entry to start with 'tmac', got {tmac_hook.get('entry')!r}"
        )
