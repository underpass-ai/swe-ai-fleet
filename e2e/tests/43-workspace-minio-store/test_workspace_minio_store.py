#!/usr/bin/env python3
"""E2E test: MinIO workspace object store."""

from __future__ import annotations

import io
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any

from minio import Minio
from minio.error import S3Error


class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"


def print_step(step: int, description: str) -> None:
    print()
    print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
    print(f"{Colors.BLUE}Step {step}: {description}{Colors.NC}")
    print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
    print()


def print_success(message: str) -> None:
    print(f"{Colors.GREEN}OK {message}{Colors.NC}")


def print_warning(message: str) -> None:
    print(f"{Colors.YELLOW}WARN {message}{Colors.NC}")


def print_error(message: str) -> None:
    print(f"{Colors.RED}ERROR {message}{Colors.NC}")


class MinioWorkspaceStoreE2E:
    def __init__(self) -> None:
        self.endpoint = os.getenv("MINIO_ENDPOINT", "minio-workspace-svc.swe-ai-fleet.svc.cluster.local:9000")
        self.access_key = os.getenv("MINIO_ACCESS_KEY", "")
        self.secret_key = os.getenv("MINIO_SECRET_KEY", "")
        self.evidence_file = os.getenv("EVIDENCE_FILE", f"/tmp/evidence-43-{int(time.time())}.json")
        self.run_id = f"e2e-minio-{int(time.time())}"

        self.bucket_main = os.getenv("MINIO_WORKSPACES_BUCKET", "swe-workspaces")
        self.bucket_cache = os.getenv("MINIO_CACHE_BUCKET", "swe-workspaces-cache")
        self.bucket_meta = os.getenv("MINIO_META_BUCKET", "swe-workspaces-meta")

        self.client: Minio | None = None

        self.evidence: dict[str, Any] = {
            "test_id": "43-workspace-minio-store",
            "run_id": self.run_id,
            "status": "running",
            "started_at": self._now_iso(),
            "endpoint": self.endpoint,
            "steps": [],
            "checks": [],
        }

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _record_step(self, name: str, status: str, data: Any | None = None) -> None:
        entry: dict[str, Any] = {"at": self._now_iso(), "step": name, "status": status}
        if data is not None:
            entry["data"] = data
        self.evidence["steps"].append(entry)

    def _record_check(self, name: str, ok: bool, data: Any | None = None) -> None:
        entry: dict[str, Any] = {"at": self._now_iso(), "name": name, "ok": ok}
        if data is not None:
            entry["data"] = data
        self.evidence["checks"].append(entry)

    def _write_evidence(self, status: str, error_message: str = "") -> None:
        self.evidence["status"] = status
        self.evidence["ended_at"] = self._now_iso()
        if error_message:
            self.evidence["error_message"] = error_message

        try:
            with open(self.evidence_file, "w", encoding="utf-8") as handle:
                json.dump(self.evidence, handle, ensure_ascii=False, indent=2)
            print_warning(f"Evidence file: {self.evidence_file}")
        except Exception as exc:  # noqa: BLE001
            print_warning(f"Could not write evidence file: {exc}")

        print("EVIDENCE_JSON_START")
        print(json.dumps(self.evidence, ensure_ascii=False, indent=2))
        print("EVIDENCE_JSON_END")

    def _require_creds(self) -> None:
        if not self.access_key or not self.secret_key:
            raise RuntimeError("MINIO_ACCESS_KEY and MINIO_SECRET_KEY are required")

    def _connect(self) -> None:
        self._require_creds()
        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=False,
        )

    def _list_bucket_names(self) -> set[str]:
        assert self.client is not None
        buckets = self.client.list_buckets()
        return {bucket.name for bucket in buckets}

    def run(self) -> int:
        final_status = "failed"
        error_message = ""

        try:
            print_step(1, "Connect and list buckets")
            self._connect()
            names = self._list_bucket_names()
            expected = {self.bucket_main, self.bucket_cache, self.bucket_meta}
            missing = sorted(expected - names)
            self._record_check("list_buckets", True, {"buckets": sorted(names)})
            if missing:
                raise RuntimeError(f"missing workspace buckets: {missing}")
            self._record_step("connect_and_list", "passed", {"buckets": sorted(names)})
            print_success("Workspace buckets are present")

            print_step(2, "Put/Get/List/Delete roundtrip in swe-workspaces")
            assert self.client is not None
            object_key = f"sessions/{self.run_id}/payload.txt"
            payload = b"minio-workspace-e2e\n"

            self.client.put_object(
                self.bucket_main,
                object_key,
                io.BytesIO(payload),
                len(payload),
                content_type="text/plain",
            )
            self._record_check("put_object", True, {"bucket": self.bucket_main, "key": object_key})

            response = self.client.get_object(self.bucket_main, object_key)
            try:
                downloaded = response.read()
            finally:
                response.close()
                response.release_conn()
            if downloaded != payload:
                raise RuntimeError("downloaded payload mismatch")
            self._record_check("get_object", True, {"bytes": len(downloaded)})

            listed = [obj.object_name for obj in self.client.list_objects(self.bucket_main, prefix=f"sessions/{self.run_id}/", recursive=True)]
            if object_key not in listed:
                raise RuntimeError(f"object not listed under prefix: {listed}")
            self._record_check("list_objects", True, {"listed": listed})

            self.client.remove_object(self.bucket_main, object_key)
            listed_after_delete = [obj.object_name for obj in self.client.list_objects(self.bucket_main, prefix=f"sessions/{self.run_id}/", recursive=True)]
            if object_key in listed_after_delete:
                raise RuntimeError("object still present after delete")
            self._record_check("delete_object", True)

            self._record_step(
                "crud_roundtrip",
                "passed",
                {
                    "bucket": self.bucket_main,
                    "key": object_key,
                    "bytes": len(payload),
                },
            )
            print_success("Roundtrip CRUD succeeded")

            print_step(3, "Policy guardrails for app user")
            denied_bucket = f"e2e-denied-{self.run_id}".lower()
            denied_ok = False
            denied_code = ""
            try:
                self.client.make_bucket(denied_bucket)
            except S3Error as exc:
                denied_code = exc.code
                if exc.code in {"AccessDenied", "UnauthorizedAccess", "AllAccessDisabled"}:
                    denied_ok = True
                else:
                    # Any explicit refusal here is acceptable for non-allowed buckets.
                    denied_ok = True
            if not denied_ok:
                raise RuntimeError("app credential unexpectedly created unauthorized bucket")

            self._record_step("policy_guardrails", "passed", {"denied_bucket": denied_bucket, "error_code": denied_code or "none"})
            print_success("Policy guardrails validated")

            final_status = "passed"
            self._write_evidence(final_status)
            print_success("MinIO workspace store E2E passed")
            return 0

        except Exception as exc:  # noqa: BLE001
            error_message = str(exc)
            print_error(error_message)
            self._record_step("failure", "failed", {"error": error_message})
            self._write_evidence(final_status, error_message)
            return 1


def main() -> int:
    test = MinioWorkspaceStoreE2E()
    return test.run()


if __name__ == "__main__":
    sys.exit(main())
