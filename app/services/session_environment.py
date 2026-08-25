"""
Per-session Python environment: package install/remove/list and a minimal
status check, backing issue #5's "Workspace-Umgebung verständlich machen".

A genuinely different concern from session_workspace.py's file CRUD - this
touches a session's own .venv/ (see run_sandboxed.sh) and needs network
access (installing a package), unlike every other sandboxed operation in
this app, which is why it lives in its own module with its own small,
explicitly-whitelisted privileged script (manage_venv.sh) rather than being
folded into code_sandbox.py's network-isolated execution path.
"""
import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Optional

from services.session_workspace import SESSION_FILES_DIR

logger = logging.getLogger(__name__)

RUNNER_USER = "liara-runner"
MANAGE_VENV_SCRIPT = str(Path(__file__).resolve().parent.parent / "scripts" / "manage_venv.sh")
TIMEOUT_SECONDS = 90  # pip install can be network-bound; generous but bounded

# Allowlist-by-shape, not a package-name allowlist (that would be its own
# kind of over-engineering) - a plain name, or name==version / name>=version.
# Deliberately rejects: URLs, VCS refs (git+...), "-e ." editable installs,
# any --flag (starts with "-", never matches), and anything containing shell
# metacharacters or whitespace, since none of those characters appear in the
# allowed classes below.
PACKAGE_SPEC_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]*(?:(?:==|>=)[A-Za-z0-9][A-Za-z0-9._-]*)?$"
)


def is_valid_package_spec(spec: str) -> bool:
    return bool(spec) and bool(PACKAGE_SPEC_PATTERN.match(spec.strip()))


def _workspace_dir(user_id: int, session_id: int) -> Path:
    return SESSION_FILES_DIR / str(user_id) / str(session_id) / "workspace"


def _venv_python(user_id: int, session_id: int) -> Path:
    return SESSION_FILES_DIR / str(user_id) / str(session_id) / ".venv" / "bin" / "python3"


def venv_exists(user_id: int, session_id: int) -> bool:
    return _venv_python(user_id, session_id).is_file()


def _run_manage_venv(user_id: int, session_id: int, action: str, package_spec: str = "") -> subprocess.CompletedProcess:
    workspace_dir = _workspace_dir(user_id, session_id)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    # package_spec omitted entirely (not passed as "") for list/version - the
    # script's own `${3:-}` default handles a missing 3rd arg identically.
    command = ["sudo", "-n", "-u", RUNNER_USER, "--", MANAGE_VENV_SCRIPT, str(workspace_dir), action]
    if package_spec:
        command.append(package_spec)
    return subprocess.run(
        command, capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
    )


def install_package(user_id: int, session_id: int, spec: str) -> dict:
    spec = (spec or "").strip()
    if not is_valid_package_spec(spec):
        return {"ok": False, "error": "Ungültige Paket-Angabe (nur \"name\", \"name==version\" oder \"name>=version\")."}
    try:
        result = _run_manage_venv(user_id, session_id, "install", spec)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"Installation von {spec} hat das Zeitlimit ({TIMEOUT_SECONDS}s) überschritten."}
    except Exception as e:
        logger.warning(f"session_environment: install_package failed: {e}")
        return {"ok": False, "error": f"Installation fehlgeschlagen: {e}"}
    if result.returncode != 0:
        return {"ok": False, "error": (result.stderr or result.stdout or "Installation fehlgeschlagen.")[-2000:]}
    return {"ok": True, "output": result.stdout[-2000:]}


def remove_package(user_id: int, session_id: int, name: str) -> dict:
    name = (name or "").strip()
    if not is_valid_package_spec(name):
        return {"ok": False, "error": "Ungültiger Paketname."}
    try:
        result = _run_manage_venv(user_id, session_id, "remove", name)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"Entfernen von {name} hat das Zeitlimit ({TIMEOUT_SECONDS}s) überschritten."}
    except Exception as e:
        logger.warning(f"session_environment: remove_package failed: {e}")
        return {"ok": False, "error": f"Entfernen fehlgeschlagen: {e}"}
    if result.returncode != 0:
        return {"ok": False, "error": (result.stderr or result.stdout or "Entfernen fehlgeschlagen.")[-2000:]}
    return {"ok": True, "output": result.stdout[-2000:]}


def list_packages(user_id: int, session_id: int) -> dict:
    """Session-added packages only (pip's --local already excludes anything
    inherited from the shared runner-venv via --system-site-packages)."""
    if not venv_exists(user_id, session_id):
        return {"ok": True, "packages": []}
    try:
        result = _run_manage_venv(user_id, session_id, "list")
    except Exception as e:
        return {"ok": False, "error": str(e)}
    if result.returncode != 0:
        return {"ok": False, "error": (result.stderr or "Paketliste konnte nicht gelesen werden.")[-2000:]}
    try:
        packages = json.loads(result.stdout)
    except ValueError:
        return {"ok": False, "error": "Paketliste konnte nicht gelesen werden (ungültige Ausgabe)."}
    return {"ok": True, "packages": [f"{p['name']}=={p['version']}" for p in packages]}


def get_environment_status(user_id: int, session_id: int) -> dict:
    """Minimal, on-demand status for issue #5's environment display - not a
    dashboard, just enough to answer "is there a venv, what Python, how many
    packages". A session that has never run anything yet is a normal, calm
    state ("not yet created"), not an error."""
    if not venv_exists(user_id, session_id):
        return {"exists": False}
    try:
        version_result = _run_manage_venv(user_id, session_id, "version")
        version = (version_result.stdout or version_result.stderr or "").strip() or "Python"
    except Exception:
        version = "Python"
    packages = list_packages(user_id, session_id)
    return {
        "exists": True,
        "python_version": version,
        "package_count": len(packages.get("packages", [])),
    }
