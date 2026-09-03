#!/usr/bin/env python3
"""
Preview Daemon - bridges the Workspace sandbox's isolated network namespace
so a dev server started inside it (npm run dev, python3 -m http.server, ...)
can be reached by the browser via the backend's HTTP reverse-proxy.

Why this exists: the Workspace terminal (run_sandboxed_shell.sh) execs the
user's shell under `unshare --net --map-root-user`, a brand-new network
namespace with only a loopback interface - deliberate, so arbitrary sandboxed
code has zero network access (see run_sandboxed.sh's own comments). A dev
server listening on "127.0.0.1:5173" inside that namespace is therefore not
reachable from the backend's own (host) namespace at all - not even via
"127.0.0.1", since that resolves to a *different* loopback per namespace.

This script is the ONE place that crosses that boundary, and it does exactly
one thing: relay raw TCP bytes between a normal listening socket in the HOST
namespace and 127.0.0.1:<inside_port> inside the target process's namespace,
via `nsenter --net=/proc/<pid>/ns/net`. It never touches HTTP, headers, or
paths - that all stays in ordinary, unprivileged backend code
(api/routers/workspace_preview.py), which just talks plain TCP/HTTP to the
local port this daemon exposes. Keeping the privileged surface to "relay
bytes on one validated port" (not a general shell-through) is the whole
point of splitting it out into its own root-run script instead of extending
run_sandboxed.sh's model.

Must run as root (nsenter --net requires CAP_SYS_ADMIN relative to the
target namespace's owning user namespace - the sandboxed process only "is
root" *inside its own* unshared user+net namespace via --map-root-user, that
grants it nothing on the host side). Invoked by the backend (running as an
unprivileged user) via a narrowly-scoped NOPASSWD sudoers rule pinned to
this exact script path - see the module docstring in
api/routers/workspace_preview.py for the sudoers line and the reasoning
about why args aren't (and can't be) restricted by sudoers itself, only by
this script's own validation below.

Two modes:
  start <sudo_pid> <inside_port> <local_port> <pidfile>
    <sudo_pid> is the PID of the `sudo -n -u liara-runner -- ...` monitor
    process workspace_terminal.py directly forked for this session's shell -
    sudo forks again internally to actually become liara-runner, so this
    script (running as root, with no cwd/ptrace permission barrier) walks
    that process's descendants to find the real liara-runner-owned PID and
    refuses to start if none exists (shell already exited, or sudo_pid was
    never a real sudo invocation at all - this is the guard against relaying
    into an arbitrary process's namespace just because a caller claims a
    PID). Binds 127.0.0.1:<local_port> in the *current* (host) namespace,
    writes its own PID to <pidfile>, then serves forever: each accepted
    connection spawns one `nsenter --net=... -- python3 -c <inner>` child
    that connects to 127.0.0.1:<inside_port> *inside* the target namespace
    and relays bytes between it and the accepted connection via inherited
    stdin/stdout pipes (file descriptors survive nsenter/exec - that's the
    actual namespace-crossing trick; nsenter changes what a *new* socket()
    call would join, not any FD already open in the child before it re-execs
    into the target ns). Exits on its own after IDLE_TIMEOUT_SECONDS with no
    active connections, so an abandoned preview doesn't run as root forever
    without the caller needing a separate stop call.
  stop <pidfile>
    Reads <pidfile>, checks the PID's own cmdline still shows this exact
    script in "start" mode (not just "some PID that happens to be in the
    file" - the file lives in a root-owned directory the caller can't
    tamper with, but this check costs nothing and removes any doubt), then
    SIGTERMs it.
"""
import os
import sys
import time
import signal
import socket
import subprocess
import selectors

RUNNER_USER = "liara-runner"
IDLE_TIMEOUT_SECONDS = 20 * 60  # no accepted connection in 20 min -> exit
ACCEPT_POLL_SECONDS = 1.0
RELAY_BUFSIZE = 65536

# Executed inside the target network namespace via `nsenter --net=... -- python3 -c INNER_SCRIPT <inside_port>`.
# Deliberately minimal: connect to the given port on that namespace's own
# loopback, then relay stdin<->socket<->stdout in raw bytes. No imports
# beyond the standard library the base python3 already has.
INNER_SCRIPT = """
import socket, sys, os, selectors
port = int(sys.argv[1])
s = socket.create_connection(("127.0.0.1", port), timeout=10)
s.settimeout(None)
sel = selectors.DefaultSelector()
sel.register(sys.stdin.fileno(), selectors.EVENT_READ, "in")
sel.register(s.fileno(), selectors.EVENT_READ, "sock")
while True:
    for key, _ in sel.select():
        if key.data == "in":
            data = os.read(sys.stdin.fileno(), 65536)
            if not data:
                sys.exit(0)
            s.sendall(data)
        else:
            data = s.recv(65536)
            if not data:
                sys.exit(0)
            os.write(sys.stdout.fileno(), data)
"""


def _uid_of(pid: int):
    try:
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith("Uid:"):
                    return int(line.split()[1])
    except FileNotFoundError:
        pass
    return None


def _children_of(pid: int):
    """Reads /proc/<pid>/task/*/children - lists a process's direct
    children, readable by root for any pid regardless of owning uid (unlike
    /proc/<pid>/cwd, which needs ptrace permission - see
    workspace_preview.py's module docstring for why the unprivileged
    backend can't do this walk itself)."""
    kids = set()
    try:
        for tid in os.listdir(f"/proc/{pid}/task"):
            try:
                with open(f"/proc/{pid}/task/{tid}/children") as f:
                    kids.update(int(x) for x in f.read().split())
            except FileNotFoundError:
                continue
    except FileNotFoundError:
        pass
    return kids


def _resolve_runner_pid(sudo_pid: int):
    """workspace_terminal.py only knows (and can safely, permission-wise,
    know) the PID of the `sudo -n -u liara-runner -- ...` monitor process it
    directly forked - sudo itself forks again internally to actually become
    liara-runner, and that descendant is what needs to be nsenter'd into.
    Root has no permission barrier walking the process tree to find it, so
    that resolution happens here (running as root), not in the unprivileged
    backend. BFS rather than assuming a fixed depth: sudo's own process
    tree shape isn't a contract this script should depend on. Returns the
    first liara-runner-owned descendant found, or None if the shell has
    since exited (sudo_pid dead or childless)."""
    frontier = [sudo_pid]
    seen = set()
    while frontier:
        pid = frontier.pop(0)
        if pid in seen:
            continue
        seen.add(pid)
        uid = _uid_of(pid)
        if uid is not None:
            import pwd
            try:
                if pwd.getpwuid(uid).pw_name == RUNNER_USER:
                    return pid
            except KeyError:
                pass
        frontier.extend(_children_of(pid))
    return None


def _relay_one_connection(conn: socket.socket, target_pid: int, inside_port: int):
    proc = subprocess.Popen(
        ["nsenter", f"--net=/proc/{target_pid}/ns/net", "--",
         "python3", "-c", INNER_SCRIPT, str(inside_port)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    conn.setblocking(False)
    os.set_blocking(proc.stdin.fileno(), False)
    os.set_blocking(proc.stdout.fileno(), False)

    sel = selectors.DefaultSelector()
    sel.register(conn, selectors.EVENT_READ, "conn")
    sel.register(proc.stdout, selectors.EVENT_READ, "proc")
    try:
        while proc.poll() is None:
            for key, _ in sel.select(timeout=1.0):
                if key.data == "conn":
                    try:
                        data = conn.recv(RELAY_BUFSIZE)
                    except (BlockingIOError, InterruptedError):
                        continue
                    if not data:
                        return
                    try:
                        proc.stdin.write(data)
                        proc.stdin.flush()
                    except BrokenPipeError:
                        return
                else:
                    try:
                        data = os.read(proc.stdout.fileno(), RELAY_BUFSIZE)
                    except BlockingIOError:
                        continue
                    if not data:
                        return
                    conn.sendall(data)
    finally:
        exit_code = proc.poll()
        if exit_code is not None and exit_code != 0:
            try:
                stderr_tail = proc.stderr.read()
                print(f"nsenter relay for pid {target_pid} port {inside_port} exited {exit_code}: "
                      f"{stderr_tail.decode(errors='replace') if stderr_tail else '(no stderr)'}",
                      file=sys.stderr, flush=True)
            except Exception:
                pass
        try:
            proc.kill()
            proc.wait(timeout=2)
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


def cmd_start(sudo_pid: int, inside_port: int, local_port: int, pidfile: str):
    if not (1 <= inside_port <= 65535) or not (1 <= local_port <= 65535):
        print("invalid port", file=sys.stderr)
        sys.exit(1)
    target_pid = _resolve_runner_pid(sudo_pid)
    if target_pid is None:
        print(f"refusing: no {RUNNER_USER} descendant found under sudo pid {sudo_pid} (shell exited?)", file=sys.stderr)
        sys.exit(1)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", local_port))
    server.listen(64)
    server.settimeout(ACCEPT_POLL_SECONDS)

    os.makedirs(os.path.dirname(pidfile), exist_ok=True)
    with open(pidfile, "w") as f:
        f.write(str(os.getpid()))
    os.chmod(pidfile, 0o644)

    last_activity = time.time()

    def _sigterm(_signum, _frame):
        sys.exit(0)
    signal.signal(signal.SIGTERM, _sigterm)

    print(f"preview_daemon listening on 127.0.0.1:{local_port} -> pid {target_pid} netns port {inside_port}", flush=True)
    try:
        while True:
            try:
                conn, _addr = server.accept()
            except socket.timeout:
                if time.time() - last_activity > IDLE_TIMEOUT_SECONDS:
                    print("idle timeout, exiting", flush=True)
                    return
                continue
            last_activity = time.time()
            pid = os.fork()
            if pid == 0:
                server.close()
                _relay_one_connection(conn, target_pid, inside_port)
                os._exit(0)
            else:
                conn.close()
    finally:
        try:
            os.remove(pidfile)
        except OSError:
            pass


def cmd_stop(pidfile: str):
    try:
        with open(pidfile) as f:
            pid = int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            cmdline = f.read().replace(b"\x00", b" ").decode(errors="replace")
    except FileNotFoundError:
        try:
            os.remove(pidfile)
        except OSError:
            pass
        return
    if "preview_daemon.py" not in cmdline:
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    mode = sys.argv[1]
    if mode == "start" and len(sys.argv) == 6:
        cmd_start(int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5])
    elif mode == "stop" and len(sys.argv) == 3:
        cmd_stop(sys.argv[2])
    else:
        print("usage: preview_daemon.py start <sudo_pid> <inside_port> <local_port> <pidfile>", file=sys.stderr)
        print("       preview_daemon.py stop <pidfile>", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
