#!/usr/bin/env python3
"""Deterministic image canary scanner for D7Y Harbor Phase 0 posture.

Scans a built image (and, optionally, a synthetic-secret rebuild) to confirm the
agent/verifier images contain no D7Y source checkout, eval definitions, expected
outcomes, graders, benchmark material, host settings, generated Claude identity
state (the installer's `.claude/` directory and `.claude.json`), or credentials.
It also runs a synthetic-secret canary: it rebuilds the agent Dockerfile with a
throwaway secret build argument and a secret-bearing context file, then asserts
the secret never enters the image, proving the build does not bake in context
material.

The scanner FAILS CLOSED. A scan, canary build, or cleanup that cannot execute
is never reported `CLEAN`: it is reported as a distinct command failure with
redacted diagnostics and a non-zero exit, so a missing image, a dead daemon, or
a Docker exit code such as 125 can never become absence evidence.

Dependency-free standard library only (subprocess to the docker CLI). It does
not call any model or network.

Limitation: a filesystem scan can prove that searched-for forbidden material is
absent and that named secret bytes do not appear; it cannot exhaustively disprove
unknown secret bytes without reading every byte. Results state that boundary.
"""

from __future__ import annotations

import argparse
import json
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path

HARBOR_DIR = Path(__file__).resolve().parents[1]
AGENT_DOCKERFILE = HARBOR_DIR / "images" / "agent" / "Dockerfile"

# Distinctive markers that must never appear in a clean agent/verifier image.
# The installer-generated identity state (the `.claude/` directory and the
# top-level `.claude.json` carrying generated machineID/userID) is removed from
# the retained agent image after the build-time version checks; both are scanned
# for explicitly below and reported as forbidden when present.
FORBIDDEN_FILES = (
    "evals.json",
    "benchmark.json",
    "settings.json",
    "settings.local.json",
    "SKILL.md",
    "check-initiatives.py",
    ".claude.json",
)
FORBIDDEN_CONTENT = (
    "starting-initiatives",
    "check-initiatives",
    "initiatives/README",
    "eval-execution-harness",
    "docs/plans/",
    "docs/prompts/",
    "d7y-eval-phase0",
    "sk-ant-",
    "machineID",
    "userID",
)
SECRET_VALUE_MARKERS = ("sk-canary-d7y",)

# Installer-generated identity paths that the retained agent image must not keep.
AGENT_IDENTITY_PATHS = ("/home/agent/.claude", "/home/agent/.claude.json")

# Scan decision statuses. Anything other than "clean" fails the gate.
STATUS_CLEAN = "clean"
STATUS_DIRTY = "dirty"
STATUS_COMMAND_FAILURE = "command_failure"


def _run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess:
    """Run a command, decoding bytes leniently so binary output never aborts us."""
    proc = subprocess.run(cmd, capture_output=True, **kwargs)  # type: ignore[arg-type]
    return subprocess.CompletedProcess(
        args=cmd,
        returncode=proc.returncode,
        stdout=proc.stdout.decode("utf-8", errors="replace") if proc.stdout else "",
        stderr=proc.stderr.decode("utf-8", errors="replace") if proc.stderr else "",
    )


def _stderr_tail(text: str, lines: int = 5, full_token: str | None = None) -> list[str]:
    """Return the last few non-empty stderr lines, redacted of the live canary token.

    If ``full_token`` is provided, redact the complete token including its random
    suffix. Otherwise redact only the static marker prefix.
    """
    tail: list[str] = []
    for line in text.strip().splitlines()[-lines:]:
        # Full redaction if we have the complete canary token
        if full_token and full_token in line:
            line = line.replace(full_token, "<redacted-canary-token>")
        else:
            # Fall back to prefix-only redaction
            for marker in SECRET_VALUE_MARKERS:
                line = line.replace(marker, "<redacted-canary-token>")
        if line.strip():
            tail.append(line.strip())
    return tail


def inspect_env(image: str) -> list[str]:
    proc = _run(["docker", "image", "inspect", image, "--format", "{{json .Config.Env}}"])
    if proc.returncode != 0:
        raise RuntimeError(f"docker inspect failed for {image}: {proc.stderr.strip()}")
    env_json = proc.stdout.strip()
    if not env_json:
        return []
    try:
        env = json.loads(env_json)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"docker inspect returned malformed JSON for {image}: {exc}") from exc
    if env is None:
        return []
    if not isinstance(env, list) or not all(isinstance(item, str) for item in env):
        raise RuntimeError(f"docker inspect returned invalid environment data for {image}")
    return env


PROTOCOL_SECTIONS = ("FILES", "CONTENT", "IDENTITY", "FIND_EXIT", "GREP_EXIT")


def _parse_protocol(text: str) -> dict:
    """Parse the scanner protocol, rejecting incomplete or ambiguous output."""
    lines = text.splitlines()
    counts = {name: lines.count(name) for name in PROTOCOL_SECTIONS}
    invalid_counts = [f"{name}={counts[name]}" for name in PROTOCOL_SECTIONS if counts[name] != 1]
    if invalid_counts:
        raise ValueError("protocol sections must appear exactly once: " + ", ".join(invalid_counts))

    indexes = [lines.index(name) for name in PROTOCOL_SECTIONS]
    if indexes != sorted(indexes):
        raise ValueError("protocol sections are out of order")
    if any(line.strip() for line in lines[:indexes[0]]):
        raise ValueError("unexpected output before FILES section")

    values: dict[str, list[str]] = {}
    for position, name in enumerate(PROTOCOL_SECTIONS):
        start = indexes[position] + 1
        end = indexes[position + 1] if position + 1 < len(indexes) else len(lines)
        values[name] = [line.strip() for line in lines[start:end] if line.strip()]

    if values["IDENTITY"] not in (["present"], ["absent"]):
        raise ValueError("IDENTITY must contain exactly one value: present or absent")

    exits: dict[str, int] = {}
    for name in ("FIND_EXIT", "GREP_EXIT"):
        if len(values[name]) != 1:
            raise ValueError(f"{name} must contain exactly one integer")
        try:
            exits[name] = int(values[name][0])
        except ValueError as exc:
            raise ValueError(f"{name} must contain exactly one integer") from exc
        if exits[name] < 0:
            raise ValueError(f"{name} must be non-negative")

    return {
        "files": values["FILES"],
        "content": values["CONTENT"],
        "identity_present": values["IDENTITY"] == ["present"],
        "find_exit": exits["FIND_EXIT"],
        "grep_exit": exits["GREP_EXIT"],
    }


def _env_key(entry: str) -> str:
    """Return only an environment key so reports never echo credential values."""
    return entry.split("=", 1)[0]


def scan_image(image: str) -> dict:
    """Scan a built image's filesystem and configured env for forbidden material.

    Fails closed: any failure to execute the scan (non-zero `docker run`, a dead
    daemon, or an unreadable image config) sets ``scan_command_failed`` so the
    caller can never treat a failed inspection as absence evidence.
    """
    find_expr = " -o ".join(f"-name '{name}'" for name in FORBIDDEN_FILES)
    grep_expr = " ".join(f"-e '{pat}'" for pat in FORBIDDEN_CONTENT + SECRET_VALUE_MARKERS)
    identity_test = " || ".join(f"test -e '{p}'" for p in AGENT_IDENTITY_PATHS)

    # Run as root for inspection while preserving the configured runtime user.
    # Command output is staged in temporary files so no pipeline can mask the
    # evidence-producing find/grep status. Only bounded diagnostics are emitted.
    script = (
        "set -eu; "
        "scan_tmp=\"$(mktemp -d)\"; "
        "trap 'rm -rf \"$scan_tmp\"' EXIT HUP INT TERM; "
        "find_exit=0; "
        "find / -xdev \\( " + find_expr + " \\) "
        ">\"$scan_tmp/files\" 2>\"$scan_tmp/find.err\" || find_exit=$?; "
        "grep_exit=0; "
        "grep -rIl --exclude-dir=proc --exclude-dir=sys --exclude-dir=dev "
        + grep_expr + " / >\"$scan_tmp/content\" 2>\"$scan_tmp/grep.err\" || grep_exit=$?; "
        "if " + identity_test + "; then identity=present; else identity=absent; fi; "
        "printf 'FILES\\n'; sed -n '1,50p' \"$scan_tmp/files\"; "
        "printf 'CONTENT\\n'; sed -n '1,50p' \"$scan_tmp/content\"; "
        "printf 'IDENTITY\\n%s\\nFIND_EXIT\\n%s\\nGREP_EXIT\\n%s\\n' "
        "\"$identity\" \"$find_exit\" \"$grep_exit\"; "
        "if [ \"$find_exit\" -ne 0 ]; then sed -n '1,5p' \"$scan_tmp/find.err\" >&2; fi; "
        "if [ \"$grep_exit\" -gt 1 ]; then sed -n '1,5p' \"$scan_tmp/grep.err\" >&2; fi"
    )
    proc = _run(["docker", "run", "--rm", "--user", "0:0", "--entrypoint", "sh", image, "-c", script])
    scan_command_failed = proc.returncode != 0
    env_inspect_error: str | None = None
    try:
        env = inspect_env(image)
    except RuntimeError as error:
        # Without the configured env we cannot confirm cleanliness: fail closed.
        env = []
        env_inspect_error = str(error)
        scan_command_failed = True

    protocol_error: str | None = None
    parsed = {
        "files": [],
        "content": [],
        "identity_present": False,
        "find_exit": None,
        "grep_exit": None,
    }
    try:
        parsed = _parse_protocol(proc.stdout)
    except ValueError as error:
        protocol_error = str(error)
        scan_command_failed = True

    find_exit = parsed["find_exit"]
    grep_exit = parsed["grep_exit"]
    internal_traversal_failed = (
        (find_exit is not None and find_exit > 0)
        or (grep_exit is not None and grep_exit > 1)
    )
    if internal_traversal_failed:
        scan_command_failed = True

    env_secret_hits = sorted({_env_key(e) for e in env if any(m in e for m in SECRET_VALUE_MARKERS)})
    env_token_hits = sorted({
        _env_key(e)
        for e in env
        if e.startswith("ANTHROPIC_AUTH_TOKEN=") and e.split("=", 1)[1]
    })
    return {
        "image": image,
        "forbidden_files": parsed["files"],
        "forbidden_content": parsed["content"],
        "identity_state_present": parsed["identity_present"],
        "env_secret_hits": env_secret_hits,
        "env_token_value_hits": env_token_hits,
        "scan_command_failed": scan_command_failed,
        "scan_exit_code": proc.returncode,
        "scan_stderr_tail": _stderr_tail(proc.stderr) if scan_command_failed else [],
        "env_inspect_error": env_inspect_error,
        "protocol_error": protocol_error,
        "find_exit": find_exit,
        "grep_exit": grep_exit,
        "internal_traversal_failed": internal_traversal_failed,
    }


def classify_scan(result: dict) -> str:
    """Reduce a scan result to a decision status. Anything but ``clean`` fails."""
    if result.get("scan_command_failed"):
        return STATUS_COMMAND_FAILURE
    if (
        result.get("forbidden_files")
        or result.get("forbidden_content")
        or result.get("identity_state_present")
        or result.get("env_secret_hits")
        or result.get("env_token_value_hits")
    ):
        return STATUS_DIRTY
    return STATUS_CLEAN


def synthetic_secret_canary(dockerfile: Path) -> dict:
    """Rebuild the agent Dockerfile with a synthetic secret; assert it stays out.

    The secret is supplied both as a build argument and as a file in the build
    context. Because the Dockerfile never COPY/ADDs context files and never reads
    the secret arg, the resulting image must not contain the secret.

    Fails closed on any execution failure: a failed canary build, a failed scan
    of the rebuilt image, or a failed cleanup is reported with a distinct status
    and redacted diagnostics, never as ``clean``.
    """
    token = f"sk-canary-d7y-{secrets.token_hex(16)}"
    build_stderr_tail: list[str] = []
    scan_result: dict | None = None
    scan_status: str | None = None
    leaked = False
    cleanup_error: list[str] | None = None
    status = STATUS_CLEAN

    with tempfile.TemporaryDirectory(prefix="d7y-canary-") as tmp:
        ctx = Path(tmp)
        # Copy the real Dockerfile and add a secret-bearing context file the
        # Dockerfile deliberately does not reference.
        (ctx / "Dockerfile").write_text(dockerfile.read_text(encoding="utf-8"))
        (ctx / "secret-canary.env").write_text(f"ANTHROPIC_AUTH_TOKEN={token}\n")
        tag = "d7y-eval-phase0-canary:scratch"
        build = _run(
            [
                "docker", "build",
                "--build-arg", f"ANTHROPIC_AUTH_TOKEN={token}",
                "-t", tag,
                "-f", str(ctx / "Dockerfile"),
                str(ctx),
            ]
        )
        if build.returncode != 0:
            status = "build_failure"
            build_stderr_tail = _stderr_tail(build.stderr, full_token=token)
        else:
            scan_result = scan_image(tag)
            scan_status = classify_scan(scan_result)
            leaked = (
                token in " ".join(scan_result.get("forbidden_content", []))
                or bool(scan_result.get("env_secret_hits"))
                or bool(scan_result.get("env_token_value_hits"))
            )
            if scan_status == STATUS_COMMAND_FAILURE:
                status = "scan_failure"
            elif leaked:
                status = "leaked"
            elif scan_status == STATUS_DIRTY:
                status = "dirty_image"
            else:
                status = STATUS_CLEAN

        rmi = _run(["docker", "rmi", "-f", tag])
        if rmi.returncode != 0:
            cleanup_error = _stderr_tail(rmi.stderr, full_token=token)
            status = "cleanup_failure"

    return {
        "canary_token": "<redacted-canary-token>",
        "status": status,
        "build_exit_code": build.returncode,
        "build_stderr_tail": build_stderr_tail,
        "scan_status": scan_status,
        "scan_command_failed": scan_result.get("scan_command_failed") if scan_result else None,
        "leaked": leaked,
        "cleanup_error": cleanup_error,
    }


def main(argv: list[str] | None = None) -> int:
    """Scan images and (optionally) the synthetic-secret canary.

    The deterministic unit tests drive this through the module-level ``_run``
    seam (patching it with canned docker responses); production calls resolve
    ``_run`` to the real docker CLI. ``argv`` lets tests pass a fixed argument
    list instead of ``sys.argv``.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", nargs="*", default=["d7y-eval-phase0-agent:2.1.218", "d7y-eval-phase0-verifier:phase0"])
    parser.add_argument("--canary", action="store_true", help="also run the synthetic-secret rebuild canary")
    args = parser.parse_args(argv)

    report = {"images": {}, "limitation": (
        "A filesystem scan proves the searched-for forbidden material and named "
        "secret bytes are absent; it cannot exhaustively disprove unknown secret "
        "bytes without reading every byte of the image."
    )}
    failed = False
    for image in args.images:
        result = scan_image(image)
        report["images"][image] = result
        status = classify_scan(result)
        if status != STATUS_CLEAN:
            failed = True
        print(f"{status.upper()}: {image}")
        if status != STATUS_CLEAN:
            print(json.dumps(result, indent=2))

    if args.canary:
        canary = synthetic_secret_canary(AGENT_DOCKERFILE)
        report["synthetic_secret_canary"] = canary
        status = canary["status"]
        if status != STATUS_CLEAN:
            failed = True
        print(f"{status.upper()}: synthetic-secret canary")
        if status != STATUS_CLEAN:
            print(json.dumps(canary, indent=2))

    print(json.dumps(report, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
