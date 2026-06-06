# Backend API Feedback — Lovable Integration

Feedback from the Lovable frontend build and how this repo addresses it.

**API version:** 1.4 (see `data/api_contract.json`, `GET /api/contract`)

---

## 1. Inconsistent envelope shapes — **FIXED (v1.4)**

**Was:** `/api/trials`, `/api/papers`, `/api/patients-like-you`, etc. returned different top-level shapes.

**Now:** All data GET endpoints return:

```json
{
  "data": <payload>,
  "meta": {
    "updated_at": "2026-06-07T12:00:00Z",
    "source": "trials.json",
    "api_version": "1.4",
    "count": 20
  }
}
```

**Transition:** Add `?legacy=1` to get pre-1.4 shapes during migration.

**Client:** Use `unwrapApi()` from `lovable/src/lib/agentApi.ts`.

---

## 2. Field naming drift — **FIXED (aliases kept)**

| Canonical | Deprecated alias (still sent) |
|-----------|------------------------------|
| `patient_match.pct_of_trial` | `pct` on patients-like-you rows |
| `treatment.control` | `treatment.comparator` |
| `paper.ref` | `paper.title` |
| `paper.topic` | `paper.type` |

Field dictionary: `GET /api/contract` → `field_dictionary`.

---

## 3. Type coercion — **FIXED at API layer**

- `phase` → always **string** (`"3"`, `"1b/2"`)
- `efficacy` → never `null`; default `{ "primary": [], "subgroups": [] }` plus any flat legacy fields

Normalization runs on every `/api/trials` response (`scripts/api_schema.py`).

---

## 4. `match_type` enum — **DOCUMENTED**

All values in `data/api_contract.json` → `match_type_enum`:

`by_design`, `published_subgroup`, `published_eligible`, `retrospective_cn_plus`, `wrong_setting`, `wrong_timing`, `wrong_population`, `none`, `indirect`

**Frontend:** Import `MATCH_TYPES` from `agentApi.ts`. Treat unknown values as `"none"` (defensive badge).

New values require updating `api_contract.json` + `MATCH_TYPES` before shipping.

---

## 5. Papers schema — **FIXED**

`/api/papers` normalizes each paper with:

- `ref` (from `title`)
- `topic` (from `type`)
- `year` (from `year` / `pubdate` / `discovered_at`)
- `source_url` (from `url`)

Legacy fields (`title`, `type`, `url`) unchanged during transition.

---

## 6. Copy ownership — **OPTION ADDED**

Clinical/UI copy can stay in the Lovable frontend:

- `GET /api/dashboard-charts?include_copy=0` — data + chart ids/series only
- `GET /api/interpretations?include_copy=0` — strips `ui_copy`, `talking_points_for_oncologist`

Default `include_copy=1` keeps full copy for local admin UI.

---

## 7. `patient_match` on trials — **FIXED**

All 20 trials in `data/trials.json` include `patient_match` (enriched via `scripts/enrich_trials_ui_data.py`).

API always returns `patient_match` on each trial; missing blocks get a safe fallback from `cn1_cn_plus_n`.

`/api/patients-like-you` remains the curated hero table; `/api/trials` is the full source of truth.

---

## 8. ngrok URL rotation — **OPEN (ops)**

ngrok free tier URLs change on restart. Options:

- Cloudflare Tunnel with fixed hostname
- Fly.io / Railway / small VPS with stable domain
- Lovable static fallback (`lovable/*.json`) when PC offline

Run `python scripts/show_agent_config.py` after each ngrok restart.

---

## 9. CORS + cache — **IMPROVED**

- `Access-Control-Allow-Origin` (from `CORS_ORIGINS` in `.env`)
- `Access-Control-Allow-Headers` includes `ngrok-skip-browser-warning`
- `Cache-Control: public, max-age=60` on JSON responses

ngrok bypass header still recommended for ngrok free tier interstitial.

---

## 10. `updated_at` per endpoint — **FIXED**

Every enveloped response includes `meta.updated_at` (file mtime UTC).

`/api/papers` meta also includes `updated` from `papers_index.json` when wrapped.

---

## Endpoints (v1.4)

| Path | Notes |
|------|--------|
| `GET /api/contract` | Field dictionary + match_type enum |
| `GET /api/trials?wrap=1` | Normalized trials + categories + meta |
| `GET /api/papers?wrap=1` | Normalized papers |
| `GET /api/*` | `?legacy=1` old shape; `?include_copy=0` strip UI copy |

---

## Tell Lovable (v1.4)

```
Backend upgraded to API v1.4. All GET data endpoints return { data, meta: { updated_at, source, api_version } }.
```

---

## Post v1.4 feedback — **ADDRESSED in v1.5**

| Item | v1.5 change |
|------|-------------|
| List shapes inconsistent | **Fixed** — all lists use `data.items[]` + `data.kind`. Deprecated: `trials`, `papers`, `rows`, `charts` until **2026-09-01** |
| `meta.count` missing | **Fixed** — always present (singletons = 1; glossary = terms+steps) |
| Deprecated aliases | **Sunset 2026-09-01**. Use `?strict=1` now to test without aliases |
| `/api/pending` envelope | **Fixed** — `{ data: { kind: pending, items: [] }, meta }` |
| `/api/status`, `/api/health`, POST actions | **Documented** in `/api/contract` → `envelope.does_not_apply_to` — bare JSON |
| `meta.source` filenames | **Fixed** — logical names: `trials`, `papers`, `pending`, … |
| ETag / 304 | **Added** — `meta.etag` + `ETag` header + `If-None-Match` support |
| JSON Schema | **Added** — `GET /api/schema`, `GET /api/schema/trial` |
| match_type labels | **Contract is source of truth** — use `fetchMatchTypeLabels()` from agentApi.ts |
| `?legacy=1` sunset | **2026-09-01** in `/api/contract` |
| CORS + Cache-Control | **Improved** — `Vary: Origin`, `Expose-Headers: ETag`, max-age=60. ngrok header only for ngrok interstitial |

### v1.5 client helpers

```typescript
import { unwrapApi, unwrapList, unwrapObject, fetchMatchTypeLabels } from "@/lib/agentApi";

const trials = unwrapList<Trial>(await fetch("/api/trials?wrap=1"));
const interpretations = unwrapObject(await fetch("/api/interpretations"));
const labels = await fetchMatchTypeLabels(); // replaces hardcoded MatchBadges
```

### Endpoints without envelope

- `GET /api/health`
- `GET /api/status`
- `POST /api/search`, `/api/refresh` (return status shape)
- `POST /api/approve`, `/api/reject` (action result)

## Tell Lovable (v1.5)

```
API v1.5. Re-copy agentApi.ts.

Lists: always data.items (unwrapList). Objects: data.object (unwrapObject).
match_type badge labels: fetchMatchTypeLabels() from /api/contract — delete hardcoded enum in MatchBadges.tsx.
Poll with If-None-Match: meta.etag for 304.
Deprecated aliases removed 2026-09-01 — migrate to items/control/ref/topic/pct_of_trial now.
?legacy=1 removed 2026-09-01.
JSON types: GET /api/schema/trial
```
