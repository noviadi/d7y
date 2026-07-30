#!/usr/bin/env python3
"""D7Y Harbor Phase 0 posture validation and content-digest logic.

Dependency-free standard library only. This module never calls a model, a
network, or the Docker API. It is the deterministic gate for the Phase 0
executable inputs:

- the approved non-secret API profile (`evals/harbor/profiles/claude-primary.json`);
- the Harbor execution envelope (`evals/harbor/config/execution-posture.json`);
- the `starting-initiatives` runtime payload
  (`evals/harbor/payloads/starting-initiatives.json`).

It also owns the digest logic Phase 1 consumes: the profile's redacted
configuration digest and the per-file content digests of the staged payload.

The human-approved profile values are recorded here as module constants so the
validator is itself a faithful record of what was authorized. The credential
value is external by construction: only its key name is recorded anywhere.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

HARBOR_ROOT = Path(__file__).resolve().parents[3]
HARBOR_DIR = Path(__file__).resolve().parents[1]
PROFILE_PATH = HARBOR_DIR / "profiles" / "claude-primary.json"
POSTURE_PATH = HARBOR_DIR / "config" / "execution-posture.json"
PAYLOAD_PATH = HARBOR_DIR / "payloads" / "starting-initiatives.json"

# --- Human-approved, non-secret API profile inputs (from the Phase 0 prompt) -
APPROVED_PROFILE_NAME = "claude-primary"
APPROVED_ENDPOINT = "https://api.z.ai/api/anthropic"
APPROVED_ALLOWED_HOST = "api.z.ai"
APPROVED_REQUESTED_MODEL = "claude-sonnet-5"
APPROVED_ROUTED_MODEL = "glm-4.7"
APPROVED_CREDENTIAL_KEY = "ANTHROPIC_AUTH_TOKEN"
APPROVED_RUNTIME_ENV = {
    "ANTHROPIC_BASE_URL": "https://api.z.ai/api/anthropic",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "glm-4.7",
    "API_TIMEOUT_MS": "3000000",
    "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "1000000",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
}
# Host-side defaults that must NOT be forwarded into Harbor trials.
EXCLUDED_RUNTIME_DEFAULTS = (
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
)

# --- Harbor execution envelope (Phase 0 posture) ----------------------------
APPROVED_CPUS = 2
APPROVED_MEMORY_MB = 4096
APPROVED_STORAGE_MB = 10240
APPROVED_AGENT_TIMEOUT_SEC = 600
APPROVED_VERIFIER_TIMEOUT_SEC = 120
APPROVED_BUILD_TIMEOUT_SEC = 600
APPROVED_AGENT_USER = "agent"
APPROVED_VERIFIER_USER = "verifier"

# --- Payload contract -------------------------------------------------------
# Repository paths that may be staged into the agent environment. Anything not
# in this allowlist (or a declared per-case slot) is forbidden payload input.
APPROVED_PAYLOAD_SOURCES = (
    "initiatives/README.md",
    "d7y",
    "scripts/check-initiatives.py",
    "skills/starting-initiatives/SKILL.md",
)
# Repository roots/paths that must never be staged into the agent environment.
FORBIDDEN_PAYLOAD_MARKERS = (
    "evals/",
    "evals.json",
    "docs/plans/",
    "docs/prompts/",
    ".claude/settings",
    "settings.json",
    "benchmark.json",
    "graders/",
    "/tests/",
    "expected_output",
)


class PostureError(Exception):
    """Raised when a Phase 0 input violates the approved posture."""


def canonical_json(obj: Any) -> str:
    """Stable JSON encoding used for all digests and comparisons."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_hex(path.read_bytes())


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PostureError(f"{path}: cannot read valid UTF-8 JSON: {error}") from error


def redacted_profile_digest(profile: dict[str, Any]) -> str:
    """SHA-256 over the canonical profile with the digest value nulled.

    The credential value is external and never present, so the digest covers
    only the non-secret values and key names recorded in the profile.
    """
    copy = json.loads(json.dumps(profile))
    node = copy.setdefault("redacted_digest", {})
    node["value"] = None
    return sha256_hex(canonical_json(copy).encode("utf-8"))


def validate_profile(profile: dict[str, Any], path: Path) -> list[str]:
    errors: list[str] = []
    where = str(path)

    def expect(condition: bool, message: str) -> None:
        if not condition:
            errors.append(f"{where}: {message}")

    expect(profile.get("schema_version") == 1, "schema_version must equal 1")
    expect(profile.get("profile") == APPROVED_PROFILE_NAME, f"profile must be {APPROVED_PROFILE_NAME!r}")

    route = profile.get("route", {})
    expect(route.get("kind") == "proxy", "route.kind must be 'proxy' (intentional z.ai proxy)")
    expect(route.get("provider_attestation") == "unavailable",
           "route.provider_attestation must be 'unavailable' until runtime evidence exists")
    expect(route.get("effective_model_provider") == "unavailable",
           "route.effective_model_provider must be 'unavailable' until runtime evidence exists")

    endpoint = profile.get("endpoint", {})
    expect(endpoint.get("agent_visible_url") == APPROVED_ENDPOINT,
           f"endpoint.agent_visible_url must be {APPROVED_ENDPOINT!r}")
    expect(endpoint.get("allowed_hosts") == [APPROVED_ALLOWED_HOST],
           f"endpoint.allowed_hosts must be exactly [{APPROVED_ALLOWED_HOST!r}]")

    expect(profile.get("requested_model") == APPROVED_REQUESTED_MODEL,
           f"requested_model must be {APPROVED_REQUESTED_MODEL!r}")
    expect(profile.get("expected_routed_model") == APPROVED_ROUTED_MODEL,
           f"expected_routed_model must be {APPROVED_ROUTED_MODEL!r}")

    credential = profile.get("credential", {})
    expect(credential.get("key_name") == APPROVED_CREDENTIAL_KEY,
           f"credential.key_name must be {APPROVED_CREDENTIAL_KEY!r}")
    expect(credential.get("value") == "external",
           "credential.value must be the literal 'external'; the secret is never recorded")
    handling = credential.get("handling", "")
    expect("verifier" in handling and "persisted" in handling,
           "credential.handling must forbid verifier receipt and persistence")

    runtime_env = profile.get("runtime_env", {})
    allowlist = runtime_env.get("allowlist")
    expect(isinstance(allowlist, dict), "runtime_env.allowlist must be an object")
    if isinstance(allowlist, dict):
        expect(allowlist == APPROVED_RUNTIME_ENV,
               "runtime_env.allowlist must contain exactly the approved non-secret values")
        # Defence in depth: no approved value may itself look like a secret or
        # carry an unrelated Opus/Haiku default.
        for key, value in allowlist.items():
            expect(key in APPROVED_RUNTIME_ENV, f"unexpected runtime env key {key!r}")
            expect(not str(value).startswith("sk-"), f"runtime env {key!r} must not be a secret literal")
    excluded = runtime_env.get("excluded_defaults", [])
    for default in EXCLUDED_RUNTIME_DEFAULTS:
        expect(default in excluded, f"excluded_defaults must list {default!r}")

    harbor_runtime = profile.get("harbor_runtime", {})
    expect(harbor_runtime.get("allowed_hosts") == [APPROVED_ALLOWED_HOST],
           f"harbor_runtime.allowed_hosts must be exactly [{APPROVED_ALLOWED_HOST!r}]")
    expect(harbor_runtime.get("network_mode") == "allowlist",
           "harbor_runtime.network_mode must be 'allowlist'")

    digest_node = profile.get("redacted_digest", {})
    expect(digest_node.get("algorithm") == "sha256", "redacted_digest.algorithm must be 'sha256'")
    recorded = digest_node.get("value")
    expected = redacted_profile_digest(profile)
    expect(isinstance(recorded, str) and recorded == expected,
           "redacted_digest.value must equal the recomputed redacted digest")
    expect("credential value is external" in digest_node.get("semantics", "").lower(),
           "redacted_digest.semantics must state the credential value is external")

    return errors


def validate_execution_posture(posture: dict[str, Any], path: Path) -> list[str]:
    errors: list[str] = []
    where = str(path)

    def expect(condition: bool, message: str) -> None:
        if not condition:
            errors.append(f"{where}: {message}")

    expect(posture.get("schema_version") == 1, "schema_version must equal 1")
    expect(posture.get("phase") == 0, "phase must equal 0")

    resources = posture.get("resources", {})
    expect(resources.get("cpus") == APPROVED_CPUS, f"resources.cpus must be {APPROVED_CPUS}")
    expect(resources.get("cpu_enforcement_policy") == "limit",
           "resources.cpu_enforcement_policy must be 'limit' (explicit ceiling)")
    expect(resources.get("memory_mb") == APPROVED_MEMORY_MB,
           f"resources.memory_mb must be {APPROVED_MEMORY_MB}")
    expect(resources.get("memory_enforcement_policy") == "limit",
           "resources.memory_enforcement_policy must be 'limit' (explicit ceiling)")
    expect(resources.get("storage_mb") == APPROVED_STORAGE_MB,
           f"resources.storage_mb must be {APPROVED_STORAGE_MB}")
    expect(resources.get("agent_timeout_sec") == APPROVED_AGENT_TIMEOUT_SEC,
           f"resources.agent_timeout_sec must be {APPROVED_AGENT_TIMEOUT_SEC}")
    expect(resources.get("verifier_timeout_sec") == APPROVED_VERIFIER_TIMEOUT_SEC,
           f"resources.verifier_timeout_sec must be {APPROVED_VERIFIER_TIMEOUT_SEC}")
    expect(resources.get("build_timeout_sec") == APPROVED_BUILD_TIMEOUT_SEC,
           f"resources.build_timeout_sec must be {APPROVED_BUILD_TIMEOUT_SEC}")

    storage = posture.get("storage_enforcement", {})
    expect(storage.get("declared_storage_mb") == APPROVED_STORAGE_MB,
           "storage_enforcement.declared_storage_mb must match the declared storage")
    # The decisive Phase 0 rule: storage is recorded unsupported, never simulated.
    expect(storage.get("effective_support") == "unsupported",
           "storage_enforcement.effective_support must be 'unsupported', not simulated")
    expect("XFS" in storage.get("basis", "") or "xfs" in storage.get("basis", "").lower(),
           "storage_enforcement.basis must explain the missing XFS/quota data root")

    users = posture.get("users", {})
    expect(users.get("agent") == APPROVED_AGENT_USER, f"users.agent must be {APPROVED_AGENT_USER!r}")
    expect(users.get("verifier") == APPROVED_VERIFIER_USER,
           f"users.verifier must be {APPROVED_VERIFIER_USER!r}")

    network = posture.get("network", {})
    expect(network.get("environment_baseline") == "no-network",
           "network.environment_baseline must be 'no-network'")
    agent_phase = network.get("agent_phase", {})
    expect(agent_phase.get("mode") == "allowlist", "network.agent_phase.mode must be 'allowlist'")
    expect(agent_phase.get("allowed_hosts") == [APPROVED_ALLOWED_HOST],
           f"network.agent_phase.allowed_hosts must be exactly [{APPROVED_ALLOWED_HOST!r}]")
    verifier_net = network.get("verifier", {})
    expect(verifier_net.get("mode") == "no-network", "network.verifier.mode must be 'no-network'")
    expect(verifier_net.get("environment_mode") == "separate",
           "network.verifier.environment_mode must be 'separate'")

    return errors


def _safe_repo_relative(value: str) -> bool:
    candidate = Path(value)
    return not candidate.is_absolute() and ".." not in candidate.parts and bool(candidate.parts)


def validate_payload(payload: dict[str, Any], path: Path) -> list[str]:
    errors: list[str] = []
    where = str(path)

    def expect(condition: bool, message: str) -> None:
        if not condition:
            errors.append(f"{where}: {message}")

    expect(payload.get("schema_version") == 1, "schema_version must equal 1")
    expect(payload.get("skill") == "starting-initiatives", "payload.skill must be 'starting-initiatives'")

    staged = payload.get("staged", [])
    expect(isinstance(staged, list) and staged, "staged must be a non-empty array")
    seen_sources: set[str] = set()
    for index, entry in enumerate(staged or []):
        entry_where = f"{where}.staged[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{entry_where}: entry must be an object")
            continue
        source = entry.get("source")
        destination = entry.get("destination")
        arm = entry.get("arm")
        expect(isinstance(source, str) and _safe_repo_relative(source),
               f"{entry_where}.source: must be a safe repo-relative path")
        expect(isinstance(destination, str) and _safe_repo_relative(destination),
               f"{entry_where}.destination: must be a safe workspace-relative path")
        expect(arm in ("both", "treatment"), f"{entry_where}.arm: must be 'both' or 'treatment'")

        # Forbidden material must never be staged, by marker or by path escape.
        for marker in FORBIDDEN_PAYLOAD_MARKERS:
            if isinstance(source, str) and marker in source:
                errors.append(f"{entry_where}.source: forbidden payload material ({marker!r})")

        if isinstance(source, str) and source not in seen_sources:
            seen_sources.add(source)
            repo_path = (HARBOR_ROOT / source).resolve()
            try:
                root = HARBOR_ROOT.resolve()
                repo_path.relative_to(root)
            except ValueError:
                errors.append(f"{entry_where}.source: resolves outside the repository")
                continue
            if source in APPROVED_PAYLOAD_SOURCES:
                if not repo_path.is_file():
                    errors.append(f"{entry_where}.source: approved file missing: {source}")
                elif str(entry.get("sha256")) != sha256_file(repo_path):
                    errors.append(f"{entry_where}.sha256: does not match {source}")
            else:
                errors.append(f"{entry_where}.source: not in the approved payload allowlist: {source}")

    # The fixed payload must include every approved source.
    for required in APPROVED_PAYLOAD_SOURCES:
        if required not in seen_sources:
            errors.append(f"{where}: missing required payload source {required!r}")

    return errors


def run_all() -> list[tuple[Path, list[str]]]:
    results: list[tuple[Path, list[str]]] = []
    for raw, validator in (
        (PROFILE_PATH, validate_profile),
        (POSTURE_PATH, validate_execution_posture),
        (PAYLOAD_PATH, validate_payload),
    ):
        if not raw.is_file():
            results.append((raw, [f"{raw}: required input missing"]))
            continue
        try:
            value = load_json(raw)
        except PostureError as error:
            results.append((raw, [str(error)]))
            continue
        results.append((raw, validator(value, raw)))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    failed = False
    for path, errors in run_all():
        if errors:
            failed = True
            print(f"INVALID: {path}")
            for error in errors:
                print(f"  {error}")
        else:
            print(f"VALID: {path}")
    if failed:
        return 1
    print("Phase 0 posture: all inputs valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
