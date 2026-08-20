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

- `command` (required): shell string, runs via `subprocess.run(..., shell=True)`
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
  "finished_at": null
}
```

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
  "finished_at": "2026-08-20T..."
}
```

`status` is one of: `running`, `done` (exited, check `exit_code`), `error`
(the job itself failed to run, e.g. bad cwd), `timeout` (hit the 300s cap).

404 means the job_id is unknown or its result already expired.

---

## Limits

| | |
|---|---|
| Max runtime per command | 300s (`EXEC_TIMEOUT`), then `status: "timeout"` |
| Output kept | last 20,000 chars each of stdout/stderr (`OUTPUT_CAP`) |
| Job result lifetime | 1h in Redis (`JOB_TTL_SECONDS`), then gone (404) |
| Default cwd | repo root (`/opt/liara`) |
| Concurrency | job state lives in Redis, not in-process memory, so it works correctly across gunicorn's multiple worker processes |

---

## Known caveats (read before assuming something is broken)

1. **No TTY, so plain `sudo` fails.** Any command needing `sudo` must be
   covered by a `NOPASSWD` sudoers rule (see `/etc/sudoers.d/liara-deploy` on
   the server) — `sudo` refuses to prompt for a password over a
   non-interactive pipe. If a command fails with `"a terminal is required to
   read the password"`, that's this, not a bug in the endpoint.

2. **Self-restart hazard.** If the command restarts the backend itself
   (`./update.sh` when `app/*` changed, or `./restart_backend.sh` directly),
   the *next poll request* will very likely get an **HTTP 502** while
   `systemctl restart liara-backend` is mid-flight — nginx has nowhere to
   proxy to for a second. This is expected, not a failure of the command.
   **Verify success with a separate check afterward** (e.g. hit
   `GET /api/admin/health/full`, or check `systemctl is-active liara-backend`
   in a fresh command) rather than trusting that job's own final poll.

3. **No cancel yet.** A job killed mid-flight by a self-restart (or one that
   hits the timeout) can stay stuck at `status: "running"` forever (up to the
   1h TTL) — nothing ever writes its final state. Don't poll such a job
   indefinitely; if a self-restart is involved, move on and verify some other
   way instead.

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
