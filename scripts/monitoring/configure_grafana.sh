#!/usr/bin/env bash
# Configure Grafana for microservices monitoring using HTTP API
# Idempotent: creates/updates datasources and folders.

set -euo pipefail

# --- Configuration (env vars) ---
GRAFANA_URL="${GRAFANA_URL:-https://grafana.swe-ai-fleet.underpassai.com}"
# Require API token (admin role)
GRAFANA_TOKEN="${GRAFANA_TOKEN:-}"

# Common datasources
PROM_URL="${PROM_URL:-http://prometheus.swe-ai-fleet.svc.cluster.local:9090}"
LOKI_URL="${LOKI_URL:-}"           # e.g. http://loki.swe-ai-fleet.svc.cluster.local:3100
TEMPO_URL="${TEMPO_URL:-}"         # e.g. http://tempo.swe-ai-fleet.svc.cluster.local:3200

# Folders and tags
FOLDER_NAME="${FOLDER_NAME:-Microservices}"
FOLDER_UID="${FOLDER_UID:-microservices}"

# --- Helpers ---
api() {
  local method="$1" path="$2" body="${3:-}"
  if [[ -z "$GRAFANA_TOKEN" ]]; then
    echo "GRAFANA_TOKEN is required (admin API token)" >&2
    exit 1
  fi
  local auth_hdr=( -H "Authorization: Bearer ${GRAFANA_TOKEN}" )
  if [[ -n "$body" ]]; then
    curl -sS -X "$method" "${GRAFANA_URL}${path}" \
      -H 'Content-Type: application/json' \
      "${auth_hdr[@]}" \
      -d "$body"
  else
    curl -sS -X "$method" "${GRAFANA_URL}${path}" \
      -H 'Content-Type: application/json' \
      "${auth_hdr[@]}"
  fi
}

upsert_prometheus_ds() {
  echo "==> Upserting Prometheus datasource at ${PROM_URL}"
  local payload
  payload=$(jq -n --arg url "$PROM_URL" '{
    name: "Prometheus",
    type: "prometheus",
    access: "proxy",
    url: $url,
    isDefault: true,
    jsonData: { httpMethod: "POST" }
  }')
  # Try by name: delete if exists, then create
  local existing
  existing=$(api GET "/api/datasources/name/Prometheus" || true)
  if jq -e '.id' <<<"$existing" >/dev/null 2>&1; then
    local id
    id=$(jq -r '.id' <<<"$existing")
    api DELETE "/api/datasources/${id}" >/dev/null || true
  fi
  api POST "/api/datasources" "$payload" | jq '.'
}

upsert_loki_ds() {
  [[ -z "$LOKI_URL" ]] && { echo "==> Skipping Loki (LOKI_URL not set)"; return 0; }
  echo "==> Upserting Loki datasource at ${LOKI_URL}"
  local payload
  payload=$(jq -n --arg url "$LOKI_URL" '{
    name: "Loki",
    type: "loki",
    access: "proxy",
    url: $url,
    jsonData: { }
  }')
  local existing
  existing=$(api GET "/api/datasources/name/Loki" || true)
  if jq -e '.id' <<<"$existing" >/dev/null 2>&1; then
    local id
    id=$(jq -r '.id' <<<"$existing")
    api DELETE "/api/datasources/${id}" >/dev/null || true
  fi
  api POST "/api/datasources" "$payload" | jq '.'
}

upsert_tempo_ds() {
  [[ -z "$TEMPO_URL" ]] && { echo "==> Skipping Tempo (TEMPO_URL not set)"; return 0; }
  echo "==> Upserting Tempo datasource at ${TEMPO_URL}"
  local payload
  payload=$(jq -n --arg url "$TEMPO_URL" '{
    name: "Tempo",
    type: "tempo",
    access: "proxy",
    url: $url,
    jsonData: { }
  }')
  local existing
  existing=$(api GET "/api/datasources/name/Tempo" || true)
  if jq -e '.id' <<<"$existing" >/dev/null 2>&1; then
    local id
    id=$(jq -r '.id' <<<"$existing")
    api DELETE "/api/datasources/${id}" >/dev/null || true
  fi
  api POST "/api/datasources" "$payload" | jq '.'
}

upsert_folder() {
  echo "==> Upserting folder '${FOLDER_NAME}' (uid=${FOLDER_UID})"
  # Try to get by UID
  local got
  got=$(api GET "/api/folders/${FOLDER_UID}" || true)
  if jq -e '.id' <<<"$got" >/dev/null 2>&1; then
    local upd
    upd=$(jq -n --arg title "$FOLDER_NAME" '{title: $title}')
    api PUT "/api/folders/${FOLDER_UID}" "$upd" | jq '.'
  else
    local create
    create=$(jq -n --arg title "$FOLDER_NAME" --arg uid "$FOLDER_UID" '{title: $title, uid: $uid}')
    api POST "/api/folders" "$create" | jq '.'
  fi
}

require_tools() {
  command -v curl >/dev/null || { echo "curl is required"; exit 1; }
  command -v jq >/dev/null || { echo "jq is required"; exit 1; }
}

main() {
  require_tools
  echo "Target Grafana: ${GRAFANA_URL}"
  # Smoke test auth
  api GET "/api/health" | jq '.'

  upsert_prometheus_ds
  upsert_loki_ds
  upsert_tempo_ds
  upsert_folder

  echo "✅ Grafana configuration completed."
}

main "$@"
