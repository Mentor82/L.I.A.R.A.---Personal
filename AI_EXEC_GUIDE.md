# 🤖 AI Exec Guide

How AI agents (Claude, GitHub Copilot, Codex, Gemini, or anything else with
an admin JWT) can run shell commands on the Liara server programmatically,
without driving the interactive WebSocket PTY terminal.

---

## Why this exists

The admin panel already has a full interactive terminal (`terminal_pty.py`,
WebSocket + xterm.js). It's great for a human, but automating it (simulating
keystrokes, waiting for output, detecting when a command finished) is
fragile — Enter key events don't always register, focus is easy to lose, and
there's no structured way to know a command's exit code.

`terminal_exec_router.py` gives the same admin-level shell access through a
plain async JSON API instead: submit a command, get a `job_id` back
immediately, poll for the structured result. Same trust level as the PTY
terminal (admin-only) — just a cleaner shape for tooling to consume.

---

## Auth

Every request needs a Bearer token for a user with `role=admin`:

```bash
curl -s -X POST https://liara.mw-dresden.de/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"..."}'
# -> { "access_token": "...", "refresh_token": "...", "token_type": "bearer", "user": {...} }
```

Send `Authorization: Bearer <access_token>` on every call. Access tokens are
short-lived. Refresh with:

```bash
curl -s -X POST https://liara.mw-dresden.de/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<refresh_token>"}'
```

**Important:** refresh tokens are single-use/rotating — the refresh response
contains a **new** `refresh_token`. Store that one, not just the new
`access_token`, or your *next* refresh will fail with `"Refresh token
mismatch - possible security issue"` because the one you're holding was
already consumed.

---

## Endpoints

### `POST /api/admin/terminal/exec`

```json
{ "command": "git log -1 --oneline", "cwd": "frontend" }
```

- `command` (required): shell string, runs via `subprocess.Popen(..., shell=True, start_new_session=True)`
  in its own process group, so a timeout kills the whole tree it spawned, not
  just the shell itself.
- `cwd` (optional): path relative to the repo root. Must stay inside it
  (`../../etc` etc. is rejected with 400). Defaults to the repo root.

Returns immediately (the command runs in the background):

```json
{
  "job_id": "b3f1...",
  "command": "git log -1 --oneline",
  "status": "running",
  "exit_code": null,
  "stdout": "",
  "stderr": "",
  "started_at": "2026-08-20T...",
  "finished_at": null,
  "user_id": 1,
  "username": "admin"
}
```

`user_id`/`username` are whoever's token submitted the job - see **Job
ownership** below.

### `GET /api/admin/terminal/exec/{job_id}`

Poll this (every ~1s is reasonable) until `status` is no longer `"running"`:

```json
{
  "job_id": "b3f1...",
  "command": "git log -1 --oneline",
  "status": "done",
  "exit_code": 0,
  "stdout": "6b77420 Health check: stop scoring...\n",
  "stderr": "",
  "started_at": "2026-08-20T...",
  "finished_at": "2026-08-20T...",
  "user_id": 1,
  "username": "admin"
}
```

`status` is one of: `running`, `done` (exited, check `exit_code`), `error`
(the job itself failed to run, e.g. bad cwd), `timeout` (hit the 300s cap,
process group killed).

404 means the job_id is unknown or its result already expired. 403 means the
job exists but belongs to a different admin (see below). 503 means Redis
itself is unreachable - the exec system can't function without it.

---

## Limits

| | |
|---|---|
| Max runtime per command | 300s (`EXEC_TIMEOUT`), then `status: "timeout"` + whole process group killed |
| Output kept | last 20,000 bytes each of stdout/stderr (`OUTPUT_CAP`), tailed from temp files - not a RAM limit on the command itself |
| Job result lifetime | 1h in Redis (`JOB_TTL_SECONDS`), then gone (404) |
| Default cwd | repo root (`/opt/liara`) |
| Concurrency | job state lives in Redis, not in-process memory, so it works correctly across gunicorn's multiple worker processes |
| Visibility | a job is only readable by the admin who submitted it (403 otherwise) |

---

## Job ownership

Every job records `user_id`/`username` from the submitting admin's JWT.
`GET /exec/{job_id}` 403s if the requesting admin isn't the same one who
called `POST /exec` for that job. Job IDs are `uuid4` (unguessable in
practice), but this makes the access policy explicit instead of "whoever
has a valid admin token and the ID can read it."

If you're building a tool that submits a job as one identity and expects to
poll it as another, that won't work here - poll with the same token you
submitted with.

---

## Audit log

Every finished job appends one JSON line to `/var/log/liara/ai_exec_audit.log`
on the server (not exposed over the API):

```json
{"job_id": "...", "user_id": 1, "username": "admin", "command": "...", "cwd": "/opt/liara", "started_at": "...", "finished_at": "...", "status": "done", "exit_code": 0}
```

Deliberately excludes `stdout`/`stderr` (can contain secrets) and outlives
the 1h Redis TTL on the job result itself. If you need "what did admin X run
last week", this is where to look (via the WebSocket PTY terminal or SSH -
not through this API).

---

## Known caveats (read before assuming something is broken)

1. **No TTY, so plain `sudo` fails.** Any command needing `sudo` must be
   covered by a `NOPASSWD` sudoers rule (see `/etc/sudoers.d/liara-deploy` on
   the server) — `sudo` refuses to prompt for a password over a
   non-interactive pipe. If a command fails with `"a terminal is required to
   read the password"`, that's this, not a bug in the endpoint.

2. **Self-restart hazard — eliminated for the normal deploy path.**
   `update.sh` now reloads the backend instead of restarting it
   (`reload_backend.sh` → `systemctl reload liara-backend`, i.e. `SIGHUP` to
   the Gunicorn master). The master never stops listening — it starts new
   workers with the updated code and only retires the old ones once they've
   finished in-flight requests — so nginx never has a dead upstream to proxy
   to. No 502, and no cgroup-kill risk for whatever called it (a plain
   `reload` never stops the unit, so `KillMode=control-group` never
   triggers). This is now the default for any `app/*` change via
   `update.sh`.

   `restart_backend.sh` still exists for the rare case a real restart is
   needed (changed `requirements.txt`, env vars, or the unit file itself —
   things a code reload can't pick up). That path still schedules the
   restart via `systemd-run --on-active=2s ...` (a transient unit owned by
   PID 1, outside `liara-backend`'s cgroup) so a caller running inside it
   gets a couple seconds to finish and save its result first, but the actual
   restart a moment later can still cause a brief **HTTP 502** on unrelated
   requests — verify it separately via `tail -1
   /var/log/liara/restart_result.log` or `GET /api/admin/health/full`, don't
   rely on `restart_backend.sh`'s own exit code for that.

3. **No cancel yet.** A normal timeout finalizes cleanly (`status: "timeout"`,
   process group killed - see below). Self-restart jobs no longer get killed
   mid-flight (see above), but any other cause of the whole worker process
   dying unexpectedly would still leave a job stuck at `status: "running"`
   until the 1h TTL expires, since nothing would be left to write its final
   state.

4. **Same privilege as the PTY terminal.** This is full shell access gated
   only by `require_admin` (JWT validated → active user → role check). Don't
   treat it as lower-risk than the terminal just because it's JSON-shaped.

---

## Human-facing equivalent

Same capability is available to a person in the browser: Admin → Terminal →
"➕ Neuer Tab" → type "🤖 AI" → type a command in the box → "📤 Senden". Same
backend, same job/poll model, just rendered as a chat-style log instead of
raw JSON. Component: `frontend/src/components/AiExecTab.jsx`.

---

## Full example

```bash
BASE=https://liara.mw-dresden.de
TOKEN=$(curl -s -X POST $BASE/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"..."}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

JOB_ID=$(curl -s -X POST $BASE/api/admin/terminal/exec \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"command":"git log -1 --oneline"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['job_id'])")

sleep 1
curl -s $BASE/api/admin/terminal/exec/$JOB_ID -H "Authorization: Bearer $TOKEN"
```

---

## Source

- Backend: [`app/api/routers/terminal_exec_router.py`](app/api/routers/terminal_exec_router.py)
- Frontend: [`frontend/src/components/AiExecTab.jsx`](frontend/src/components/AiExecTab.jsx),
  wired into [`frontend/src/components/TerminalTabs.jsx`](frontend/src/components/TerminalTabs.jsx)
  as the `type: 'ai'` tab.
