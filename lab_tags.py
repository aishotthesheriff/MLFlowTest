"""Canonical trace tags for the MLFlowTest lab (F-010).

Every experiment script tags its traces with the same core keys so traces can be
filtered reliably across experiments. Scenario-specific keys (``tool_case``,
``case``, ``turn``, ``session_id``, ``model_endpoint``) are passed as extras.

``env`` defaults to ``local``; set ``LAB_ENV`` to mark a different environment.
``git_sha`` is the short HEAD of this repository at trace-creation time, or
``unknown`` when the script runs outside a git checkout.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

TAG_KEYS = ("lab_book", "scenario", "env", "git_sha")


def git_sha() -> str:
    """Short HEAD commit for this repo, or 'unknown' if git is unavailable."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=Path(__file__).resolve().parent,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def base_tags(lab_book: str, scenario: str, **extra: str) -> dict[str, str]:
    """Return the canonical tag dict for a trace, plus scenario-specific extras."""
    tags = {
        "lab_book": lab_book,
        "scenario": scenario,
        "env": os.getenv("LAB_ENV", "local"),
        "git_sha": git_sha(),
    }
    tags.update(extra)
    return tags
