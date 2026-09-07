"""Scoped, best-effort git commits for the machine-memory layer.

Called after flush.py or compile.py durably writes its own files. Commits
only the paths that script itself just wrote — never `git add -A` — so an
automated pass can never sweep in unrelated work sitting uncommitted
elsewhere in the vault (a human mid-edit, say). Failure here must never
break the caller: the memory write already succeeded and matters more than
its git record, so every git error is swallowed and reported through the
caller's own write_health instead of raised.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Callable, Sequence


def commit_paths(
    vault_root: Path,
    paths: Sequence[str],
    message: str,
    report: Callable[[str], None],
    runner: Callable[..., "subprocess.CompletedProcess[str]"] | None = None,
) -> bool:
    """Stage and commit exactly `paths` (relative to vault_root) if changed.

    Returns True on a real commit, False if there was nothing to commit or
    git was unavailable. `report(error)` is called on any failure; it never
    raises out of here.
    """
    if not paths:
        return False
    run = runner or subprocess.run
    if runner is None and shutil.which("git") is None:
        report("git-missing")
        return False
    try:
        status = run(
            ["git", "-C", str(vault_root), "status", "--porcelain", "--", *paths],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if status.returncode != 0:
            report(f"git-status-failed:{status.returncode}")
            return False
        if not status.stdout.strip():
            return False

        add = run(
            ["git", "-C", str(vault_root), "add", "--", *paths],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if add.returncode != 0:
            report(f"git-add-failed:{add.returncode}")
            return False

        commit = run(
            ["git", "-C", str(vault_root), "commit", "-m", message, "--", *paths],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if commit.returncode != 0:
            report(f"git-commit-failed:{commit.returncode}")
            return False
        return True
    except (OSError, subprocess.SubprocessError) as exc:
        report(f"git-commit-exception:{exc.__class__.__name__}")
        return False
