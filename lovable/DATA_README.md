# Lovable Data Package

Upload these files to your Lovable project under `src/data/`:

| File | Description |
|------|-------------|
| `patient_profile.json` | Target patient clinical profile |
| `trials.json` | 12 trials with efficacy, patient counts, fit scores |
| `interpretations.json` | Narrative text, talking points, UI copy |

Reference charts in `../visualizations/` — recreate interactively in Lovable with Recharts using values from `trials.json`.

## Key numbers for charts

### cN1 / node-positive patient counts
| Trial | total_n | cn1_cn_plus_n |
|-------|--------:|--------------:|
| EV-ECLIPSE | 23 | 23 |
| EV-302 LN-only | 886 | 207 |
| NIAGARA cN1 | 1063 | 58 |
| KEYNOTE-905 cN1 | 344 | 17 |
| CheckMate 274 pN1 | 709 | 143 |
| SWOG 8710 | 307 | 0 |

### Hazard ratios
| Endpoint | HR | 95% CI |
|----------|---:|--------|
| EV-302 LN-only PFS | 0.47 | 0.32–0.70 |
| EV-302 LN-only OS | 0.51 | 0.33–0.79 |
| NIAGARA overall EFS | 0.68 | 0.56–0.82 |
| NIAGARA cN1 EFS | 0.75 | 0.22–1.64 (NS) |
| KEYNOTE-905 EFS | 0.40 | 0.28–0.57 |
| KEYNOTE-905 OS | 0.50 | 0.33–0.74 |

### pCR rates
| Trial | Experimental | Control |
|-------|-------------:|--------:|
| KEYNOTE-905 | 57.1% | 8.6% |
| NIAGARA | 37.3% | 27.5% |
