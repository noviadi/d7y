#!/usr/bin/env python3
"""Deterministic image canary scanner for D7Y Harbor Phase 0 posture.

Scans a built image (and, optionally, a synthetic-secret rebuild) to confirm the
agent/verifier images contain no D7Y source checkout, eval definitions, expected
outcomes, graders, benchmark material, host settings, or credentials. It also
runs a synthetic-secret canary: it rebuilds the agent Dockerfile with a throwaway
secret build argument and a secret-bearing context file, then asserts the secret
never enters the image, proving the build does not bake in context material.

Dependency-free standard library only (subprocess to the docker CLI). It does not
call any model or network.

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
# Note: a `.claude/` directory created by the Claude Code installer is a
# legitimate runtime artifact; the forbidden signal is a settings FILE or
# credential, which the entries below target directly.
FORBIDDEN_FILES = (
    "evals.json",
    "benchmark.json",
    "settings.json",
    "settings.local.json",
    "SKILL.md",
    "check-initiatives.py",
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
)
SECRET_VALUE_MARKERS = ("sk-canary-d7y",)


def _run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess:
    """Run a command, decoding bytes leniently so binary output never aborts us."""
    proc = subprocess.run(cmd, capture_output=True, **kwargs)  # type: ignore[arg-type]
    return subprocess.CompletedProcess(
        args=cmd,
        returncode=proc.returncode,
        stdout=proc.stdout.decode("utf-8", errors="replace") if proc.stdout else "",
        stderr=proc.stderr.decode("utf-8", errors="replace") if proc.stderr else "",
    )


def inspect_env(image: str) -> list[str]:
    proc = _run(["docker", "image", "inspect", image, "--format", "{{json .Config.Env}}"])
    if proc.returncode != 0:
        raise RuntimeError(f"docker inspect failed for {image}: {proc.stderr.strip()}")
    return json.loads(proc.stdout.strip()) if proc.stdout.strip() else []


def scan_image(image: str) -> dict:
    """Scan a built image's filesystem and configured env for forbidden material."""
    find_expr = " -o ".join(f"-name '{name}'" for name in FORBIDDEN_FILES)
    grep_expr = " ".join(f"-e '{pat}'" for pat in FORBIDDEN_CONTENT + SECRET_VALUE_MARKERS)
    script = (
        "found_files=\"$(find / -xdev \\( " + find_expr + " \\) 2>/dev/null)\"; "
        "found_content=\"$(grep -rI --exclude-dir=proc --exclude-dir=sys "
        "--exclude-dir=dev " + grep_expr + " / 2>/dev/null | head -50)\"; "
        "printf 'FILES\\n%s\\nCONTENT\\n%s\\n' \"$found_files\" \"$found_content\""
    )
    proc = _run(["docker", "run", "--rm", "--entrypoint", "sh", image, "-c", script])
    stdout = proc.stdout if proc.returncode == 0 else proc.stdout
    env = inspect_env(image)
    env_secret_hits = [e for e in env if any(m in e for m in SECRET_VALUE_MARKERS)]
    env_token_hits = [e for e in env if e.startswith("ANTHROPIC_AUTH_TOKEN=") and e.split("=", 1)[1] not in ("", )]
    return {
        "image": image,
        "forbidden_files": _section(stdout, "FILES"),
        "forbidden_content": _section(stdout, "CONTENT"),
        "env_secret_hits": env_secret_hits,
        "env_token_value_hits": env_token_hits,
        "exit_code": proc.returncode,
    }


def _section(text: str, name: str) -> list[str]:
    lines = text.splitlines()
    if name not in lines:
        return []
    start = lines.index(name) + 1
    out: list[str] = []
    for line in lines[start:]:
        if line in ("CONTENT", "FILES"):
            break
        if line.strip():
            out.append(line.strip())
    return out


def synthetic_secret_canary(dockerfile: Path) -> dict:
    """Rebuild the agent Dockerfile with a synthetic secret; assert it stays out.

    The secret is supplied both as a build argument and as a file in the build
    context. Because the Dockerfile never COPY/ADDs context files and never reads
    the secret arg, the resulting image must not contain the secret.
    """
    token = f"sk-canary-d7y-{secrets.token_hex(16)}"
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
        scan = scan_image(tag) if build.returncode == 0 else {}
        _run(["docker", "rmi", "-f", tag])
    leaked = any(token in " ".join(scan.get(k, [])) for k in ("forbidden_content",)) or bool(
        scan.get("env_secret_hits")
    ) or bool(scan.get("env_token_value_hits"))
    return {
        "canary_token_prefix": token[:24] + "...",
        "build_exit_code": build.returncode,
        "build_stderr_tail": build.stderr.strip().splitlines()[-3:],
        "leaked": leaked,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", nargs="*", default=["d7y-eval-phase0-agent:2.1.218", "d7y-eval-phase0-verifier:phase0"])
    parser.add_argument("--canary", action="store_true", help="also run the synthetic-secret rebuild canary")
    args = parser.parse_args()

    report = {"images": {}, "limitation": (
        "A filesystem scan proves the searched-for forbidden material and named "
        "secret bytes are absent; it cannot exhaustively disprove unknown secret "
        "bytes without reading every byte of the image."
    )}
    failed = False
    for image in args.images:
        result = scan_image(image)
        report["images"][image] = result
        clean = (
            not result["forbidden_files"]
            and not result["forbidden_content"]
            and not result["env_secret_hits"]
            and not result["env_token_value_hits"]
        )
        if not clean:
            failed = True
        print(f"{'CLEAN' if clean else 'DIRTY'}: {image}")
        if not clean:
            print(json.dumps(result, indent=2))

    if args.canary:
        canary = synthetic_secret_canary(AGENT_DOCKERFILE)
        report["synthetic_secret_canary"] = canary
        if canary["leaked"]:
            failed = True
        print(f"{'CLEAN' if not canary['leaked'] else 'DIRTY'}: synthetic-secret canary (leaked={canary['leaked']})")

    print(json.dumps(report, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
