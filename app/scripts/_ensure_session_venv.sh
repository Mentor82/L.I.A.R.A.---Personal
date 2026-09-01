# Shared by run_sandboxed.sh and manage_venv.sh (issue #5) - sourced as a
# bash function library, never itself sudo-invoked/whitelisted directly.
# Creates SESSION_VENV if missing and wires it up to inherit the shared
# runner-venv's packages (matplotlib etc.) without fully reinstalling them.
# Supports multi-version Pythons (3.11, 3.12, 3.13, 3.14).

ensure_session_venv() {
  local session_venv="$1"
  local py_ver="${2:-3.14}"
  local parent_dir
  parent_dir="$(dirname "$session_venv")"

  if [ -x "$session_venv/bin/python3" ]; then
    if [ "$py_ver" = "3.14" ]; then
      if [ "$session_venv" = "$parent_dir/.venv" ] && [ ! -e "$parent_dir/.venv_3.14" ]; then
        ln -sf .venv "$parent_dir/.venv_3.14" 2>/dev/null || true
      elif [ "$session_venv" = "$parent_dir/.venv_3.14" ] && [ ! -e "$parent_dir/.venv" ]; then
        ln -sf .venv_3.14 "$parent_dir/.venv" 2>/dev/null || true
      fi
    fi
    return 0
  fi

  local runner_venv="/opt/liara/runner-venvs/$py_ver"
  if [ ! -d "$runner_venv" ] || [ ! -x "$runner_venv/bin/python3" ]; then
    runner_venv="/opt/liara/runner-venv"
  fi
  if [ ! -x "$runner_venv/bin/python3" ]; then
    # Fallback to system python3 if runner-venv is not present (e.g. dev/CI)
    python3 -m venv "$session_venv" || return 1
    return 0
  fi

  "$runner_venv/bin/python3" -m venv "$session_venv" || return 1
  local runner_site
  runner_site="$("$runner_venv/bin/python3" -c 'import site; print(site.getsitepackages()[0])' 2>/dev/null)" || true
  local session_site
  session_site="$("$session_venv/bin/python3" -c 'import site; print(site.getsitepackages()[0])' 2>/dev/null)" || true
  if [ -n "$runner_site" ] && [ -n "$session_site" ] && [ -d "$session_site" ]; then
    echo "$runner_site" > "$session_site/_runner_venv.pth"
  fi
  chmod -R 777 "$session_venv" 2>/dev/null || true

  if [ "$py_ver" = "3.14" ]; then
    if [ "$session_venv" = "$parent_dir/.venv" ] && [ ! -e "$parent_dir/.venv_3.14" ]; then
      ln -sf .venv "$parent_dir/.venv_3.14" 2>/dev/null || true
    elif [ "$session_venv" = "$parent_dir/.venv_3.14" ] && [ ! -e "$parent_dir/.venv" ]; then
      ln -sf .venv_3.14 "$parent_dir/.venv" 2>/dev/null || true
    fi
  fi
}
