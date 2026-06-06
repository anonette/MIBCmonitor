#!/usr/bin/env python3
"""Pull live agent JSON into lovable/ for static Lovable src/data/ upload."""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOVABLE = ROOT / "lovable"
sys.path.insert(0, str(ROOT / "scripts"))

from env_config import agent_api_key, agent_port, load_dotenv  # noqa: E402

load_dotenv()

BASE = f"http://127.0.0.1:{agent_port()}"
KEY = agent_api_key()

ENDPOINTS = {
    "trials.json": "/api/trials?wrap=1",
    "papers_index.json": "/api/papers?wrap=1",
    "interpretations.json": "/api/interpretations",
    "patient_profile.json": "/api/patient-profile",
    "glossary_pathway.json": "/api/glossary-pathway",
    "patients_like_you.json": "/api/patients-like-you",
    "dashboard_charts.json": "/api/dashboard-charts",
}


def fetch(path: str) -> dict | list:
    req = urllib.request.Request(f"{BASE}{path}", headers={"X-API-Key": KEY})
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def main() -> None:
    print(f"Agent: {BASE}")
    for filename, path in ENDPOINTS.items():
        data = fetch(path)
        out = LOVABLE / filename
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"  wrote {out.relative_to(ROOT)}")
    print("Done. Upload lovable/*.json to Lovable src/data/ or let Lovable curl the same endpoints.")


if __name__ == "__main__":
    main()
