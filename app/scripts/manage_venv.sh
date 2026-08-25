#!/bin/bash
# Session-venv package management, invoked as the unprivileged `liara-runner`
# user via `sudo -u liara-runner` from app/services/session_environment.py -
# the same pattern as run_sandboxed.sh: a NOPASSWD sudoers rule whitelists
# this exact script path, with a fixed positional-argument shape. Every
# value (workspace_dir, action, package_spec) is already validated Python-
# side (action against a fixed enum, package_spec against a strict
# name[==|>=]version regex, see session_environment.py's PACKAGE_SPEC_PATTERN)
# before this is ever invoked, so nothing here re-parses untrusted input.
#
# Usage: manage_venv.sh <workspace_dir> <install|remove|list|version> [package_spec]
#
# Unlike run_sandboxed.sh, this deliberately does NOT run under `unshare
# --net`: installing a package needs real network access to reach PyPI - the
# one intentional exception to this sandbox's otherwise network-isolated
# execution model (see code_sandbox.py's docstring). Regular script
# execution is completely unaffected by this script existing.
set -euo pipefail

WORKSPACE_DIR="$1"
ACTION="$2"
PACKAGE_SPEC="${3:-}"

# Same sibling-of-workspace/ location run_sandboxed.sh uses and creates -
# reused here (created on first package install/remove for a session that
# has never run any code yet), not a second, separate venv concept.
# shellcheck source=_ensure_session_venv.sh
source "$(dirname "$0")/_ensure_session_venv.sh"
SESSION_VENV="$(dirname "$WORKSPACE_DIR")/.venv"
ensure_session_venv "$SESSION_VENV"

# Modest resource limits - this only ever runs pip, not arbitrary user code,
# but still shouldn't be able to fork-bomb or hang forever on a bad network.
ulimit -t 60
ulimit -u 32

# Not `set -e`-fatal for install/remove specifically: the trailing chmod
# below must still run (liara-runner just created new, non-world-writable
# files pip installed) even when pip itself fails, same reasoning as
# run_sandboxed.sh's own suspend-errexit-for-the-run block.
set +e
case "$ACTION" in
  install)
    "$SESSION_VENV/bin/python3" -m pip install --disable-pip-version-check --no-input -- "$PACKAGE_SPEC"
    CODE=$?
    ;;
  remove)
    "$SESSION_VENV/bin/python3" -m pip uninstall --disable-pip-version-check --no-input -y -- "$PACKAGE_SPEC"
    CODE=$?
    ;;
  list)
    # --local restricts to packages actually installed under this venv's own
    # site-packages, excluding anything reachable only via the _runner_venv.pth
    # sys.path addition (ensure_session_venv) - so this only ever reports what
    # THIS session itself added, exactly what the "📦 Pakete" UI should show.
    "$SESSION_VENV/bin/python3" -m pip list --local --format=json --disable-pip-version-check
    CODE=$?
    ;;
  version)
    "$SESSION_VENV/bin/python3" --version
    CODE=$?
    ;;
  *)
    echo "Unknown action: $ACTION" >&2
    exit 1
    ;;
esac
set -e

# Same reasoning as ensure_session_venv's own trailing chmod: an install/
# remove just added or removed liara-runner-owned files with their own
# default permissions - keep the whole tree world-writable so a later
# session deletion (rmtree, running as the backend) can still clean it up.
# Only meaningful for install/remove; harmless no-op cost for list/version.
chmod -R 777 "$SESSION_VENV" 2>/dev/null || true

exit "$CODE"
