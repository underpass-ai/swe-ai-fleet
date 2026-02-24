#!/usr/bin/env python3
"""E2E test: security dependency scan + SBOM generation.

Validates:
- catalog exposes security.scan_dependencies and sbom.generate
- tool execution succeeds on a minimal Go workspace
- sbom.generate emits sbom.cdx.json artifact metadata
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any

from workspace_common import WorkspaceE2EBase, print_error, print_step, print_success


class WorkspaceSecuritySBOME2E(WorkspaceE2EBase):
    def __init__(self) -> None:
        super().__init__(
            test_id="24-workspace-security-sbom",
            run_id_prefix="e2e-ws-security-sbom",
            workspace_url=os.getenv(
                "WORKSPACE_URL",
                "http://workspace.swe-ai-fleet.svc.cluster.local:50053",
            ),
            evidence_file=os.getenv("EVIDENCE_FILE", f"/tmp/e2e-24-{int(time.time())}.json"),
        )

    def _create_session(self) -> str:
        payload = {
            "principal": {
                "tenant_id": "e2e-tenant",
                "actor_id": "e2e-security-sbom",
                "roles": ["developer"],
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
        approved: bool = False,
    ) -> tuple[int, dict[str, Any], dict[str, Any] | None]:
        return self.invoke(
            session_id=session_id,
            tool_name=tool_name,
            args=args,
            approved=approved,
            timeout=120,
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

            print_step(2, "Session and catalog checks")
            session_id = self._create_session()
            status, body = self.request("GET", f"/v1/sessions/{session_id}/tools")
            if status != 200:
                raise RuntimeError(f"list tools failed ({status}): {body}")
            tools = [str(item.get("name", "")).strip() for item in body.get("tools", []) if isinstance(item, dict)]

            required_tools = {"fs.write_file", "security.scan_dependencies", "sbom.generate"}
            missing = sorted(item for item in required_tools if item not in tools)
            if missing:
                raise RuntimeError(f"catalog missing required tools: {missing}")
            self.record_step("catalog", "passed", {"required_tools": sorted(required_tools), "tool_count": len(tools)})
            print_success("Catalog exposes security.scan_dependencies and sbom.generate")

            print_step(3, "Prepare minimal Go project in workspace")
            go_mod = "module example.com/e2e/securitysbom\n\ngo 1.23\n"
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="fs.write_file",
                args={"path": "go.mod", "content": go_mod},
                approved=True,
            )
            self.assert_invocation_succeeded(invocation=inv, body=body, label="write go.mod")

            main_go = (
                "package main\n\n"
                "import \"fmt\"\n\n"
                "func main() {\n"
                "    fmt.Println(\"security-sbom\")\n"
                "}\n"
            )
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="fs.write_file",
                args={"path": "main.go", "content": main_go},
                approved=True,
            )
            self.assert_invocation_succeeded(invocation=inv, body=body, label="write main.go")
            self.record_step("workspace_seed", "passed")
            print_success("Workspace seeded with Go module")

            print_step(4, "Run dependency scan")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="security.scan_dependencies",
                args={"path": ".", "max_dependencies": 200},
            )
            self.assert_invocation_succeeded(invocation=inv, body=body, label="security.scan_dependencies")
            output = inv.get("output", {}) if isinstance(inv, dict) else {}
            project_type = str(output.get("project_type", "")).strip()
            dep_count = int(output.get("dependencies_count", 0))
            if project_type != "go":
                raise RuntimeError(f"dependency scan project_type mismatch: {project_type}")
            if dep_count < 1:
                raise RuntimeError(f"dependency scan returned no dependencies: {output}")
            self.record_step("dependency_scan", "passed", {"project_type": project_type, "dependencies_count": dep_count})
            print_success("security.scan_dependencies succeeded")

            print_step(5, "Generate SBOM and validate artifact")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="sbom.generate",
                args={"path": ".", "format": "cyclonedx-json", "max_components": 200},
            )
            self.assert_invocation_succeeded(invocation=inv, body=body, label="sbom.generate")
            sbom_output = inv.get("output", {}) if isinstance(inv, dict) else {}
            if str(sbom_output.get("artifact_name", "")).strip() != "sbom.cdx.json":
                raise RuntimeError(f"unexpected sbom artifact_name: {sbom_output}")
            invocation_id = str(inv.get("id", "")).strip() if isinstance(inv, dict) else ""
            if not invocation_id:
                raise RuntimeError("sbom invocation id missing")

            status, artifacts_body = self.request("GET", f"/v1/invocations/{invocation_id}/artifacts")
            if status != 200:
                raise RuntimeError(f"list invocation artifacts failed ({status}): {artifacts_body}")
            artifact_names = [
                str(item.get("name", "")).strip()
                for item in artifacts_body.get("artifacts", [])
                if isinstance(item, dict)
            ]
            if "sbom.cdx.json" not in artifact_names:
                raise RuntimeError(f"sbom.cdx.json not found in artifacts: {artifact_names}")

            self.record_step(
                "sbom_generate",
                "passed",
                {"invocation_id": invocation_id, "artifact_names": artifact_names},
            )
            print_success("sbom.generate produced sbom.cdx.json artifact metadata")

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
    return WorkspaceSecuritySBOME2E().run()


if __name__ == "__main__":
    sys.exit(main())
