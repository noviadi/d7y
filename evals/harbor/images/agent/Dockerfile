# syntax=docker/dockerfile:1
#
# D7Y eval agent image (Harbor-native, Phase 0 posture).
#
# Purpose: a small, reproducible container that already contains the exact pinned
# Claude Code version plus the shell/process tools the Harbor claude-code adapter
# and the runtime-injected D7Y payload require. Because the version is pre-built,
# Harbor's claude-code adapter detects `claude --version` matches the requested
# version and does NOT install the agent at trial time.
#
# This image intentionally contains NO D7Y source checkout, eval definitions,
# expected outcomes, graders, benchmark material, host settings, or credentials.
# The agent payload (instruction, fixtures, `initiatives/README.md`, `d7y`,
# `scripts/check-initiatives.py`, and the target skill) is staged into the task
# environment by the adapter at run time, never baked into this image. The build
# context is this directory only (see .dockerignore), so no repository source is
# sent to the daemon.

# Digest-pinned base. The amd64 platform digest is recorded here so a rebuild on
# this host resolves to identical base bytes; the manifest-list digest is also
# recorded in posture.json. `python:3.12-slim` supplies python3 + bash, the only
# interpreter the dependency-free `d7y` facade and `check-initiatives.py` need.
ARG BASE_IMAGE=python:3.12-slim@sha256:cab2dbf575e971934a81e4622f5aba17aa7929719bd7e31033a3a83b97fd0464
FROM ${BASE_IMAGE}

# Claude Code version pinned by the eval profile. Harbor compares this against
# `claude --version` and skips its own install when it matches.
ARG CLAUDE_CODE_VERSION=2.1.218
# Pinned native installer. downloads.claude.ai is a reviewed bootstrap
# destination. The installer downloads the platform binary and verifies it
# against the version manifest checksum before installing, so the installed
# bytes are content-addressed by the pinned version.
ARG CLAUDE_BOOTSTRAP_URL=https://downloads.claude.ai/claude-code-releases/bootstrap.sh
ARG CLAUDE_BOOTSTRAP_SHA256=cde4f1702d3b1695f92b73d26888364e17bca476e17f0fd676484c951d36c125

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1

# Runtime shell/process tools only:
#   ca-certificates - TLS roots for the versioned download.
#   curl            - required by the native installer bootstrap.
#   procps          - ps/pgrep; Harbor's claude-code adapter relies on these for
#                     agent process-tree cleanup.
# No D7Y payload, eval, grader, or credential material is installed here.
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl procps \
 && rm -rf /var/lib/apt/lists/*

# Non-root agent user, matching the declared [agent].user = "agent". The native
# installer writes the launcher to this user's ~/.local/bin.
RUN groupadd --system --gid 1000 agent \
 && useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash agent

USER agent
ENV HOME=/home/agent
ENV PATH=/home/agent/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Fetch the pinned installer, verify its digest, install the pinned version, then
# drop the downloaded archive to keep the layer small. The installer verifies the
# platform binary against the version manifest before installing.
RUN set -euo pipefail; \
    cd "${HOME}"; \
    curl -fsSL "${CLAUDE_BOOTSTRAP_URL}" -o bootstrap.sh; \
    printf '%s  bootstrap.sh\n' "${CLAUDE_BOOTSTRAP_SHA256}" | sha256sum -c -; \
    bash bootstrap.sh "${CLAUDE_CODE_VERSION}"; \
    rm -f bootstrap.sh; \
    rm -rf "${HOME}/.claude/downloads"; \
    claude --version

# Final posture gate: the pinned agent version and required interpreters/tools
# resolve from the non-root user's environment. This proves the install without
# any model call.
RUN claude --version | grep -E '2\.1\.218' \
 && python3 --version \
 && command -v bash \
 && command -v ps \
 && command -v pgrep
