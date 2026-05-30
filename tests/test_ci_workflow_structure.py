"""Structure meta-test for .github/workflows/ci.yml (T-003).

The delivery plan (plan-critic C1; TODO.md T-003 + "False concurrency caught"
§1) REQUIRES every CI stage to be present-and-stubbed UP FRONT, so the three
parallel streams (S1/S2/S3) and the later fixture-filling tasks (T-101 wires
contracts, T-304 fills F1 calibration, T-402 fills F2 mitigate) only ADD fixtures
INSIDE an already-declared stage and NEVER edit the workflow layout. If a future
edit drops a stage, this test must go RED.

We deliberately do NOT depend on PyYAML (the project is Python-stdlib only, and
there is no PyYAML in the env). A hand-rolled YAML subset parser would be a
second untested unit that could drift from the real GitHub Actions parser —
exactly the fake-diverges-from-prod hazard the charter warns about. So this test
reads the workflow as TEXT and asserts the presence of stable MARKER TOKENS the
implementer must include (one per required stage), plus the few invariants the
acceptance criteria name (python 3.12; the pins/size-guard/docs commands). The
test is robust to formatting — it searches for tokens, not exact indentation.

Each required stage maps to a STABLE TOKEN. The contract with the implementer:
declare each stage with a COLLISION-FREE MARKER of the exact form

    stage:<token>

embedded in that job/step's `name:` (e.g. `name: pins (stage:pins)`). We use
the `stage:` prefix deliberately because bare words like "lint", "docs", or
"unit" already appear incidentally in any workflow (paths filters, comments,
`markdownlint`, `docs/**`) — matching those bare would be a FALSE GREEN that
lets the implementer drop the real stage while the test stays happy. The
`stage:<token>` marker cannot collide with incidental text, so its presence
proves the stage was declared on purpose.

ARCHITECTURE.md "Validation — two physical tiers" (~L547) enumerates the CI
stages; TODO.md T-003 acceptance restates them and adds the F1/F2 placeholders
and the size-guard hardening note.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"


# ---------------------------------------------------------------------------
# Required stage tokens. Each entry: (token, why-it-must-exist).
# The token is the stable marker the implementer embeds in a job/step `name:`.
# WHY documented per token so a future reader knows what a dropped stage costs.
# ---------------------------------------------------------------------------

REQUIRED_STAGE_TOKENS = {
    "lint": "lint stage — shellcheck/ansible-lint/yamllint/ruff (ARCH L549).",
    "unit": "unit stage — pytest over scorer/fold/chain/contract loaders on fakes (ARCH L550).",
    "contracts": "contracts stage — JSON-Schema validation; PLACEHOLDER here, wired in T-101. Must exist up front so T-101 only fills fixtures.",
    "f1-calibration": "F1 DETECT calibration stage — PLACEHOLDER here, fixtures filled by T-304. Must exist up front so T-304 never edits layout.",
    "f2-mitigate": "F2 MITIGATE deny-everything stage — PLACEHOLDER here, fixtures filled by T-402. Must exist up front so T-402 never edits layout.",
    "syntax": "syntax stage — vagrant/ansible/compose/packer validate (ARCH L552).",
    "pins": "pins stage — runs scripts/pins_gate.py (the gate this PR also adds).",
    "docs": "docs stage — mkdocs build --strict + link-check (ARCH L554).",
    "secrets": "secrets stage — gitleaks (ARCH L555).",
    "size-guard": "size-guard stage — runs scripts/size_guard.py (T-001 forward guard).",
}


def workflow_text() -> str:
    assert WORKFLOW.exists(), (
        f"the CI workflow must exist at {WORKFLOW} (T-003 locks the structure "
        "up front for S1/S2/S3 to stay file-disjoint)"
    )
    return WORKFLOW.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Every required stage token is present — one assertion (concept) per token.
# ---------------------------------------------------------------------------

def marker(token: str) -> str:
    """The collision-free declaration marker the implementer must embed."""
    return f"stage:{token}"


@pytest.mark.parametrize("token", sorted(REQUIRED_STAGE_TOKENS))
def test_required_stage_token_present(token):
    """Each required CI stage is declared via its `stage:<token>` marker.

    Robust to formatting: we search the raw text for the marker, not for an
    exact `name:` line, so reindenting or reordering does not false-fail. The
    `stage:` prefix prevents incidental matches (e.g. `markdownlint` matching a
    bare "lint") that would be false greens.
    """
    text = workflow_text()
    assert marker(token) in text, (
        f"CI stage marker {marker(token)!r} missing from ci.yml. "
        f"WHY required: {REQUIRED_STAGE_TOKENS[token]} "
        "Dropping it lets a future PR ship without that gate."
    )


def test_no_required_stage_is_missing_as_a_set():
    """A single failure message listing ALL missing stages (faster triage)."""
    text = workflow_text()
    missing = sorted(t for t in REQUIRED_STAGE_TOKENS if marker(t) not in text)
    assert missing == [], (
        f"ci.yml is missing required stage markers: {[marker(t) for t in missing]}. "
        "Every stage must be present-and-stubbed up front (plan-critic C1)."
    )


# ---------------------------------------------------------------------------
# 2. The acceptance-criteria invariants the spec calls out by name.
# ---------------------------------------------------------------------------

def test_pins_stage_invokes_pins_gate_script():
    """The pins stage must actually RUN scripts/pins_gate.py, not just name it."""
    text = workflow_text()
    assert "pins_gate.py" in text, (
        "the pins stage must invoke scripts/pins_gate.py (the gate added in "
        "this PR); a named-but-unwired stage is a false green."
    )


def test_size_guard_stage_invokes_size_guard_script():
    """The size-guard stage must RUN scripts/size_guard.py (T-001 forward guard)."""
    text = workflow_text()
    assert "size_guard.py" in text, (
        "the size-guard stage must invoke scripts/size_guard.py."
    )


def test_size_guard_invoked_with_explicit_root():
    """size-guard must pass an explicit known-good root (not bare).

    TODO.md T-003 hardening note: os.walk silently yields nothing for a missing
    path, so a typo'd root is a quiet false-pass. The stage must invoke the
    guard with an explicit root (e.g. `size_guard.py .`) so a missing-root typo
    cannot pass green. We assert the script is followed by a root argument.
    """
    text = workflow_text()
    # Match `size_guard.py` followed (same line) by a non-flag argument (the root).
    invocation = re.search(r"size_guard\.py\s+(\S+)", text)
    assert invocation is not None, (
        "size_guard.py must be invoked WITH a root argument; a bare invocation "
        "risks the silent missing-root false-pass (T-003 hardening note)."
    )
    arg = invocation.group(1)
    assert not arg.startswith("-"), (
        f"the argument after size_guard.py must be a root path, got {arg!r}"
    )


def test_docs_stage_runs_mkdocs_strict():
    """The docs stage must run `mkdocs build --strict` (ARCH L554)."""
    text = workflow_text()
    assert "mkdocs build --strict" in text, (
        "the docs stage must run `mkdocs build --strict` so a broken doc fails CI."
    )


def test_secrets_stage_uses_gitleaks():
    """The secrets stage must use gitleaks (ARCH L555)."""
    text = workflow_text()
    assert re.search(r"gitleaks", text, re.IGNORECASE), (
        "the secrets stage must run gitleaks."
    )


def test_unit_stage_runs_pytest():
    """The unit stage must run pytest (ARCH L550)."""
    text = workflow_text()
    assert "pytest" in text, "the unit stage must run pytest over the fakes."


def test_matrix_pins_python_312():
    """The single matrix axis is python 3.12 (ARCH L558; T-003 acceptance).

    Accepts "3.12" with or without surrounding quotes so a YAML string vs bare
    number does not false-fail.
    """
    text = workflow_text()
    assert "3.12" in text, (
        "the workflow must pin python 3.12 (the only matrix axis)."
    )


def test_workflow_triggers_on_pull_request():
    """Push-blocking CI must run on pull_request (so it can gate merges)."""
    text = workflow_text()
    assert "pull_request" in text, (
        "a push-blocking CI must trigger on pull_request to gate PRs."
    )
