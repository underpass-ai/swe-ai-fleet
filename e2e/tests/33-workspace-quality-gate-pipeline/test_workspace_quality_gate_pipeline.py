#!/usr/bin/env python3
"""E2E test: quality.gate and CI pipeline integration (CAT-016)."""

from __future__ import annotations

import os
import sys
import time
from typing import Any

from workspace_common import WorkspaceE2EBase, print_error, print_step, print_success


class WorkspaceQualityGatePipelineE2E(WorkspaceE2EBase):
    def __init__(self) -> None:
        super().__init__(
            test_id="33-workspace-quality-gate-pipeline",
            run_id_prefix="e2e-ws-quality-gate",
            workspace_url=os.getenv(
                "WORKSPACE_URL",
                "http://workspace.swe-ai-fleet.svc.cluster.local:50053",
            ),
            evidence_file=os.getenv("EVIDENCE_FILE", f"/tmp/e2e-33-{int(time.time())}.json"),
        )

    def _create_session(self) -> str:
        payload = {
            "principal": {
                "tenant_id": "e2e-tenant",
                "actor_id": "e2e-quality-gate",
                "roles": ["developer"],
            },
            "allowed_paths": ["."],
            "expires_in_seconds": 3600,
        }
        return self.create_session(payload=payload)

    def _invoke(
        self,
        *,
        session_id: str,
        tool_name: str,
        args: dict[str, Any],
        approved: bool = False,
        timeout: int = 120,
    ) -> tuple[int, dict[str, Any], dict[str, Any] | None]:
        return self.invoke(
            session_id=session_id,
            tool_name=tool_name,
            args=args,
            approved=approved,
            timeout=timeout,
        )

    def _assert_failed(self, *, invocation: dict[str, Any] | None, body: dict[str, Any], label: str) -> None:
        if invocation is None:
            raise RuntimeError(f"{label}: missing invocation")
        status = str(invocation.get("status", "")).strip()
        if status != "failed":
            raise RuntimeError(f"{label}: expected failed invocation, got {status}")
        error = self.extract_error(invocation, body)
        if not str(error.get("code", "")).strip():
            raise RuntimeError(f"{label}: expected error code in failed invocation")

    def _assert_artifact_present(self, invocation_id: str, artifact_name: str) -> None:
        status, body = self.request("GET", f"/v1/invocations/{invocation_id}/artifacts")
        if status != 200:
            raise RuntimeError(f"list invocation artifacts failed ({status}): {body}")
        names = [
            str(item.get("name", "")).strip()
            for item in body.get("artifacts", [])
            if isinstance(item, dict)
        ]
        if artifact_name not in names:
            raise RuntimeError(f"artifact {artifact_name} not found for invocation {invocation_id}: {names}")

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

            print_step(2, "Session and catalog checks")
            session_id = self._create_session()
            status, body = self.request("GET", f"/v1/sessions/{session_id}/tools")
            if status != 200:
                raise RuntimeError(f"list tools failed ({status}): {body}")
            tools = [str(item.get("name", "")).strip() for item in body.get("tools", []) if isinstance(item, dict)]
            required_tools = [
                "fs.write_file",
                "quality.gate",
                "ci.run_pipeline",
            ]
            missing = [tool for tool in required_tools if tool not in tools]
            if missing:
                raise RuntimeError(f"catalog missing tools: {missing}")
            self.record_step("catalog", "passed", {"tool_count": len(tools), "required_tools": required_tools})
            print_success("Catalog exposes CAT-016 tools")

            print_step(3, "Create minimal Go project in workspace")
            go_mod = "module example.com/e2e\n\ngo 1.23\n"
            go_code = "\n".join(
                [
                    "package demo",
                    "",
                    "func Add(a int, b int) int {",
                    "    return a + b",
                    "}",
                ]
            )
            go_test = "\n".join(
                [
                    "package demo",
                    "",
                    "import \"testing\"",
                    "",
                    "func TestAdd(t *testing.T) {",
                    "    if Add(2, 3) != 5 {",
                    "        t.Fatalf(\"expected 5\")",
                    "    }",
                    "}",
                ]
            )

            for path, content in [
                ("go.mod", go_mod),
                ("add.go", go_code),
                ("add_test.go", go_test),
            ]:
                _, body, inv = self._invoke(
                    session_id=session_id,
                    tool_name="fs.write_file",
                    approved=True,
                    args={"path": path, "content": content},
                )
                self.assert_invocation_succeeded(invocation=inv, body=body, label=f"fs.write_file({path})")
            self.record_step("seed_go_project", "passed")
            print_success("Go project created")

            print_step(4, "Run ci.run_pipeline with strict quality gate (expect fail on quality_gate)")
            http_status, body, inv = self._invoke(
                session_id=session_id,
                tool_name="ci.run_pipeline",
                args={
                    "target": "./...",
                    "include_static_analysis": False,
                    "include_coverage": False,
                    "include_quality_gate": True,
                    "fail_fast": True,
                    "quality_gate": {
                        "min_coverage_percent": 95,
                        "max_failed_tests": 0,
                    },
                },
                timeout=300,
            )
            if http_status not in (200, 500):
                raise RuntimeError(f"ci.run_pipeline unexpected HTTP status {http_status}: {body}")
            self._assert_failed(invocation=inv, body=body, label="ci.run_pipeline")
            pipeline_output = inv.get("output", {}) if isinstance(inv, dict) else {}
            if pipeline_output.get("failed_step") != "quality_gate":
                raise RuntimeError(f"expected failed_step=quality_gate, got {pipeline_output}")
            gate_output = pipeline_output.get("quality_gate", {})
            if not isinstance(gate_output, dict) or gate_output.get("status") != "fail":
                raise RuntimeError(f"expected quality_gate.status=fail, got {gate_output}")
            invocation_id = str(inv.get("id", "")).strip() if isinstance(inv, dict) else ""
            self._assert_artifact_present(invocation_id, "quality-gate-report.json")
            self.record_step("ci_pipeline_quality_gate", "passed", {"failed_step": "quality_gate"})
            print_success("ci.run_pipeline quality gate integration verified")

            print_step(5, "Run quality.gate directly with passing metrics")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="quality.gate",
                args={
                    "metrics": {
                        "coverage_percent": 99,
                        "diagnostics_count": 0,
                        "failed_tests_count": 0,
                    },
                    "min_coverage_percent": 90,
                    "max_diagnostics": 0,
                    "max_failed_tests": 0,
                },
            )
            self.assert_invocation_succeeded(invocation=inv, body=body, label="quality.gate")
            quality_output = inv.get("output", {}) if isinstance(inv, dict) else {}
            if quality_output.get("status") != "pass":
                raise RuntimeError(f"quality.gate expected pass status, got {quality_output}")
            invocation_id = str(inv.get("id", "")).strip() if isinstance(inv, dict) else ""
            self._assert_artifact_present(invocation_id, "quality-gate-report.json")
            self.record_step("quality_gate_direct", "passed", {"status": "pass"})
            print_success("quality.gate direct invocation verified")

            final_status = "passed"
            self.record_step("test_result", "passed")
            print_success("E2E 33 completed successfully")
            return 0
        except Exception as exc:
            error_message = str(exc)
            print_error(error_message)
            self.record_step("failure", "failed", {"error": error_message})
            return 1
        finally:
            self.cleanup_sessions()
            self.write_evidence(final_status, error_message)


def main() -> int:
    return WorkspaceQualityGatePipelineE2E().run()


if __name__ == "__main__":
    sys.exit(main())
