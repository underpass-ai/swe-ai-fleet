#!/usr/bin/env python3
"""E2E test: workspace external tools governance (profiles/scopes).

Covers policy behavior for the new external connector catalog:
- profile allowlist enforcement
- queue allowlist enforcement
- redis key-prefix allowlist enforcement
- non-policy execution path for allowed requests
"""

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


class WorkspaceProfilesGovernanceE2E:
    def __init__(self) -> None:
        self.workspace_url = os.getenv(
            "WORKSPACE_URL",
            "http://workspace.swe-ai-fleet.svc.cluster.local:50053",
        ).rstrip("/")
        self.evidence_file = os.getenv("EVIDENCE_FILE", f"/tmp/e2e-21-{int(time.time())}.json")
        self.sessions: list[str] = []
        self.run_id = f"e2e-ws-governance-{int(time.time())}"
        self.invocation_counter = 0

        self.evidence: dict[str, Any] = {
            "test_id": "21-workspace-profiles-governance",
            "run_id": self.run_id,
            "status": "running",
            "started_at": self._now_iso(),
            "workspace_url": self.workspace_url,
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
        timeout: int = 60,
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
        entry: dict[str, Any] = {
            "at": self._now_iso(),
            "step": name,
            "status": status,
        }
        if data is not None:
            entry["data"] = data
        self.evidence["steps"].append(entry)

    def _record_invocation(
        self,
        *,
        session_id: str,
        tool: str,
        http_status: int,
        invocation: dict[str, Any] | None,
        body: dict[str, Any],
    ) -> None:
        inv = invocation or {}
        err = inv.get("error")
        if not isinstance(err, dict):
            top = body.get("error")
            err = top if isinstance(top, dict) else {}

        self.evidence["invocations"].append(
            {
                "at": self._now_iso(),
                "session_id": session_id,
                "tool": tool,
                "http_status": http_status,
                "invocation_id": inv.get("id"),
                "invocation_status": inv.get("status"),
                "error_code": err.get("code"),
                "error_message": err.get("message"),
            }
        )

    def _create_session(
        self,
        *,
        actor_id: str,
        roles: list[str],
        metadata: dict[str, str],
    ) -> str:
        payload = {
            "principal": {
                "tenant_id": "e2e-tenant",
                "actor_id": actor_id,
                "roles": roles,
            },
            "metadata": metadata,
            "expires_in_seconds": 3600,
        }
        status, body = self._request("POST", "/v1/sessions", payload)
        if status != 201:
            raise RuntimeError(f"create session failed ({status}): {body}")

        session_id = str(body.get("session", {}).get("id", "")).strip()
        if not session_id:
            raise RuntimeError(f"create session missing id: {body}")

        self.sessions.append(session_id)
        self.evidence["sessions"].append(
            {
                "at": self._now_iso(),
                "session_id": session_id,
                "actor_id": actor_id,
                "roles": roles,
                "metadata": metadata,
            }
        )
        return session_id

    def _invoke(
        self,
        *,
        session_id: str,
        tool_name: str,
        args: dict[str, Any],
        approved: bool = False,
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
            timeout=90,
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

    def _assert_policy_denied(
        self,
        *,
        status: int,
        body: dict[str, Any],
        invocation: dict[str, Any] | None,
        label: str,
    ) -> None:
        if invocation is None:
            raise RuntimeError(f"{label}: missing invocation in response body")

        inv_error = invocation.get("error")
        if not isinstance(inv_error, dict):
            inv_error = body.get("error") if isinstance(body.get("error"), dict) else {}
        code = str(inv_error.get("code", "")).strip()
        if code != "policy_denied":
            raise RuntimeError(f"{label}: expected policy_denied, got code={code}, status={status}, body={body}")

    def _assert_not_policy_denied(
        self,
        *,
        status: int,
        body: dict[str, Any],
        invocation: dict[str, Any] | None,
        label: str,
    ) -> None:
        if invocation is None:
            raise RuntimeError(f"{label}: missing invocation in response body")

        inv_error = invocation.get("error")
        if not isinstance(inv_error, dict):
            inv_error = body.get("error") if isinstance(body.get("error"), dict) else {}
        code = str(inv_error.get("code", "")).strip()
        if code in ("policy_denied", "approval_required"):
            raise RuntimeError(f"{label}: unexpected policy block ({code})")

        inv_status = str(invocation.get("status", "")).strip()
        if inv_status != "succeeded":
            raise RuntimeError(f"{label}: expected succeeded invocation, got status={inv_status}, status={status}, body={body}")

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
            session_a = self._create_session(
                actor_id="e2e-governance-a",
                roles=["devops"],
                metadata={
                    "allowed_profiles": "dev.redis",
                    "allowed_redis_key_prefixes": "sandbox:,dev:",
                    "allowed_rabbit_queues": "sandbox.,dev.",
                },
            )
            status, body = self._request("GET", f"/v1/sessions/{session_a}/tools")
            if status != 200:
                raise RuntimeError(f"list tools failed ({status}): {body}")
            tools = [str(item.get("name", "")).strip() for item in body.get("tools", []) if isinstance(item, dict)]
            required_tools = {
                "conn.list_profiles",
                "rabbit.consume",
                "redis.get",
                "redis.exists",
                "mongo.find",
                "mongo.aggregate",
            }
            missing = sorted(name for name in required_tools if name not in tools)
            if missing:
                raise RuntimeError(f"catalog missing required tools: {missing}")
            self._record_step(
                "catalog",
                "passed",
                {
                    "tool_count": len(tools),
                    "required_tools": sorted(required_tools),
                },
            )
            print_success(f"Catalog includes required tools ({len(required_tools)})")

            print_step(3, "Policy denial by profile allowlist")
            status, body, inv = self._invoke(
                session_id=session_a,
                tool_name="rabbit.queue_info",
                args={"profile_id": "dev.rabbit", "queue": "sandbox.jobs"},
            )
            self._assert_policy_denied(status=status, body=body, invocation=inv, label="rabbit profile deny")

            status, body, inv = self._invoke(
                session_id=session_a,
                tool_name="mongo.find",
                args={"profile_id": "dev.mongo", "database": "sandbox", "collection": "todos", "limit": 5},
            )
            self._assert_policy_denied(status=status, body=body, invocation=inv, label="mongo profile deny")
            self._record_step("profile_allowlist_enforced", "passed")
            print_success("Profile allowlist enforcement validated")

            print_step(4, "Policy denial by redis key prefix")
            status, body, inv = self._invoke(
                session_id=session_a,
                tool_name="redis.get",
                args={"profile_id": "dev.redis", "key": "prod:secret"},
            )
            self._assert_policy_denied(status=status, body=body, invocation=inv, label="redis prefix deny")

            status, body, inv = self._invoke(
                session_id=session_a,
                tool_name="redis.exists",
                args={"profile_id": "dev.redis", "keys": ["sandbox:e2e:key1"]},
            )
            self._assert_not_policy_denied(
                status=status,
                body=body,
                invocation=inv,
                label="redis exists allowed scope",
            )
            self._record_step("redis_prefix_enforced", "passed")
            print_success("Redis key-prefix governance validated")

            print_step(5, "Queue/database scope controls")
            session_b = self._create_session(
                actor_id="e2e-governance-b",
                roles=["devops"],
                metadata={
                    "allowed_profiles": "dev.rabbit,dev.mongo",
                    "allowed_rabbit_queues": "sandbox.,dev.",
                },
            )

            status, body, inv = self._invoke(
                session_id=session_b,
                tool_name="rabbit.consume",
                args={"profile_id": "dev.rabbit", "queue": "prod.jobs", "max_messages": 1, "timeout_ms": 500},
            )
            self._assert_policy_denied(status=status, body=body, invocation=inv, label="rabbit queue deny")

            status, body, inv = self._invoke(
                session_id=session_b,
                tool_name="mongo.find",
                args={"profile_id": "dev.mongo", "database": "prod", "collection": "todos", "limit": 5},
            )
            self._assert_policy_denied(status=status, body=body, invocation=inv, label="mongo database deny")
            self._record_step("queue_database_scope_enforced", "passed")
            print_success("Queue/database scope controls validated")

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
    return WorkspaceProfilesGovernanceE2E().run()


if __name__ == "__main__":
    sys.exit(main())
