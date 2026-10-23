"""Git diff helper for TMAC CI — computes the Changed_File_Set.

This module is the *only* module in the CI layer that interacts with git.
It never imports any TMAC engine module and never places a token on a command line.

Only stdlib dependencies: subprocess, fnmatch.
"""

import fnmatch
import subprocess
from os import fspath
from pathlib import Path


class GitRefError(Exception):
    """Raised when a git ref is missing or cannot be resolved.

    Attributes:
        ref_label: A human-readable name identifying which ref failed,
                   e.g. "base_ref" or "head_ref".
        ref_value: The actual ref string that could not be resolved.
    """

    def __init__(self, ref_label: str, ref_value: str | None) -> None:
        self.ref_label = ref_label
        self.ref_value = ref_value
        super().__init__(
            f"Cannot resolve {ref_label} '{ref_value}': "
            "ref is missing or not a valid git object."
        )


def changed_tf_files(
    base_ref: str,
    head_ref: str,
    repo_dir: str = ".",
    pattern: str = "*.tf",
) -> list[str]:
    """Return the Changed_File_Set for a git range.

    Computes the set of files that (a) match *pattern* (fnmatch on basename) and
    (b) were Added, Modified, or Renamed between *base_ref* and *head_ref*.

    Algorithm:
    1. Validate both refs with ``git -C <repo_dir> rev-parse --verify <ref>``.
       Raises :class:`GitRefError` for the first ref that cannot be resolved,
       naming it by *ref_label* (R1.7, R1.8).
    2. Run ``git -C <repo_dir> diff --name-status --diff-filter=AMR <base>...<head>``.
    3. For rename lines (``Rxxx<TAB>old<TAB>new``), keep the **new** path.
    4. Filter: keep only paths whose basename matches *pattern* via :func:`fnmatch.fnmatch`.
    5. Return a **sorted, de-duplicated** list of paths (determinism, R1.2, R1.3).

    Args:
        base_ref: The base git ref (e.g. the merge-base SHA, branch name, or tag).
        head_ref: The head git ref (e.g. the PR/MR head SHA or branch).
        repo_dir: Path to the git repository root.  Defaults to ``"."``.
        pattern:  Glob pattern applied to the file's basename.  Defaults to ``"*.tf"``.

    Returns:
        A sorted, de-duplicated list of relative file paths.

    Raises:
        GitRefError: If either ref cannot be resolved by git.
        subprocess.CalledProcessError: If git exits unexpectedly for any other reason.
    """
    repo_path = fspath(Path(repo_dir))

    # --- Step 1: validate both refs ---
    _validate_ref("base_ref", base_ref, repo_path)
    _validate_ref("head_ref", head_ref, repo_path)

    # --- Step 2: compute the diff ---
    result = subprocess.run(
        [
            "git",
            "-C",
            repo_path,
            "diff",
            "--name-status",
            "--diff-filter=AMR",
            f"{base_ref}...{head_ref}",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    # --- Steps 3 & 4: parse output, extract paths, filter ---
    paths: set[str] = set()
    for line in result.stdout.splitlines():
        line = line.rstrip("\n")
        if not line:
            continue

        parts = line.split("\t")
        status_code = parts[0]

        if status_code.startswith("R"):
            # Rename: R<score> <TAB> old_path <TAB> new_path
            if len(parts) < 3:
                continue
            file_path = parts[2]
        else:
            # Added (A) or Modified (M): <status> <TAB> <path>
            if len(parts) < 2:
                continue
            file_path = parts[1]

        basename = Path(file_path).name
        if fnmatch.fnmatch(basename, pattern):
            paths.add(file_path)

    # --- Step 5: return sorted, de-duplicated list ---
    return sorted(paths)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _validate_ref(ref_label: str, ref_value: str, repo_path: str) -> None:
    """Run ``git rev-parse --verify`` for *ref_value*; raise GitRefError if it fails."""
    proc = subprocess.run(
        ["git", "-C", repo_path, "rev-parse", "--verify", ref_value],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise GitRefError(ref_label=ref_label, ref_value=ref_value)
