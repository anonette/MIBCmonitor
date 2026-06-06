# Node-Positive MIBC Evidence Explorer

Personal evidence system for **one patient category only**:

> **Regionally node-positive muscle-invasive bladder cancer (cN1–cN3, cM0)** — systemic therapy first, then possible curative local treatment (cystectomy or radiation).

**Not** a general bladder cancer resource. The site, data, and agent are scoped to perioperative / neoadjuvant decisions for involved pelvic nodes without distant metastases.

**Example profile:** pT2 high-grade, L1, PET-positive external iliac node, cN1 cM0 — compare trials by how many patients match this profile and what is known about them.

---

## What lives where

```
c:\dev\cancer\
├── data/                  # Canonical JSON datasets (source of truth)
├── lovable/               # Copy of data + Lovable build prompts + API client
├── scripts/               # Agent, API server, enrichment, CLI tools
├── web/                   # Local browser UI (served by agent_server.py)
├── wiki/                  # Human-readable evidence articles
├── raw/bladder-cancer/    # Source notes / discovered paper markdown
├── canvases/              # Cursor canvas — interactive trial comparison
├── visualizations/        # PNG charts (run generate_visualizations.py)
├── .env                   # Secrets (gitignored) — see .env.example
└── README.md              # This file
```

### `data/` — structured evidence

| File | What it is |
|------|------------|
| `trials.json` | **20 trials** with efficacy, fit scores, `patient_match` (n like you, certainty), and `subgroup_outcomes`. Version in `meta.version`. |
| `papers_index.json` | **~32 papers/trials** discovered by the agent. Each has `status`: `approved`, `rejected`, or `needs_review`. |
| `patient_profile.json` | Target clinical profile + `website_scope` (what the app includes/excludes). |
| `interpretations.json` | Narrative sections, talking points, `tumor_board_questions`, UI copy. |
| `patients_like_you.json` | Overview hero table — studies ranked by patients matching the profile. |
| `glossary_pathway.json` | 7-step treatment pathway + searchable glossary terms. |
| `agent_log.json` | Audit log of agent runs (searches, validation, errors). |
| `evidence_registry.csv` | Evidence IDs (EV-xxx) cross-referenced to sources. |

The agent **reads and writes** `trials.json` and `papers_index.json`. Everything else is served read-only over the API.

### `lovable/` — web app package

Mirrors of `data/*.json` plus files for building the **Lovable** (cloud React) app:

| File | Purpose |
|------|---------|
| `PASTE_INTO_LOVABLE.txt` | **Main build prompt** — 9 pages, live API, review queue, patient-match UI. Paste this into Lovable to start or rebuild. |
| `PROMPT_REVIEW_QUEUE.txt` | Follow-up prompt if you only need the approve/reject review queue. |
| `PROMPT_UI_ENRICHMENT.txt` | Follow-up for patient_match badges, glossary, tumor board. |
| `src/lib/agentApi.ts` | TypeScript client — copy to Lovable `src/lib/agentApi.ts`. |
| `LOVABLE_LIVE_API.md` | Step-by-step ngrok + env var setup. |
| `DATA_README.md` | Which JSON files to upload to Lovable `src/data/`. |

### `scripts/` — automation

| Script | What it does |
|--------|----------------|
| `agent_server.py` | **Main entry point.** HTTP server on port 8765: local UI + REST API for Lovable. |
| `agent_core.py` | Core logic: validate datasets, PubMed/CT.gov search, review queue, approve/reject, refresh watched NCTs. |
| `show_agent_config.py` | Prints `VITE_AGENT_API_URL` and `VITE_AGENT_API_KEY` to paste into Lovable. |
| `env_config.py` | Loads `.env` (API keys, port, CORS). |
| `enrich_trials_ui_data.py` | Adds `patient_match` and `subgroup_outcomes` to every trial in `trials.json`. |
| `research_agent.py` | CLI alternative: `--compare`, `--list`, `--watch-trials` without the web server. |
| `generate_visualizations.py` | Builds PNG charts in `visualizations/` from `trials.json`. |

### `web/index.html` — local control panel

Opened automatically at `http://127.0.0.1:8765` when you start the agent. Use this for:

- **Search for new studies** — PubMed + ClinicalTrials.gov → new rows in `papers_index.json` (`needs_review`)
- **Validate existing data** — missing fields, bad counts, data-quality info
- **Refresh watched trials** — pull latest status from CT.gov for tracked NCT IDs
- **Review queue** — approve or reject auto-discovered papers (same workflow as Lovable)

Localhost requests skip API-key auth; ngrok/Lovable require `X-API-Key`.

### `wiki/` — compiled knowledge

Long-form evidence write-ups. Start here:

- `wiki/bladder-cancer/cn1-mibc-evidence-comparison.md` — trial-by-trial fit and argument priority
- `wiki/bladder-cancer/patient-profile-cn1-mibc.md` — target profile detail
- `wiki/bladder-cancer/research-agent.md` — how the agent workflow fits together

### `raw/bladder-cancer/` — source material

Markdown notes ingested or auto-discovered during research (e.g. EV-304 ASCO GU abstract, Zargar-Shoshtar cN+ NAC paper). Feeds wiki and manual curation; not served directly by the API.

---

## How the pieces connect

```
┌─────────────────┐     ngrok HTTPS      ┌──────────────────────┐
│  Your PC        │ ◄─────────────────── │  Lovable app (cloud) │
│  agent_server   │   VITE_AGENT_API_*   │  React + agentApi.ts │
│  data/*.json    │                      └──────────────────────┘
└────────┬────────┘
         │ http://127.0.0.1:8765
         ▼
┌─────────────────┐
│  web/index.html │  ← local review queue + refresh buttons
└─────────────────┘
```

1. **You** run the agent on your PC — it owns the JSON files.
2. **Lovable** fetches live data via ngrok (`fetchAllLiveData()`), or falls back to static `src/data/*.json` if the API is down.
3. **Review queue:** agent finds candidates → `needs_review` in `papers_index.json` → you approve/reject in local UI or Lovable → `approved` / `rejected`. Approve does **not** auto-merge into `trials.json` yet.

---

## Quick start

### 1. Configure secrets

```powershell
copy .env.example .env
# Edit .env — set AGENT_API_KEY (random string) and optional LLM keys
python -c "import secrets; print(secrets.token_urlsafe(32))"   # generate key
```

### 2. Start agent + expose to Lovable

```powershell
cd c:\dev\cancer
python scripts\agent_server.py          # local UI at http://127.0.0.1:8765

# In a second terminal:
ngrok http 8765
# Copy HTTPS URL into .env as AGENT_PUBLIC_URL
python scripts\show_agent_config.py     # copy VITE_* vars into Lovable Settings
```

Full Lovable wiring: `lovable/LOVABLE_LIVE_API.md`

### 3. Build the Lovable app

1. Paste `lovable/PASTE_INTO_LOVABLE.txt` into Lovable.
2. Upload `lovable/*.json` → Lovable `src/data/`.
3. Copy `lovable/src/lib/agentApi.ts` → `src/lib/agentApi.ts`.
4. Set env vars, **republish** (required after URL/key changes).

### 4. CLI alternatives

```powershell
python scripts\research_agent.py --compare
python scripts\research_agent.py --list
python scripts\research_agent.py --watch-trials
python scripts\generate_visualizations.py
python scripts\enrich_trials_ui_data.py
```

---

## API reference

Base URL: `http://127.0.0.1:8765` (local) or your ngrok HTTPS URL.

Header on all routes except `/api/health`: `X-API-Key: <AGENT_API_KEY>`

**API v1.4:** Data endpoints return `{ data, meta: { updated_at, source, api_version } }`. See `BACKEND_FEEDBACK.md` and `GET /api/contract`. Use `?legacy=1` for old shapes during migration.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check (no auth) |
| GET | `/api/status` | Agent state, counts, last run |
| GET | `/api/trials` | All trials (array) |
| GET | `/api/papers` | All papers (array) |
| GET | `/api/pending` | Review queue with assessment hints |
| GET | `/api/interpretations` | Narrative + tumor board content |
| GET | `/api/patient-profile` | Target profile + website scope |
| GET | `/api/patients-like-you` | Overview hero table data |
| GET | `/api/glossary-pathway` | Pathway steps + glossary |
| GET | `/api/dashboard-charts` | Visual dashboard chart labels, captions, caveats |
| GET | `/api/validate` | Dataset validation report |
| POST | `/api/search` | Full PubMed + CT.gov scan |
| POST | `/api/refresh` | Refresh watched NCT trial statuses |
| POST | `/api/approve` | `{"paper_id": "..."}` — mark paper approved |
| POST | `/api/reject` | `{"paper_id": "...", "reason": "optional"}` |

---

## Key trials (for this profile)

| Study | Why it matters |
|-------|----------------|
| **EV-304 / KEYNOTE-B15** | n=808 perioperative EV+pembro vs GC; cisplatin-eligible incl. cN1 M0; EFS HR 0.53 |
| **EV-ECLIPSE** | Only prospective trial **by design** for node-positive perioperative EV+pembro (n≈23) |
| **NIAGARA** | Approved perioperative durvalumab; cN1 subgroup n=58, EFS HR 0.75 (NS) |
| **EV-302 LN-only** | Strong efficacy but **metastatic** setting — label as wrong-setting context |
| **Zargar-Shoshtar** | Retrospective: 304 cN+, 56% pN0 in cN1 with chemo |

Wrong-setting trials (metastatic, adjuvant-only) stay in the dataset but are flagged via `patient_match.match_type`.

---

## Validation messages

The agent runs `validate_datasets()` on each search. Severity levels:

| Level | Meaning |
|-------|---------|
| `error` | Data bug (e.g. cN1 n > total_n) — blocks `ok: false` |
| `warning` | Missing required field or unwatched NCT |
| `info` | Nice-to-have (e.g. trial has NCT but no `source_url`) |

Check results in the local UI or `GET /api/validate`.

---

## Target patient profile

Defined in `data/patient_profile.json`:

- **Stage:** cT2, **cN1**, **cM0** — PET-positive external iliac node
- **Pathology:** pT2 high-grade, L1 (LVSI)
- **Intent:** Perioperative systemic therapy before possible radical cystectomy
- **Key question:** EV+pembro vs standard cisplatin NAC — how many trial patients actually match?

---

## License / disclaimer

Educational research tool only. Not medical advice. Does not cover node-negative MIBC, bladder-sparing protocols, or metastatic first-line treatment except as labeled cross-setting context.
