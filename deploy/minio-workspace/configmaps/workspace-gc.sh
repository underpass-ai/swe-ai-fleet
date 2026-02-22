#!/bin/sh
set -eu

require_env() {
  name="$1"
  eval "value=\${$name:-}"
  if [ -z "$value" ]; then
    echo "Missing env var: ${name}" >&2
    exit 1
  fi
}

require_env "MINIO_ENDPOINT"
require_env "WORKSPACE_ACCESS_KEY"
require_env "WORKSPACE_SECRET_KEY"
require_env "BUCKET"
require_env "PREFIX"
require_env "RETENTION_DAYS"

alias_name="ws"
dry_run="${GC_DRY_RUN:-false}"

mc alias set "${alias_name}" "${MINIO_ENDPOINT}" "${WORKSPACE_ACCESS_KEY}" "${WORKSPACE_SECRET_KEY}"

echo "GC starting. bucket=${BUCKET} prefix=${PREFIX} retention_days=${RETENTION_DAYS} dry_run=${dry_run}"

# Preferred mode: strict lastModified comparison with mc + jq.
if command -v jq >/dev/null 2>&1; then
  cutoff_epoch="$(date -u -d "${RETENTION_DAYS} days ago" +%s)"
  echo "Using jq mode. cutoff_epoch=${cutoff_epoch}"

  mc ls --recursive --json "${alias_name}/${BUCKET}/${PREFIX}" \
    | jq -r --argjson cutoff "${cutoff_epoch}" '
        select(.type=="file")
        | . as $o
        | ($o.lastModified | sub("\\.[0-9]+Z$"; "Z") | fromdateiso8601) as $ts
        | select($ts < $cutoff)
        | $o.key
      ' \
    | while IFS= read -r key; do
        [ -z "${key}" ] && continue
        echo "Deleting ${BUCKET}/${key}"
        if [ "${dry_run}" != "true" ]; then
          mc rm --force "${alias_name}/${BUCKET}/${key}"
        fi
      done
else
  # Fallback mode: relies on mc's own object age filter.
  echo "jq not found in image; using mc find --older-than fallback"
  mc find "${alias_name}/${BUCKET}/${PREFIX}" --type f --older-than "${RETENTION_DAYS}d" --print \
    | while IFS= read -r path; do
        [ -z "${path}" ] && continue
        echo "Deleting ${path}"
        if [ "${dry_run}" != "true" ]; then
          mc rm --force "${path}"
        fi
      done
fi

echo "GC completed."
