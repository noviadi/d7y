# D7Y Harbor Phase 0 Executable Posture

This directory holds the reproducible **executable inputs** for the Harbor-native
skill-eval execution foundation described in
[`docs/plans/eval-execution-harness.md`](../../docs/plans/eval-execution-harness.md).
Phase 0 establishes posture only: the pinned Harbor invocation, local Docker
access, digest-recorded agent and verifier images, the approved non-secret API
profile, the resource/network/timeout envelope, and the `starting-initiatives`
runtime payload. It does **not** run a Harbor trial or build the smoke task,
adapter, grader, or comparison runner — those are later phases.

The machine-readable build record (versions, digests, pre-build commit, canary
results, limitations) lives in `posture.json`, written after the final image
build. The human-readable summary is appended to the governing plan.

## Layout

```text
evals/harbor/
├── README.md                         # this overview
├── posture.json                      # final build record (post-build)
├── profiles/
│   └── claude-primary.json           # approved non-secret API profile
├── config/
│   └── execution-posture.json        # Harbor resource/network/timeout envelope
├── images/
│   ├── agent/Dockerfile              # Claude Code agent image recipe
│   └── verifier/Dockerfile           # separate verifier image recipe
├── payloads/
│   └── starting-initiatives.json     # runtime payload manifest
└── scripts/
    ├── posture.py                    # profile/posture/payload validator + digests
    ├── test_posture.py               # focused parser/digest tests
    ├── scan_image.py                 # image canary + synthetic-secret scanner (fails closed)
    └── test_scan_image.py            # scanner fail-closed tests (no Docker daemon)
```

## Inputs

- **Profile** (`profiles/claude-primary.json`) — the approved, non-secret
  `claude-primary` API profile: requested model `claude-sonnet-5`, intentional
  z.ai proxy endpoint `https://api.z.ai/api/anthropic`, exact allowed host
  `api.z.ai`, the allowlisted runtime env key names and values, the credential
  **key name** (`ANTHROPIC_AUTH_TOKEN`, value external), and a redacted SHA-256
  configuration digest. No credential value is ever recorded.
- **Execution envelope** (`config/execution-posture.json`) — 2 CPUs (limit), 4096
  MiB memory (limit), 10240 MiB declared storage, 600 s agent timeout, 120 s
  verifier timeout, non-root `agent`/`verifier` users, `no-network` environment
  baseline, `allowlist`-to-`api.z.ai` agent phase, and a `separate` no-network
  verifier. Local-Docker writable-layer storage enforcement is `unsupported`.
- **Payload** (`payloads/starting-initiatives.json`) — the exact files staged into
  a trial, each with a content SHA-256: `initiatives/README.md`, `d7y`,
  `scripts/check-initiatives.py` (both arms), and `skills/starting-initiatives/SKILL.md`
  (treatment only). It explicitly excludes eval definitions, expected outcomes,
  graders, benchmarks, plans, prompts, source checkout, host settings, and
  credentials.

## Images

Both images are built from a digest-pinned `python:3.12-slim` base with a build
context of only their Dockerfile directory (`.dockerignore` excludes everything
else), so no repository source is sent to the daemon.

- **Agent** (`images/agent/Dockerfile`) — installs the pinned Claude Code native
  build via the checksum-verified official installer and the shell/process tools
  Harbor's claude-code adapter needs (`curl`, `procps`). The recorded linux-x64
  binary SHA-256 is an explicit build input (`CLAUDE_CODE_BINARY_SHA256`) and is
  verified against the installed binary during the build, independent of the
  installer's manifest check. After all version checks, the installer-generated
  identity state (`~/.claude/` and `~/.claude.json`, carrying generated
  machine/user IDs) is removed and asserted absent. Harbor detects
  `claude --version` matches the requested version and skips runtime install.
- **Verifier** (`images/verifier/Dockerfile`) — the separate, no-network verifier
  posture: a clean `python3` + `bash` base as a non-root `verifier` user, with no
  case-specific graders (Phase 0 posture only).

Build (resources prefixed `d7y-eval-phase0-` per the handoff envelope):

```sh
docker build -t d7y-eval-phase0-agent:2.1.218  -f evals/harbor/images/agent/Dockerfile    evals/harbor/images/agent
docker build -t d7y-eval-phase0-verifier:phase0 -f evals/harbor/images/verifier/Dockerfile evals/harbor/images/verifier
```

## Validate and scan

```sh
python3 evals/harbor/scripts/posture.py             # validate profile, envelope, payload + digests
python3 evals/harbor/scripts/test_posture.py        # focused parser/digest tests (26)
python3 evals/harbor/scripts/test_scan_image.py     # scanner fail-closed tests (14), no Docker daemon
python3 evals/harbor/scripts/scan_image.py --canary # image canary + synthetic-secret scan (fails closed)
```

The scanner **fails closed**: a scan, canary build, canary scan, or cleanup that
cannot execute is reported as a distinct command failure with redacted
diagnostics and a non-zero exit — never `CLEAN` — so a missing image, dead
daemon, or Docker exit code such as 125 can never become absence evidence.

## Reproducibility

"Reproducible" here means **pinned content inputs plus a recorded, verifiable
retained image identity**, not byte-for-byte reproducibility across rebuilds:

- the base image is pinned by amd64 manifest digest, the Claude Code version by
  `ARG`, the installer bootstrap by SHA-256, and the installed binary by the
  recorded SHA-256 (enforced during the build);
- an independent `--no-cache` rebuild does **not** yield a stable image digest —
  each `RUN` layer is stamped with a build-time timestamp, so two independent
  builds always differ in layer history (demonstrated: the unchanged verifier
  recipe rebuilt no-cache produced a different digest);
- Debian package resolution is **not** snapshot-pinned (`apt-get update`
  resolves the current trixie set at build time);
- a cache-backed rebuild is therefore not independent reproducibility and is not
  used as proof;
- any future rebuild that yields a different digest must be rescanned (real
  scanner + canary, both fail-closed) and re-recorded before use.

## Invariants

- No source checkout, host settings, eval definitions, expected outcomes,
  graders, benchmark material, generated identity state, or credentials are
  baked into either image. The agent image's installer-generated `~/.claude/`
  and `~/.claude.json` are removed after the version checks and asserted absent.
- Credential values are external; only the key name is recorded anywhere.
- Harbor-managed writable-layer storage enforcement is recorded `unsupported`,
  not simulated; the declared `storage_mb` is task metadata only.
- Effective model/provider remain runtime evidence, recorded when the endpoint
  exposes them and otherwise `unavailable` — not assumed from this profile.
