# Lovable App Prompt — MIBC cN1 Evidence Explorer

Copy everything below the line into Lovable as your initial prompt. Upload the JSON files from `c:\dev\cancer\data\` and PNG files from `c:\dev\cancer\visualizations\` as project assets (or paste JSON contents into Lovable's data store).

---

## PROMPT START

Build a **premium medical evidence explorer** web app for a specific bladder cancer patient profile and their oncology team. The app must feel like a **clinical decision intelligence tool** — not a generic dashboard. Think: clean medical UI (similar to Flatiron/OncoKB polish), calm typography, high information density without clutter.

### App name
**NodePositive MIBC Evidence Explorer**

### Target user
Family member / advocate preparing for an oncology consultation about **perioperative systemic therapy before cystectomy** for:

> **pT2 high-grade muscle-invasive urothelial carcinoma · L1 (lymphovascular invasion) · PET-positive external iliac lymph node · cN1 cM0 · no distant metastases**

### Core purpose
Help the user **compare clinical trial evidence**, see **how many patients in each study match this exact profile**, understand **interpretations and limitations**, and build a **structured argument** for the oncologist visit.

---

## DATA FILES (import these)

Use these JSON files as the app's data layer. Load at build time or via static import.

### 1. `patient_profile.json`
Patient clinical profile, cisplatin-eligible vs ineligible scenarios, key questions.

### 2. `trials.json`
Full trial registry with:
- `trials[]` — 12 studies with phase, setting, total_n, cn1_cn_plus_n, fit_tier, fit_score, efficacy objects, interpretations
- `categories[]` — color-coded treatment categories
- `fit_tiers{}` — tier definitions A, B, B-, C, D

### 3. `interpretations.json`
- `sections[]` — narrative interpretations per theme
- `talking_points_for_oncologist[]` — bullet list for visit
- `ui_copy` — disclaimer, banners, tier legend

### 4. Reference images (from `visualizations/` folder)
Use as seed/reference or recreate interactively with Recharts:
- `01_cn1_patient_counts.png` — bar chart of matching patient N per trial
- `02_fit_scores.png` — horizontal bar relevance scores
- `03_ev302_ln_only_orr.png` — ORR comparison EV-302 LN-only
- `04_hazard_ratio_forest.png` — HR forest plot
- `05_pcr_rates.png` — pCR across perioperative trials
- `06_category_distribution.png` — pie of evidence categories
- `07_pathway_evidence.png` — pathway strength by scenario

---

## INFORMATION ARCHITECTURE — 6 PAGES

### Page 1: Overview (Home)
**Hero banner** with patient profile chips: `pT2` `HG` `L1` `cN1` `cM0` `PET+ external iliac`

**Headline card** — pull from `interpretations.sections[id=headline]`

**4 stat cards:**
| Stat | Value | Subtext |
|------|-------|---------|
| Best design match | EV-ECLIPSE | n≈23, Tier A |
| Strongest EV+pembro data | EV-302 LN-only | n=207 (wrong setting) |
| Approved perioperative IO | NIAGARA | n=58 cN1 subgroup |
| Czech NAC standard cN1 RCT data | 0 patients | SWOG 8710 was N0 only |

**Interactive bar chart** (Recharts): X = trial name, Y = `cn1_cn_plus_n`, color by `fit_tier`, tooltip shows total_n and match_pct.

**Quick scenario toggle** at top: `Cisplatin-eligible` | `Cisplatin-ineligible` — changes highlighted recommendations below.

**Disclaimer footer** from `interpretations.ui_copy.disclaimer`

---

### Page 2: Trial Explorer (main data table)
Sortable, filterable **data table** of all trials from `trials.json`:

**Columns:** Priority | Study | Phase | Setting | Total N | cN1/cN+ n | Match % | Fit Tier (badge) | Fit Score | Status

**Filters:**
- Fit tier (multi-select: A, B, B-, C, D)
- Category (EV+pembro, Standard NAC, Perioperative IO, Adjuvant, Retro)
- Setting toggle: Perioperative only | All
- Search by study name / NCT

**Row click** → opens Trial Detail drawer (Page 3 pattern)

**Visual:** horizontal bar chart of fit_score sorted descending (same data as `02_fit_scores.png`)

---

### Page 3: Trial Detail (slide-over panel or dedicated route `/trial/:id`)
For each trial show:

1. **Header:** study_id, NCT link (external), phase badge, status, fit tier badge with score
2. **Patient match card:**
   - Large numbers: `cn1_cn_plus_n` / `total_n` / `match_pct`
   - Progress bar showing what % of trial matches target profile
   - Label: `cn1_cn_plus_label` if present
3. **Treatment arms** from `treatment` object
4. **Efficacy section** (if `efficacy` exists):
   - For EV-302: tabbed Overall | LN-only subgroup with ORR, PFS, OS, HR + CI
   - For NIAGARA: Overall + cN1 subgroup with NS warning if CI crosses 1
   - For KEYNOTE-905: EFS, OS, pCR with 2-year rates
   - Forest plot dot for HR if available
5. **Eligibility highlights** (bullet list)
6. **Limitation for this patient** (amber callout)
7. **Interpretation** (blue callout) — plain language, 2-3 sentences
8. **Source link** button → `source_url`

---

### Page 4: Visual Evidence Dashboard
Recreate all 7 charts **interactively** with Recharts (not static images):

1. **cN1 patient counts** — grouped bar, show n and % of total
2. **Fit scores** — horizontal bar, color by tier
3. **EV-302 LN-only ORR** — grouped bar ORR vs CR, EV+P vs chemo
4. **Hazard ratio forest** — custom chart: point + CI whisker, vertical line at HR=1, color by category. Include NS label when CI crosses 1
5. **pCR comparison** — KEYNOTE-905, NIAGARA, SWOG approximate
6. **Category pie** — evidence distribution
7. **Pathway evidence** — horizontal bars for cisplatin scenarios

Each chart needs:
- Title with specific metric
- Axis labels with units
- Caption: data source + date
- Tooltip with exact values

---

### Page 5: Clinical Interpretation & Argument Builder
**Two-column layout:**

**Left: Narrative sections** from `interpretations.sections[]` — accordion cards:
- Best design match (EV-ECLIPSE)
- Strongest efficacy (EV-302)
- Approved alternative (NIAGARA)
- Czech standard (SWOG)
- Evidence gap (EV-304)
- Adjuvant backup

**Right: Argument Builder** (interactive checklist)
Pre-populated talking points from `talking_points_for_oncologist`. User can:
- Check/uncheck points to include in visit brief
- Add custom notes (localStorage)
- **Export button** → generates printable PDF or copy-to-clipboard markdown summary

**Decision matrix table** (key feature):

| If patient is... | 1st line evidence | Matching n | Strength | Gap |
|------------------|-------------------|------------|----------|-----|
| Cisplatin-eligible | NIAGARA | 58 cN1 | Phase 3 approved | cN1 subgroup NS |
| Cisplatin-eligible | EV+pembro | EV-ECLIPSE ~23 | Phase 2 only | No phase 3 |
| Cisplatin-ineligible | KEYNOTE-905 | ~17 cN1 | Phase 3 positive | Tiny cN1 subset |
| Any | EV-302 LN-only | 207 | Strong HRs | Metastatic setting |

---

### Page 6: Comparison Tool
**Select 2-4 trials** via multi-select dropdown → side-by-side comparison:

Compare fields:
- total_n, cn1_cn_plus_n, match_pct, fit_tier, fit_score
- phase, setting, treatment
- key efficacy endpoints
- limitation_for_patient
- interpretation

**Visual diff:** highlight where one trial is stronger/weaker for the target profile. Use green/red only for fit_score comparison, not for medical "better/worse" claims.

**"Closest match to patient"** badge on EV-ECLIPSE automatically.

---

## DESIGN SYSTEM

### Aesthetic
- **Medical-trust aesthetic**: white/off-white background `#FAFBFC`, cards with subtle border `#E2E8F0`, no gradients, no shadows heavier than `shadow-sm`
- **Typography**: Inter or Source Sans 3. Headings semibold, body 15-16px, excellent line-height
- **Primary accent**: deep teal `#0F766E` (trust/clinical)
- **Secondary**: slate `#475569`
- **Tier badge colors:**
  - A: green `#16A34A`
  - B: emerald `#059669`
  - B-: amber `#D97706`
  - C: slate `#94A3B8`
  - D: light slate `#CBD5E1`

### Components to build
- `FitTierBadge` — colored pill with tooltip explaining tier
- `PatientMatchMeter` — progress bar + fraction
- `TrialCard` — compact card for grid views
- `HRForestRow` — point estimate + CI line
- `ScenarioToggle` — cisplatin eligible/ineligible
- `DisclaimerBanner` — persistent subtle footer
- `NCTLink` — external link icon + NCT number
- `StatCard` — number + label + subtext

### UX requirements
- **Mobile responsive** — tables become cards on mobile
- **Keyboard accessible** — all interactive elements
- **Tooltips** on every medical acronym first use (MIBC, pCR, EFS, HR, ORR, NAC, EV, etc.)
- **No alarmist language** — factual, balanced, always show limitations alongside efficacy
- **Loading states** — skeleton cards (data is static JSON, but simulate for polish)

---

## TECH STACK (Lovable defaults)
- React + TypeScript + Tailwind + shadcn/ui
- Recharts for all visualizations
- React Router for 6 pages
- Data: import JSON from `/src/data/` (copy the 3 JSON files there)
- State: Zustand or React context for scenario toggle + comparison selection + argument builder checks
- localStorage for user notes and checklist state

---

## SAMPLE DATA BINDING (TypeScript types)

```typescript
type FitTier = 'A' | 'B' | 'B-' | 'C' | 'D' | 'B-pending' | 'C-adj';

interface Trial {
  id: string;
  study_id: string;
  nct_id?: string;
  category: string;
  phase: number | string;
  priority: number | null;
  setting: string;
  total_n: number | null;
  cn1_cn_plus_n: number | null;
  cn1_cn_plus_label?: string;
  match_pct: number | null;
  fit_tier: FitTier;
  fit_score: number;
  treatment?: { experimental: string; comparator: string | null };
  efficacy?: Record<string, unknown>;
  limitation_for_patient?: string;
  interpretation: string;
  status?: string;
  source_url?: string;
}
```

---

## PRIORITY IMPLEMENTATION ORDER

1. Load JSON data + Overview page with stat cards + bar chart
2. Trial Explorer table with filters + tier badges
3. Trial Detail drawer with patient match meter + efficacy
4. Visual Evidence Dashboard (all Recharts)
5. Interpretation page + argument builder with export
6. Comparison tool

---

## CRITICAL CONTENT RULES

- Always distinguish **perioperative cN1 cM0** (curative) from **metastatic LN-only** (EV-302)
- Always note **NIAGARA cN1 n=58 subgroup was NOT statistically significant**
- Always note **SWOG 8710 had 0 cN1 patients**
- Never claim EV+pembro is standard of care for cisplatin-eligible cN1 perioperative — say "investigational" or "phase 2/3 pending"
- Include disclaimer on every page

---

## PROMPT END
