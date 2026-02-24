#!/usr/bin/env python3
"""E2E test: workspace api.benchmark governance."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any


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


class WorkspaceAPIBenchmarkE2E:
    def __init__(self) -> None:
        self.workspace_url = os.getenv(
            "WORKSPACE_URL",
            "http://workspace.swe-ai-fleet.svc.cluster.local:50053",
        ).rstrip("/")
        self.bench_endpoint = os.getenv(
            "BENCH_ENDPOINT",
            "http://workspace.swe-ai-fleet.svc.cluster.local:50053",
        ).strip()
        self.evidence_file = os.getenv("EVIDENCE_FILE", f"/tmp/e2e-34-{int(time.time())}.json")
        self.run_id = f"e2e-ws-api-benchmark-{int(time.time())}"
        self.sessions: list[str] = []
        self.invocation_counter = 0

        self.evidence: dict[str, Any] = {
            "test_id": "34-workspace-api-benchmark",
            "run_id": self.run_id,
            "status": "running",
            "started_at": self._now_iso(),
            "workspace_url": self.workspace_url,
            "bench_endpoint": self.bench_endpoint,
            "steps": [],
            "sessions": [],
            "invocations": [],
        }

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        timeout: int = 120,
    ) -> tuple[int, dict[str, Any]]:
        url = self.workspace_url + path
        data = None
        headers = {"Content-Type": "application/json"}
        auth_token = os.getenv("WORKSPACE_AUTH_TOKEN", "").strip()
        if auth_token:
            headers.update({
                os.getenv("WORKSPACE_AUTH_TOKEN_HEADER", "X-Workspace-Auth-Token"): auth_token,
                os.getenv("WORKSPACE_AUTH_TENANT_HEADER", "X-Workspace-Tenant-Id"): os.getenv("WORKSPACE_AUTH_TENANT_ID", "e2e-tenant"),
                os.getenv("WORKSPACE_AUTH_ACTOR_HEADER", "X-Workspace-Actor-Id"): os.getenv("WORKSPACE_AUTH_ACTOR_ID", "e2e-workspace"),
                os.getenv("WORKSPACE_AUTH_ROLES_HEADER", "X-Workspace-Roles"): os.getenv("WORKSPACE_AUTH_ROLES", "developer,devops"),
            })
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = response.read().decode("utf-8")
                return response.getcode(), (json.loads(body) if body else {})
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8")
            try:
                parsed = json.loads(body) if body else {}
            except Exception:
                parsed = {"raw": body}
            return exc.code, parsed

    def _record_step(self, name: str, status: str, data: Any | None = None) -> None:
        entry: dict[str, Any] = {"at": self._now_iso(), "step": name, "status": status}
        if data is not None:
            entry["data"] = data
        self.evidence["steps"].append(entry)

    def _extract_error(self, invocation: dict[str, Any] | None, body: dict[str, Any]) -> dict[str, Any]:
        if isinstance(invocation, dict) and isinstance(invocation.get("error"), dict):
            return invocation["error"]
        if isinstance(body.get("error"), dict):
            return body["error"]
        return {}

    def _record_invocation(
        self,
        *,
        session_id: str,
        tool: str,
        http_status: int,
        invocation: dict[str, Any] | None,
        body: dict[str, Any],
    ) -> None:
        error = self._extract_error(invocation, body)
        self.evidence["invocations"].append(
            {
                "at": self._now_iso(),
                "session_id": session_id,
                "tool": tool,
                "http_status": http_status,
                "invocation_id": invocation.get("id") if isinstance(invocation, dict) else None,
                "invocation_status": invocation.get("status") if isinstance(invocation, dict) else None,
                "error_code": error.get("code"),
                "error_message": error.get("message"),
            }
        )

    def _create_session(self) -> str:
        payload = {
            "principal": {
                "tenant_id": "e2e-tenant",
                "actor_id": "e2e-api-benchmark",
                "roles": ["devops"],
            },
            "metadata": {
                "allowed_profiles": "bench.workspace",
                "connection_profiles_json": json.dumps(
                    [
                        {
                            "id": "bench.workspace",
                            "kind": "http",
                            "description": "Benchmark workspace health endpoint",
                            "read_only": True,
                            "scopes": {"routes": ["/healthz"]},
                        }
                    ]
                ),
            },
            "expires_in_seconds": 3600,
        }

        status, body = self._request("POST", "/v1/sessions", payload)
        if status != 201:
            raise RuntimeError(f"create session failed ({status}): {body}")
        session_id = str(body.get("session", {}).get("id", "")).strip()
        if not session_id:
            raise RuntimeError(f"create session missing id: {body}")

        self.sessions.append(session_id)
        self.evidence["sessions"].append({"at": self._now_iso(), "session_id": session_id, "payload": payload})
        return session_id

    def _invoke(
        self,
        *,
        session_id: str,
        tool_name: str,
        args: dict[str, Any],
        approved: bool = False,
        timeout: int = 180,
    ) -> tuple[int, dict[str, Any], dict[str, Any] | None]:
        self.invocation_counter += 1
        payload = {
            "correlation_id": f"{self.run_id}-{self.invocation_counter:04d}",
            "approved": approved,
            "args": args,
        }
        status, body = self._request(
            "POST",
            f"/v1/sessions/{session_id}/tools/{tool_name}/invoke",
            payload,
            timeout=timeout,
        )
        invocation = body.get("invocation") if isinstance(body, dict) else None
        self._record_invocation(
            session_id=session_id,
            tool=tool_name,
            http_status=status,
            invocation=invocation if isinstance(invocation, dict) else None,
            body=body if isinstance(body, dict) else {},
        )
        return status, body, invocation if isinstance(invocation, dict) else None

    def _assert_succeeded(self, *, invocation: dict[str, Any] | None, body: dict[str, Any], label: str) -> None:
        if invocation is None:
            raise RuntimeError(f"{label}: missing invocation")
        status = str(invocation.get("status", "")).strip()
        if status != "succeeded":
            raise RuntimeError(f"{label}: expected succeeded, got {status} ({self._extract_error(invocation, body)})")

    def _assert_error_code(
        self,
        *,
        invocation: dict[str, Any] | None,
        body: dict[str, Any],
        label: str,
        expected_code: str,
    ) -> None:
        if invocation is None:
            raise RuntimeError(f"{label}: missing invocation")
        error = self._extract_error(invocation, body)
        code = str(error.get("code", "")).strip()
        if code != expected_code:
            raise RuntimeError(f"{label}: expected {expected_code}, got {code}")

    def _write_evidence(self, status: str, error_message: str = "") -> None:
        self.evidence["status"] = status
        self.evidence["ended_at"] = self._now_iso()
        if error_message:
            self.evidence["error_message"] = error_message

        try:
            with open(self.evidence_file, "w", encoding="utf-8") as handle:
                json.dump(self.evidence, handle, ensure_ascii=False, indent=2)
            print_warning(f"Evidence file: {self.evidence_file}")
        except Exception as exc:
            print_warning(f"Could not write evidence file: {exc}")

        print("EVIDENCE_JSON_START")
        print(json.dumps(self.evidence, ensure_ascii=False, indent=2))
        print("EVIDENCE_JSON_END")

    def cleanup(self) -> None:
        for session_id in self.sessions:
            try:
                self._request("DELETE", f"/v1/sessions/{session_id}")
            except Exception:
                pass

    def run(self) -> int:
        final_status = "failed"
        error_message = ""
        try:
            print_step(1, "Workspace health")
            status, body = self._request("GET", "/healthz")
            if status != 200 or body.get("status") != "ok":
                raise RuntimeError(f"health check failed ({status}): {body}")
            self._record_step("health", "passed")
            print_success("Workspace API is healthy")

            print_step(2, "Session and catalog checks")
            session_id = self._create_session()
            status, body = self._request("GET", f"/v1/sessions/{session_id}/tools")
            if status != 200:
                raise RuntimeError(f"list tools failed ({status}): {body}")
            tools = [str(item.get("name", "")).strip() for item in body.get("tools", []) if isinstance(item, dict)]
            if "api.benchmark" not in tools:
                raise RuntimeError("catalog missing api.benchmark")
            self._record_step("catalog", "passed", {"tool_count": len(tools)})
            print_success("api.benchmark is present in catalog")

            print_step(3, "Happy path benchmark")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="api.benchmark",
                approved=True,
                args={
                    "profile_id": "bench.workspace",
                    "request": {"method": "GET", "path": "/healthz", "headers": {"accept": "application/json"}},
                    "load": {"mode": "constant_vus", "duration_ms": 10000, "vus": 5},
                    "thresholds": {"p95_ms": 5000, "error_rate": 0.20, "checks": 0.50},
                },
                timeout=240,
            )
            self._assert_succeeded(invocation=inv, body=body, label="benchmark happy path")
            output = inv.get("output", {}) if isinstance(inv, dict) else {}
            requests = output.get("requests", 0)
            if not isinstance(requests, int) or requests <= 0:
                raise RuntimeError(f"benchmark happy path expected requests > 0, got: {requests}")
            thresholds = output.get("thresholds", {})
            if not isinstance(thresholds, dict) or thresholds.get("passed") is not True:
                raise RuntimeError(f"benchmark happy path thresholds expected passed=true, got: {thresholds}")
            self._record_step("benchmark_happy_path", "passed", {"requests": requests})
            print_success("Benchmark happy path validated")

            print_step(4, "Policy denied route")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="api.benchmark",
                approved=True,
                args={
                    "profile_id": "bench.workspace",
                    "request": {"method": "GET", "path": "/metrics"},
                    "load": {"mode": "constant_vus", "duration_ms": 1000, "vus": 1},
                },
            )
            self._assert_error_code(invocation=inv, body=body, label="policy denied route", expected_code="policy_denied")
            self._record_step("policy_denied_route", "passed")
            print_success("Route allowlist policy deny validated")

            print_step(5, "Constraints violation")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="api.benchmark",
                approved=True,
                args={
                    "profile_id": "bench.workspace",
                    "request": {"method": "GET", "path": "/healthz"},
                    "load": {"mode": "constant_vus", "duration_ms": 1000, "vus": 500},
                },
            )
            self._assert_error_code(invocation=inv, body=body, label="constraints violation", expected_code="invalid_argument")
            self._record_step("constraints_violation", "passed")
            print_success("Limits validation behaves as expected")

            final_status = "passed"
            self._record_step("final", "passed")
            return 0
        except Exception as exc:
            error_message = str(exc)
            self._record_step("failure", "failed", {"error": error_message})
            print_error(error_message)
            return 1
        finally:
            self.cleanup()
            self._write_evidence(final_status, error_message)


def main() -> int:
    return WorkspaceAPIBenchmarkE2E().run()


if __name__ == "__main__":
    sys.exit(main())
