"""
Sandboxed code execution for LLM-generated Python/Julia (chat "Run" button).

Security model (see plan for the full reasoning, summarized here):
- Never shell=True - the interpreter is invoked directly, code lives in a file.
- A fresh subprocess per run, no persistent daemon - no cross-session state.
- Runs as a dedicated unprivileged `liara-runner` OS user via `sudo -n -u`,
  not the LIARA backend's own user - a real filesystem boundary, not just a
  cwd convention. Also wrapped in `unshare --net` for network isolation when
  available; if unavailable and isolation is required, execution is refused
  rather than silently running unisolated.
- resource.setrlimit in preexec_fn as an outer defense layer; the invoked
  run_sandboxed.sh script sets its own per-language ulimits too, in case sudo
  strips inherited limits.
- Hard wall-clock timeout, process-group kill on expiry (mirrors the existing
  admin-only terminal_exec_router.py mechanics).
- Output captured via tempfile and tail-capped, never subprocess.PIPE, so a
  runaway script can't exhaust this process's memory.
"""
import contextlib
import logging
import mimetypes
import os
try:
    import resource
except ImportError:
    resource = None
import shutil
import signal
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from services.session_workspace import (
    SESSION_FILES_DIR, record_file_event, MAX_SESSION_FILE, MAX_SESSION_TOTAL,
    workspace_total_size, workspace_lock, ensure_session_venv_dir,
    ensure_session_metadata_dir,
)

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 90
OUTPUT_CAP = 20000  # bytes kept per stdout/stderr (tail)
MAX_INLINE_IMAGE = 5 * 1024 * 1024  # 5 MiB

RUNNER_USER = "liara-runner"
RUNNER_SCRIPT = str(Path(__file__).resolve().parent.parent / "scripts" / "run_sandboxed.sh")
REQUIRE_NETWORK_ISOLATION = os.getenv("CODE_EXEC_REQUIRE_NETWORK_ISOLATION", "true").lower() != "false"

# CPU seconds / max child processes applied via preexec_fn, before sudo/exec -
# an outer layer in addition to run_sandboxed.sh's own `ulimit` calls. Raised
# from 15s (confirmed live: a CAD-agent script using raw OCP/OpenCascade
# bindings got SIGKILLed by this - compiled C++ geometry-kernel bindings have
# real cold-start import/link overhead well beyond a typical script).
CPU_LIMIT_SECONDS = 90
NPROC_LIMIT = 32
# Per-language virtual memory limits (bytes): Julia reserves large virtual
# address space without using it proportionally, so a Python-sized limit
# would kill it at startup/package-load.
MEMORY_LIMITS = {
    "python": 1 * 1024 * 1024 * 1024,
    "python3.14": 1 * 1024 * 1024 * 1024,
    "python3.13": 1 * 1024 * 1024 * 1024,
    "python3.12": 1 * 1024 * 1024 * 1024,
    "python3.11": 1 * 1024 * 1024 * 1024,
    "julia": 4 * 1024 * 1024 * 1024,
}

LANGUAGE_ALIASES = {
    "py": "python3.14",
    "python": "python3.14",
    "python3": "python3.14",
    "python3.14": "python3.14",
    "py314": "python3.14",
    "3.14": "python3.14",
    "python3.13": "python3.13",
    "py313": "python3.13",
    "3.13": "python3.13",
    "python3.12": "python3.12",
    "py312": "python3.12",
    "3.12": "python3.12",
    "python3.11": "python3.11",
    "py311": "python3.11",
    "3.11": "python3.11",
    "jl": "julia",
    "julia": "julia",
}

AVAILABLE_RUNTIMES = [
    {"id": "python3.14", "name": "Python 3.14 (Standard)", "version": "3.14.7", "language": "python", "default": True},
    {"id": "python3.13", "name": "Python 3.13", "version": "3.13.15", "language": "python", "default": False},
    {"id": "python3.12", "name": "Python 3.12", "version": "3.12.14", "language": "python", "default": False},
    {"id": "python3.11", "name": "Python 3.11", "version": "3.11.16", "language": "python", "default": False},
    {"id": "julia", "name": "Julia", "version": "1.x", "language": "julia", "default": False},
]

def get_interpreter_binary(normalized_lang: str) -> str:
    """Returns candidate interpreter binary for pre-flight availability check."""
    if normalized_lang.startswith("python3."):
        ver = normalized_lang.replace("python", "")
        cand = f"/opt/liara/runner-venvs/{ver}/bin/python3"
        if os.path.exists(cand):
            return cand
        cand_global = f"/opt/liara/runner-venv/bin/python3"
        if os.path.exists(cand_global):
            return cand_global
        return os.sys.executable
    elif normalized_lang.startswith("python"):
        cand_314 = "/opt/liara/runner-venvs/3.14/bin/python3"
        if os.path.exists(cand_314):
            return cand_314
        return os.sys.executable
    elif normalized_lang == "julia":
        return "julia"
    return os.sys.executable

def get_script_filename(normalized_lang: str) -> str:
    if normalized_lang.startswith("python") or normalized_lang == "python":
        return "script.py"
    return "script.jl"

def normalize_language(language: str) -> Optional[str]:
    return LANGUAGE_ALIASES.get((language or "").strip().lower())


@dataclass
class SandboxFile:
    name: str
    mime_type: str
    size: int
    status: str  # "created" | "modified"
    inline: bool = False
    inline_base64: Optional[str] = None


@dataclass
class SandboxResult:
    run_id: str
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    timed_out: bool = False
    files: List[SandboxFile] = field(default_factory=list)
    error: Optional[str] = None  # set for pre-execution failures (missing interpreter, sandbox unavailable)


def _tail(file_obj, n: int) -> str:
    file_obj.seek(0, os.SEEK_END)
    size = file_obj.tell()
    file_obj.seek(max(0, size - n))
    return file_obj.read().decode("utf-8", errors="replace")


def _snapshot(workspace_dir: Path) -> Dict[str, Tuple[int, float]]:
    """Keyed by the full relative (`/`-separated) path, not just the bare
    name, so a script that creates its own subfolder is tracked correctly -
    same path identity used everywhere else in the workspace (explorer,
    editor tabs, tool-calling). No sidecar-filename exclusion needed here
    (issue #6) - LIARA's own manifest/proposals/lock state lives in
    metadata/, a sibling of workspace_dir, so it was never reachable via
    this rglob() to begin with."""
    snapshot = {}
    if not workspace_dir.exists():
        return snapshot
    for entry in workspace_dir.rglob("*"):
        if entry.is_file() and not entry.is_symlink():
            stat = entry.stat()
            relpath = entry.relative_to(workspace_dir).as_posix()
            snapshot[relpath] = (stat.st_size, stat.st_mtime)
    return snapshot


def _diff_snapshot(
    before: Dict[str, Tuple[int, float]], workspace_dir: Path
) -> List[SandboxFile]:
    results = []
    if not workspace_dir.exists():
        return results
    for entry in workspace_dir.rglob("*"):
        # Symlinks are rejected outright, both for downloads and here - a
        # script could otherwise os.symlink() a sensitive path into its
        # workspace and have it show up as a normal "generated file".
        if entry.is_symlink() or not entry.is_file():
            continue
        relpath = entry.relative_to(workspace_dir).as_posix()
        stat = entry.stat()
        current = (stat.st_size, stat.st_mtime)
        prior = before.get(relpath)
        if prior is None:
            status = "created"
        elif prior != current:
            status = "modified"
        else:
            continue  # unchanged, not part of this run's output
        mime_type, _ = mimetypes.guess_type(entry.name)
        results.append(SandboxFile(
            name=relpath,
            mime_type=mime_type or "application/octet-stream",
            size=stat.st_size,
            status=status,
        ))
    return results


def _preexec(language: str):
    def _apply():
        if hasattr(os, "setsid"):
            os.setsid()  # own process group, so a timeout can kill the whole tree
        if resource is not None:
            try:
                resource.setrlimit(resource.RLIMIT_CPU, (CPU_LIMIT_SECONDS, CPU_LIMIT_SECONDS))
                resource.setrlimit(resource.RLIMIT_NPROC, (NPROC_LIMIT, NPROC_LIMIT))
                mem_limit = MEMORY_LIMITS[language]
                resource.setrlimit(resource.RLIMIT_AS, (mem_limit, mem_limit))
                resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_SESSION_FILE, MAX_SESSION_FILE))
            except (ValueError, OSError) as e:
                logger.warning(f"code_sandbox: preexec rlimit setup failed: {e}")
    return _apply


def _build_command(language: str, workspace_dir: Path, script_path: Path) -> List[str]:
    # Network isolation (unshare --net) happens *inside* run_sandboxed.sh, not
    # wrapped here - sudo's NOPASSWD rule whitelists that exact script as the
    # command it execs, and wrapping `unshare` around the sudo call would make
    # `unshare` the exec'd command instead, which never matches the rule.
    return ["sudo", "-n", "-u", RUNNER_USER, "--",
            RUNNER_SCRIPT, language, str(workspace_dir), str(script_path)]


def run_code(
    language: str, code: str, session_dir: Path, timeout: int = TIMEOUT_SECONDS,
    user_id: Optional[int] = None, session_id: Optional[int] = None,
) -> SandboxResult:
    """
    session_dir: the per-session root (SESSION_FILES_DIR/{user_id}/{session_id}/).
    Writes the script under session_dir/.runs/{run_id}/, executes with
    session_dir/workspace/ as cwd, and diffs that workspace before/after.

    user_id/session_id are optional only for backwards compatibility with any
    other caller - when given (the code-exec router always passes them), every
    created/modified file is recorded in the workspace manifest as
    source="code_runner" so the Workspace UI can show it was Run-generated.
    """
    run_id = str(uuid.uuid4())
    normalized = normalize_language(language)
    if not normalized:
        return SandboxResult(run_id=run_id, error=f"Nicht unterstützte Sprache: {language}")

    interpreter = get_interpreter_binary(normalized)
    if not shutil.which(interpreter) and not os.path.exists(interpreter):
        label = f"Python ({normalized})" if "python" in normalized else "Julia"
        return SandboxResult(run_id=run_id, error=f"{label} ist auf dem Server nicht installiert.")

    if not shutil.which("unshare") and REQUIRE_NETWORK_ISOLATION:
        return SandboxResult(
            run_id=run_id,
            error="Netzwerk-Isolation ist erforderlich (CODE_EXEC_REQUIRE_NETWORK_ISOLATION=true), "
                  "aber 'unshare' ist auf diesem Server nicht verfügbar. Ausführung abgelehnt."
        )

    workspace_dir = session_dir / "workspace"
    run_dir = session_dir / ".runs" / run_id
    workspace_dir.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)

    # liara-runner (a different OS user) needs execute/traverse permission on
    # every ancestor directory to reach run_dir/workspace_dir at all - relying
    # on the backend process's umask to happen to leave these traversable
    # would be fragile, so set it explicitly on the whole chain up to
    # SESSION_FILES_DIR.
    for ancestor in (SESSION_FILES_DIR, session_dir.parent, session_dir):
        try:
            os.chmod(ancestor, 0o755)
        except OSError:
            pass

    script_path = run_dir / get_script_filename(normalized)
    script_path.write_text(code, encoding="utf-8")
    # liara-runner needs to read this script - world-readable/traversable,
    # but not writable, since nothing writes back into run_dir.
    os.chmod(run_dir, 0o755)
    os.chmod(script_path, 0o644)
    # workspace_dir is where the script's own output lands, so liara-runner
    # needs write access here too. World-writable is acceptable since this
    # directory only ever contains this session's own generated content.
    os.chmod(workspace_dir, 0o777)
    # Same reasoning for .venv (issue #5) - see ensure_session_venv_dir's
    # docstring for why this can't just be liara-runner creating it itself.
    ensure_session_venv_dir(session_dir)
    # metadata/ (issue #6) - pre-created here too so a brand-new session's
    # very first run already has it at the right (0o700, backend-only)
    # permissions, same as workspace_dir/.venv above. Not strictly required
    # (record_file_event's first call would create it lazily too), but
    # matches the existing precedent of pre-creating every session
    # sub-directory up front rather than leaving it to whichever call
    # happens to touch it first.
    ensure_session_metadata_dir(session_dir)

    result = SandboxResult(run_id=run_id)

    # The whole snapshot -> execute -> diff cycle has to be one atomic section
    # per session (issue #8) - two runs racing here can snapshot/diff the same
    # workspace/ concurrently and misattribute each other's output files. An
    # asyncio.Lock in the router serializes same-worker requests but can't
    # reach across gunicorn's several worker processes; workspace_lock's
    # flock() can, since it's a real OS-level lock on a shared file. Skipped
    # entirely for the (unused-in-practice) legacy no-ids caller - nothing to
    # race with when nothing gets recorded against a session anyway.
    lock_cm = workspace_lock(user_id, session_id) if (user_id is not None and session_id is not None) else contextlib.nullcontext()
    with lock_cm:
        before = _snapshot(workspace_dir)
        command = _build_command(normalized, workspace_dir, script_path)

        with tempfile.TemporaryFile() as stdout_f, tempfile.TemporaryFile() as stderr_f:
            try:
                process = subprocess.Popen(
                    command, cwd=str(workspace_dir),
                    stdout=stdout_f, stderr=stderr_f,
                    preexec_fn=_preexec(normalized),
                )
                try:
                    process.wait(timeout=timeout)
                    result.exit_code = process.returncode
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait()
                    result.timed_out = True

                result.stdout = _tail(stdout_f, OUTPUT_CAP)
                result.stderr = _tail(stderr_f, OUTPUT_CAP)
                if result.timed_out:
                    result.stderr = (result.stderr + f"\n[Abgebrochen nach {timeout}s Timeout]")[-OUTPUT_CAP:]
                if result.exit_code == 1 and "sudo: " in result.stderr.lower():
                    result.error = (
                        "Sandbox-Ausführung fehlgeschlagen - der liara-runner-User ist vermutlich "
                        "noch nicht eingerichtet (siehe Setup-Anleitung)."
                    )
            except Exception as e:
                result.error = f"Sandbox-Fehler: {e}"

        # A script's own os.makedirs()'d subfolder is owned by liara-runner, not
        # world-writable like workspace_dir itself - the backend (a different,
        # less-privileged OS user) has no way to chmod a path it doesn't own, so
        # this can only be fixed from inside run_sandboxed.sh (which runs AS
        # liara-runner and does its own trailing `chmod -R 777` there) rather
        # than here after the fact.
        changed_files = _diff_snapshot(before, workspace_dir)

        # Workspace quota enforcement (issue #8) - RLIMIT_FSIZE above is a
        # defense-in-depth cap on any SINGLE file during the run itself, but it
        # can't know about the session's *aggregate* size across pre-existing
        # files. A manual create/write already enforces both MAX_SESSION_FILE and
        # MAX_SESSION_TOTAL; sandbox output previously bypassed both entirely
        # (only snapshotted/diffed, never size-checked). Reject the whole run's
        # output rather than partially keeping it - simpler to reason about than
        # picking which files to keep, and this is already the rare/abuse case.
        oversized = [f for f in changed_files if f.size > MAX_SESSION_FILE]
        over_total = workspace_total_size(workspace_dir) > MAX_SESSION_TOTAL
        if changed_files and (oversized or over_total):
            for f in changed_files:
                try:
                    (workspace_dir / f.name).unlink()
                except OSError:
                    pass
            reasons = []
            if oversized:
                reasons.append(f"{len(oversized)} Datei(en) über dem Limit von {MAX_SESSION_FILE // (1024 * 1024)} MiB")
            if over_total:
                reasons.append(f"Workspace-Gesamtlimit von {MAX_SESSION_TOTAL // (1024 * 1024)} MiB überschritten")
            quota_error = "Ausführung erzeugte zu große Ausgabe (" + ", ".join(reasons) + ") - alle neu erzeugten/geänderten Dateien wurden verworfen."
            result.error = f"{result.error} {quota_error}" if result.error else quota_error
            changed_files = []

        if user_id is not None and session_id is not None:
            for f in changed_files:
                record_file_event(user_id, session_id, f.name, source="code_runner", execution_id=run_id)
        inline_count = 0
        for f in changed_files:
            if f.mime_type.startswith("image/") and f.size <= MAX_INLINE_IMAGE and inline_count < 4:
                try:
                    import base64
                    data = (workspace_dir / f.name).read_bytes()
                    f.inline = True
                    f.inline_base64 = f"data:{f.mime_type};base64,{base64.b64encode(data).decode()}"
                    inline_count += 1
                except OSError:
                    pass
        result.files = changed_files

    # Retention (issue #8) - the submitted script isn't needed after
    # execution: stdout/stderr are already captured above and any output
    # file is already recorded, so clean it up immediately rather than
    # letting .runs/ accumulate hidden, unbounded storage outside the
    # Workspace's own quota. Best-effort, matches delete_session_workspace's
    # own "never block on cleanup" convention.
    try:
        shutil.rmtree(run_dir)
    except OSError:
        pass

    return result
