#!/usr/bin/env python3
"""Generate static visualizations for Lovable app and local review."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "trials.json"
OUT = ROOT / "visualizations"
OUT.mkdir(parents=True, exist_ok=True)

# Accessible palette
COLORS = {
    "A": "#16a34a",
    "B": "#059669",
    "B-": "#d97706",
    "C": "#94a3b8",
    "D": "#cbd5e1",
    "C-adj": "#7c3aed",
    "B-pending": "#2563eb",
}


def load_trials():
    with DATA.open(encoding="utf-8") as f:
        return json.load(f)["trials"]


def tier_color(tier: str) -> str:
    return COLORS.get(tier, "#64748b")


def chart_cn1_patient_counts():
    raw = load_trials()
    trials = []
    for t in raw:
        n = t.get("cn1_cn_plus_n") or 0
        if n > 0 or t["id"] in ("ev-eclipse", "ev-304"):
            entry = dict(t)
            if t["id"] == "ev-304" and not n:
                entry["cn1_cn_plus_n"] = t.get("cn1_cn_plus_n_estimated", 40)
                entry["study_id"] = "EV-304 (cN1 est.)"
            trials.append(entry)
    trials = sorted(trials, key=lambda t: -(t.get("cn1_cn_plus_n") or 0))

    names = [t["study_id"].replace(" / ", "\n") for t in trials]
    counts = [t.get("cn1_cn_plus_n") or 0 for t in trials]
    totals = [t.get("total_n") or 0 for t in trials]
    colors = [tier_color(t["fit_tier"]) for t in trials]

    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(names))
    bars = ax.bar(x, counts, color=colors, edgecolor="white", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(names, fontsize=8, rotation=0, ha="center")
    ax.set_ylabel("Patients with cN1 / node-positive overlap (n)")
    ax.set_title("Patients matching node-positive profile by trial\n(target: cN1 cM0 perioperative MIBC)")
    ax.set_ylim(0, max(counts) * 1.15)

    for i, (bar, total) in enumerate(zip(bars, totals)):
        h = bar.get_height()
        label = f"n={int(h)}"
        if total:
            label += f"\n({h/total*100:.1f}% of {total})" if total != h else ""
        ax.text(bar.get_x() + bar.get_width() / 2, h + 4, label, ha="center", va="bottom", fontsize=7)

    legend_patches = [mpatches.Patch(color=c, label=f"Tier {k}") for k, c in COLORS.items() if k in {t["fit_tier"] for t in trials}]
    ax.legend(handles=legend_patches, loc="upper right", fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "01_cn1_patient_counts.png", dpi=150)
    plt.close(fig)
    print(f"Wrote {OUT / '01_cn1_patient_counts.png'}")


def chart_fit_scores():
    trials = sorted(load_trials(), key=lambda t: -(t.get("fit_score") or 0))
    names = [t["study_id"][:22] for t in trials]
    scores = [t.get("fit_score") or 0 for t in trials]
    colors = [tier_color(t["fit_tier"]) for t in trials]

    fig, ax = plt.subplots(figsize=(11, 7))
    y = np.arange(len(names))
    ax.barh(y, scores, color=colors, height=0.7)
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=8)
    ax.set_xlabel("Evidence fit score (0-100) for target patient profile")
    ax.set_title("Trial relevance scoring\ncT2 cN1 cM0, perioperative intent")
    ax.set_xlim(0, 105)
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "02_fit_scores.png", dpi=150)
    plt.close(fig)
    print(f"Wrote {OUT / '02_fit_scores.png'}")


def chart_ev302_ln_only_orr():
    labels = ["ORR", "Complete response"]
    evp = [77.5, 50.0]
    chemo = [53.4, 26.2]
    x = np.arange(len(labels))
    w = 0.35

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(x - w/2, evp, w, label="EV+pembrolizumab (n=103)", color="#2563eb")
    ax.bar(x + w/2, chemo, w, label="Chemotherapy (n=104)", color="#94a3b8")
    ax.set_ylabel("Response rate (%)")
    ax.set_title("EV-302 lymph-node-only subgroup\n(not perioperative — metastatic setting)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 95)
    ax.legend()
    for i, (a, b) in enumerate(zip(evp, chemo)):
        ax.text(i - w/2, a + 2, f"{a}%", ha="center", fontsize=9)
        ax.text(i + w/2, b + 2, f"{b}%", ha="center", fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "03_ev302_ln_only_orr.png", dpi=150)
    plt.close(fig)
    print(f"Wrote {OUT / '03_ev302_ln_only_orr.png'}")


def chart_hazard_ratios():
    """Forest-style HR comparison for key trials."""
    entries = [
        ("EV-304 EFS (cis-eligible)", 0.53, 0.41, 0.70, "ev_pembro"),
        ("EV-304 OS (cis-eligible)", 0.65, 0.48, 0.89, "ev_pembro"),
        ("EV-302 LN-only PFS", 0.47, 0.32, 0.70, "ev_pembro"),
        ("EV-302 LN-only OS", 0.51, 0.33, 0.79, "ev_pembro"),
        ("NIAGARA overall EFS", 0.68, 0.56, 0.82, "perioperative"),
        ("NIAGARA cN1 EFS", 0.75, 0.22, 1.64, "perioperative"),
        ("KEYNOTE-905 EFS", 0.40, 0.28, 0.57, "ev_pembro"),
        ("KEYNOTE-905 OS", 0.50, 0.33, 0.74, "ev_pembro"),
        ("CheckMate 274 DFS", 0.70, 0.55, 0.90, "adjuvant"),
    ]
    color_map = {"ev_pembro": "#2563eb", "perioperative": "#059669", "adjuvant": "#7c3aed"}

    fig, ax = plt.subplots(figsize=(10, 6))
    y = np.arange(len(entries))
    for i, (label, hr, lo, hi, cat) in enumerate(entries):
        ax.plot([lo, hi], [i, i], color=color_map[cat], linewidth=2.5, solid_capstyle="round")
        ax.scatter([hr], [i], color=color_map[cat], s=80, zorder=5)
        sig = " (NS)" if lo <= 1 <= hi else ""
        ax.text(hi + 0.05, i, f"HR {hr}{sig}", va="center", fontsize=8)

    ax.axvline(1.0, color="#ef4444", linestyle="--", linewidth=1, alpha=0.8, label="No effect (HR=1)")
    ax.set_yticks(y)
    ax.set_yticklabels([e[0] for e in entries], fontsize=9)
    ax.set_xlabel("Hazard ratio (<1 favors experimental)")
    ax.set_title("Key efficacy hazard ratios across trials\n(subgroups where applicable)")
    ax.set_xlim(0, 1.8)
    ax.invert_yaxis()
    ax.legend(loc="lower right")
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "04_hazard_ratio_forest.png", dpi=150)
    plt.close(fig)
    print(f"Wrote {OUT / '04_hazard_ratio_forest.png'}")


def chart_retro_pn0_rates():
    """Retrospective pathologic nodal response in cN+ MIBC."""
    labels = ["Zargar-Shoshtar\n(all cN+)", "Zargar cN1\nsubset", "cN+ radiologic\n(n=76 chemo)", "NCDB\nypN0"]
    rates = [48, 56, 40.8, 35]
    colors = ["#059669", "#16a34a", "#0d9488", "#64748b"]

    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(labels))
    ax.bar(x, rates, color=colors, width=0.55)
    ax.set_ylabel("Pathologic nodal response (%)")
    ax.set_title("Retrospective pN0 / ypN0 rates after NAC in cN+ MIBC\n(cisplatin-based chemotherapy, not EV+pembro)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylim(0, 70)
    for i, r in enumerate(rates):
        ax.text(i, r + 2, f"{r}%", ha="center", fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "08_retro_pn0_rates.png", dpi=150)
    plt.close(fig)
    print(f"Wrote {OUT / '08_retro_pn0_rates.png'}")


def chart_perioperative_pcR():
    labels = ["EV-304\n(cis-eligible)", "KEYNOTE-905\n(cis-inel)", "NIAGARA\n(durva+GC)"]
    exp = [55.8, 57.1, 37.3]
    ctrl = [32.5, 8.6, 27.5]
    note = ["vs GC", "vs RC alone", "vs GC alone"]

    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(labels))
    ax.bar(x, exp, color=["#2563eb", "#059669", "#64748b"], width=0.55)
    ax.set_ylabel("Pathologic complete response (%)")
    ax.set_title("Pathologic complete response rates — perioperative trials")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylim(0, 70)
    for i, (e, c, n) in enumerate(zip(exp, ctrl, note)):
        txt = f"{e}%\n(ctrl {c}%)"
        ax.text(i, e + 2, txt, ha="center", fontsize=8)
        ax.text(i, -5, n, ha="center", fontsize=7, color="#64748b")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "05_pcr_rates.png", dpi=150)
    plt.close(fig)
    print(f"Wrote {OUT / '05_pcr_rates.png'}")


def chart_setting_distribution():
    trials = load_trials()
    settings = {}
    for t in trials:
        cat = t.get("category", "other")
        settings[cat] = settings.get(cat, 0) + 1

    labels = {
        "ev_pembro": "EV + Pembrolizumab",
        "standard_nac": "Standard NAC",
        "perioperative_io": "Perioperative IO+Chemo",
        "adjuvant_io": "Adjuvant IO",
        "metastatic": "Metastatic",
        "retrospective": "Retro / Meta",
    }
    cats = list(settings.keys())
    vals = [settings[c] for c in cats]
    lbls = [labels.get(c, c) for c in cats]
    cols = ["#2563eb", "#64748b", "#059669", "#7c3aed", "#d97706", "#94a3b8"][:len(cats)]

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.pie(vals, labels=lbls, autopct="%1.0f%%", colors=cols, startangle=140,
           textprops={"fontsize": 9})
    ax.set_title("Evidence base by treatment category\n(12 tracked studies)")
    fig.tight_layout()
    fig.savefig(OUT / "06_category_distribution.png", dpi=150)
    plt.close(fig)
    print(f"Wrote {OUT / '06_category_distribution.png'}")


def chart_argument_flow():
    """Simple decision-tree style summary as horizontal bars."""
    scenarios = [
        ("Cisplatin-eligible: NIAGARA (approved)", 72, "#059669"),
        ("Cisplatin-eligible: EV+pembro (EV-ECLIPSE / EV-304)", 75, "#2563eb"),
        ("Cisplatin-eligible: Standard NAC (SWOG/meta)", 35, "#64748b"),
        ("Cisplatin-ineligible: KEYNOTE-905 EV+pembro", 58, "#2563eb"),
        ("Any: EV-302 LN-only (metastatic activity)", 55, "#d97706"),
        ("Post-surgery: CheckMate 274 adjuvant", 30, "#7c3aed"),
    ]
    fig, ax = plt.subplots(figsize=(10, 5))
    names = [s[0] for s in scenarios]
    scores = [s[1] for s in scenarios]
    colors = [s[2] for s in scenarios]
    y = np.arange(len(names))
    ax.barh(y, scores, color=colors, height=0.65)
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=9)
    ax.set_xlabel("Evidence strength score for target profile")
    ax.set_title("Treatment pathway evidence strength by scenario")
    ax.set_xlim(0, 100)
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(OUT / "07_pathway_evidence.png", dpi=150)
    plt.close(fig)
    print(f"Wrote {OUT / '07_pathway_evidence.png'}")


def main():
    plt.style.use("seaborn-v0_8-whitegrid")
    chart_cn1_patient_counts()
    chart_fit_scores()
    chart_ev302_ln_only_orr()
    chart_hazard_ratios()
    chart_retro_pn0_rates()
    chart_perioperative_pcR()
    chart_setting_distribution()
    chart_argument_flow()
    print(f"\nAll visualizations saved to {OUT}")


if __name__ == "__main__":
    main()
