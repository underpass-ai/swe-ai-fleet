#!/usr/bin/env python3
"""E2E test: workspace external tools governance (profiles/scopes).

Covers policy behavior for the new external connector catalog:
- profile allowlist enforcement
- queue allowlist enforcement
- redis key-prefix allowlist enforcement
- non-policy execution path for allowed requests
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any

from workspace_common import WorkspaceE2EBase, print_error, print_step, print_success


class WorkspaceProfilesGovernanceE2E(WorkspaceE2EBase):
    def __init__(self) -> None:
        super().__init__(
            test_id="21-workspace-profiles-governance",
            run_id_prefix="e2e-ws-governance",
            workspace_url=os.getenv(
                "WORKSPACE_URL",
                "http://workspace.swe-ai-fleet.svc.cluster.local:50053",
            ),
            evidence_file=os.getenv("EVIDENCE_FILE", f"/tmp/e2e-21-{int(time.time())}.json"),
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
        return self.create_session(
            payload=payload,
            session_record={
                "actor_id": actor_id,
                "roles": roles,
                "metadata": metadata,
            },
        )

    def _invoke(
        self,
        *,
        session_id: str,
        tool_name: str,
        args: dict[str, Any],
        approved: bool = False,
    ) -> tuple[int, dict[str, Any], dict[str, Any] | None]:
        return self.invoke(
            session_id=session_id,
            tool_name=tool_name,
            args=args,
            approved=approved,
            timeout=90,
        )

    def run(self) -> int:
        final_status = "failed"
        error_message = ""
        try:
            print_step(1, "Workspace health")
            status, body = self.request("GET", "/healthz")
            if status != 200 or body.get("status") != "ok":
                raise RuntimeError(f"health check failed ({status}): {body}")
            self.record_step("health", "passed")
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
            status, body = self.request("GET", f"/v1/sessions/{session_a}/tools")
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
            self.record_step(
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
            self.assert_policy_denied(status=status, body=body, invocation=inv, label="rabbit profile deny")

            status, body, inv = self._invoke(
                session_id=session_a,
                tool_name="mongo.find",
                args={"profile_id": "dev.mongo", "database": "sandbox", "collection": "todos", "limit": 5},
            )
            self.assert_policy_denied(status=status, body=body, invocation=inv, label="mongo profile deny")
            self.record_step("profile_allowlist_enforced", "passed")
            print_success("Profile allowlist enforcement validated")

            print_step(4, "Policy denial by redis key prefix")
            status, body, inv = self._invoke(
                session_id=session_a,
                tool_name="redis.get",
                args={"profile_id": "dev.redis", "key": "prod:secret"},
            )
            self.assert_policy_denied(status=status, body=body, invocation=inv, label="redis prefix deny")

            status, body, inv = self._invoke(
                session_id=session_a,
                tool_name="redis.exists",
                args={"profile_id": "dev.redis", "keys": ["sandbox:e2e:key1"]},
            )
            self.assert_not_policy_denied(
                status=status,
                body=body,
                invocation=inv,
                label="redis exists allowed scope",
            )
            self.record_step("redis_prefix_enforced", "passed")
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
            self.assert_policy_denied(status=status, body=body, invocation=inv, label="rabbit queue deny")

            status, body, inv = self._invoke(
                session_id=session_b,
                tool_name="mongo.find",
                args={"profile_id": "dev.mongo", "database": "prod", "collection": "todos", "limit": 5},
            )
            self.assert_policy_denied(status=status, body=body, invocation=inv, label="mongo database deny")
            self.record_step("queue_database_scope_enforced", "passed")
            print_success("Queue/database scope controls validated")

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
    return WorkspaceProfilesGovernanceE2E().run()


if __name__ == "__main__":
    sys.exit(main())
