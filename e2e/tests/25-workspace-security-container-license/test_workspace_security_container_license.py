#!/usr/bin/env python3
"""E2E test: container scan + license policy check.

Validates:
- catalog exposes security.scan_container and security.license_check
- security.scan_container returns structured findings (Trivy or heuristic fallback)
- security.license_check evaluates policy and reports fail on denied unknown licenses
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


class WorkspaceSecurityContainerLicenseE2E:
    def __init__(self) -> None:
        self.workspace_url = os.getenv(
            "WORKSPACE_URL",
            "http://workspace.swe-ai-fleet.svc.cluster.local:50053",
        ).rstrip("/")
        self.evidence_file = os.getenv("EVIDENCE_FILE", f"/tmp/e2e-25-{int(time.time())}.json")
        self.run_id = f"e2e-ws-security-container-license-{int(time.time())}"
        self.sessions: list[str] = []
        self.invocation_counter = 0

        self.evidence: dict[str, Any] = {
            "test_id": "25-workspace-security-container-license",
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
                "actor_id": "e2e-security-container-license",
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
        timeout: int = 150,
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
        artifacts = [
            str(item.get("name", "")).strip()
            for item in body.get("artifacts", [])
            if isinstance(item, dict)
        ]
        if artifact_name not in artifacts:
            raise RuntimeError(f"artifact {artifact_name} not found in invocation {invocation_id}: {artifacts}")

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

            required_tools = {"fs.write_file", "security.scan_container", "security.license_check"}
            missing = sorted(item for item in required_tools if item not in tools)
            if missing:
                raise RuntimeError(f"catalog missing required tools: {missing}")
            self._record_step("catalog", "passed", {"required_tools": sorted(required_tools), "tool_count": len(tools)})
            print_success("Catalog exposes security.scan_container and security.license_check")

            print_step(3, "Prepare workspace fixture")
            go_mod = "module example.com/e2e/licensecheck\n\ngo 1.23\n"
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="fs.write_file",
                args={"path": "go.mod", "content": go_mod},
                approved=True,
            )
            self._assert_succeeded(invocation=inv, body=body, label="write go.mod")

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
            print_success("Workspace fixture created")

            print_step(4, "Run security.scan_container")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="security.scan_container",
                args={"path": ".", "max_findings": 100, "severity_threshold": "medium"},
            )
            self._assert_succeeded(invocation=inv, body=body, label="security.scan_container")
            scan_output = inv.get("output", {}) if isinstance(inv, dict) else {}
            findings_count = int(scan_output.get("findings_count", 0))
            scanner = str(scan_output.get("scanner", "")).strip()
            if scanner not in ("trivy", "heuristic-dockerfile"):
                raise RuntimeError(f"security.scan_container unexpected scanner: {scanner}")
            if findings_count < 1:
                if scanner == "heuristic-dockerfile":
                    raise RuntimeError(f"security.scan_container returned no findings: {scan_output}")
                print_warning(
                    "security.scan_container returned 0 findings with trivy; "
                    "accepting clean scan output"
                )
            scan_invocation_id = str(inv.get("id", "")).strip() if isinstance(inv, dict) else ""
            if not scan_invocation_id:
                raise RuntimeError("security.scan_container missing invocation id")
            self._assert_artifact_present(scan_invocation_id, "container-scan-findings.json")
            self._record_step(
                "security_scan_container",
                "passed",
                {"scanner": scanner, "findings_count": findings_count, "invocation_id": scan_invocation_id},
            )
            print_success("security.scan_container produced structured findings")

            print_step(5, "Run security.license_check with deny unknown policy")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="security.license_check",
                args={
                    "path": ".",
                    "max_dependencies": 200,
                    "allowed_licenses": ["MIT"],
                    "unknown_policy": "deny",
                },
            )
            self._assert_succeeded(invocation=inv, body=body, label="security.license_check")
            license_output = inv.get("output", {}) if isinstance(inv, dict) else {}
            status_value = str(license_output.get("status", "")).strip()
            unknown_count = int(license_output.get("unknown_count", 0))
            if status_value != "fail":
                raise RuntimeError(f"expected license check status fail, got: {license_output}")
            if unknown_count < 1:
                raise RuntimeError(f"expected unknown_count >= 1, got: {license_output}")
            license_invocation_id = str(inv.get("id", "")).strip() if isinstance(inv, dict) else ""
            if not license_invocation_id:
                raise RuntimeError("security.license_check missing invocation id")
            self._assert_artifact_present(license_invocation_id, "license-check-report.json")
            self._record_step(
                "security_license_check",
                "passed",
                {
                    "status": status_value,
                    "unknown_count": unknown_count,
                    "invocation_id": license_invocation_id,
                },
            )
            print_success("security.license_check policy evaluation returned fail as expected")

            final_status = "passed"
            self._record_step("test_result", "passed")
            print_success("E2E 25 completed successfully")
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
    test = WorkspaceSecurityContainerLicenseE2E()
    return test.run()


if __name__ == "__main__":
    sys.exit(main())
