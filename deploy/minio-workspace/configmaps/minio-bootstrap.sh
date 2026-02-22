#!/usr/bin/env bash
set -euo pipefail

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing env var: ${name}" >&2
    exit 1
  fi
}

require_env "MINIO_ENDPOINT"
require_env "MINIO_ROOT_USER"
require_env "MINIO_ROOT_PASSWORD"
require_env "WORKSPACE_ACCESS_KEY"
require_env "WORKSPACE_SECRET_KEY"

WORKSPACES_BUCKET="${WORKSPACES_BUCKET:-swe-workspaces}"
CACHE_BUCKET="${CACHE_BUCKET:-swe-workspaces-cache}"
META_BUCKET="${META_BUCKET:-swe-workspaces-meta}"

alias_name="ws"
mc alias set "${alias_name}" "${MINIO_ENDPOINT}" "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}"

buckets=(
  "${WORKSPACES_BUCKET}"
  "${CACHE_BUCKET}"
  "${META_BUCKET}"
)

for b in "${buckets[@]}"; do
  echo "Ensuring bucket ${b}"
  mc mb --ignore-existing "${alias_name}/${b}"
done

echo "Ensuring workspace service user"
mc admin user add "${alias_name}" "${WORKSPACE_ACCESS_KEY}" "${WORKSPACE_SECRET_KEY}" || true

cat >/tmp/workspace-policy.json <<EOF_POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "WorkspaceBucketsRW",
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetBucketLocation",
        "s3:ListBucketMultipartUploads"
      ],
      "Resource": [
        "arn:aws:s3:::${WORKSPACES_BUCKET}",
        "arn:aws:s3:::${CACHE_BUCKET}",
        "arn:aws:s3:::${META_BUCKET}"
      ]
    },
    {
      "Sid": "WorkspaceObjectsRW",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:AbortMultipartUpload",
        "s3:ListMultipartUploadParts"
      ],
      "Resource": [
        "arn:aws:s3:::${WORKSPACES_BUCKET}/*",
        "arn:aws:s3:::${CACHE_BUCKET}/*",
        "arn:aws:s3:::${META_BUCKET}/*"
      ]
    }
  ]
}
EOF_POLICY

mc admin policy create "${alias_name}" workspace-svc-policy /tmp/workspace-policy.json || true
mc admin policy attach "${alias_name}" workspace-svc-policy --user "${WORKSPACE_ACCESS_KEY}" || true

echo "Bootstrap completed."
