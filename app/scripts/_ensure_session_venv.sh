# Shared by run_sandboxed.sh and manage_venv.sh (issue #5) - sourced as a
# bash function library, never itself sudo-invoked/whitelisted directly.
# Creates SESSION_VENV if missing and wires it up to inherit the shared
# runner-venv's packages (matplotlib etc.) without fully reinstalling them.
#
# `python -m venv --system-site-packages` does NOT achieve that inheritance
# here - confirmed empirically on the live server. CPython's venv module
# resolves "system site packages" against whatever the CREATING interpreter's
# own pyvenv.cfg declares as its "home" (the ORIGINAL base Python
# installation, e.g. /usr/bin), not against the immediately-enclosing venv's
# own site-packages - so a venv created from runner-venv's interpreter with
# that flag ends up pointing at the bare system Python, never at
# runner-venv's site-packages where matplotlib etc. actually live.
#
# A .pth file is the standard, reliable fix instead: any *.pth file found in
# a venv's site-packages directory is read by Python's site module at
# startup, and each line in it is appended to sys.path as an extra search
# location - this is just an additional search path, independent of any
# venv/base-prefix relationship, so it works regardless of the quirk above.
# The session's own site-packages (where its own pip installs land) is
# already on sys.path ahead of any .pth-appended directory, so a
# session-specific install correctly shadows a same-named package inherited
# from runner-venv.
ensure_session_venv() {
  local session_venv="$1"
  if [ -x "$session_venv/bin/python3" ]; then
    return 0
  fi
  /opt/liara/runner-venv/bin/python3 -m venv "$session_venv" || return 1
  local runner_site
  runner_site="$(/opt/liara/runner-venv/bin/python3 -c 'import site; print(site.getsitepackages()[0])')" || return 1
  local session_site
  session_site="$("$session_venv/bin/python3" -c 'import site; print(site.getsitepackages()[0])')" || return 1
  echo "$runner_site" > "$session_site/_runner_venv.pth"
  # The venv's own top-level dir is already 0o777 (code_sandbox.py/
  # session_environment.py pre-create it as the backend's own user for
  # exactly this reason), but everything venv/pip just created INSIDE it
  # belongs to liara-runner with its own default (often 0o755) permissions -
  # same reasoning as run_sandboxed.sh's trailing workspace_dir chmod: the
  # backend, a different OS user, can only ever chmod paths it owns, so this
  # has to happen here, as liara-runner, right after creation, or a later
  # session deletion's recursive rmtree (running as the backend) would fail
  # partway through this same tree. Best-effort, never fails the run over it.
  chmod -R 777 "$session_venv" 2>/dev/null || true
}
