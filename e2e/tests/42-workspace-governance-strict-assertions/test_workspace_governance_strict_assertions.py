#!/usr/bin/env python3
"""E2E test: strict governance assertions for policy and endpoint hardening.

Validates strict contract expectations:
- allowlist-positive operations must succeed
- approval-gated operations without approval return approval_required
- read_only/scope policy denials return policy_denied
- metadata endpoint override is ignored (server-side endpoints prevail)
"""

from __future__ import annotations

import base64
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


class WorkspaceGovernanceStrictAssertionsE2E:
    def __init__(self) -> None:
        self.workspace_url = os.getenv(
            "WORKSPACE_URL",
            "http://workspace.swe-ai-fleet.svc.cluster.local:50053",
        ).rstrip("/")
        self.evidence_file = os.getenv("EVIDENCE_FILE", f"/tmp/e2e-42-{int(time.time())}.json")

        self.run_id = f"e2e-ws-governance-strict-{int(time.time())}"
        self.sessions: list[str] = []
        self.invocation_counter = 0

        # These metadata endpoints must be ignored by the workspace service.
        self.poison_endpoints = {
            "dev.redis": "invalid-redis-host.invalid:6379",
            "dev.nats": "nats://invalid-nats-host.invalid:4222",
        }

        self.evidence: dict[str, Any] = {
            "test_id": "42-workspace-governance-strict-assertions",
            "run_id": self.run_id,
            "status": "running",
            "started_at": self._now_iso(),
            "workspace_url": self.workspace_url,
            "poison_metadata_endpoints": self.poison_endpoints,
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
        timeout: int = 90,
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
        approved: bool,
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
                "approved": approved,
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
                "actor_id": "e2e-governance-strict",
                "roles": ["devops"],
            },
            "metadata": {
                "allowed_profiles": "dev.redis,dev.nats",
                "allowed_redis_key_prefixes": "sandbox:,dev:",
                "allowed_nats_subjects": "sandbox.>,dev.>",
                "connection_profile_endpoints_json": json.dumps(self.poison_endpoints),
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
        approved: bool,
        timeout: int = 90,
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
            approved=approved,
            http_status=status,
            invocation=invocation if isinstance(invocation, dict) else None,
            body=body if isinstance(body, dict) else {},
        )
        return status, body, invocation if isinstance(invocation, dict) else None

    def _assert_error_contract(
        self,
        *,
        status: int,
        body: dict[str, Any],
        invocation: dict[str, Any] | None,
        expected_http_status: int,
        expected_invocation_status: str,
        expected_error_code: str,
        label: str,
    ) -> None:
        if invocation is None:
            raise RuntimeError(f"{label}: missing invocation")
        if status != expected_http_status:
            raise RuntimeError(f"{label}: expected http_status={expected_http_status}, got {status}")
        inv_status = str(invocation.get("status", "")).strip()
        if inv_status != expected_invocation_status:
            raise RuntimeError(
                f"{label}: expected invocation.status={expected_invocation_status}, got {inv_status}"
            )
        error = self._extract_error(invocation, body)
        code = str(error.get("code", "")).strip()
        if code != expected_error_code:
            raise RuntimeError(f"{label}: expected error.code={expected_error_code}, got {code}")

    def _assert_succeeded(
        self,
        *,
        status: int,
        body: dict[str, Any],
        invocation: dict[str, Any] | None,
        label: str,
    ) -> dict[str, Any]:
        if invocation is None:
            raise RuntimeError(f"{label}: missing invocation")
        if status != 200:
            raise RuntimeError(f"{label}: expected http_status=200, got {status}")
        inv_status = str(invocation.get("status", "")).strip()
        if inv_status != "succeeded":
            error = self._extract_error(invocation, body)
            raise RuntimeError(f"{label}: expected succeeded, got {inv_status} ({error})")
        output = invocation.get("output")
        if not isinstance(output, dict):
            raise RuntimeError(f"{label}: missing output payload")
        return output

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

            print_step(2, "Session bootstrap and catalog checks")
            session_id = self._create_session()
            status, body = self._request("GET", f"/v1/sessions/{session_id}/tools")
            if status != 200:
                raise RuntimeError(f"list tools failed ({status}): {body}")

            tools = [str(item.get("name", "")).strip() for item in body.get("tools", []) if isinstance(item, dict)]
            required_tools = {
                "conn.list_profiles",
                "conn.describe_profile",
                "redis.exists",
                "redis.get",
                "redis.set",
                "nats.subscribe_pull",
                "nats.publish",
            }
            missing = sorted(name for name in required_tools if name not in tools)
            if missing:
                raise RuntimeError(f"catalog missing required tools: {missing}")

            self._record_step(
                "catalog",
                "passed",
                {"tool_count": len(tools), "required_tools": sorted(required_tools)},
            )
            print_success(f"Catalog includes required tools ({len(required_tools)})")

            print_step(3, "Strict deny contracts: approval and policy")
            status, body, inv = self._invoke(
                session_id=session_id,
                tool_name="redis.set",
                args={"profile_id": "dev.redis", "key": "sandbox:e2e:strict-key", "value": "x", "ttl_seconds": 60},
                approved=False,
            )
            self._assert_error_contract(
                status=status,
                body=body,
                invocation=inv,
                expected_http_status=428,
                expected_invocation_status="denied",
                expected_error_code="approval_required",
                label="redis.set without approval",
            )

            status, body, inv = self._invoke(
                session_id=session_id,
                tool_name="nats.publish",
                args={
                    "profile_id": "dev.nats",
                    "subject": "sandbox.strict.events",
                    "payload_base64": base64.b64encode(f"{self.run_id}:no-approval".encode("utf-8")).decode("utf-8"),
                },
                approved=False,
            )
            self._assert_error_contract(
                status=status,
                body=body,
                invocation=inv,
                expected_http_status=428,
                expected_invocation_status="denied",
                expected_error_code="approval_required",
                label="nats.publish without approval",
            )

            status, body, inv = self._invoke(
                session_id=session_id,
                tool_name="redis.set",
                args={"profile_id": "dev.redis", "key": "sandbox:e2e:strict-key", "value": "x", "ttl_seconds": 60},
                approved=True,
            )
            self._assert_error_contract(
                status=status,
                body=body,
                invocation=inv,
                expected_http_status=500,
                expected_invocation_status="failed",
                expected_error_code="policy_denied",
                label="redis.set read_only with approval",
            )

            status, body, inv = self._invoke(
                session_id=session_id,
                tool_name="nats.publish",
                args={
                    "profile_id": "dev.nats",
                    "subject": "sandbox.strict.events",
                    "payload_base64": base64.b64encode(f"{self.run_id}:approved".encode("utf-8")).decode("utf-8"),
                },
                approved=True,
            )
            self._assert_error_contract(
                status=status,
                body=body,
                invocation=inv,
                expected_http_status=500,
                expected_invocation_status="failed",
                expected_error_code="policy_denied",
                label="nats.publish read_only with approval",
            )

            status, body, inv = self._invoke(
                session_id=session_id,
                tool_name="redis.get",
                args={"profile_id": "dev.redis", "key": "prod:secret"},
                approved=False,
            )
            self._assert_error_contract(
                status=status,
                body=body,
                invocation=inv,
                expected_http_status=403,
                expected_invocation_status="denied",
                expected_error_code="policy_denied",
                label="redis.get key prefix deny",
            )

            self._record_step("strict_denies", "passed")
            print_success("Strict denial contracts validated")

            print_step(4, "Metadata endpoint override is ignored")
            status, body, inv = self._invoke(
                session_id=session_id,
                tool_name="redis.exists",
                args={"profile_id": "dev.redis", "keys": ["sandbox:e2e:key1"]},
                approved=False,
            )
            redis_output = self._assert_succeeded(
                status=status,
                body=body,
                invocation=inv,
                label="redis.exists allowlisted call",
            )

            status, body, inv = self._invoke(
                session_id=session_id,
                tool_name="nats.subscribe_pull",
                args={"profile_id": "dev.nats", "subject": "sandbox.events", "max_messages": 1, "timeout_ms": 500},
                approved=False,
                timeout=120,
            )
            nats_output = self._assert_succeeded(
                status=status,
                body=body,
                invocation=inv,
                label="nats.subscribe_pull allowlisted call",
            )

            self._record_step(
                "metadata_endpoint_override_blocked",
                "passed",
                {
                    "poison_endpoints": self.poison_endpoints,
                    "redis_summary": redis_output.get("summary"),
                    "nats_summary": nats_output.get("summary"),
                },
            )
            print_success("Allowlisted operations succeeded despite poisoned metadata endpoints")

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
    return WorkspaceGovernanceStrictAssertionsE2E().run()


if __name__ == "__main__":
    sys.exit(main())
