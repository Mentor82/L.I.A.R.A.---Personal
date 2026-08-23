#!/bin/bash
# Sandboxed code runner, invoked as the unprivileged `liara-runner` user via
# `sudo -u liara-runner` from app/services/code_sandbox.py. This is the exact
# fixed command a NOPASSWD sudoers rule grants - no shell metacharacters ever
# reach it from the caller, just a language tag, a workspace dir, and a
# script path, so the sudoers rule can pin this one script with no argument
# wildcards to reason about.
#
# Usage: run_sandboxed.sh <python|julia> <workspace_dir> <script_path>
# Runs with <workspace_dir> as cwd (so relative output paths land there) but
# executes <script_path> directly (the LLM's code lives under .runs/{run_id}/,
# separate from the workspace it's allowed to write into).
set -euo pipefail

LANGUAGE="$1"
WORKSPACE_DIR="$2"
SCRIPT_PATH="$3"

# Network isolation has to happen *inside* this script, not by wrapping the
# sudo call in `unshare` from the Python caller: sudo's NOPASSWD rule
# whitelists this exact script as the command it execs - if the caller instead
# execs `unshare ... -- run_sandboxed.sh`, the command sudo checks against the
# sudoers rule is `unshare`, which never matches, and sudo demands a password.
# So: self-reexec once under a fresh net+user namespace, marked by an env var
# to avoid unshare'ing recursively forever.
if [ -z "${LIARA_SANDBOX_NETNS:-}" ] && command -v unshare >/dev/null 2>&1; then
  exec env LIARA_SANDBOX_NETNS=1 unshare --net --map-root-user -- "$0" "$@"
fi

cd "$WORKSPACE_DIR"

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
    exec python3 "$SCRIPT_PATH"
    ;;
  julia)
    ulimit -v 4194304   # 4 GiB - empirically tune during rollout
    exec julia "$SCRIPT_PATH"
    ;;
  *)
    echo "Unknown language: $LANGUAGE" >&2
    exit 1
    ;;
esac
