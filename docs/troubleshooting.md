# Troubleshooting

Common local issues and how to resolve them.

## 1. Backend port 8000 in use

```bash
lsof -iTCP:8000 -sTCP:LISTEN
# or:
ss -tlnp | grep :8000
kill <PID>
```

The backend defaults to port 8000. If a previous run did not exit cleanly, re-launching will fail with `address already in use`. Identify and stop the process holding the port.

## 2. Frontend cannot reach backend

Symptom: 404, CORS errors, or "fetch failed" in the browser console.

Check:

- Backend is running on `http://localhost:8000`. Visit `http://localhost:8000/api/health` directly — it should return `{"status": "healthy"}`.
- Frontend is reaching the configured origin. CORS allowlist is set in `backend/main.py` to `http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:8000`, `http://127.0.0.1:8000`. If you serve the frontend on a different origin, add it there.
- WebSocket connections: the chat WS rejects unknown `Origin` headers. Set `YOGA_WS_ALLOWED_ORIGINS=http://your.origin:port` (comma-separated for multiple) to extend the allowlist.

## 3. Encryption key missing or unreadable

Symptom: `RuntimeError: unable to read or create encryption key at .../data/encryption.key`.

The Fernet key is created lazily at first encrypt/decrypt call. If you see this error, the `data/` directory is unwritable. Recreate the key:

```bash
mkdir -p data
rm -f data/encryption.key
python -c "from backend.services.encryption import get_fernet; get_fernet()"
```

This regenerates `data/encryption.key` with mode `0o600`. Note: regenerating the key invalidates any previously encrypted Spotify tokens — re-link Spotify in Settings.

## 4. Spotify OAuth state mismatch

Symptom: Spotify callback returns 400 "Invalid or expired OAuth state".

The state has a 10-minute TTL. If you took longer than that to complete the auth flow, restart it:

1. Disconnect Spotify in Settings (or `DELETE /api/spotify/disconnect`).
2. Click "Connect Spotify" again.
3. Complete the auth flow within 10 minutes.

## 5. Cloud LLM streaming and resilience

Streaming is supported for OpenAI, Anthropic, DeepSeek, and Google (Gemini) — chunks arrive token-by-token through the chat WebSocket. Google streams via the `streamGenerateContent` endpoint with `?alt=sse`, parsed as SSE `data: {…}` lines. Local Ollama also streams natively.

Cloud calls (both blocking and streaming) are wrapped in a retry + circuit-breaker layer:

- **Retries**: up to 3 attempts on transient failures — `httpx.ConnectError`, `httpx.ReadTimeout`, `httpx.WriteTimeout`, `httpx.PoolTimeout`, and any 5xx response. Backoff is 1s before retry 2 and 4s before retry 3, with ±20% jitter. 4xx responses are not retried (caller's fault).
- **Streaming retries**: only before the first chunk has been yielded. Once any text has flowed to the client, a mid-stream connection drop terminates cleanly without retry — partial output is preferred over duplicating tokens.
- **Per-provider circuit breaker**: 5 consecutive failures trip the breaker for that provider. While OPEN, calls short-circuit with `[Cloud Call Failed] circuit open …` for an initial 30s cooldown. The first call after the cooldown is a HALF_OPEN trial — success closes the breaker and resets the cooldown; failure re-OPENs it with the cooldown doubled (capped at 300s).

If streaming hangs or yields no chunks, check `data/sangha.log` for `cloud_call_start` / `cloud_call_done` / `cloud_call_failed` / `cloud_retry` / `cloud_circuit_opened` / `cloud_circuit_closed` entries. Circuit-breaker state is in-memory and resets on backend restart.

## 6. Where to find logs

Application logs are written to `data/sangha.log`. The file rotates at 10 MB with up to 5 backups (`data/sangha.log.1`, `data/sangha.log.2`, ...). Console output mirrors INFO-level messages; the log file captures the same. Both the active file and rotated backups are gitignored.

Log lines never include API keys, prompt text, or LLM response bodies — only provider, model, mode, latency, and status codes. Log files are safe to attach when reporting issues.

## 7. Spotify is logged out / playlist creation fails

Spotify access tokens expire about an hour after the OAuth dance. The backend now refreshes the access token automatically using the stored refresh token whenever a Spotify call is about to be made and the access token is within 60 seconds of expiry (or already expired). Refresh-token rotation is honored: if Spotify returns a new refresh token in the refresh response, it is encrypted and persisted.

If playlist creation still fails after a fresh login, the refresh token may have been revoked Spotify-side (manual revocation, password change, or a long inactivity gap). Reconnect:

1. Open the Settings page.
2. Click "Disconnect" (or `DELETE /api/spotify/disconnect`).
3. Click "Connect Spotify" and complete the OAuth flow.

The backend logs `spotify_refresh_failed` with the error class on each failed refresh; check `data/sangha.log` for context.

## 8. Backing up or migrating your data

The Settings page has a **Data** section with Export and Import controls.

### Export

Settings → Data → **Export** downloads a single ZIP containing every user-data table (flows, sessions, Spotify auth, generated playlists, custom themes), `transition_guides.json`, and — if it exists — `data/encryption.key`. The bundle is named `yoga-companion-export-YYYYMMDD-HHMMSS.zip`.

**The export contains decrypted secrets** (Spotify access + refresh tokens, your encryption key). Keep the file private. The backend does the same already on disk in `data/`, so the export does not weaken security beyond what's already there — but the file is portable, so don't email or upload it.

### Import

Settings → Data → **Import** prompts for a previously exported ZIP and **REPLACES all existing local data** with the bundle's contents. Export first if you want a backup of the current state. Schema version mismatches are rejected with a controlled error.

### Migrating between machines

1. On the old machine: Settings → Data → Export. Save the ZIP somewhere portable.
2. On the new machine: install Digital Sangha and run it once so the data dir exists.
3. Open Settings → Data → Import and select the ZIP. The import overwrites the local DB, transition guides, and encryption key.
4. Spotify tokens are re-encrypted with the imported key on apply, so playlists that depend on Spotify auth continue to work without reconnecting.

If you'd rather keep the new machine's existing encryption key, copy `data/encryption.key` aside before importing and restore it afterwards — then reconnect Spotify (the imported encrypted tokens will no longer match your key).
