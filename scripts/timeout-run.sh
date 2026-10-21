#!/usr/bin/env bash
set -euo pipefail
curl -sS -X POST http://localhost:8000/agent/run \
  -H 'Content-Type: application/json' \
  -d '{"customer_reference":"CUST-98421","conversation_id":"conv-timeout-001","query":"Please check whether I can increase my personal loan limit from 20000 to 45000.","requested_limit":45000,"failure_mode":"risk_timeout","policy_version":"1.0.0"}' | tee /tmp/timeout-response.json | python3 -m json.tool
