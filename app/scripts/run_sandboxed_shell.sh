#!/bin/bash
# Sandboxed interactive shell, invoked as the unprivileged `liara-runner` user
# via `sudo -u liara-runner` from the Workspace terminal WebSocket endpoint
# (api/routers/workspace_terminal.py) - the interactive-shell counterpart to
# run_sandboxed.sh's one-shot script execution. Same fixed-command shape: no
# shell metacharacters ever reach it from the caller, just a workspace_dir -
# the sudoers NOPASSWD rule pins this exact script with no argument
# wildcards to reason about (same reasoning as run_sandboxed.sh).
#
# Usage: run_sandboxed_shell.sh <workspace_dir>
# Drops into an interactive bash shell with <workspace_dir> as cwd, the
# session's own Python venv (see _ensure_session_venv.sh) already on PATH,
# and the same network isolation as a one-shot run. Deliberately no
# CPU-time limit here (unlike run_sandboxed.sh's CPU_LIMIT_SECONDS) - an
# interactive session is expected to sit open, mostly idle, for a while;
# memory/process-count/file-size caps still apply throughout.

set -euo pipefail

WORKSPACE_DIR="$1"

# Same self-reexec-under-unshare trick as run_sandboxed.sh, for the same
# sudoers reason - see that script's own comment for the full explanation.
if [ -z "${LIARA_SANDBOX_NETNS:-}" ] && command -v unshare >/dev/null 2>&1; then
  exec env LIARA_SANDBOX_NETNS=1 unshare --net --map-root-user -- "$0" "$@"
fi

# unshare --net hands us a fresh net namespace with a loopback interface
# that exists but starts DOWN - found live 2026-09-03 while building the
# Workspace preview feature: a dev server bound fine inside the sandbox, but
# connecting to 127.0.0.1 from *any* process in the same namespace (inside
# or outside the sandbox) failed with "Network is unreachable", because
# loopback traffic itself doesn't route until `lo` is up - not specific to
# the preview bridge. --map-root-user makes us root *inside this new
# namespace only* (no host-level privilege gained), which is exactly enough
# to bring lo up ourselves. Isolation from the outside world is unaffected -
# this only makes 127.0.0.1 *within* the sandbox's own namespace usable.
ip link set dev lo up 2>/dev/null || true

cd "$WORKSPACE_DIR"

# shellcheck source=_ensure_session_venv.sh
source "$(dirname "$0")/_ensure_session_venv.sh"
SESSION_VENV="$(dirname "$WORKSPACE_DIR")/.venv"
ensure_session_venv "$SESSION_VENV" || true

# shellcheck source=_ensure_session_node_modules.sh
source "$(dirname "$0")/_ensure_session_node_modules.sh"
ensure_session_node_modules "$WORKSPACE_DIR" || true

if [ -x "$SESSION_VENV/bin/python3" ]; then
  export PATH="$SESSION_VENV/bin:$PATH"
  export VIRTUAL_ENV="$SESSION_VENV"
fi
export PYTHONPATH="$WORKSPACE_DIR${PYTHONPATH:+:$PYTHONPATH}"

# Memory/process/file-size caps mirror code_sandbox.py's one-shot limits.
# ulimit -v raised from 1 GiB to 4 GiB (matching run_sandboxed.sh's Julia
# case) after a live crash found 2026-09-04 while testing the new npm/Konva
# support: `node` itself won't even start under 1 GiB - V8 reserves a large
# virtual-address "CodeRange" region during Isolate init regardless of
# actual heap usage, and a too-tight ulimit -v aborts that reservation with
# a fatal, uncatchable OOM before any user code runs (confirmed live: fails
# under 1 GiB, succeeds under 4 GiB). This is *address space*, not real
# memory pressure - Node/Julia both need this headroom just to boot, unlike
# Python, which is why only those two need the larger number.
ulimit -v 4194304   # 4 GiB
# ulimit -u raised from 32 to 128 after a live crash found 2026-09-04 while
# testing Vite: Rolldown's Rayon thread pool sizes itself to the host's CPU
# count and, combined with Node's own libuv/V8 background threads, blew
# through 32 threads for this UID and aborted with
# ThreadPoolBuildError/EAGAIN before Vite could even start.
ulimit -u 128
ulimit -f 204800    # matches MAX_SESSION_FILE (100 MiB), in 512-byte blocks

export TERM=xterm-256color
export PS1='\[\e[36m\]liara-sandbox\[\e[0m\]:\W\$ '

exec bash --norc -i
