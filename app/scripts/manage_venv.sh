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
SESSION_VENV="$(dirname "$WORKSPACE_DIR")/.venv"

if [ ! -x "$SESSION_VENV/bin/python3" ]; then
  /opt/liara/runner-venv/bin/python3 -m venv --system-site-packages "$SESSION_VENV"
fi

# Modest resource limits - this only ever runs pip, not arbitrary user code,
# but still shouldn't be able to fork-bomb or hang forever on a bad network.
ulimit -t 60
ulimit -u 32

case "$ACTION" in
  install)
    "$SESSION_VENV/bin/python3" -m pip install --disable-pip-version-check --no-input -- "$PACKAGE_SPEC"
    ;;
  remove)
    "$SESSION_VENV/bin/python3" -m pip uninstall --disable-pip-version-check --no-input -y -- "$PACKAGE_SPEC"
    ;;
  list)
    # --local excludes packages inherited from --system-site-packages (i.e.
    # the shared runner-venv), so this only ever reports what THIS session
    # itself added - exactly what the "📦 Pakete" UI should show.
    "$SESSION_VENV/bin/python3" -m pip list --local --format=json --disable-pip-version-check
    ;;
  version)
    "$SESSION_VENV/bin/python3" --version
    ;;
  *)
    echo "Unknown action: $ACTION" >&2
    exit 1
    ;;
esac
