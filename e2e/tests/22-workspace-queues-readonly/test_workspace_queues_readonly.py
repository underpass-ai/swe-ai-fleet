#!/usr/bin/env python3
"""E2E test: queue tools read-only governance.

Validates:
- queue tools are exposed for devops sessions
- write-style queue tools are exposed but approval-gated
- read_only profiles block queue writes even when approved
- subject/topic/queue allowlists enforce policy_denied
- allowlisted requests are not blocked by policy (may still fail at runtime)
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


def print_error(message: str) -> None:
    print(f"{Colors.RED}ERROR {message}{Colors.NC}")


def print_warning(message: str) -> None:
    print(f"{Colors.YELLOW}WARN {message}{Colors.NC}")


class WorkspaceQueuesReadonlyE2E:
    def __init__(self) -> None:
        self.workspace_url = os.getenv(
            "WORKSPACE_URL",
            "http://workspace.swe-ai-fleet.svc.cluster.local:50053",
        ).rstrip("/")
        self.evidence_file = os.getenv("EVIDENCE_FILE", f"/tmp/e2e-22-{int(time.time())}.json")
        self.run_id = f"e2e-ws-queues-{int(time.time())}"
        self.sessions: list[str] = []
        self.invocation_counter = 0

        self.evidence: dict[str, Any] = {
            "test_id": "22-workspace-queues-readonly",
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
        item: dict[str, Any] = {"at": self._now_iso(), "step": name, "status": status}
        if data is not None:
            item["data"] = data
        self.evidence["steps"].append(item)

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
                "actor_id": "e2e-queues-readonly",
                "roles": ["devops"],
            },
            "metadata": {
                "allowed_profiles": "dev.nats,dev.kafka,dev.rabbit",
                "allowed_nats_subjects": "sandbox.>,dev.>",
                "allowed_kafka_topics": "sandbox.,dev.",
                "allowed_rabbit_queues": "sandbox.,dev.",
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

            print_step(2, "Session and queue catalog")
            session_id = self._create_session()
            status, body = self._request("GET", f"/v1/sessions/{session_id}/tools")
            if status != 200:
                raise RuntimeError(f"list tools failed ({status}): {body}")
            tools = [str(item.get("name", "")).strip() for item in body.get("tools", []) if isinstance(item, dict)]

            required_tools = {
                "nats.subscribe_pull",
                "nats.publish",
                "kafka.topic_metadata",
                "kafka.consume",
                "kafka.produce",
                "rabbit.queue_info",
                "rabbit.consume",
                "rabbit.publish",
            }
            missing = sorted(item for item in required_tools if item not in tools)
            if missing:
                raise RuntimeError(f"catalog missing queue governed tools: {missing}")

            self._record_step(
                "catalog",
                "passed",
                {
                    "tool_count": len(tools),
                    "required_tools": sorted(required_tools),
                    "governed_write_tools": ["nats.publish", "kafka.produce", "rabbit.publish"],
                },
            )
            print_success("Queue governed catalog shape validated")

            print_step(3, "Policy deny checks (subject/topic/queue)")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="nats.subscribe_pull",
                args={"profile_id": "dev.nats", "subject": "prod.events", "max_messages": 1, "timeout_ms": 500},
            )
            self._assert_policy_denied(invocation=inv, body=body, label="nats subject deny")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="kafka.topic_metadata",
                args={"profile_id": "dev.kafka", "topic": "prod.events"},
            )
            self._assert_policy_denied(invocation=inv, body=body, label="kafka topic deny")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="rabbit.queue_info",
                args={"profile_id": "dev.rabbit", "queue": "prod.jobs", "timeout_ms": 500},
            )
            self._assert_policy_denied(invocation=inv, body=body, label="rabbit queue deny")

            self._record_step("policy_deny_scopes", "passed")
            print_success("Scope deny checks validated")

            print_step(4, "Write tools require approval")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="nats.publish",
                args={"profile_id": "dev.nats", "subject": "sandbox.events", "payload": "hello"},
            )
            self._assert_approval_required(invocation=inv, body=body, label="nats publish approval")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="kafka.produce",
                args={"profile_id": "dev.kafka", "topic": "sandbox.events", "value": "hello"},
            )
            self._assert_approval_required(invocation=inv, body=body, label="kafka produce approval")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="rabbit.publish",
                args={"profile_id": "dev.rabbit", "queue": "sandbox.jobs", "payload": "hello"},
            )
            self._assert_approval_required(invocation=inv, body=body, label="rabbit publish approval")

            self._record_step("write_approval_gate", "passed")
            print_success("Write tools enforce approval gate")

            print_step(5, "Read-only profiles deny writes even when approved")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="nats.publish",
                args={"profile_id": "dev.nats", "subject": "sandbox.events", "payload": "hello"},
                approved=True,
            )
            self._assert_policy_denied(invocation=inv, body=body, label="nats publish read_only deny")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="kafka.produce",
                args={"profile_id": "dev.kafka", "topic": "sandbox.events", "value": "hello"},
                approved=True,
            )
            self._assert_policy_denied(invocation=inv, body=body, label="kafka produce read_only deny")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="rabbit.publish",
                args={"profile_id": "dev.rabbit", "queue": "sandbox.jobs", "payload": "hello"},
                approved=True,
            )
            self._assert_policy_denied(invocation=inv, body=body, label="rabbit publish read_only deny")

            self._record_step("read_only_write_deny", "passed")
            print_success("Read-only profiles block queue writes")

            print_step(6, "Allowlisted queue reads (not policy blocked)")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="nats.subscribe_pull",
                args={"profile_id": "dev.nats", "subject": "sandbox.events", "max_messages": 2, "timeout_ms": 500},
            )
            self._assert_not_policy_denied(invocation=inv, body=body, label="nats allow")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="kafka.topic_metadata",
                args={"profile_id": "dev.kafka", "topic": "sandbox.events"},
            )
            self._assert_not_policy_denied(invocation=inv, body=body, label="kafka metadata allow")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="kafka.consume",
                args={
                    "profile_id": "dev.kafka",
                    "topic": "sandbox.events",
                    "partition": 0,
                    "offset_mode": "latest",
                    "max_messages": 2,
                    "timeout_ms": 500,
                },
            )
            self._assert_not_policy_denied(invocation=inv, body=body, label="kafka consume allow")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="kafka.consume",
                args={
                    "profile_id": "dev.kafka",
                    "topic": "sandbox.events",
                    "partition": 0,
                    "offset_mode": "timestamp",
                    "timestamp_ms": int(time.time() * 1000) - 60000,
                    "max_messages": 2,
                    "timeout_ms": 500,
                },
            )
            self._assert_not_policy_denied(invocation=inv, body=body, label="kafka consume timestamp allow")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="rabbit.queue_info",
                args={"profile_id": "dev.rabbit", "queue": "sandbox.jobs", "timeout_ms": 500},
            )
            self._assert_not_policy_denied(invocation=inv, body=body, label="rabbit queue_info allow")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="rabbit.consume",
                args={"profile_id": "dev.rabbit", "queue": "sandbox.jobs", "max_messages": 2, "timeout_ms": 500},
            )
            self._assert_not_policy_denied(invocation=inv, body=body, label="rabbit consume allow")

            self._record_step("allowlisted_reads", "passed")
            print_success("Allowlisted queue reads are not policy-blocked")

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
    return WorkspaceQueuesReadonlyE2E().run()


if __name__ == "__main__":
    sys.exit(main())
