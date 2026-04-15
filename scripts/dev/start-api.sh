#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../../api"
WEB_FRONTEND_URL="${WEB_FRONTEND_URL:-http://127.0.0.1:5185}" uv run console-api
