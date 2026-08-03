#!/usr/bin/env python3
"""Thin capture-grader for the ``starting-initiatives`` skill (eval Stage 1a).

This is a *capture-grader*, not a benchmark runner. It grades **one pointed-at
workspace** by reusing the existing deterministic initiative checker
(``scripts/check-initiatives.py`` → ``inventory``). It invokes no agent, runs no
baseline/treatment pair, and reports no pass-rate or maturity.

It emits only the dimensions for which it has evidence — in Stage 1a that is the
``outcome`` dimension alone (the workspace's deterministic initiative inventory).
All other dimensions (process, invocation, quality, efficiency, environment, pair)
are explicitly ``N/A``; they are never fabricated.

See ``docs/plans/iterative-skill-eval-harness.md`` (Stage 1a) and
``docs/skill-evaluations.md`` for the contract this implements.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

SCHEMA_VERSION = 1

# Resolve paths relative to this file so the grader works from any CWD.
# evals/run/workspace_grader.py -> repo root is two parents up.
REPO = Path(__file__).resolve().parents[2]
CHECKER = REPO / "scripts" / "check-initiatives.py"

# Dimensions this grader has no evidence for in Stage 1a. Recorded as N/A rather
# than fabricated, per the claim-scoped-validity principle.
NA_DIMENSIONS = ("process", "invocation", "quality", "efficiency", "environment", "pair")


def _load_inventory():
    """Load ``inventory()`` from the hyphen-named checker via importlib.

    The checker is ``check-initiatives.py`` (a hyphenated name is not a valid
    Python identifier), so it cannot be imported normally. We load it from its
    file path instead — no copy, no shell-out, no edit to the checker.
    """
    if not CHECKER.is_file():
        raise FileNotFoundError(f"checker not found: {CHECKER}")
    spec = importlib.util.spec_from_file_location("check_initiatives", CHECKER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load checker module from {CHECKER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.inventory


def _git_commit(path: Path) -> str:
    """Best-effort short commit for ``path``'s repo; ``unknown`` if not in git."""
    try:
        out = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--short", "HEAD"],
            check=True, capture_output=True, text=True,
        )
        return out.stdout.strip() or "unknown"
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return "unknown"


def _provenance(workspace: Path, skill: str, when: str) -> dict:
    skill_commit = "unknown"
    skill_dir = REPO / "agents" / "skills" / skill
    if skill_dir.is_dir():
        skill_commit = _git_commit(skill_dir)
    return {
        "d7y_commit": _git_commit(REPO),
        "skill_commit": skill_commit,
        "checker": "scripts/check-initiatives.py",
        "grader": "evals/run/workspace_grader.py",
        "date": when,
    }


def grade(workspace: Path, skill: str = "starting-initiatives") -> dict:
    """Grade one workspace's initiative inventory.

    Returns a layered result dict with the ``outcome`` dimension and a
    ``failure_class``. Never mutates the workspace.
    """
    workspace = workspace.resolve()
    inventory = _load_inventory()

    status: str
    failure_class: str
    records: list[dict] = []
    inv: dict | None = None

    if not workspace.is_dir():
        status, failure_class = "ungradable", "evidence_error"
        detail = f"workspace does not exist or is not a directory: {workspace}"
    elif not (workspace / "initiatives").is_dir():
        status, failure_class = "ungradable", "ungradable"
        detail = "workspace has no initiatives/ directory; nothing to grade"
    else:
        try:
            inv = inventory(workspace)
        except Exception as exc:  # noqa: BLE001 — record, do not crash
            status, failure_class = "ungradable", "evidence_error"
            detail = f"inventory() raised: {type(exc).__name__}: {exc}"
        else:
            records = [
                {
                    "slug": rec.get("slug"),
                    "path": rec.get("path"),
                    "valid": bool(rec.get("valid")),
                    "errors": list(rec.get("errors", [])),
                }
                for rec in inv.get("initiatives", [])
            ]
            if inv.get("valid"):
                status, failure_class = "pass", "none"
            else:
                status, failure_class = "fail", "assertion_fail"
            detail = None

    outcome = {
        "status": status,
        "inventory_valid": bool(inv.get("valid")) if inv is not None else None,
        "count": inv.get("count") if inv is not None else 0,
        "workspace_errors": list(inv.get("errors", [])) if inv is not None else [],
        "records": records,
    }
    if detail:
        outcome["detail"] = detail

    captured_artifacts = sorted(
        str(p.relative_to(workspace))
        for p in workspace.glob("initiatives/*/initiative.md")
    ) if workspace.is_dir() else []

    return {
        "schema_version": SCHEMA_VERSION,
        "skill": skill,
        "workspace": str(workspace),
        "dimensions": {
            "outcome": outcome,
            **{dim: {"status": "N/A"} for dim in NA_DIMENSIONS},
        },
        "captured": captured_artifacts,
        "failure_class": failure_class,
    }


def capture(workspace: Path, transcript_path: Path | None, out_dir: Path) -> list[str]:
    """Copy produced initiative artifacts (and an optional transcript) into out_dir.

    Copies only; never mutates the input workspace. Returns the list of captured
    destination paths (relative to out_dir).
    """
    workspace = workspace.resolve()
    artifacts_dir = out_dir / "artifacts"
    captured: list[str] = []

    for md in sorted(workspace.glob("initiatives/*/initiative.md")):
        slug = md.parent.name
        dest_dir = artifacts_dir / "initiatives" / slug
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / "initiative.md"
        shutil.copy2(md, dest)
        captured.append(str(dest.relative_to(out_dir)))

    if transcript_path is not None:
        transcript_path = Path(transcript_path).resolve()
        if transcript_path.is_file():
            dest = artifacts_dir / transcript_path.name
            shutil.copy2(transcript_path, dest)
            captured.append(str(dest.relative_to(out_dir)))

    return captured


def emit(result: dict, provenance: dict, out_dir: Path, captured: list[str]) -> None:
    """Write checks.json and summary.md into out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {**result, "provenance": provenance}
    result["captured"] = captured or result.get("captured", [])

    (out_dir / "checks.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    outcome = result["dimensions"]["outcome"]
    lines = [
        f"# Workspace grade — {result['skill']}",
        "",
        f"- **workspace:** `{result['workspace']}`",
        f"- **outcome:** `{outcome['status']}` (inventory_valid={outcome['inventory_valid']}, "
        f"count={outcome['count']})",
        f"- **failure_class:** `{result['failure_class']}`",
        "",
        "## Provenance",
        "",
        f"- d7y commit: `{provenance['d7y_commit']}`",
        f"- skill commit: `{provenance['skill_commit']}`",
        f"- checker: `{provenance['checker']}`",
        f"- date: {provenance['date']}",
        "",
        "## Dimensions with evidence",
        "",
        "Only `outcome` has Stage-1a evidence. Other dimensions "
        f"({', '.join(NA_DIMENSIONS)}) are N/A — not fabricated.",
        "",
    ]
    if outcome.get("workspace_errors"):
        lines += ["## Workspace errors", ""]
        lines += [f"- {e}" for e in outcome["workspace_errors"]]
        lines.append("")
    if outcome.get("records"):
        lines += ["## Records", ""]
        for rec in outcome["records"]:
            flag = "ok" if rec["valid"] else "INVALID"
            lines.append(f"- `{rec['slug']}` — {flag}")
            for err in rec["errors"]:
                lines.append(f"  - {err}")
        lines.append("")
    if result["captured"]:
        lines += ["## Captured artifacts", ""]
        lines += [f"- `{c}`" for c in result["captured"]]
        lines.append("")
    (out_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def _default_out_dir(skill: str) -> Path:
    """Auto-incrementing evals/runs/<skill>/iteration-<N>/."""
    base = REPO / "evals" / "runs" / skill
    n = 1
    if base.is_dir():
        existing = [
            int(p.name.split("-")[1])
            for p in base.iterdir()
            if p.is_dir() and p.name.startswith("iteration-")
            and p.name[10:].isdigit()
        ]
        n = max(existing) + 1 if existing else 1
    return base / f"iteration-{n}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="workspace_grader.py",
        description="Grade one workspace's initiative inventory (eval Stage 1a capture-grader).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("workspace", help="path to the workspace to grade")
    parser.add_argument("--skill", default="starting-initiatives",
                        help="skill name (default: starting-initiatives)")
    parser.add_argument("--transcript", default=None,
                        help="optional transcript file to capture alongside artifacts")
    parser.add_argument("--out", default=None,
                        help="output dir (default: evals/runs/<skill>/iteration-<N>/)")
    parser.add_argument("--date", default=None,
                        help="date for provenance (default: today)")
    parser.add_argument("--no-emit", action="store_true",
                        help="grade only; print checks.json to stdout, write no files")
    args = parser.parse_args(argv)

    workspace = Path(args.workspace)
    out_dir = Path(args.out) if args.out else _default_out_dir(args.skill)
    when = args.date or date.today().isoformat()

    try:
        result = grade(workspace, skill=args.skill)
    except FileNotFoundError as exc:
        print(f"workspace_grader: {exc}", file=sys.stderr)
        return 2

    provenance = _provenance(workspace, args.skill, when)

    if args.no_emit:
        result["provenance"] = provenance
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["failure_class"] in ("none",) else 1

    captured = capture(workspace,
                       Path(args.transcript) if args.transcript else None, out_dir)
    emit(result, provenance, out_dir, captured)
    print(f"graded {result['dimensions']['outcome']['status']} "
          f"(failure_class={result['failure_class']}) -> {out_dir}")
    return 0 if result["failure_class"] == "none" else 1


if __name__ == "__main__":
    sys.exit(main())
