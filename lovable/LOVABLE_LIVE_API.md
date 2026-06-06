# Lovable Live API Setup (Option 2)

Connect your Lovable app to the running evidence agent so **Refresh evidence** pulls live data.

## Step 1 — Configure backend `.env`

Add these lines to `c:\dev\cancer\.env` (keep your existing API keys):

```env
AGENT_API_KEY=your-long-random-secret-here
AGENT_PORT=8765
AGENT_HOST=0.0.0.0
AGENT_PUBLIC_URL=
CORS_ORIGINS=*
```

Generate a key:
```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Step 2 — Start the agent API

```powershell
cd c:\dev\cancer
python scripts\agent_server.py
```

## Step 3 — Expose to internet (ngrok)

Lovable runs in the cloud and cannot reach `localhost`. Use ngrok:

```powershell
ngrok http 8765
```

Copy the **HTTPS** URL (e.g. `https://abc123.ngrok-free.app`) into `.env`:

```env
AGENT_PUBLIC_URL=https://abc123.ngrok-free.app
```

## Step 4 — Lovable environment variables

In Lovable project → **Settings → Environment variables**:

| Variable | Value |
|----------|--------|
| `VITE_AGENT_API_URL` | `https://abc123.ngrok-free.app` (your ngrok URL) |
| `VITE_AGENT_API_KEY` | Same as `AGENT_API_KEY` in backend `.env` |

## Step 5 — Paste API integration into Lovable

Copy `lovable/src/lib/agentApi.ts` into your Lovable project at `src/lib/agentApi.ts`.

Add a **Refresh evidence** button on the Overview page that:

1. Calls `runEvidenceSearch()`
2. Polls `pollUntilDone()` every 2s
3. Reloads trials/papers via `fetchLiveTrials()` / `fetchLivePapers()`
4. Shows `pending_papers` with **needs_review** badge
5. **Approve** calls `approvePaper(id)`

## API reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/health` | No | Health check |
| GET | `/api/status` | Yes | Agent state + pending papers |
| GET | `/api/trials` | Yes | Full trials.json |
| GET | `/api/papers` | Yes | Full papers_index.json |
| GET | `/api/interpretations` | Yes | interpretations.json (tumor board, UI copy) |
| GET | `/api/patient-profile` | Yes | patient_profile.json |
| GET | `/api/glossary-pathway` | Yes | glossary_pathway.json |
| GET | `/api/patients-like-you` | Yes | patients_like_you.json |
| GET | `/api/dashboard-charts` | Yes | dashboard_charts.json (chart labels & captions) |
| POST | `/api/search` | Yes | Run full scan |
| POST | `/api/refresh` | Yes | Refresh watched NCT trials |
| POST | `/api/approve` | Yes | `{"paper_id": "..."}` |

Header: `X-API-Key: <AGENT_API_KEY>`

## Test from PowerShell

```powershell
$key = "YOUR_AGENT_API_KEY"
$base = "https://YOUR-NGROK-URL"
Invoke-RestMethod -Uri "$base/api/health"
Invoke-RestMethod -Uri "$base/api/status" -Headers @{"X-API-Key"=$key}
```
