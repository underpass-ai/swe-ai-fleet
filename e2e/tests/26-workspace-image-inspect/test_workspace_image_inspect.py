#!/usr/bin/env python3
"""E2E test: image.inspect tool.

Validates:
- catalog exposes image.inspect
- dockerfile mode returns deterministic structured issues
- image_ref mode returns deterministic structured issues
- artifacts are generated for both invocations
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


class WorkspaceImageInspectE2E:
    def __init__(self) -> None:
        self.workspace_url = os.getenv(
            "WORKSPACE_URL",
            "http://workspace.swe-ai-fleet.svc.cluster.local:50053",
        ).rstrip("/")
        self.evidence_file = os.getenv("EVIDENCE_FILE", f"/tmp/e2e-26-{int(time.time())}.json")
        self.run_id = f"e2e-ws-image-inspect-{int(time.time())}"
        self.sessions: list[str] = []
        self.invocation_counter = 0

        self.evidence: dict[str, Any] = {
            "test_id": "26-workspace-image-inspect",
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
                "actor_id": "e2e-image-inspect",
                "roles": ["developer"],
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
            if "image.inspect" not in tools:
                raise RuntimeError("catalog missing image.inspect")
            self._record_step("catalog", "passed", {"tool_count": len(tools)})
            print_success("Catalog exposes image.inspect")

            print_step(3, "Seed Dockerfile fixture")
            dockerfile = (
                "FROM alpine:latest\n"
                "RUN curl -fsSL https://example.com/install.sh | sh\n"
                "RUN chmod 777 /tmp\n"
            )
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="fs.write_file",
                args={"path": "Dockerfile", "content": dockerfile},
                approved=True,
            )
            self._assert_succeeded(invocation=inv, body=body, label="write Dockerfile")
            self._record_step("workspace_seed", "passed")
            print_success("Dockerfile fixture created")

            print_step(4, "Inspect Dockerfile")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="image.inspect",
                args={"context_path": ".", "dockerfile_path": "Dockerfile", "max_issues": 100},
            )
            self._assert_succeeded(invocation=inv, body=body, label="image.inspect dockerfile")
            docker_output = inv.get("output", {}) if isinstance(inv, dict) else {}
            if str(docker_output.get("source_type", "")).strip() != "dockerfile":
                raise RuntimeError(f"dockerfile inspect source_type mismatch: {docker_output}")
            if int(docker_output.get("issues_count", 0)) < 1:
                raise RuntimeError(f"dockerfile inspect returned no issues: {docker_output}")
            docker_invocation_id = str(inv.get("id", "")).strip() if isinstance(inv, dict) else ""
            if not docker_invocation_id:
                raise RuntimeError("dockerfile inspect missing invocation id")
            self._assert_artifact_present(docker_invocation_id, "image-inspect-report.json")
            self._record_step(
                "inspect_dockerfile",
                "passed",
                {"issues_count": docker_output.get("issues_count"), "invocation_id": docker_invocation_id},
            )
            print_success("Dockerfile inspect succeeded")

            print_step(5, "Inspect image reference")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="image.inspect",
                args={"image_ref": "ghcr.io/acme/demo:latest", "max_issues": 100},
            )
            self._assert_succeeded(invocation=inv, body=body, label="image.inspect image_ref")
            ref_output = inv.get("output", {}) if isinstance(inv, dict) else {}
            if str(ref_output.get("source_type", "")).strip() != "image_ref":
                raise RuntimeError(f"image_ref inspect source_type mismatch: {ref_output}")
            if str(ref_output.get("registry", "")).strip() != "ghcr.io":
                raise RuntimeError(f"image_ref inspect registry mismatch: {ref_output}")
            if int(ref_output.get("issues_count", 0)) < 1:
                raise RuntimeError(f"image_ref inspect returned no issues: {ref_output}")
            ref_invocation_id = str(inv.get("id", "")).strip() if isinstance(inv, dict) else ""
            if not ref_invocation_id:
                raise RuntimeError("image_ref inspect missing invocation id")
            self._assert_artifact_present(ref_invocation_id, "image-inspect-report.json")
            self._record_step(
                "inspect_image_ref",
                "passed",
                {"issues_count": ref_output.get("issues_count"), "invocation_id": ref_invocation_id},
            )
            print_success("Image reference inspect succeeded")

            final_status = "passed"
            self._record_step("test_result", "passed")
            print_success("E2E 26 completed successfully")
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
    test = WorkspaceImageInspectE2E()
    return test.run()


if __name__ == "__main__":
    sys.exit(main())
