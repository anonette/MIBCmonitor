# Research Agent: MIBC cN1 Evidence Checker

**Updated:** 2026-06-06

Automated agent that ingests new papers/trials, scores them against the [patient profile](patient-profile-cn1-mibc.md), and updates the [evidence comparison](cn1-mibc-evidence-comparison.md).

## Quick Start (Windows PowerShell)

```powershell
cd c:\dev\cancer

# RECOMMENDED: Click-to-run web UI
python scripts\agent_server.py
# Browser opens http://localhost:8765
# Click "Search for new studies" to validate + search PubMed + ClinicalTrials.gov + merge new data

# CLI alternatives
python scripts\research_agent.py --compare
python scripts\research_agent.py --watch-trials
python scripts\research_agent.py --source "https://clinicaltrials.gov/study/NCT05239624"
```

### Web UI buttons

| Button | Action |
|--------|--------|
| Search for new studies | Full scan: validate → PubMed + CT.gov search → add to `papers_index.json` → refresh NCT trials |
| Validate existing data | Check trials.json / papers_index.json for gaps and errors |
| Refresh watched trials | Update status and enrollment for 9 tracked NCT IDs |

## What the Agent Does

1. **Fetch / read** source into `raw/bladder-cancer/YYYY-MM-DD-slug.md`
2. **Extract** structured fields: trial name, NCT, phase, setting, total N, cN1/cN+ count, treatment, endpoints, HRs, pCR rates
3. **Score fit** against target profile (Tier A/B/C/D)
4. **Append** findings to `data/evidence_registry.csv`
5. **Optionally compile** wiki updates when `--compile-wiki` is passed

## Fit Scoring Rubric

| Tier | Criteria | Score 0–100 |
|------|----------|-------------|
| A | Perioperative/neoadjuvant; cN1 M0 MIBC; cystectomy planned; EV+pembro or direct comparator | 90–100 |
| B | Perioperative MIBC with some cN1 patients OR strong nodal subgroup | 60–89 |
| B− | Metastatic LN-only or perioperative but wrong drug/population | 40–59 |
| C | Wrong setting (adjuvant only, metastatic 1L, N0-only foundational) | 10–39 |
| D | Meta-analysis / retrospective cN+ | 20–50 (context only) |

## Tracked Studies (Seed Registry)

Pre-loaded in `data/evidence_registry.csv`:

- EV-ECLIPSE, EV-302, EV-103, KEYNOTE-905, NIAGARA
- SWOG 8710, BA06, NAC meta-analyses
- CheckMate 274, AMBASSADOR, JAVELIN 100, CheckMate 901

## Agent Commands

| Command | Purpose |
|---------|---------|
| `python scripts/research_agent.py --list` | Show registry sorted by fit score |
| `python scripts/research_agent.py --compare` | Print patient-count comparison table |
| `python scripts/research_agent.py --source <url\|file>` | Ingest new source |
| `python scripts/research_agent.py --watch-trials` | Refresh ClinicalTrials.gov status for known NCT IDs |

## See Also

- [Evidence Comparison](cn1-mibc-evidence-comparison.md)
- [Patient Profile](patient-profile-cn1-mibc.md)
