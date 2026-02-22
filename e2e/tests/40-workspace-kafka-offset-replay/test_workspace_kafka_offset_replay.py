#!/usr/bin/env python3
"""E2E test: Kafka offset replay contract (earliest/latest/absolute/timestamp)."""

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


class WorkspaceKafkaOffsetReplayE2E:
    def __init__(self) -> None:
        self.workspace_url = os.getenv(
            "WORKSPACE_URL",
            "http://workspace.swe-ai-fleet.svc.cluster.local:50053",
        ).rstrip("/")
        self.kafka_endpoint = os.getenv(
            "E2E_KAFKA_ENDPOINT",
            "e2e-kafka.swe-ai-fleet.svc.cluster.local:9092",
        )
        self.evidence_file = os.getenv("EVIDENCE_FILE", f"/tmp/e2e-40-{int(time.time())}.json")

        self.run_id = f"e2e-ws-kafka-offset-{int(time.time())}"
        self.profile_id = "rw.kafka"
        self.topic = "sandbox.events"
        self.invocation_counter = 0
        self.sessions: list[str] = []

        self.marker_prefix = f"kafka-offset-replay:{self.run_id}"
        self.markers = [f"{self.marker_prefix}:m{i}" for i in range(3)]
        self.latest_marker = f"{self.marker_prefix}:latest"

        self.evidence: dict[str, Any] = {
            "test_id": "40-workspace-kafka-offset-replay",
            "run_id": self.run_id,
            "status": "running",
            "started_at": self._now_iso(),
            "workspace_url": self.workspace_url,
            "kafka_endpoint": self.kafka_endpoint,
            "topic": self.topic,
            "markers": self.markers + [self.latest_marker],
            "steps": [],
            "sessions": [],
            "invocations": [],
        }

    def _profiles_json(self) -> str:
        return json.dumps(
            [
                {
                    "id": self.profile_id,
                    "kind": "kafka",
                    "description": "RW Kafka profile for offset replay e2e",
                    "read_only": False,
                    "scopes": {"topics": ["sandbox.", "dev."]},
                }
            ]
        )

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
                "actor_id": "e2e-kafka-offset-replay",
                "roles": ["devops"],
            },
            "metadata": {
                "allowed_profiles": self.profile_id,
                "allowed_kafka_topics": "sandbox.,dev.",
                "connection_profiles_json": self._profiles_json(),
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

    def _assert_succeeded(self, *, invocation: dict[str, Any] | None, body: dict[str, Any], label: str) -> dict[str, Any]:
        if invocation is None:
            raise RuntimeError(f"{label}: missing invocation")
        status = str(invocation.get("status", "")).strip()
        if status != "succeeded":
            raise RuntimeError(f"{label}: expected succeeded, got {status} ({self._extract_error(invocation, body)})")
        output = invocation.get("output")
        if not isinstance(output, dict):
            raise RuntimeError(f"{label}: missing output payload")
        return output

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
            raise RuntimeError(f"{label}: expected {expected_code}, got {code} ({error})")

    def _decode_b64(self, raw: Any) -> str:
        if not isinstance(raw, str) or raw == "":
            return ""
        try:
            return base64.b64decode(raw.encode("utf-8"), validate=True).decode("utf-8", errors="replace")
        except Exception:
            return ""

    def _extract_messages(self, output: dict[str, Any]) -> list[dict[str, Any]]:
        raw_messages = output.get("messages")
        return [item for item in raw_messages if isinstance(item, dict)] if isinstance(raw_messages, list) else []

    def _find_offsets_for_markers(self, messages: list[dict[str, Any]], markers: list[str]) -> dict[str, int]:
        found: dict[str, int] = {}
        marker_set = set(markers)
        for item in messages:
            decoded = self._decode_b64(item.get("value_base64"))
            if decoded in marker_set and decoded not in found:
                try:
                    found[decoded] = int(item.get("offset", -1))
                except Exception:
                    continue
        return found

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
            print_step(1, "Workspace health and kafka catalog")
            status, body = self._request("GET", "/healthz")
            if status != 200 or body.get("status") != "ok":
                raise RuntimeError(f"health check failed ({status}): {body}")

            session_id = self._create_session()
            status, body = self._request("GET", f"/v1/sessions/{session_id}/tools")
            if status != 200:
                raise RuntimeError(f"list tools failed ({status}): {body}")
            tools = [str(item.get("name", "")).strip() for item in body.get("tools", []) if isinstance(item, dict)]

            required = {"kafka.produce", "kafka.consume", "kafka.topic_metadata"}
            missing = sorted(name for name in required if name not in tools)
            if missing:
                raise RuntimeError(f"catalog missing kafka tools: {missing}")

            self._record_step("catalog", "passed", {"required": sorted(required), "tool_count": len(tools)})
            print_success("Kafka catalog exposed")

            print_step(2, "Approval and policy gates")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="kafka.produce",
                args={"profile_id": self.profile_id, "topic": self.topic, "value": "hello"},
                approved=False,
            )
            self._assert_error_code(invocation=inv, body=body, label="kafka.produce approval", expected_code="approval_required")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="kafka.consume",
                args={"profile_id": self.profile_id, "topic": "prod.events", "max_messages": 1},
                approved=False,
            )
            self._assert_error_code(invocation=inv, body=body, label="kafka.consume topic deny", expected_code="policy_denied")
            self._record_step("approval_policy_gates", "passed")
            print_success("Approval/policy gates validated")

            print_step(3, "Offset argument validation")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="kafka.consume",
                args={
                    "profile_id": self.profile_id,
                    "topic": self.topic,
                    "partition": 0,
                    "offset_mode": "absolute",
                    "max_messages": 1,
                },
                approved=False,
            )
            self._assert_error_code(invocation=inv, body=body, label="absolute missing offset", expected_code="invalid_argument")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="kafka.consume",
                args={
                    "profile_id": self.profile_id,
                    "topic": self.topic,
                    "partition": 0,
                    "offset_mode": "timestamp",
                    "max_messages": 1,
                },
                approved=False,
            )
            self._assert_error_code(invocation=inv, body=body, label="timestamp missing timestamp_ms", expected_code="invalid_argument")
            self._record_step("offset_validation", "passed")
            print_success("Offset validation errors are enforced")

            print_step(4, "Produce marker messages")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="kafka.topic_metadata",
                args={"profile_id": self.profile_id, "topic": self.topic},
                approved=False,
                timeout=120,
            )
            output = self._assert_succeeded(invocation=inv, body=body, label="kafka.topic_metadata")
            partition_count = int(output.get("partition_count", 0))
            if partition_count < 1:
                raise RuntimeError(f"expected kafka topic with partition_count >= 1, got {partition_count}")

            produce_start_ms = int(time.time() * 1000)
            for idx, marker in enumerate(self.markers):
                _, body, inv = self._invoke(
                    session_id=session_id,
                    tool_name="kafka.produce",
                    args={
                        "profile_id": self.profile_id,
                        "topic": self.topic,
                        "partition": 0,
                        "key": f"{self.run_id}:{idx}",
                        "value": marker,
                        "value_encoding": "utf8",
                        "timeout_ms": 3000,
                    },
                    approved=True,
                    timeout=120,
                )
                self._assert_succeeded(invocation=inv, body=body, label=f"kafka.produce marker {idx}")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="kafka.produce",
                args={
                    "profile_id": self.profile_id,
                    "topic": self.topic,
                    "partition": 0,
                    "key": f"{self.run_id}:latest",
                    "value": self.latest_marker,
                    "value_encoding": "utf8",
                    "timeout_ms": 3000,
                },
                approved=True,
                timeout=120,
            )
            self._assert_succeeded(invocation=inv, body=body, label="kafka.produce latest marker")

            self._record_step("produce_markers", "passed", {"produce_start_ms": produce_start_ms})
            print_success("Marker messages produced")

            print_step(5, "Replay by timestamp and absolute offset")
            found_offsets: dict[str, int] = {}
            timestamp_output: dict[str, Any] | None = None
            for attempt in range(1, 5):
                _, body, inv = self._invoke(
                    session_id=session_id,
                    tool_name="kafka.consume",
                    args={
                        "profile_id": self.profile_id,
                        "topic": self.topic,
                        "partition": 0,
                        "offset_mode": "timestamp",
                        "timestamp_ms": produce_start_ms - 2000,
                        "max_messages": 200,
                        "max_bytes": 1048576,
                        "timeout_ms": 3000,
                    },
                    approved=False,
                    timeout=120,
                )
                output = self._assert_succeeded(invocation=inv, body=body, label=f"kafka.consume timestamp attempt {attempt}")
                timestamp_output = output
                if str(output.get("offset_mode", "")).strip() != "timestamp":
                    raise RuntimeError(f"timestamp consume returned wrong offset_mode: {output}")

                messages = self._extract_messages(output)
                found_offsets = self._find_offsets_for_markers(messages, self.markers)
                if len(found_offsets) == len(self.markers):
                    break
                time.sleep(0.4)

            if len(found_offsets) != len(self.markers):
                raise RuntimeError(f"timestamp replay did not include all produced markers, found={found_offsets}")

            first_offset = min(found_offsets.values())
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="kafka.consume",
                args={
                    "profile_id": self.profile_id,
                    "topic": self.topic,
                    "partition": 0,
                    "offset_mode": "absolute",
                    "offset": first_offset,
                    "max_messages": 10,
                    "max_bytes": 1048576,
                    "timeout_ms": 3000,
                },
                approved=False,
                timeout=120,
            )
            absolute_output = self._assert_succeeded(invocation=inv, body=body, label="kafka.consume absolute")
            if str(absolute_output.get("offset_mode", "")).strip() != "absolute":
                raise RuntimeError(f"absolute consume returned wrong offset_mode: {absolute_output}")
            if int(absolute_output.get("offset", -1)) != first_offset:
                raise RuntimeError(f"absolute consume output offset mismatch: {absolute_output}")

            absolute_messages = self._extract_messages(absolute_output)
            if not absolute_messages:
                raise RuntimeError("absolute consume returned no messages")
            first_msg_offset = int(absolute_messages[0].get("offset", -1))
            if first_msg_offset != first_offset:
                raise RuntimeError(
                    f"absolute consume first message offset mismatch: got={first_msg_offset} expected={first_offset}"
                )

            self._record_step(
                "timestamp_absolute_replay",
                "passed",
                {
                    "found_offsets": found_offsets,
                    "first_offset": first_offset,
                    "timestamp_count": int(timestamp_output.get("message_count", 0)) if isinstance(timestamp_output, dict) else 0,
                    "absolute_count": int(absolute_output.get("message_count", 0)),
                },
            )
            print_success("Timestamp and absolute replay validated")

            print_step(6, "Earliest/latest contract checks")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="kafka.consume",
                args={
                    "profile_id": self.profile_id,
                    "topic": self.topic,
                    "partition": 0,
                    "offset_mode": "earliest",
                    "max_messages": 5,
                    "max_bytes": 1048576,
                    "timeout_ms": 3000,
                },
                approved=False,
                timeout=120,
            )
            earliest_output = self._assert_succeeded(invocation=inv, body=body, label="kafka.consume earliest")
            if str(earliest_output.get("offset_mode", "")).strip() != "earliest":
                raise RuntimeError(f"earliest consume returned wrong offset_mode: {earliest_output}")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="kafka.consume",
                args={
                    "profile_id": self.profile_id,
                    "topic": self.topic,
                    "partition": 0,
                    "offset_mode": "latest",
                    "max_messages": 5,
                    "max_bytes": 1048576,
                    "timeout_ms": 3000,
                },
                approved=False,
                timeout=120,
            )
            latest_output = self._assert_succeeded(invocation=inv, body=body, label="kafka.consume latest")
            if str(latest_output.get("offset_mode", "")).strip() != "latest":
                raise RuntimeError(f"latest consume returned wrong offset_mode: {latest_output}")

            latest_messages = self._extract_messages(latest_output)
            latest_count = int(latest_output.get("message_count", 0))
            if latest_count < 0:
                raise RuntimeError(f"latest consume returned invalid message_count: {latest_output}")
            latest_found = False
            for item in latest_messages:
                if self.latest_marker in self._decode_b64(item.get("value_base64")):
                    latest_found = True
                    break
            if not latest_messages:
                print_warning("latest consume returned no messages; accepting empty tail window")
            elif not latest_found:
                print_warning("latest consume window did not include latest marker")

            self._record_step(
                "earliest_latest_modes",
                "passed",
                {
                    "earliest_count": int(earliest_output.get("message_count", 0)),
                    "latest_count": latest_count,
                    "latest_marker_found": latest_found,
                },
            )
            print_success("Earliest/latest modes validated")

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
    return WorkspaceKafkaOffsetReplayE2E().run()


if __name__ == "__main__":
    sys.exit(main())
