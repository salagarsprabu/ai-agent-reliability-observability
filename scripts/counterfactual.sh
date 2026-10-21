#!/usr/bin/env bash
set -euo pipefail
SESSION_ID="${1:?Usage: $0 SESSION_ID}"
curl -sS -X POST "http://localhost:8000/sessions/${SESSION_ID}/counterfactual" \
  -H 'Content-Type: application/json' -d '{"policy_version":"2.0.0"}' | python3 -m json.tool
