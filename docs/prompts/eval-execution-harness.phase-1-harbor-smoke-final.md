---
status: committed
plan: docs/plans/eval-execution-harness.md
execution: phase-1-harbor-smoke-final
executor: claude-code
branch: work/eval-harness-smoke-final
worktree: /home/noviadi/Developments/discovery/d7y-worktrees/eval-harness-smoke-final
permissionProfile: implementation-commit
commit: allowed
---

# Final Phase 1 implementation handoff

Implement only Phase 1 of `docs/plans/eval-execution-harness.md` in this fresh
worktree. Two delegated drafts were rejected for invalid Harbor schemas and
false completion. This is the final review cycle: do not improvise a wrapper or
claim success without real Harbor trial output.

Use Harbor 0.20.0 `trial start -p <task-dir> -a oracle` and the standard task
layout. Do not use `harbor exec` or `harbor job start`. The installed parser
model is authoritative. A minimal valid `task.toml` has this shape (extend it
only with fields from that model):

```toml
schema_version = "1.3"
artifacts = ["/logs/artifacts/*"]

[task]
name = "d7y/phase1-smoke"
description = "Synthetic Phase 1 Harbor Oracle smoke"

[environment]
docker_image = "d7y-eval-phase0-agent:2.1.218"
os = "linux"
network_mode = "no-network"
cpus = 2
memory_mb = 4096
storage_mb = 10240

[agent]
timeout_sec = 600
network_mode = "allowlist"
allowed_hosts = ["api.z.ai"]
user = "agent"

[verifier]
timeout_sec = 120
environment_mode = "separate"
user = "verifier"

[verifier.environment]
docker_image = "d7y-eval-phase0-verifier:phase0"
os = "linux"
network_mode = "no-network"
```

Validate this file with Harbor before adding other fields. Use the actual
standard paths: `instruction.md`, `solution/solve.sh`, `tests/test.sh`, agent
`/solution`, verifier `/tests`, and `/logs/{agent,verifier,artifacts}`. The
Oracle solution must read a synthetic input staged under the task contract,
write declared artifacts under `/logs/artifacts`, report user/workdir and
network result, and exit zero for the positive case. The separate verifier
must validate only transferred artifacts and always overwrite
`/logs/verifier/reward.txt`; no private checker material may be in the agent
image or task input.

Use exactly the recorded Phase 0 profile, envelope, images and payload
contract. Prove no checkout, host home, Claude settings, or Docker socket is
visible. Run exactly five real Harbor trials: positive, missing artifact,
nonzero Oracle exit, timeout, and denied network. Preserve exact trial IDs and
logs, diagnostics, resource/timeout/network/mount/verifier observations, and
map failures canonically. Record storage quota as unsupported without probing.

Use only a synthetic fake canary value where the approved contract requires
it. Scan task files, logs, trajectories, verifier output, and artifacts after
finalization; raw bytes mean `evidence_error`, quarantine, and no success
claim. Evidence must begin absent, be user-owned mode `0700`, be finalized with
absolute path/inventory/SHA-256 hashes, and remain outside Git. Clean Docker
resources with `d7y-eval-phase1-` prefixes.

Before trials, commit executable task/verifier inputs and record that commit in
every trial. Do not edit source after the first trial. Only modify
`evals/harbor/`, `DEVELOPMENT.md`, the Phase 1 feedback section of the plan,
and the required evidence directory. Run focused tests, `python3
evals/validate_skill_evals.py`, `./d7y validate`, `git diff --check`, and
`git status --short`. Append detailed Phase 1 feedback, commit the branch, and
leave it clean. Do not modify prompts, skills, canon, other plans, or `main`;
do not rebase, merge, push, amend, force, or perform lifecycle operations.
