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
}
