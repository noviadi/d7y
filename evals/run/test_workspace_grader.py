#!/usr/bin/env python3
"""Focused self-tests for the Stage 1a workspace capture-grader.

These are deterministic fixture tests — no agent is invoked. They materialize
small workspace trees in a temp dir, point the grader at them, and assert the
graded outcome. They do NOT exercise a live skill run; the real captured run is
graded separately as the Stage 1a exit-gate artifact.

Run: python3 evals/run/test_workspace_grader.py
"""

from __future__ import annotations

import hashlib
import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
GRADER = HERE / "workspace_grader.py"


def _load_grader():
    spec = importlib.util.spec_from_file_location("workspace_grader", GRADER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# A contract-valid initiative, mirroring the skill's own fixture shape.
VALID_INITIATIVE = """\
---
title: Customer Interview Analysis
status: active
created: 2026-07-20
updated: 2026-07-20
aliases: [interview synthesis]
related: []
---

# Customer Interview Analysis

## Provisional intent

### Outcome

Turn customer interviews into traceable findings without losing disagreement.

### Subject

Researchers analyzing customer interviews.

### Constraints and anti-goals

Support discovery; do not fabricate polished claims without provenance.

## Primary uncertainty

Whether structured synthesis saves time without flattening contradictions.

## Current understanding

### Evidence

Manual synthesis across interviews is slow.

### Assumptions

Provenance and contradictions matter enough to invalidate naive summaries.

## Current state

Active. Next move: compare workflows and define evidence-preservation needs.
"""

README = "# Initiative Organization\n\nContract placeholder for fixtures.\n"


def _make_workspace(tmp: Path, initiative_md: str | None, slug: str = "customer-interview-analysis",
                    readme: str = README) -> Path:
    """Materialize a workspace tree. If initiative_md is None, omit it."""
    ws = tmp / "ws"
    ini = ws / "initiatives"
    ini.mkdir(parents=True)
    (ini / "README.md").write_text(readme, encoding="utf-8")
    if initiative_md is not None:
        d = ini / slug
        d.mkdir()
        (d / "initiative.md").write_text(initiative_md, encoding="utf-8")
    return ws


def _sha_tree(path: Path) -> str:
    """Stable hash of a directory tree's contents (path-relative names + bytes)."""
    h = hashlib.sha256()
    for p in sorted(path.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(path)).encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def _fail(msg: str) -> None:
    raise AssertionError(msg)


def test_valid_passes(g) -> None:
    with tempfile.TemporaryDirectory() as t:
        ws = _make_workspace(Path(t), VALID_INITIATIVE)
        r = g.grade(ws)
        if r["dimensions"]["outcome"]["status"] != "pass":
            _fail(f"expected pass, got {r['dimensions']['outcome']['status']}: {r}")
        if r["failure_class"] != "none":
            _fail(f"expected failure_class none, got {r['failure_class']}")
        if r["dimensions"]["outcome"]["count"] != 1:
            _fail(f"expected count 1, got {r['dimensions']['outcome']['count']}")
        rec = r["dimensions"]["outcome"]["records"][0]
        if rec["slug"] != "customer-interview-analysis" or not rec["valid"]:
            _fail(f"bad record: {rec}")
        if r["captured"] != ["initiatives/customer-interview-analysis/initiative.md"]:
            _fail(f"bad captured: {r['captured']}")


def test_missing_heading_fails(g) -> None:
    broken = VALID_INITIATIVE.replace("## Primary uncertainty\n", "## Dropped\n")
    with tempfile.TemporaryDirectory() as t:
        ws = _make_workspace(Path(t), broken)
        r = g.grade(ws)
        if r["dimensions"]["outcome"]["status"] != "fail":
            _fail(f"expected fail, got {r['dimensions']['outcome']['status']}")
        if r["failure_class"] != "assertion_fail":
            _fail(f"expected assertion_fail, got {r['failure_class']}")
        rec = r["dimensions"]["outcome"]["records"][0]
        if rec["valid"]:
            _fail(f"record should be invalid: {rec}")
        if not any("heading" in e or "Provisional" in e or "Primary" in e
                   or "section" in e.lower() for e in rec["errors"]):
            _fail(f"errors should mention the missing heading/section: {rec['errors']}")


def test_bad_slug_fails(g) -> None:
    with tempfile.TemporaryDirectory() as t:
        ws = _make_workspace(Path(t), VALID_INITIATIVE, slug="Bad Slug Spaces")
        r = g.grade(ws)
        if r["dimensions"]["outcome"]["status"] != "fail":
            _fail(f"expected fail for non-canonical slug, got {r['dimensions']['outcome']['status']}")
        rec = r["dimensions"]["outcome"]["records"][0]
        if not any("slug" in e.lower() for e in rec["errors"]):
            _fail(f"errors should mention the slug: {rec['errors']}")


def test_bad_date_fails(g) -> None:
    broken = VALID_INITIATIVE.replace("created: 2026-07-20", "created: 20-July-2026")
    with tempfile.TemporaryDirectory() as t:
        ws = _make_workspace(Path(t), broken)
        r = g.grade(ws)
        if r["dimensions"]["outcome"]["status"] != "fail":
            _fail(f"expected fail for bad date, got {r['dimensions']['outcome']['status']}")
        rec = r["dimensions"]["outcome"]["records"][0]
        if not any("created" in e.lower() or "date" in e.lower() for e in rec["errors"]):
            _fail(f"errors should mention the date field: {rec['errors']}")


def test_placeholder_remainders_fails(g) -> None:
    # The checker flags angle-bracket template placeholders (<...>) in the body.
    broken = VALID_INITIATIVE.replace(
        "Turn customer interviews into traceable findings without losing disagreement.",
        "<describe the outcome here>",
    )
    with tempfile.TemporaryDirectory() as t:
        ws = _make_workspace(Path(t), broken)
        r = g.grade(ws)
        if r["dimensions"]["outcome"]["status"] != "fail":
            _fail(f"expected fail for placeholder remainders, got {r['dimensions']['outcome']['status']}")
        rec = r["dimensions"]["outcome"]["records"][0]
        if not any("placeholder" in e.lower() for e in rec["errors"]):
            _fail(f"errors should mention placeholders: {rec['errors']}")


def test_no_initiatives_ungradable(g) -> None:
    with tempfile.TemporaryDirectory() as t:
        ws = Path(t) / "empty"
        ws.mkdir()
        (ws / "file.txt").write_text("not a d7y workspace", encoding="utf-8")
        r = g.grade(ws)
        if r["dimensions"]["outcome"]["status"] != "ungradable":
            _fail(f"expected ungradable, got {r['dimensions']['outcome']['status']}")
        if r["failure_class"] != "ungradable":
            _fail(f"expected failure_class ungradable, got {r['failure_class']}")


def test_nonexistent_workspace(g) -> None:
    r = g.grade(Path("/tmp/does-not-exist-d7y-grader-xyz"))
    if r["dimensions"]["outcome"]["status"] != "ungradable":
        _fail(f"expected ungradable, got {r['dimensions']['outcome']['status']}")
    if r["failure_class"] != "evidence_error":
        _fail(f"expected failure_class evidence_error, got {r['failure_class']}")


def test_capture_does_not_mutate_input(g) -> None:
    with tempfile.TemporaryDirectory() as t:
        tdir = Path(t)
        ws = _make_workspace(tdir, VALID_INITIATIVE)
        before = _sha_tree(ws)
        out_dir = tdir / "out"
        captured = g.capture(ws, None, out_dir)
        after = _sha_tree(ws)
        if before != after:
            _fail("capture() mutated the input workspace")
        # artifact was copied into the out dir
        expected = out_dir / "artifacts" / "initiatives" / "customer-interview-analysis" / "initiative.md"
        if not expected.is_file():
            _fail(f"capture did not copy artifact to {expected}: {captured}")


def test_emit_writes_checks_and_summary(g) -> None:
    with tempfile.TemporaryDirectory() as t:
        tdir = Path(t)
        ws = _make_workspace(tdir, VALID_INITIATIVE)
        out_dir = tdir / "out"
        result = g.grade(ws)
        provenance = {"d7y_commit": "deadbeef", "skill_commit": "deadbeef",
                      "checker": "scripts/check-initiatives.py",
                      "grader": "evals/run/workspace_grader.py", "date": "2026-08-03"}
        captured = g.capture(ws, None, out_dir)
        g.emit(result, provenance, out_dir, captured)
        checks = out_dir / "checks.json"
        summary = out_dir / "summary.md"
        import json
        if not checks.is_file() or not summary.is_file():
            _fail("emit did not write checks.json and summary.md")
        data = json.loads(checks.read_text(encoding="utf-8"))
        if data["provenance"]["d7y_commit"] != "deadbeef":
            _fail("provenance not recorded in checks.json")
        if "outcome" not in data["dimensions"]:
            _fail("outcome dimension missing from checks.json")


def test_provenance_recorded(g) -> None:
    with tempfile.TemporaryDirectory() as t:
        ws = _make_workspace(Path(t), VALID_INITIATIVE)
        prov = g._provenance(ws, "starting-initiatives", "2026-08-03")
        for key in ("d7y_commit", "skill_commit", "checker", "grader", "date"):
            if key not in prov:
                _fail(f"provenance missing {key}: {prov}")
        if prov["checker"] != "scripts/check-initiatives.py":
            _fail(f"bad checker provenance: {prov['checker']}")


def main() -> int:
    g = _load_grader()
    tests = [
        test_valid_passes,
        test_missing_heading_fails,
        test_bad_slug_fails,
        test_bad_date_fails,
        test_placeholder_remainders_fails,
        test_no_initiatives_ungradable,
        test_nonexistent_workspace,
        test_capture_does_not_mutate_input,
        test_emit_writes_checks_and_summary,
        test_provenance_recorded,
    ]
    failures = 0
    for test in tests:
        try:
            test(g)
            print(f"ok   {test.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {test.__name__}: {exc}")
    print(f"\n{len(tests) - failures}/{len(tests)} workspace_grader tests passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
