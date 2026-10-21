#!/usr/bin/env bash
set -euo pipefail
SESSION_ID="${1:?Usage: $0 SESSION_ID}"
curl -sS -X POST "http://localhost:8000/sessions/${SESSION_ID}/reconstruct" | python3 -m json.tool
