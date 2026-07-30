#!/usr/bin/env python3
"""Focused tests for the Phase 0 posture parser and digest logic.

Covers: canonical JSON stability, SHA-256 vectors, the redacted profile digest
(independence from the recorded value, determinism, sensitivity), and the
profile / execution-envelope / payload validators (acceptance plus the
violation branches that matter for Phase 0 safety). Stdlib unittest only.

Run: python3 evals/harbor/scripts/test_posture.py
"""

from __future__ import annotations

import copy
import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import posture  # noqa: E402


def valid_profile() -> dict:
    profile = {
        "schema_version": 1,
        "profile": posture.APPROVED_PROFILE_NAME,
        "route": {
            "kind": "proxy",
            "description": "intentional z.ai proxy",
            "provider_attestation": "unavailable",
            "effective_model_provider": "unavailable",
        },
        "endpoint": {
            "agent_visible_url": posture.APPROVED_ENDPOINT,
            "allowed_hosts": [posture.APPROVED_ALLOWED_HOST],
        },
        "requested_model": posture.APPROVED_REQUESTED_MODEL,
        "expected_routed_model": posture.APPROVED_ROUTED_MODEL,
        "credential": {
            "key_name": posture.APPROVED_CREDENTIAL_KEY,
            "value": "external",
            "handling": "opaque trial-scoped agent injection; never read, persisted, or passed to the verifier",
        },
        "runtime_env": {
            "allowlist": dict(posture.APPROVED_RUNTIME_ENV),
            "excluded_defaults": list(posture.EXCLUDED_RUNTIME_DEFAULTS),
        },
        "harbor_runtime": {
            "allowed_hosts": [posture.APPROVED_ALLOWED_HOST],
            "network_mode": "allowlist",
        },
        "redacted_digest": {
            "algorithm": "sha256",
            "value": None,
            "semantics": "SHA-256 over canonical profile with the digest value nulled; "
            "the credential value is external and excluded by construction",
        },
    }
    profile["redacted_digest"]["value"] = posture.redacted_profile_digest(profile)
    return profile


def valid_execution_posture() -> dict:
    return {
        "schema_version": 1,
        "phase": 0,
        "resources": {
            "cpus": posture.APPROVED_CPUS,
            "cpu_enforcement_policy": "limit",
            "memory_mb": posture.APPROVED_MEMORY_MB,
            "memory_enforcement_policy": "limit",
            "storage_mb": posture.APPROVED_STORAGE_MB,
            "agent_timeout_sec": posture.APPROVED_AGENT_TIMEOUT_SEC,
            "verifier_timeout_sec": posture.APPROVED_VERIFIER_TIMEOUT_SEC,
            "build_timeout_sec": posture.APPROVED_BUILD_TIMEOUT_SEC,
        },
        "storage_enforcement": {
            "declared_storage_mb": posture.APPROVED_STORAGE_MB,
            "effective_support": "unsupported",
            "basis": "local Docker overlay2/ext4 has no XFS/project-quota data root; "
            "Harbor passes storage through only on quota-capable providers",
        },
        "users": {"agent": posture.APPROVED_AGENT_USER, "verifier": posture.APPROVED_VERIFIER_USER},
        "network": {
            "environment_baseline": "no-network",
            "agent_phase": {"mode": "allowlist", "allowed_hosts": [posture.APPROVED_ALLOWED_HOST]},
            "verifier": {"mode": "no-network", "environment_mode": "separate"},
        },
    }


class TestDigestLogic(unittest.TestCase):
    def test_canonical_json_is_sorted_and_compact(self) -> None:
        encoded = posture.canonical_json({"b": 1, "a": [3, 1, 2]})
        self.assertEqual(encoded, '{"a":[3,1,2],"b":1}')

    def test_sha256_known_vector(self) -> None:
        self.assertEqual(posture.sha256_hex(b""), hashlib.sha256(b"").hexdigest())
        self.assertEqual(
            posture.sha256_hex(b"abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        )

    def test_redacted_digest_is_independent_of_recorded_value(self) -> None:
        base = valid_profile()
        different_value = copy.deepcopy(base)
        different_value["redacted_digest"]["value"] = "deadbeef"
        # The recorded value is nulled before hashing, so both compute the same.
        self.assertEqual(
            posture.redacted_profile_digest(base),
            posture.redacted_profile_digest(different_value),
        )

    def test_redacted_digest_is_deterministic_and_sensitive(self) -> None:
        profile = valid_profile()
        first = posture.redacted_profile_digest(profile)
        self.assertEqual(first, posture.redacted_profile_digest(copy.deepcopy(profile)))
        profile["requested_model"] = "claude-opus-4-8"
        self.assertNotEqual(first, posture.redacted_profile_digest(profile))

    def test_redacted_digest_excludes_credential_value(self) -> None:
        # Only key names are recorded; there is no value field to leak.
        profile = valid_profile()
        self.assertEqual(profile["credential"]["value"], "external")
        digest = posture.redacted_profile_digest(profile)
        # Mutating the key name (not the value) changes the digest.
        profile["credential"]["key_name"] = "OTHER_KEY"
        self.assertNotEqual(digest, posture.redacted_profile_digest(profile))


class TestProfileValidator(unittest.TestCase):
    def test_valid_profile_passes(self) -> None:
        self.assertEqual(posture.validate_profile(valid_profile(), Path("p")), [])

    def test_rejects_unapproved_endpoint(self) -> None:
        profile = valid_profile()
        profile["endpoint"]["agent_visible_url"] = "https://api.anthropic.com"
        self.assertTrue(posture.validate_profile(profile, Path("p")))

    def test_rejects_unapproved_host(self) -> None:
        profile = valid_profile()
        profile["endpoint"]["allowed_hosts"] = ["api.anthropic.com"]
        self.assertTrue(posture.validate_profile(profile, Path("p")))

    def test_rejects_secret_like_runtime_value(self) -> None:
        profile = valid_profile()
        allowlist = dict(profile["runtime_env"]["allowlist"])
        allowlist["ANTHROPIC_BASE_URL"] = "sk-leaked-token"
        profile["runtime_env"]["allowlist"] = allowlist
        self.assertTrue(posture.validate_profile(profile, Path("p")))

    def test_rejects_forwarded_opus_default(self) -> None:
        profile = valid_profile()
        profile["runtime_env"]["excluded_defaults"] = ["ANTHROPIC_DEFAULT_HAIKU_MODEL"]
        self.assertTrue(posture.validate_profile(profile, Path("p")))

    def test_rejects_unavailable_runtime_evidence_promoted(self) -> None:
        profile = valid_profile()
        profile["route"]["effective_model_provider"] = "z.ai"
        self.assertTrue(posture.validate_profile(profile, Path("p")))

    def test_rejects_stale_redacted_digest(self) -> None:
        profile = valid_profile()
        profile["redacted_digest"]["value"] = "0" * 64
        self.assertTrue(posture.validate_profile(profile, Path("p")))


class TestExecutionPostureValidator(unittest.TestCase):
    def test_valid_posture_passes(self) -> None:
        self.assertEqual(posture.validate_execution_posture(valid_execution_posture(), Path("p")), [])

    def test_rejects_simulated_storage(self) -> None:
        posture_data = valid_execution_posture()
        posture_data["storage_enforcement"]["effective_support"] = "simulated"
        self.assertTrue(posture.validate_execution_posture(posture_data, Path("p")))

    def test_rejects_supported_storage_claim(self) -> None:
        posture_data = valid_execution_posture()
        posture_data["storage_enforcement"]["effective_support"] = "supported"
        self.assertTrue(posture.validate_execution_posture(posture_data, Path("p")))

    def test_rejects_relaxed_cpu_policy(self) -> None:
        posture_data = valid_execution_posture()
        posture_data["resources"]["cpu_enforcement_policy"] = "auto"
        self.assertTrue(posture.validate_execution_posture(posture_data, Path("p")))

    def test_rejects_wrong_timeout(self) -> None:
        posture_data = valid_execution_posture()
        posture_data["resources"]["agent_timeout_sec"] = 1200
        self.assertTrue(posture.validate_execution_posture(posture_data, Path("p")))

    def test_rejects_public_verifier_network(self) -> None:
        posture_data = valid_execution_posture()
        posture_data["network"]["verifier"]["mode"] = "public"
        self.assertTrue(posture.validate_execution_posture(posture_data, Path("p")))

    def test_rejects_shared_verifier_environment(self) -> None:
        posture_data = valid_execution_posture()
        posture_data["network"]["verifier"]["environment_mode"] = "shared"
        self.assertTrue(posture.validate_execution_posture(posture_data, Path("p")))


class TestPayloadValidator(unittest.TestCase):
    def _valid_staged(self) -> list[dict]:
        return [
            {
                "source": source,
                "destination": source,
                "arm": "treatment" if source.startswith("skills/") else "both",
                "sha256": posture.sha256_file(posture.HARBOR_ROOT / source),
            }
            for source in posture.APPROVED_PAYLOAD_SOURCES
        ]

    def _payload(self) -> dict:
        return {"schema_version": 1, "skill": "starting-initiatives", "staged": self._valid_staged()}

    def test_valid_payload_passes(self) -> None:
        self.assertEqual(posture.validate_payload(self._payload(), Path("p")), [])

    def test_rejects_forbidden_eval_material(self) -> None:
        payload = self._payload()
        payload["staged"].append(
            {"source": "evals/runs/secret/evals.json", "destination": "x", "arm": "both", "sha256": "x"}
        )
        errors = posture.validate_payload(payload, Path("p"))
        self.assertTrue(any("forbidden payload material" in e for e in errors))

    def test_rejects_non_allowlisted_source(self) -> None:
        payload = self._payload()
        payload["staged"].append(
            {"source": "docs/plans/eval-execution-harness.md", "destination": "x", "arm": "both", "sha256": "x"}
        )
        errors = posture.validate_payload(payload, Path("p"))
        self.assertTrue(any("forbidden payload material" in e for e in errors))

    def test_rejects_wrong_content_digest(self) -> None:
        payload = self._payload()
        payload["staged"][0]["sha256"] = "0" * 64
        errors = posture.validate_payload(payload, Path("p"))
        self.assertTrue(any("does not match" in e for e in errors))

    def test_rejects_path_escape(self) -> None:
        payload = self._payload()
        payload["staged"][0]["source"] = "../etc/passwd"
        errors = posture.validate_payload(payload, Path("p"))
        self.assertTrue(errors)

    def test_rejects_missing_required_source(self) -> None:
        payload = self._payload()
        payload["staged"] = payload["staged"][1:]
        errors = posture.validate_payload(payload, Path("p"))
        self.assertTrue(any("missing required payload source" in e for e in errors))

    def test_rejects_duplicate_source(self) -> None:
        payload = self._payload()
        duplicate = copy.deepcopy(payload["staged"][0])
        payload["staged"].append(duplicate)
        errors = posture.validate_payload(payload, Path("p"))
        self.assertTrue(any("duplicate payload source" in e for e in errors))


if __name__ == "__main__":
    unittest.main(verbosity=2)
