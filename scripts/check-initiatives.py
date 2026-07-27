#!/usr/bin/env python3
"""Shared deterministic implementation for D7Y initiative inventory and validation.

This is the single source of initiative parsing, validation, relationship
checking, and structured result construction. It is consumed by the user-facing
``d7y initiatives list`` and ``d7y initiatives check`` commands, by contributor
validation (``d7y validate`` and ``d7y validate initiatives``), and indirectly by
the ``starting-initiatives`` skill through the CLI contract.

Parsing, validation, relationship checks, and structured result construction are
independent from human presentation: ``inventory`` produces one versioned result,
and the ``check`` and ``list`` views only differ in how they present it. The
implementation has no dependencies and writes no state.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path


ALLOWED_STATUSES = {"active", "paused", "graduated", "archived"}
REQUIRED_FIELDS = ("title", "status", "created", "updated", "aliases", "related")
LIST_FIELDS = {"aliases", "related"}
REQUIRED_HEADINGS = (
    "## Provisional intent",
    "### Outcome",
    "### Subject",
    "### Constraints and anti-goals",
    "## Primary uncertainty",
    "## Current understanding",
    "### Evidence",
    "### Assumptions",
    "## Current state",
)
SLUG_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
FIELD_RE = re.compile(r"([A-Za-z][A-Za-z0-9_-]*):(?:\s*(.*))?")


def scalar(raw: str) -> str:
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def inline_list(raw: str) -> list[str] | None:
    value = raw.strip()
    if value == "[]":
        return []
    if not (value.startswith("[") and value.endswith("]")):
        return None
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [scalar(item) for item in next(csv.reader([inner], skipinitialspace=True))]


def parse_frontmatter(lines: list[str], errors: list[str]) -> tuple[dict[str, str], dict[str, list[str]], int]:
    if not lines or lines[0].strip() != "---":
        errors.append("missing opening frontmatter delimiter")
        return {}, {}, 0

    try:
        end = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration:
        errors.append("missing closing frontmatter delimiter")
        return {}, {}, 0

    fields: dict[str, str] = {}
    lists: dict[str, list[str]] = {}
    current_list: str | None = None

    for number, line in enumerate(lines[1:end], 2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        if line[0].isspace():
            item = re.fullmatch(r"\s+-\s+(.+)", line)
            if current_list and item:
                lists[current_list].append(scalar(item.group(1)))
            continue

        match = FIELD_RE.fullmatch(line)
        if not match:
            errors.append(f"frontmatter line {number} is not a key-value field")
            current_list = None
            continue

        key, raw = match.group(1), match.group(2) or ""
        if key in fields or key in lists:
            errors.append(f"frontmatter field {key!r} is duplicated")
            current_list = None
            continue

        if key in LIST_FIELDS:
            parsed = inline_list(raw)
            if parsed is None and raw.strip():
                errors.append(f"frontmatter field {key!r} must be a list")
                lists[key] = []
                current_list = None
            elif parsed is None:
                lists[key] = []
                current_list = key
            else:
                lists[key] = parsed
                current_list = None
        else:
            fields[key] = scalar(raw)
            current_list = None

    return fields, lists, end + 1


def valid_date(value: str) -> bool:
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def inspect(path: Path, root: Path) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    slug = path.parent.name

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        return {
            "slug": slug,
            "path": str(path.relative_to(root)),
            "valid": False,
            "errors": [f"cannot read UTF-8 document: {error}"],
            "warnings": [],
        }

    fields, lists, body_start = parse_frontmatter(lines, errors)
    for key in REQUIRED_FIELDS:
        if key not in fields and key not in lists:
            errors.append(f"missing required frontmatter field {key!r}")

    title = fields.get("title", "")
    status = fields.get("status", "")
    created = fields.get("created", "")
    updated = fields.get("updated", "")
    aliases = lists.get("aliases", [])
    related = lists.get("related", [])

    if not SLUG_RE.fullmatch(slug):
        errors.append("directory name is not a lowercase hyphenated slug")
    if not title or (title.startswith("<") and title.endswith(">")):
        errors.append("title must be a concrete human-readable value")
    if status not in ALLOWED_STATUSES:
        errors.append(f"status must be one of {sorted(ALLOWED_STATUSES)}")
    if not valid_date(created):
        errors.append("created must be an ISO date in YYYY-MM-DD form")
    if not valid_date(updated):
        errors.append("updated must be an ISO date in YYYY-MM-DD form")
    if valid_date(created) and valid_date(updated) and updated < created:
        errors.append("updated date precedes created date")

    for relation in related:
        if not SLUG_RE.fullmatch(relation):
            errors.append(f"related value {relation!r} is not a valid slug")

    body = lines[body_start:]
    heading_positions: list[int] = []
    for heading in REQUIRED_HEADINGS:
        positions = [index for index, line in enumerate(body) if line.strip() == heading]
        if len(positions) != 1:
            errors.append(f"required heading {heading!r} occurs {len(positions)} times")
        else:
            heading_positions.append(positions[0])
    if len(heading_positions) == len(REQUIRED_HEADINGS) and heading_positions != sorted(heading_positions):
        errors.append("required headings are out of canonical order")

    h1 = next((line[2:].strip() for line in body if line.startswith("# ")), "")
    if not h1:
        errors.append("missing initiative title heading")
    elif title and h1 != title:
        errors.append("title heading does not match frontmatter title")

    placeholders = [line.strip() for line in body if re.fullmatch(r"<[^>]+>", line.strip())]
    if placeholders:
        errors.append("template placeholders remain in the initiative body")

    return {
        "slug": slug,
        "path": str(path.relative_to(root)),
        "title": title,
        "status": status,
        "created": created,
        "updated": updated,
        "aliases": aliases,
        "related": related,
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def inventory(root: Path) -> dict[str, object]:
    initiatives_dir = root / "initiatives"
    errors: list[str] = []
    warnings: list[str] = []

    if not (initiatives_dir / "README.md").is_file():
        errors.append("initiatives/README.md organization contract is missing")

    paths = sorted(initiatives_dir.glob("*/initiative.md")) if initiatives_dir.is_dir() else []
    records = [inspect(path, root) for path in paths]
    by_slug = {str(record["slug"]): record for record in records}

    if initiatives_dir.is_dir():
        for directory in sorted(path for path in initiatives_dir.iterdir() if path.is_dir()):
            if not (directory / "initiative.md").is_file():
                errors.append(f"{directory.relative_to(root)} has no initiative.md")
        canonical = set(paths)
        for misplaced in sorted(initiatives_dir.rglob("initiative.md")):
            if misplaced not in canonical:
                errors.append(f"{misplaced.relative_to(root)} is outside the canonical one-level layout")

    identities: dict[str, list[str]] = defaultdict(list)
    for record in records:
        slug = str(record["slug"])
        for value in [str(record.get("title", "")), *record.get("aliases", [])]:
            key = normalized(value)
            if key:
                identities[key].append(slug)
        for relation in record.get("related", []):
            target = by_slug.get(relation)
            if target is None:
                record["errors"].append(f"related initiative {relation!r} does not exist")
                record["valid"] = False
            elif slug not in target.get("related", []):
                record["errors"].append(f"related initiative {relation!r} does not link back")
                record["valid"] = False

    for identity, slugs in identities.items():
        unique = sorted(set(slugs))
        if len(unique) > 1:
            warnings.append(f"identity {identity!r} appears in initiatives: {', '.join(unique)}")

    valid = not errors and all(bool(record["valid"]) for record in records)
    return {
        "version": 1,
        "root": str(root),
        "valid": valid,
        "count": len(records),
        "errors": errors,
        "warnings": warnings,
        "initiatives": records,
    }


def with_status_filter(result: dict[str, object], status: str) -> dict[str, object]:
    """Return a presentation copy filtered to one status.

    The complete workspace is always validated first; ``valid``, ``errors``, and
    ``warnings`` keep reflecting the whole workspace. Only ``initiatives`` and
    ``count`` narrow to the matching records.
    """
    matching = [record for record in result["initiatives"] if record.get("status") == status]
    return {**result, "initiatives": matching, "count": len(matching)}


def print_check_text(result: dict[str, object]) -> None:
    status = "valid" if result["valid"] else "invalid"
    print(f"Initiatives: {status} ({result['count']} found)")
    for error in result["errors"]:
        print(f"ERROR: {error}")
    for warning in result["warnings"]:
        print(f"WARNING: {warning}")
    for record in result["initiatives"]:
        marker = "OK" if record["valid"] else "INVALID"
        print(f"{marker}: {record['slug']} [{record.get('status', '')}] {record.get('title', '')}")
        for error in record["errors"]:
            print(f"  ERROR: {error}")
        for warning in record["warnings"]:
            print(f"  WARNING: {warning}")


def print_list_text(complete: dict[str, object], displayed: dict[str, object]) -> None:
    state = "valid" if complete["valid"] else "invalid"
    total = complete["count"]
    shown = displayed["count"]
    if shown == total:
        print(f"Initiatives in {complete['root']} ({state}, {shown} listed):")
    else:
        print(f"Initiatives in {complete['root']} ({state}, {shown} of {total} listed):")

    if not displayed["initiatives"]:
        print("  (none)")
    for record in displayed["initiatives"]:
        slug = record.get("slug", "?")
        status = record.get("status") or "-"
        updated = record.get("updated") or "-"
        title = record.get("title") or "-"
        suffix = "" if record.get("valid") else "  [invalid]"
        print(f"  {slug}  {status}  {updated}  {title}{suffix}")

    # Surface workspace and per-record diagnostics from the complete workspace so
    # malformed artifacts are never silently omitted, even when filtered out.
    notes: list[str] = []
    for error in complete["errors"]:
        notes.append(f"ERROR: {error}")
    for record in complete["initiatives"]:
        for error in record.get("errors", []):
            notes.append(f"{record.get('slug', '?')}: {error}")
    for warning in complete["warnings"]:
        notes.append(f"WARNING: {warning}")
    for record in complete["initiatives"]:
        for warning in record.get("warnings", []):
            notes.append(f"{record.get('slug', '?')}: {warning}")
    if notes:
        print()
        for note in notes:
            print(note)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inventory and validate D7Y initiatives without dependencies.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Target workspace root (default: cwd)")
    parser.add_argument(
        "--status",
        choices=sorted(ALLOWED_STATUSES),
        help="Filter records by status (list view only); the workspace is still fully validated",
    )
    parser.add_argument(
        "--view",
        choices=("check", "list"),
        default="check",
        help="Human presentation view (default: check); JSON output is the same versioned shape for both",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON only")
    args = parser.parse_args()

    result = inventory(args.root.resolve())
    displayed = with_status_filter(result, args.status) if args.view == "list" and args.status else result

    if args.json:
        json.dump(displayed, sys.stdout, indent=2)
        print()
    elif args.view == "list":
        print_list_text(result, displayed)
    else:
        print_check_text(displayed)
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
