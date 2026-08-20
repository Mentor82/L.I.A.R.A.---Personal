# Terminal PTY v3.0 - Interactive Terminal Implementation

**Status**: ✅ IMPLEMENTED  
**Date**: 2025-12-05  
**Version**: 3.0.0

## Overview

Full interactive terminal with PTY (pseudo-terminal) support using xterm.js and WebSocket. Supports all interactive programs like `su`, `vim`, `top`, etc.

---

## Architecture

### Backend (FastAPI + WebSocket)

**File**: `/opt/liara/app/api/routers/terminal_pty.py` (127 lines)

- **Endpoint**: `WS /admin/terminal/ws`
- **Authentication**: JWT token via query param `?token=...`
- **Authorization**: Admin-only (checked via `get_current_user_ws`)
- **PTY Implementation**: `pty.fork()` creates real bash shell
- **I/O**: Bidirectional async communication (WebSocket ↔ PTY)
- **Cleanup**: Automatic process kill and file descriptor cleanup on disconnect

**Key Code**:
```python
# Create PTY with real bash shell
pid, fd = pty.fork()

if pid == 0:
    # Child process - execute bash
    os.execvp('bash', ['bash'])
else:
    # Parent - handle WebSocket ↔ PTY I/O
    asyncio.create_task(read_from_pty())
    asyncio.create_task(write_to_pty())
```

### Frontend (React + xterm.js)

**File**: `/opt/liara/frontend/src/components/Terminal.jsx` (280 lines)

- **Library**: `@xterm/xterm@5.3.0` (modern namespace)
- **Addons**: 
  - `@xterm/addon-fit` - Auto-resize terminal
  - `@xterm/addon-web-links` - Clickable URLs
- **Theme**: Custom dark theme (Ayu Dark inspired)
- **Connection**: WebSocket to `/api/admin/terminal/ws?token=...`
- **Features**:
  - Real-time bidirectional I/O
  - Terminal resize handling
  - ANSI color support
  - Interactive cursor

**Key Code**:
```jsx
const term = new XTerm({
  cursorBlink: true,
  theme: { background: '#0a0e14', ... }
});

const ws = new WebSocket(`ws://${host}/api/admin/terminal/ws?token=${token}`);
ws.onmessage = (e) => term.write(e.data);
term.onData((data) => ws.send(data));
```

### Authentication (WebSocket)

**File**: `/opt/liara/app/core/dependencies.py`

**New Function**: `get_current_user_ws(websocket, db)`

- Extracts token from query params (`?token=...`) or `Sec-WebSocket-Protocol` header
- Verifies JWT token via `verify_token()`
- Checks user exists, is active, and has admin role
- Raises exceptions (not HTTPException) for WebSocket context

---

## Supported Features

### ✅ Interactive Programs

- **su** - Switch user (password prompts work)
- **vim** - Full-screen text editor
- **nano** - Terminal text editor
- **top / htop** - Process monitors
- **python3** - Interactive REPL
- **ssh** - SSH to other servers
- **less / more** - Pagers

### ✅ Terminal Features

- ANSI escape codes (colors, cursor movement)
- Terminal resize (sends resize messages to PTY)
- Ctrl+C, Ctrl+D, Ctrl+Z signals
- Tab completion (bash)
- Command history (up/down arrows)
- Background processes (Ctrl+Z, bg, fg)

---

## Security

### Authentication Flow

1. User logs in to Liara → Receives JWT token
2. Frontend stores token in `localStorage.getItem('liara_token')`
3. Terminal component passes token in WebSocket URL:
   ```
   ws://localhost/api/admin/terminal/ws?token=eyJhbGc...
   ```
4. Backend validates token via `get_current_user_ws()`
5. Checks user role == ADMIN
6. If valid → PTY session starts
7. If invalid → WebSocket closes with code 1008 (Policy Violation)

### Logging

All terminal sessions are logged:
```python
logger.info(f"Terminal PTY session started for user {user.username} (id={user.id})")
```

Logs written to `/var/log/liara/error.log`

---

## Testing

### Manual Test Steps

1. **Open Admin Panel**:
   ```
   http://localhost/admin
   ```

2. **Navigate to Terminal Tab**

3. **Click "Verbinden"**
   - WebSocket connects to `/api/admin/terminal/ws?token=...`
   - Terminal shows: `🔌 Terminal verbunden`

4. **Test Basic Commands**:
   ```bash
   ls -la --color=auto
   pwd
   whoami
   ```

5. **Test Interactive Programs**:
   ```bash
   # Vim (full-screen editor)
   vim test.txt
   # Type :q! to quit
   
   # Top (process monitor)
   top
   # Press q to quit
   
   # Switch user (requires password)
   su - mirko
   ```

6. **Test Terminal Resize**:
   - Resize browser window
   - Terminal should auto-fit (via FitAddon)

7. **Test Disconnect**:
   - Click "Trennen" button
   - Terminal shows: `🔌 Verbindung getrennt`

### Expected Behavior

- Commands execute immediately (no delay)
- Colors display correctly (ANSI codes work)
- Interactive prompts accept input (password fields, vim commands)
- Terminal resizes smoothly
- No crashes on disconnect

---

## File Changes

### Backend Files

1. **`/opt/liara/app/api/routers/terminal_pty.py`** (NEW)
   - 127 lines
   - WebSocket PTY router
   - Auth, PTY fork, async I/O

2. **`/opt/liara/app/core/dependencies.py`** (MODIFIED)
   - Added `get_current_user_ws()` function
   - WebSocket authentication support

3. **`/opt/liara/app/main.py`** (MODIFIED)
   - Line 27: Import terminal_pty_router
   - Line 108: Register router

### Frontend Files

4. **`/opt/liara/frontend/src/components/Terminal.jsx`** (REWRITTEN)
   - 280 lines (was 322)
   - Removed old command execution logic
   - Implemented xterm.js + WebSocket
   - Added FitAddon, WebLinksAddon

5. **`/opt/liara/frontend/package.json`** (MODIFIED)
   - Added: `@xterm/xterm@5.3.0`
   - Added: `@xterm/addon-fit@0.10.0`
   - Added: `@xterm/addon-web-links@0.11.0`

---

## Deployment

### Backend

```bash
sudo systemctl restart liara-backend
sudo systemctl status liara-backend
```

### Frontend

```bash
cd /opt/liara/frontend
npm run build
sudo cp -r dist/* /var/www/liara/
```

### Verification

```bash
# Check routes
curl -s http://localhost:8100/docs | grep terminal

# Check logs
sudo tail -f /var/log/liara/error.log | grep -i terminal
```

---

## Troubleshooting

### Issue: WebSocket connection fails

**Symptom**: Frontend shows "WebSocket-Verbindungsfehler"

**Solutions**:
1. Check backend is running: `systemctl status liara-backend`
2. Check nginx WebSocket proxy:
   ```nginx
   location /api/ {
       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection "upgrade";
   }
   ```
3. Verify token is valid: Check browser console for auth errors

### Issue: Authentication failed

**Symptom**: Terminal shows "Authentication failed: Invalid token"

**Solutions**:
1. Check token in localStorage: `localStorage.getItem('liara_token')`
2. Re-login to get fresh token
3. Check user role is ADMIN: `SELECT role FROM users WHERE id = ...`

### Issue: Terminal not rendering

**Symptom**: Blank terminal area after connection

**Solutions**:
1. Check browser console for xterm.js errors
2. Verify CSS loaded: `/api/assets/*.css` should include xterm styles
3. Hard refresh browser: Ctrl+Shift+R

### Issue: Interactive programs don't work

**Symptom**: `su` or `vim` show garbled output

**Solutions**:
1. Check PTY is created: `ps aux | grep bash` should show shell processes
2. Verify terminal size sent: Check WebSocket messages in browser DevTools
3. Check TERM environment: Should be set in bash (default: `xterm-256color`)

---

## Future Enhancements

### Planned Features

- [ ] **Multiple Terminal Tabs**: Open multiple PTY sessions
- [ ] **Session Persistence**: Reconnect to existing PTY sessions
- [ ] **File Upload/Download**: Drag & drop files to terminal
- [ ] **Recording**: Save terminal sessions to replay later
- [ ] **Shared Sessions**: Multiple users view same terminal
- [ ] **Custom Themes**: User-selectable color schemes
- [ ] **Search**: Search terminal output (Ctrl+Shift+F)
- [ ] **Command Palette**: Quick access to common commands

### Technical Improvements

- [ ] Connection retry logic (exponential backoff)
- [ ] Terminal size auto-detection from container
- [ ] Compression for WebSocket messages (zlib)
- [ ] Rate limiting for terminal commands
- [ ] Audit log for all terminal commands executed

---

## References

- **xterm.js Docs**: https://xtermjs.org/
- **PTY Module**: https://docs.python.org/3/library/pty.html
- **FastAPI WebSockets**: https://fastapi.tiangolo.com/advanced/websockets/
- **WebSocket Protocol**: https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API

---

## Version History

### v3.0.0 (2025-12-05)
- ✅ Initial implementation
- ✅ WebSocket PTY backend
- ✅ xterm.js frontend
- ✅ Admin authentication
- ✅ Interactive program support (su, vim, top)
- ✅ Terminal resize handling
- ✅ ANSI color support

---

**Implementation Complete** ✅

Next: Test in production browser environment
