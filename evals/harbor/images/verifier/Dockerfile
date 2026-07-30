# syntax=docker/dockerfile:1
#
# D7Y eval verifier image (Harbor separate verifier, Phase 0 posture).
#
# Purpose: the no-network grading environment for a separate Harbor verifier
# ([verifier].environment_mode = "separate"). It carries only the interpreter
# the public, dependency-free D7Y initiative checker needs (python3 + bash). It
# is built from the same digest-pinned base as the agent image so both arms of a
# comparison share a common, reproducible foundation.
#
# Phase 0 establishes posture only: no case-specific private graders, expected
# outcomes, assertions, eval definitions, or benchmark material are baked in.
# Phase 1 stages the public checker and the verifier test script into the
# separate-verifier tests/ directory at task build time; the image itself stays
# free of D7Y source, settings, and credentials. The build context is this
# directory only (see .dockerignore).

ARG BASE_IMAGE=python:3.12-slim@sha256:cab2dbf575e971934a81e4622f5aba17aa7929719bd7e31033a3a83b97fd0464
FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1

# Non-root verifier user, matching the declared [verifier].user = "verifier".
# Distinct uid from the agent so the two environments are never conflated.
RUN groupadd --system --gid 1001 verifier \
 && useradd --uid 1001 --gid 1001 --create-home --shell /bin/bash verifier

USER verifier
ENV HOME=/home/verifier
ENV PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Posture gate: the public D7Y checker is dependency-free stdlib Python, so the
# base interpreter is all that is required. No network packages, no graders.
RUN python3 --version && command -v bash
