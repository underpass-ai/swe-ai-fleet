#!/usr/bin/env python3
"""E2E test: database tools governance (Redis/Mongo).

Validates:
- db tools are exposed with write governance controls
- redis key-prefix governance enforces policy
- redis read_only profile blocks write tools even with approval
- mongo database scoping enforces policy
- allowlisted reads are not policy blocked
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


class WorkspaceDBGovernedE2E:
    def __init__(self) -> None:
        self.workspace_url = os.getenv(
            "WORKSPACE_URL",
            "http://workspace.swe-ai-fleet.svc.cluster.local:50053",
        ).rstrip("/")
        self.redis_endpoint = os.getenv(
            "E2E_REDIS_ENDPOINT",
            "valkey.swe-ai-fleet.svc.cluster.local:6379",
        )
        self.mongo_endpoint = os.getenv(
            "E2E_MONGO_ENDPOINT",
            "mongodb://e2e-mongodb.swe-ai-fleet.svc.cluster.local:27017",
        )
        self.evidence_file = os.getenv("EVIDENCE_FILE", f"/tmp/e2e-23-{int(time.time())}.json")
        self.run_id = f"e2e-ws-db-{int(time.time())}"
        self.sessions: list[str] = []
        self.invocation_counter = 0

        self.evidence: dict[str, Any] = {
            "test_id": "23-workspace-db-governed",
            "run_id": self.run_id,
            "status": "running",
            "started_at": self._now_iso(),
            "workspace_url": self.workspace_url,
            "steps": [],
            "sessions": [],
            "invocations": [],
        }

    def _profile_endpoints_json(self) -> str:
        return json.dumps(
            {
                "dev.redis": self.redis_endpoint,
                "dev.mongo": self.mongo_endpoint,
            }
        )

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
                "actor_id": "e2e-db-governed",
                "roles": ["devops"],
            },
            "metadata": {
                "allowed_profiles": "dev.redis,dev.mongo",
                "allowed_redis_key_prefixes": "sandbox:,dev:",
                "connection_profile_endpoints_json": self._profile_endpoints_json(),
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

    def _assert_policy_denied(self, *, invocation: dict[str, Any] | None, body: dict[str, Any], label: str) -> None:
        if invocation is None:
            raise RuntimeError(f"{label}: missing invocation")
        error = self._extract_error(invocation, body)
        code = str(error.get("code", "")).strip()
        if code != "policy_denied":
            raise RuntimeError(f"{label}: expected policy_denied, got {code}")

    def _assert_approval_required(self, *, invocation: dict[str, Any] | None, body: dict[str, Any], label: str) -> None:
        if invocation is None:
            raise RuntimeError(f"{label}: missing invocation")
        error = self._extract_error(invocation, body)
        code = str(error.get("code", "")).strip()
        if code != "approval_required":
            raise RuntimeError(f"{label}: expected approval_required, got {code}")

    def _assert_blocked_write_gate(self, *, invocation: dict[str, Any] | None, body: dict[str, Any], label: str) -> None:
        if invocation is None:
            raise RuntimeError(f"{label}: missing invocation")
        error = self._extract_error(invocation, body)
        code = str(error.get("code", "")).strip()
        if code not in ("approval_required", "policy_denied"):
            raise RuntimeError(f"{label}: expected approval_required or policy_denied, got {code}")

    def _assert_not_policy_denied(self, *, invocation: dict[str, Any] | None, body: dict[str, Any], label: str) -> None:
        if invocation is None:
            raise RuntimeError(f"{label}: missing invocation")
        error = self._extract_error(invocation, body)
        code = str(error.get("code", "")).strip()
        if code in ("policy_denied", "approval_required"):
            raise RuntimeError(f"{label}: unexpected policy block ({code})")
        status = str(invocation.get("status", "")).strip()
        if status != "succeeded":
            raise RuntimeError(f"{label}: expected succeeded invocation, got {status}")

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

            print_step(2, "Session and DB catalog")
            session_id = self._create_session()
            status, body = self._request("GET", f"/v1/sessions/{session_id}/tools")
            if status != 200:
                raise RuntimeError(f"list tools failed ({status}): {body}")
            tools = [str(item.get("name", "")).strip() for item in body.get("tools", []) if isinstance(item, dict)]

            required_tools = {
                "redis.get",
                "redis.mget",
                "redis.scan",
                "redis.ttl",
                "redis.exists",
                "redis.set",
                "redis.del",
                "mongo.find",
                "mongo.aggregate",
            }
            missing = sorted(item for item in required_tools if item not in tools)
            if missing:
                raise RuntimeError(f"catalog missing db governed tools: {missing}")

            forbidden_tools = {"mongo.insert", "mongo.update", "mongo.delete"}
            present_forbidden = sorted(item for item in forbidden_tools if item in tools)
            if present_forbidden:
                raise RuntimeError(f"catalog exposes forbidden db write tools: {present_forbidden}")

            self._record_step(
                "catalog",
                "passed",
                {"tool_count": len(tools), "required_tools": sorted(required_tools), "forbidden_tools": sorted(forbidden_tools)},
            )
            print_success("DB governed catalog shape validated")

            print_step(3, "Policy deny checks (key prefix/database)")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="redis.get",
                args={"profile_id": "dev.redis", "key": "prod:secret"},
            )
            self._assert_policy_denied(invocation=inv, body=body, label="redis key deny")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="redis.scan",
                args={"profile_id": "dev.redis", "prefix": "prod:", "max_keys": 10},
            )
            self._assert_policy_denied(invocation=inv, body=body, label="redis prefix deny")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="redis.set",
                args={"profile_id": "dev.redis", "key": "prod:secret", "value": "top-secret", "ttl_seconds": 60},
                approved=True,
            )
            self._assert_policy_denied(invocation=inv, body=body, label="redis set key deny")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="redis.del",
                args={"profile_id": "dev.redis", "keys": ["prod:secret"]},
                approved=True,
            )
            self._assert_policy_denied(invocation=inv, body=body, label="redis del key deny")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="mongo.find",
                args={"profile_id": "dev.mongo", "database": "prod", "collection": "todos", "limit": 5},
            )
            self._assert_policy_denied(invocation=inv, body=body, label="mongo database deny")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="mongo.aggregate",
                args={"profile_id": "dev.mongo", "database": "prod", "collection": "todos", "pipeline": [], "limit": 5},
            )
            self._assert_policy_denied(invocation=inv, body=body, label="mongo aggregate database deny")

            self._record_step("policy_deny_scopes", "passed")
            print_success("Key-prefix/database deny checks validated")

            print_step(4, "Write gate checks without approval")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="redis.set",
                args={"profile_id": "dev.redis", "key": "sandbox:e2e:write-approval", "value": "blocked", "ttl_seconds": 60},
                approved=False,
            )
            self._assert_blocked_write_gate(invocation=inv, body=body, label="redis set gate")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="redis.del",
                args={"profile_id": "dev.redis", "keys": ["sandbox:e2e:write-approval"]},
                approved=False,
            )
            self._assert_blocked_write_gate(invocation=inv, body=body, label="redis del gate")

            self._record_step("approval_gates", "passed")
            print_success("Write gates validated for redis writes without approval")

            print_step(5, "Allowlisted DB reads and read_only write-deny checks")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="redis.get",
                args={"profile_id": "dev.redis", "key": "sandbox:e2e:key1"},
            )
            self._assert_not_policy_denied(invocation=inv, body=body, label="redis get allow")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="redis.mget",
                args={"profile_id": "dev.redis", "keys": ["sandbox:e2e:key1", "sandbox:e2e:key2"]},
            )
            self._assert_not_policy_denied(invocation=inv, body=body, label="redis mget allow")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="redis.scan",
                args={"profile_id": "dev.redis", "prefix": "sandbox:", "max_keys": 20},
            )
            self._assert_not_policy_denied(invocation=inv, body=body, label="redis scan allow")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="redis.ttl",
                args={"profile_id": "dev.redis", "key": "sandbox:e2e:key1"},
            )
            self._assert_not_policy_denied(invocation=inv, body=body, label="redis ttl allow")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="redis.exists",
                args={"profile_id": "dev.redis", "keys": ["sandbox:e2e:key1"]},
            )
            self._assert_not_policy_denied(invocation=inv, body=body, label="redis exists allow")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="redis.set",
                args={"profile_id": "dev.redis", "key": "sandbox:e2e:key1", "value": "hello", "ttl_seconds": 120},
                approved=True,
            )
            self._assert_policy_denied(invocation=inv, body=body, label="redis set denied on read_only profile")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="redis.del",
                args={"profile_id": "dev.redis", "keys": ["sandbox:e2e:key1"]},
                approved=True,
            )
            self._assert_policy_denied(invocation=inv, body=body, label="redis del denied on read_only profile")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="mongo.find",
                args={"profile_id": "dev.mongo", "database": "sandbox", "collection": "todos", "filter": {}, "limit": 5},
            )
            self._assert_not_policy_denied(invocation=inv, body=body, label="mongo find allow")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="mongo.aggregate",
                args={"profile_id": "dev.mongo", "database": "sandbox", "collection": "todos", "pipeline": [], "limit": 5},
            )
            self._assert_not_policy_denied(invocation=inv, body=body, label="mongo aggregate allow")

            self._record_step("allowlisted_ops", "passed")
            print_success("Allowlisted DB reads succeed and read_only writes are denied")

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
    return WorkspaceDBGovernedE2E().run()


if __name__ == "__main__":
    sys.exit(main())
