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

# Issue #5 (Workspace consolidation): each session gets its own Python venv
# instead of every session sharing /opt/liara/runner-venv directly - lets a
# session install its own extra packages without affecting any other user's
# session. Lives as SESSION_DIR/.venv, a sibling of workspace/ (same place as
# .runs/), so it's outside the Explorer/diff/search boundary without needing
# a new exclusion rule. Created lazily on first use, guarded by code_sandbox.py's
# workspace_lock so two runs of the same session can't race this step. Not
# `set -e`-fatal: a one-time creation hiccup falls back to the shared venv
# below rather than failing every future run in this session forever.
# shellcheck source=_ensure_session_venv.sh
source "$(dirname "$0")/_ensure_session_venv.sh"

PY_VER="3.14"
if [[ "$LANGUAGE" =~ 3\.([0-9]+) ]]; then
  PY_VER="3.${BASH_REMATCH[1]}"
fi

if [ "$PY_VER" = "3.14" ]; then
  if [ -d "$(dirname "$WORKSPACE_DIR")/.venv" ]; then
    SESSION_VENV="$(dirname "$WORKSPACE_DIR")/.venv"
  else
    SESSION_VENV="$(dirname "$WORKSPACE_DIR")/.venv_3.14"
  fi
else
  SESSION_VENV="$(dirname "$WORKSPACE_DIR")/.venv_$PY_VER"
fi
ensure_session_venv "$SESSION_VENV" "$PY_VER" || true

# Resource limits - last line of defense if the caller's preexec_fn rlimits
# somehow don't apply (e.g. sudo policy strips them). CPU seconds, max
# processes (blocks fork-bombs), and per-language virtual memory: Julia
# reserves large virtual address space without using it proportionally, so it
# gets a much higher ulimit -v than Python.
ulimit -t 90
ulimit -u 32
# Per-file size cap, mirrors code_sandbox.py's RLIMIT_FSIZE preexec_fn layer
# and MAX_SESSION_FILE (100 MiB) - unit here is 512-byte blocks, not bytes:
# 104857600 bytes / 512 = 204800.
ulimit -f 204800

# Not `exec`'d (unlike before) - the interpreter's own exit code is captured
# below so a trailing chmod can still run whether it succeeded or crashed.
# `set -e` is suspended just for this one call: with it active, a nonzero
# exit from the user's script would abort run_sandboxed.sh immediately at
# this line, skipping both the exit-code capture and the chmod step below -
# exactly the common case (a script erroring out) where any partial output
# it wrote still needs to be left in a state the caller (a different OS user)
# can manage.
set +e
case "$LANGUAGE" in
  python*|py*)
    ulimit -v 1048576   # 1 GiB
    SANDBOX_SITECUSTOMIZE_DIR="$(cd "$(dirname "$0")/sandbox_sitecustomize" && pwd)"
    export PYTHONPATH="$SANDBOX_SITECUSTOMIZE_DIR:$WORKSPACE_DIR${PYTHONPATH:+:$PYTHONPATH}"
    if [ -x "$SESSION_VENV/bin/python3" ]; then
      "$SESSION_VENV/bin/python3" "$SCRIPT_PATH"
    elif [ -x "/opt/liara/runner-venvs/$PY_VER/bin/python3" ]; then
      "/opt/liara/runner-venvs/$PY_VER/bin/python3" "$SCRIPT_PATH"
    elif [ -x "/opt/liara/runner-venv/bin/python3" ]; then
      /opt/liara/runner-venv/bin/python3 "$SCRIPT_PATH"
    else
      python3 "$SCRIPT_PATH"
    fi
    CODE=$?
    ;;
  julia)
    ulimit -v 4194304   # 4 GiB - empirically tune during rollout
    julia "$SCRIPT_PATH"
    CODE=$?
    ;;
  *)
    echo "Unknown language: $LANGUAGE" >&2
    exit 1
    ;;
esac
set -e

# Workspace v1 (folders): a script's own os.makedirs()'d subfolder is owned
# by this (liara-runner) user with whatever default mode mkdir gave it, not
# world-writable like $WORKSPACE_DIR itself already was before this ran. The
# LIARA backend runs as a different, less-privileged OS user that can only
# ever chmod files it owns - so this has to happen here, as the owning user,
# not later from the backend. Best-effort: never fail the run over this.
chmod -R 777 "$WORKSPACE_DIR" 2>/dev/null || true

exit "$CODE"
