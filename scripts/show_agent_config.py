#!/usr/bin/env python3
"""Print Lovable env values (AGENT_API_KEY only — for copying into Lovable settings)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from env_config import agent_api_key, agent_public_url, load_dotenv

load_dotenv()

key = agent_api_key()
url = agent_public_url()

print("Copy these into Lovable > Settings > Environment variables:\n")
print(f"VITE_AGENT_API_KEY={key or '(not set — run show after .env has AGENT_API_KEY)'}")
print(f"VITE_AGENT_API_URL={url or '(set after ngrok - AGENT_PUBLIC_URL in .env)'}")
print("\nBackend .env location: c:\\dev\\cancer\\.env")
print("Start server: python scripts\\agent_server.py")
print("Expose: ngrok http 8765")
