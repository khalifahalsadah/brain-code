"""Push n8n workflow JSON files to the n8n instance via REST API.

Usage:
    uv run python n8n/push.py append.workflow.json
    uv run python n8n/push.py synthesize.workflow.json
    uv run python n8n/push.py --all

Reads N8N_BASE_URL and N8N_API_KEY from .env (project root).
Replaces __TELEGRAM_CRED_ID__ / __TELEGRAM_CRED_NAME__ from .env if set
(TELEGRAM_CRED_ID, TELEGRAM_CRED_NAME).

If a workflow with the same name already exists, this script PATCHes it.
Otherwise it CREATEs a new one.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import urllib.request
import urllib.error
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
load_dotenv(PROJECT_ROOT / ".env")

BASE_URL = os.environ["N8N_BASE_URL"].rstrip("/")
API_KEY = os.environ["N8N_API_KEY"]
TG_CRED_ID = os.environ.get("TELEGRAM_CRED_ID", "__TELEGRAM_CRED_ID__")
TG_CRED_NAME = os.environ.get("TELEGRAM_CRED_NAME", "__TELEGRAM_CRED_NAME__")
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "__TELEGRAM_CHAT_ID__")


def _request(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "X-N8N-API-KEY": API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "brain-code/0.1 (+https://github.com/khalifah/brain-code)",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} → HTTP {e.code}: {body_text}") from None


def find_workflow_by_name(name: str) -> dict | None:
    data = _request("GET", "/api/v1/workflows?limit=250")
    for wf in data.get("data", []):
        if wf.get("name") == name:
            return wf
    return None


def push_workflow(file_path: Path) -> None:
    raw = file_path.read_text(encoding="utf-8")
    raw = raw.replace("__TELEGRAM_CRED_ID__", TG_CRED_ID)
    raw = raw.replace("__TELEGRAM_CRED_NAME__", TG_CRED_NAME)
    raw = raw.replace("__TELEGRAM_CHAT_ID__", TG_CHAT_ID)
    workflow = json.loads(raw)
    name = workflow["name"]

    # n8n API expects only certain fields on create
    payload = {
        "name": name,
        "nodes": workflow["nodes"],
        "connections": workflow["connections"],
        "settings": workflow.get("settings", {"executionOrder": "v1"}),
    }

    existing = find_workflow_by_name(name)
    if existing:
        wf_id = existing["id"]
        result = _request("PUT", f"/api/v1/workflows/{wf_id}", payload)
        print(f"updated: {name} (id={result['id']})")
    else:
        result = _request("POST", "/api/v1/workflows", payload)
        print(f"created: {name} (id={result['id']})")


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 1
    if argv[0] == "--all":
        files = sorted(ROOT.glob("*.workflow.json"))
    else:
        files = [ROOT / a if not Path(a).is_absolute() else Path(a) for a in argv]
    for f in files:
        if not f.exists():
            print(f"missing: {f}", file=sys.stderr)
            return 2
        push_workflow(f)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
