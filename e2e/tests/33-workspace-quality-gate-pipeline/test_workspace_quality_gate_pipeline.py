#!/usr/bin/env python3
"""E2E test: quality.gate and CI pipeline integration (CAT-016)."""

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


class WorkspaceQualityGatePipelineE2E:
    def __init__(self) -> None:
        self.workspace_url = os.getenv(
            "WORKSPACE_URL",
            "http://workspace.swe-ai-fleet.svc.cluster.local:50053",
        ).rstrip("/")
        self.evidence_file = os.getenv("EVIDENCE_FILE", f"/tmp/e2e-33-{int(time.time())}.json")
        self.run_id = f"e2e-ws-quality-gate-{int(time.time())}"
        self.sessions: list[str] = []
        self.invocation_counter = 0

        self.evidence: dict[str, Any] = {
            "test_id": "33-workspace-quality-gate-pipeline",
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
                "actor_id": "e2e-quality-gate",
                "roles": ["developer"],
            },
            "allowed_paths": ["."],
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
        timeout: int = 120,
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
            error = self._extract_error(invocation, body)
            code = str(error.get("code", "")).strip()
            raise RuntimeError(f"{label}: expected succeeded, got {status} ({code})")

    def _assert_failed(self, *, invocation: dict[str, Any] | None, body: dict[str, Any], label: str) -> None:
        if invocation is None:
            raise RuntimeError(f"{label}: missing invocation")
        status = str(invocation.get("status", "")).strip()
        if status != "failed":
            raise RuntimeError(f"{label}: expected failed invocation, got {status}")
        error = self._extract_error(invocation, body)
        if not str(error.get("code", "")).strip():
            raise RuntimeError(f"{label}: expected error code in failed invocation")

    def _assert_artifact_present(self, invocation_id: str, artifact_name: str) -> None:
        status, body = self._request("GET", f"/v1/invocations/{invocation_id}/artifacts")
        if status != 200:
            raise RuntimeError(f"list invocation artifacts failed ({status}): {body}")
        names = [
            str(item.get("name", "")).strip()
            for item in body.get("artifacts", [])
            if isinstance(item, dict)
        ]
        if artifact_name not in names:
            raise RuntimeError(f"artifact {artifact_name} not found for invocation {invocation_id}: {names}")

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
            required_tools = [
                "fs.write_file",
                "quality.gate",
                "ci.run_pipeline",
            ]
            missing = [tool for tool in required_tools if tool not in tools]
            if missing:
                raise RuntimeError(f"catalog missing tools: {missing}")
            self._record_step("catalog", "passed", {"tool_count": len(tools), "required_tools": required_tools})
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
                self._assert_succeeded(invocation=inv, body=body, label=f"fs.write_file({path})")
            self._record_step("seed_go_project", "passed")
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
            self._record_step("ci_pipeline_quality_gate", "passed", {"failed_step": "quality_gate"})
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
            self._assert_succeeded(invocation=inv, body=body, label="quality.gate")
            quality_output = inv.get("output", {}) if isinstance(inv, dict) else {}
            if quality_output.get("status") != "pass":
                raise RuntimeError(f"quality.gate expected pass status, got {quality_output}")
            invocation_id = str(inv.get("id", "")).strip() if isinstance(inv, dict) else ""
            self._assert_artifact_present(invocation_id, "quality-gate-report.json")
            self._record_step("quality_gate_direct", "passed", {"status": "pass"})
            print_success("quality.gate direct invocation verified")

            final_status = "passed"
            self._record_step("test_result", "passed")
            print_success("E2E 33 completed successfully")
            return 0
        except Exception as exc:
            error_message = str(exc)
            print_error(error_message)
            self._record_step("failure", "failed", {"error": error_message})
            return 1
        finally:
            self.cleanup()
            self._write_evidence(final_status, error_message)


def main() -> int:
    return WorkspaceQualityGatePipelineE2E().run()


if __name__ == "__main__":
    sys.exit(main())
