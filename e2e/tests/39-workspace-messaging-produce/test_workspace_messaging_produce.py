#!/usr/bin/env python3
"""E2E test: governed messaging write tools (publish/produce)."""

from __future__ import annotations

import base64
import json
import os
import sys
import threading
import time
from typing import Any

from workspace_common import WorkspaceE2EBase, print_error, print_step, print_success


class WorkspaceMessagingProduceE2E(WorkspaceE2EBase):
    def __init__(self) -> None:
        super().__init__(
            test_id="39-workspace-messaging-produce",
            run_id_prefix="e2e-ws-messaging-produce",
            workspace_url=os.getenv(
                "WORKSPACE_URL",
                "http://workspace.swe-ai-fleet.svc.cluster.local:50053",
            ),
            evidence_file=os.getenv("EVIDENCE_FILE", f"/tmp/e2e-39-{int(time.time())}.json"),
        )

        self.nats_endpoint = os.getenv(
            "E2E_NATS_ENDPOINT",
            "nats://e2e-nats.swe-ai-fleet.svc.cluster.local:4222",
        )
        self.kafka_endpoint = os.getenv(
            "E2E_KAFKA_ENDPOINT",
            "e2e-kafka.swe-ai-fleet.svc.cluster.local:9092",
        )
        self.rabbit_endpoint = os.getenv(
            "E2E_RABBIT_ENDPOINT",
            "amqp://e2e:e2e@e2e-rabbitmq.swe-ai-fleet.svc.cluster.local:5672/",
        )

        self.nats_profile = "rw.nats"
        self.kafka_profile = "rw.kafka"
        self.rabbit_profile = "rw.rabbit"

        self.nats_subject = "sandbox.events"
        self.kafka_topic = "sandbox.events"
        self.rabbit_queue = "sandbox.jobs"

        self.nats_marker = f"nats-marker:{self.run_id}"
        self.kafka_marker = f"kafka-marker:{self.run_id}"
        self.rabbit_marker = f"rabbit-marker:{self.run_id}"

        self.evidence["endpoints"] = {
            "nats": self.nats_endpoint,
            "kafka": self.kafka_endpoint,
            "rabbit": self.rabbit_endpoint,
        }

    def _profiles_json(self) -> str:
        return json.dumps(
            [
                {
                    "id": self.nats_profile,
                    "kind": "nats",
                    "description": "RW NATS profile for e2e publish",
                    "read_only": False,
                    "scopes": {"subjects": ["sandbox.>", "dev.>"]},
                },
                {
                    "id": self.kafka_profile,
                    "kind": "kafka",
                    "description": "RW Kafka profile for e2e produce",
                    "read_only": False,
                    "scopes": {"topics": ["sandbox.", "dev."]},
                },
                {
                    "id": self.rabbit_profile,
                    "kind": "rabbitmq",
                    "description": "RW RabbitMQ profile for e2e publish",
                    "read_only": False,
                    "scopes": {"queues": ["sandbox.", "dev."]},
                },
            ]
        )

    def _create_session(self) -> str:
        payload = {
            "principal": {
                "tenant_id": "e2e-tenant",
                "actor_id": "e2e-messaging-produce",
                "roles": ["devops"],
            },
            "metadata": {
                "allowed_profiles": f"{self.nats_profile},{self.kafka_profile},{self.rabbit_profile}",
                "allowed_nats_subjects": "sandbox.>,dev.>",
                "allowed_kafka_topics": "sandbox.,dev.",
                "allowed_rabbit_queues": "sandbox.,dev.",
                "connection_profiles_json": self._profiles_json(),
            },
            "expires_in_seconds": 3600,
        }
        return self.create_session(payload=payload)

    def _invoke(
        self,
        *,
        session_id: str,
        tool_name: str,
        args: dict[str, Any],
        approved: bool,
        timeout: int = 120,
    ) -> tuple[int, dict[str, Any], dict[str, Any] | None]:
        return self.invoke(
            session_id=session_id,
            tool_name=tool_name,
            args=args,
            approved=approved,
            timeout=timeout,
        )

    def _assert_succeeded(self, *, invocation: dict[str, Any] | None, body: dict[str, Any], label: str) -> dict[str, Any]:
        if invocation is None:
            raise RuntimeError(f"{label}: missing invocation")
        status = str(invocation.get("status", "")).strip()
        if status != "succeeded":
            raise RuntimeError(f"{label}: expected succeeded, got {status} ({self.extract_error(invocation, body)})")
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
        error = self.extract_error(invocation, body)
        code = str(error.get("code", "")).strip()
        if code != expected_code:
            raise RuntimeError(f"{label}: expected {expected_code}, got {code} ({error})")

    def _decode_base64(self, value: Any) -> str:
        if not isinstance(value, str) or value == "":
            return ""
        try:
            return base64.b64decode(value.encode("utf-8"), validate=True).decode("utf-8", errors="replace")
        except Exception:
            return ""

    def _verify_nats_delivery(self, session_id: str, subject: str, marker: str) -> None:
        for attempt in range(1, 4):
            result: dict[str, Any] = {}
            thread_error: dict[str, Exception] = {}

            def _subscriber() -> None:
                try:
                    status, body, inv = self._invoke(
                        session_id=session_id,
                        tool_name="nats.subscribe_pull",
                        args={
                            "profile_id": self.nats_profile,
                            "subject": subject,
                            "max_messages": 5,
                            "timeout_ms": 3000,
                            "max_bytes": 262144,
                        },
                        approved=False,
                        timeout=90,
                    )
                    result["status"] = status
                    result["body"] = body
                    result["invocation"] = inv
                except Exception as exc:  # pragma: no cover
                    thread_error["error"] = exc

            thread = threading.Thread(target=_subscriber, daemon=True)
            thread.start()
            time.sleep(0.25)

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="nats.publish",
                args={
                    "profile_id": self.nats_profile,
                    "subject": subject,
                    "payload": marker,
                    "payload_encoding": "utf8",
                    "timeout_ms": 2000,
                },
                approved=True,
                timeout=90,
            )
            self._assert_succeeded(invocation=inv, body=body, label=f"nats.publish attempt {attempt}")

            thread.join(timeout=10)
            if thread.is_alive():
                raise RuntimeError(f"nats.subscribe_pull attempt {attempt}: background thread did not finish")
            if "error" in thread_error:
                raise RuntimeError(f"nats.subscribe_pull attempt {attempt} failed: {thread_error['error']}")

            inv_sub = result.get("invocation")
            body_sub = result.get("body") if isinstance(result.get("body"), dict) else {}
            output = self._assert_succeeded(
                invocation=inv_sub if isinstance(inv_sub, dict) else None,
                body=body_sub,
                label=f"nats.subscribe_pull attempt {attempt}",
            )

            raw_messages = output.get("messages")
            messages = [item for item in raw_messages if isinstance(item, dict)] if isinstance(raw_messages, list) else []
            for item in messages:
                if marker in self._decode_base64(item.get("data_base64")):
                    return

            time.sleep(0.2)

        raise RuntimeError("nats publish marker not observed in subscribe_pull messages")

    def _kafka_contains_marker(self, output: dict[str, Any], marker: str) -> bool:
        raw_messages = output.get("messages")
        messages = [item for item in raw_messages if isinstance(item, dict)] if isinstance(raw_messages, list) else []
        for item in messages:
            decoded = self._decode_base64(item.get("value_base64"))
            if marker in decoded:
                return True
        return False

    def _rabbit_contains_marker(self, output: dict[str, Any], marker: str) -> bool:
        raw_messages = output.get("messages")
        messages = [item for item in raw_messages if isinstance(item, dict)] if isinstance(raw_messages, list) else []
        for item in messages:
            decoded = self._decode_base64(item.get("body_base64"))
            if marker in decoded:
                return True
        return False

    def run(self) -> int:
        final_status = "failed"
        error_message = ""
        try:
            print_step(1, "Workspace health and messaging catalog")
            status, body = self.request("GET", "/healthz")
            if status != 200 or body.get("status") != "ok":
                raise RuntimeError(f"health check failed ({status}): {body}")

            session_id = self._create_session()
            status, body = self.request("GET", f"/v1/sessions/{session_id}/tools")
            if status != 200:
                raise RuntimeError(f"list tools failed ({status}): {body}")
            tools = [str(item.get("name", "")).strip() for item in body.get("tools", []) if isinstance(item, dict)]

            required = {
                "nats.publish",
                "nats.subscribe_pull",
                "kafka.produce",
                "kafka.consume",
                "kafka.topic_metadata",
                "rabbit.publish",
                "rabbit.consume",
                "rabbit.queue_info",
            }
            missing = sorted(name for name in required if name not in tools)
            if missing:
                raise RuntimeError(f"catalog missing messaging tools: {missing}")
            self.record_step("catalog", "passed", {"required": sorted(required), "tool_count": len(tools)})
            print_success("Messaging catalog exposed")

            print_step(2, "Policy deny checks for disallowed scope")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="nats.publish",
                args={"profile_id": self.nats_profile, "subject": "prod.events", "payload": "deny"},
                approved=True,
            )
            self._assert_error_code(invocation=inv, body=body, label="nats scope deny", expected_code="policy_denied")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="kafka.produce",
                args={"profile_id": self.kafka_profile, "topic": "prod.events", "value": "deny"},
                approved=True,
            )
            self._assert_error_code(invocation=inv, body=body, label="kafka scope deny", expected_code="policy_denied")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="rabbit.publish",
                args={"profile_id": self.rabbit_profile, "queue": "prod.jobs", "payload": "deny"},
                approved=True,
            )
            self._assert_error_code(invocation=inv, body=body, label="rabbit scope deny", expected_code="policy_denied")
            self.record_step("scope_denies", "passed")
            print_success("Scope deny contract validated")

            print_step(3, "Approval gates for write tools")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="nats.publish",
                args={"profile_id": self.nats_profile, "subject": self.nats_subject, "payload": "hello"},
                approved=False,
            )
            self._assert_error_code(invocation=inv, body=body, label="nats approval", expected_code="approval_required")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="kafka.produce",
                args={"profile_id": self.kafka_profile, "topic": self.kafka_topic, "value": "hello"},
                approved=False,
            )
            self._assert_error_code(invocation=inv, body=body, label="kafka approval", expected_code="approval_required")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="rabbit.publish",
                args={"profile_id": self.rabbit_profile, "queue": self.rabbit_queue, "payload": "hello"},
                approved=False,
            )
            self._assert_error_code(invocation=inv, body=body, label="rabbit approval", expected_code="approval_required")
            self.record_step("approval_gates", "passed")
            print_success("Approval gates validated")

            print_step(4, "NATS publish and subscribe verification")
            self._verify_nats_delivery(session_id, self.nats_subject, self.nats_marker)
            self.record_step("nats_publish_subscribe", "passed")
            print_success("NATS publish marker observed")

            print_step(5, "Kafka produce and consume verification")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="kafka.produce",
                args={
                    "profile_id": self.kafka_profile,
                    "topic": self.kafka_topic,
                    "partition": 0,
                    "key": self.run_id,
                    "value": self.kafka_marker,
                    "value_encoding": "utf8",
                    "timeout_ms": 3000,
                },
                approved=True,
                timeout=120,
            )
            self._assert_succeeded(invocation=inv, body=body, label="kafka.produce")

            kafka_found = False
            for attempt in range(1, 4):
                _, body, inv = self._invoke(
                    session_id=session_id,
                    tool_name="kafka.consume",
                    args={
                        "profile_id": self.kafka_profile,
                        "topic": self.kafka_topic,
                        "partition": 0,
                        "offset_mode": "timestamp",
                        "timestamp_ms": int(time.time() * 1000) - 300000,
                        "max_messages": 200,
                        "max_bytes": 1048576,
                        "timeout_ms": 3000,
                    },
                    approved=False,
                    timeout=120,
                )
                output = self._assert_succeeded(invocation=inv, body=body, label=f"kafka.consume attempt {attempt}")
                if self._kafka_contains_marker(output, self.kafka_marker):
                    kafka_found = True
                    break
                time.sleep(0.3)
            if not kafka_found:
                raise RuntimeError("kafka marker not found in consumed messages")
            self.record_step("kafka_produce_consume", "passed")
            print_success("Kafka produce marker observed")

            print_step(6, "Rabbit publish and consume verification")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="rabbit.publish",
                args={
                    "profile_id": self.rabbit_profile,
                    "queue": self.rabbit_queue,
                    "payload": self.rabbit_marker,
                    "payload_encoding": "utf8",
                    "timeout_ms": 3000,
                },
                approved=True,
                timeout=120,
            )
            self._assert_succeeded(invocation=inv, body=body, label="rabbit.publish")

            rabbit_found = False
            for attempt in range(1, 4):
                _, body, inv = self._invoke(
                    session_id=session_id,
                    tool_name="rabbit.consume",
                    args={
                        "profile_id": self.rabbit_profile,
                        "queue": self.rabbit_queue,
                        "max_messages": 50,
                        "max_bytes": 1048576,
                        "timeout_ms": 3000,
                    },
                    approved=False,
                    timeout=120,
                )
                output = self._assert_succeeded(invocation=inv, body=body, label=f"rabbit.consume attempt {attempt}")
                if self._rabbit_contains_marker(output, self.rabbit_marker):
                    rabbit_found = True
                    break
                time.sleep(0.3)
            if not rabbit_found:
                raise RuntimeError("rabbit marker not found in consumed messages")
            self.record_step("rabbit_publish_consume", "passed")
            print_success("Rabbit publish marker observed")

            final_status = "passed"
            self.record_step("final", "passed")
            return 0

        except Exception as exc:
            error_message = str(exc)
            self.record_step("failure", "failed", {"error": error_message})
            print_error(error_message)
            return 1
        finally:
            self.cleanup_sessions()
            self.write_evidence(final_status, error_message)


def main() -> int:
    return WorkspaceMessagingProduceE2E().run()


if __name__ == "__main__":
    sys.exit(main())
