#!/bin/bash
# Sandboxed code runner, invoked as the unprivileged `liara-runner` user via
# `sudo -u liara-runner` from app/services/code_sandbox.py. This is the exact
# fixed command a NOPASSWD sudoers rule grants - no shell metacharacters ever
# reach it from the caller, just a language tag and a workdir path, so the
# sudoers rule can pin this one script with no argument wildcards to reason
# about.
#
# Usage: run_sandboxed.sh <python|julia> <workdir>
# Expects <workdir>/script.py or <workdir>/script.jl to already exist.
set -euo pipefail

LANGUAGE="$1"
WORKDIR="$2"

cd "$WORKDIR"

# Resource limits - last line of defense if the caller's preexec_fn rlimits
# somehow don't apply (e.g. sudo policy strips them). CPU seconds, max
# processes (blocks fork-bombs), and per-language virtual memory: Julia
# reserves large virtual address space without using it proportionally, so it
# gets a much higher ulimit -v than Python.
ulimit -t 15
ulimit -u 32

case "$LANGUAGE" in
  python)
    ulimit -v 1048576   # 1 GiB
    exec python3 script.py
    ;;
  julia)
    ulimit -v 4194304   # 4 GiB - empirically tune during rollout
    exec julia script.jl
    ;;
  *)
    echo "Unknown language: $LANGUAGE" >&2
    exit 1
    ;;
esac
