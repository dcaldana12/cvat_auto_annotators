#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FUNCTION_DIR="$SCRIPT_DIR/nuclio"
FUNCTION_FILE="$FUNCTION_DIR/function.yaml"

# Load config.env next to this script, or the file selected with LLM_CONFIG.
# Values from the file are exported and take precedence over shell variables.
CONFIG_FILE=""
if [[ -n "${LLM_CONFIG:-}" ]]; then
  if [[ ! -f "$LLM_CONFIG" ]]; then
    echo "Error: LLM_CONFIG points to a missing file: $LLM_CONFIG" >&2
    exit 1
  fi
  CONFIG_FILE="$LLM_CONFIG"
elif [[ -f "$SCRIPT_DIR/config.env" ]]; then
  CONFIG_FILE="$SCRIPT_DIR/config.env"
fi

if [[ -n "$CONFIG_FILE" ]]; then
  echo "Loading config from $CONFIG_FILE"
  set -a
  # shellcheck disable=SC1090
  source "$CONFIG_FILE"
  set +a
fi

CVAT_NETWORK="${CVAT_NETWORK:-cvat_cvat}"

if ! command -v nuctl >/dev/null 2>&1; then
  echo "Error: nuctl is not installed or not in PATH." >&2
  exit 1
fi

if [[ ! -f "$FUNCTION_FILE" ]]; then
  echo "Error: $FUNCTION_FILE not found." >&2
  exit 1
fi

api_key="${LLM_API_KEY:-${OPENAI_API_KEY:-}}"
if [[ -z "$api_key" ]]; then
  echo "Warning: LLM_API_KEY/OPENAI_API_KEY is not set." >&2
  echo "Set it in config.env (copy config.env.example first) or export it." >&2
  echo "Hosted endpoints will reject the request; local endpoints may work without a key." >&2
fi

# The project is created by CVAT's deploy script too; ignore errors if it exists.
nuctl create project cvat --platform local >/dev/null 2>&1 || true

env_args=()
if [[ -n "$api_key" ]]; then
  env_args+=(--env "LLM_API_KEY=$api_key")
fi

for var in \
  LLM_BASE_URL \
  LLM_MODEL \
  LLM_PROMPT \
  LLM_LABELS \
  LLM_COORDINATES \
  LLM_BOX_FORMAT \
  LLM_THRESHOLD \
  LLM_TIMEOUT \
  LLM_MAX_RETRIES \
  LLM_MAX_TOKENS \
  LLM_MAX_DETECTIONS \
  LLM_TEMPERATURE \
  LLM_IMAGE_DETAIL \
  LLM_JPEG_QUALITY \
  LLM_EXTRA_HEADERS; do
  value="${!var:-}"
  if [[ -n "$value" ]]; then
    env_args+=(--env "$var=$value")
  fi
done

nuctl deploy \
  --project-name cvat \
  --path "$FUNCTION_DIR" \
  --file "$FUNCTION_FILE" \
  --platform local \
  --env CVAT_FUNCTIONS_REDIS_HOST=cvat_redis_ondisk \
  --env CVAT_FUNCTIONS_REDIS_PORT=6666 \
  "${env_args[@]}" \
  --platform-config "{\"attributes\": {\"network\": \"$CVAT_NETWORK\"}}"

nuctl get function --platform local
