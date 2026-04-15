#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRODUCT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RUNTIME_DIR="$PRODUCT_ROOT/artifacts/dev-runtime"

API_PORT=8025
WEB_PORT=5185

API_PID_FILE="$RUNTIME_DIR/console-api.pid"
WEB_PID_FILE="$RUNTIME_DIR/console-web.pid"
API_LOG_FILE="$RUNTIME_DIR/console-api.log"
WEB_LOG_FILE="$RUNTIME_DIR/console-web.log"

mkdir -p "$RUNTIME_DIR"

is_running() {
  local pid="$1"
  kill -0 "$pid" 2>/dev/null
}

listening_pid() {
  local port="$1"
  if ! command -v lsof >/dev/null 2>&1; then
    return 0
  fi
  lsof -ti "tcp:${port}" -sTCP:LISTEN 2>/dev/null | head -n 1 || true
}

remove_pid_file() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]]; then
    rm -f "$pid_file"
  fi
}

stop_from_pid_file() {
  local name="$1"
  local pid_file="$2"

  if [[ ! -f "$pid_file" ]]; then
    return 0
  fi

  local pid
  pid="$(cat "$pid_file" 2>/dev/null || true)"
  if [[ -z "$pid" ]]; then
    remove_pid_file "$pid_file"
    return 0
  fi

  if ! is_running "$pid"; then
    remove_pid_file "$pid_file"
    return 0
  fi

  echo "Stopping ${name} (pid=${pid})"
  kill "$pid" 2>/dev/null || true

  for _ in $(seq 1 30); do
    if ! is_running "$pid"; then
      remove_pid_file "$pid_file"
      return 0
    fi
    sleep 0.2
  done

  echo "Force stopping ${name} (pid=${pid})"
  kill -9 "$pid" 2>/dev/null || true
  remove_pid_file "$pid_file"
}

ensure_port_free() {
  local name="$1"
  local port="$2"
  local pid_file="$3"
  local pid=""
  local listening=""

  listening="$(listening_pid "$port")"
  if [[ -z "$listening" ]]; then
    return 0
  fi

  if [[ -f "$pid_file" ]]; then
    pid="$(cat "$pid_file" 2>/dev/null || true)"
    if [[ -n "$pid" && "$pid" == "$listening" ]]; then
      stop_from_pid_file "$name" "$pid_file"
      return 0
    fi
  fi

  echo "Force stopping unmanaged process on port ${port} (pid=${listening})"
  kill "$listening" 2>/dev/null || true

  for _ in $(seq 1 30); do
    if [[ -z "$(listening_pid "$port")" ]]; then
      return 0
    fi
    sleep 0.2
  done

  echo "Force killing unmanaged process on port ${port} (pid=${listening})"
  kill -9 "$listening" 2>/dev/null || true

  for _ in $(seq 1 10); do
    if [[ -z "$(listening_pid "$port")" ]]; then
      return 0
    fi
    sleep 0.2
  done

  echo "Port ${port} is still occupied after force kill." >&2
  exit 1
}

start_service() {
  local name="$1"
  local pid_file="$2"
  local log_file="$3"
  shift 3

  : > "$log_file"
  nohup "$@" >>"$log_file" 2>&1 &
  local pid=$!
  echo "$pid" > "$pid_file"
  echo "Started ${name} (pid=${pid})"
}

wait_for_port() {
  local name="$1"
  local port="$2"
  local log_file="$3"

  for _ in $(seq 1 60); do
    if [[ -n "$(listening_pid "$port")" ]]; then
      return 0
    fi
    sleep 0.5
  done

  echo "${name} did not become ready on port ${port}." >&2
  echo "Recent log output:" >&2
  tail -n 40 "$log_file" >&2 || true
  exit 1
}

sync_pid_file_to_listener() {
  local name="$1"
  local port="$2"
  local pid_file="$3"

  local listening=""
  listening="$(listening_pid "$port")"
  if [[ -z "$listening" ]]; then
    echo "${name} has no listening process on port ${port}." >&2
    exit 1
  fi

  echo "$listening" > "$pid_file"
}

verify_service_alive() {
  local name="$1"
  local port="$2"
  local pid_file="$3"
  local log_file="$4"

  for _ in $(seq 1 6); do
    local pid=""
    pid="$(cat "$pid_file" 2>/dev/null || true)"
    local listening=""
    listening="$(listening_pid "$port")"

    if [[ -n "$pid" && -n "$listening" ]]; then
      if is_running "$pid"; then
        if [[ "$pid" != "$listening" ]]; then
          echo "$listening" > "$pid_file"
        fi
        return 0
      fi
    fi
    sleep 0.5
  done

  echo "${name} failed post-start verification." >&2
  echo "Recent log output:" >&2
  tail -n 40 "$log_file" >&2 || true
  exit 1
}

stop_from_pid_file "console web" "$WEB_PID_FILE"
stop_from_pid_file "console api" "$API_PID_FILE"

ensure_port_free "console web" "$WEB_PORT" "$WEB_PID_FILE"
ensure_port_free "console api" "$API_PORT" "$API_PID_FILE"

start_service "console api" "$API_PID_FILE" "$API_LOG_FILE" bash "$SCRIPT_DIR/start-api.sh"
wait_for_port "console api" "$API_PORT" "$API_LOG_FILE"
sync_pid_file_to_listener "console api" "$API_PORT" "$API_PID_FILE"
verify_service_alive "console api" "$API_PORT" "$API_PID_FILE" "$API_LOG_FILE"

start_service "console web" "$WEB_PID_FILE" "$WEB_LOG_FILE" bash "$SCRIPT_DIR/start-web.sh"
wait_for_port "console web" "$WEB_PORT" "$WEB_LOG_FILE"
sync_pid_file_to_listener "console web" "$WEB_PORT" "$WEB_PID_FILE"
verify_service_alive "console web" "$WEB_PORT" "$WEB_PID_FILE" "$WEB_LOG_FILE"

echo
echo "Console restarted."
echo "API: http://127.0.0.1:${API_PORT}"
echo "Web: http://127.0.0.1:${WEB_PORT}"
echo "API log: ${API_LOG_FILE}"
echo "Web log: ${WEB_LOG_FILE}"
