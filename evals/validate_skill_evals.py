#!/usr/bin/env python3
"""Validate D7Y skill eval definitions without dependencies."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable


ID_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
DIMENSIONS = {"invocation", "process", "outcome", "quality", "efficiency"}
KINDS = {"deterministic", "rubric", "human"}
TOP_KEYS = {"$schema", "schema_version", "skill_name", "evals"}
CASE_KEYS = {"id", "prompt", "should_trigger", "expected_output", "files", "assertions"}
FILE_KEYS = {"source", "destination"}
ASSERTION_KEYS = {"id", "dimension", "kind", "required", "description", "grader"}


def is_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def exact_keys(value: dict[str, Any], allowed: set[str], required: set[str], where: str, errors: list[str]) -> None:
    missing = sorted(required - value.keys())
    extra = sorted(value.keys() - allowed)
    if missing:
        errors.append(f"{where}: missing fields: {', '.join(missing)}")
    if extra:
        errors.append(f"{where}: unsupported fields: {', '.join(extra)}")


def safe_relative(value: str) -> bool:
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts and bool(path.parts)


def validate_assertion(value: Any, where: str, errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{where}: assertion must be an object")
        return
    required = ASSERTION_KEYS - {"grader"}
    exact_keys(value, ASSERTION_KEYS, required, where, errors)
    if not is_text(value.get("id")) or not ID_RE.fullmatch(value["id"]):
        errors.append(f"{where}.id: must be a lowercase hyphenated identifier")
    if value.get("dimension") not in DIMENSIONS:
        errors.append(f"{where}.dimension: must be one of {sorted(DIMENSIONS)}")
    if value.get("kind") not in KINDS:
        errors.append(f"{where}.kind: must be one of {sorted(KINDS)}")
    if not isinstance(value.get("required"), bool):
        errors.append(f"{where}.required: must be a boolean")
    if not is_text(value.get("description")):
        errors.append(f"{where}.description: must be non-empty text")
    if "grader" in value and not is_text(value["grader"]):
        errors.append(f"{where}.grader: must be non-empty text")


SourceChecker = Callable[[str], "str | None"]
"""A fixture-source checker returns an error message, or ``None`` when the source
resolves and exists. The disk checker validates a working-tree skill directory;
callers reading from immutable objects supply an equivalent object checker."""


def _disk_source_checker(skill_dir: Path) -> SourceChecker:
    def check(source: str) -> str | None:
        source_path = (skill_dir / source).resolve()
        if not source_path.is_relative_to(skill_dir.resolve()):
            return "resolves outside the skill directory"
        if not source_path.is_file():
            return f"fixture does not exist: {source}"
        return None

    return check


def validate_file(
    value: Any, where: str, errors: list[str], *, check_source: SourceChecker
) -> None:
    if not isinstance(value, dict):
        errors.append(f"{where}: file fixture must be an object")
        return
    exact_keys(value, FILE_KEYS, FILE_KEYS, where, errors)
    source = value.get("source")
    destination = value.get("destination")
    if not is_text(source) or not safe_relative(source):
        errors.append(f"{where}.source: must be a safe path relative to the skill directory")
    else:
        message = check_source(source)
        if message:
            errors.append(f"{where}.source: {message}")
    if not is_text(destination) or not safe_relative(destination):
        errors.append(f"{where}.destination: must be a safe path relative to the eval workspace")


def validate_case(
    value: Any, where: str, errors: list[str], *, check_source: SourceChecker
) -> None:
    if not isinstance(value, dict):
        errors.append(f"{where}: eval must be an object")
        return
    exact_keys(value, CASE_KEYS, CASE_KEYS, where, errors)
    if not is_text(value.get("id")) or not ID_RE.fullmatch(value["id"]):
        errors.append(f"{where}.id: must be a lowercase hyphenated identifier")
    if not is_text(value.get("prompt")):
        errors.append(f"{where}.prompt: must be non-empty text")
    if not isinstance(value.get("should_trigger"), bool):
        errors.append(f"{where}.should_trigger: must be a boolean")
    if not is_text(value.get("expected_output")):
        errors.append(f"{where}.expected_output: must be non-empty text")

    files = value.get("files")
    if not isinstance(files, list):
        errors.append(f"{where}.files: must be an array")
    else:
        for index, fixture in enumerate(files):
            validate_file(fixture, f"{where}.files[{index}]", errors, check_source=check_source)

    assertions = value.get("assertions")
    if not isinstance(assertions, list):
        errors.append(f"{where}.assertions: must be an array")
    else:
        for index, assertion in enumerate(assertions):
            validate_assertion(assertion, f"{where}.assertions[{index}]", errors)
        ids = [item.get("id") for item in assertions if isinstance(item, dict) and is_text(item.get("id"))]
        if len(ids) != len(set(ids)):
            errors.append(f"{where}.assertions: assertion IDs must be unique within the case")


def validate_suite_data(
    value: Any, skill_dir_name: str, check_source: SourceChecker, where: str
) -> list[str]:
    """Validate a parsed suite against the committed contract.

    ``check_source`` validates each ``files[].source`` against whatever backing
    store the caller reads from (working tree or immutable objects). Returns a
    list of human-readable errors; an empty list means the suite is valid.
    """
    errors: list[str] = []
    if not isinstance(value, dict):
        return [f"{where}: suite must be an object"]

    exact_keys(value, TOP_KEYS, {"schema_version", "skill_name", "evals"}, where, errors)
    if value.get("schema_version") != 1:
        errors.append(f"{where}.schema_version: must equal 1")
    if value.get("skill_name") != skill_dir_name:
        errors.append(f"{where}.skill_name: must match directory {skill_dir_name!r}")

    cases = value.get("evals")
    if not isinstance(cases, list):
        errors.append(f"{where}.evals: must be an array")
        return errors
    if len(cases) < 3:
        errors.append(f"{where}.evals: must contain at least three cases")
    for index, case in enumerate(cases):
        validate_case(case, f"{where}.evals[{index}]", errors, check_source=check_source)

    ids = [item.get("id") for item in cases if isinstance(item, dict) and is_text(item.get("id"))]
    if len(ids) != len(set(ids)):
        errors.append(f"{where}.evals: case IDs must be unique")
    triggers = [item.get("should_trigger") for item in cases if isinstance(item, dict)]
    if True not in triggers:
        errors.append(f"{where}.evals: requires at least one positive invocation case")
    if False not in triggers:
        errors.append(f"{where}.evals: requires at least one negative control")
    return errors


def validate_suite(path: Path) -> list[str]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return [f"{path}: cannot read valid UTF-8 JSON: {error}"]

    skill_dir = path.parent.parent
    return validate_suite_data(
        value, skill_dir.name, _disk_source_checker(skill_dir), str(path)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, help="evals.json files; defaults to every skill suite")
    args = parser.parse_args()
    paths = args.paths or sorted(Path("skills").glob("*/evals/evals.json"))
    if not paths:
        print("No skill eval suites found", file=sys.stderr)
        return 1

    failed = False
    for path in paths:
        errors = validate_suite(path)
        if errors:
            failed = True
            print(f"INVALID: {path}")
            for error in errors:
                print(f"  {error}")
        else:
            suite = json.loads(path.read_text(encoding="utf-8"))
            print(f"VALID: {path} ({len(suite['evals'])} cases)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
