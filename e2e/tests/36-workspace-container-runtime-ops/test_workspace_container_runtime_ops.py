#!/usr/bin/env python3
"""E2E test: workspace container runtime tools."""

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


class WorkspaceContainerRuntimeOpsE2E:
    def __init__(self) -> None:
        self.workspace_url = os.getenv(
            "WORKSPACE_URL",
            "http://workspace.swe-ai-fleet.svc.cluster.local:50053",
        ).rstrip("/")
        self.evidence_file = os.getenv("EVIDENCE_FILE", f"/tmp/e2e-36-{int(time.time())}.json")
        self.run_id = f"e2e-ws-container-ops-{int(time.time())}"
        self.sessions: list[str] = []
        self.invocation_counter = 0

        self.evidence: dict[str, Any] = {
            "test_id": "36-workspace-container-runtime-ops",
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
        timeout: int = 120,
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
                "actor_id": "e2e-container-ops",
                "roles": ["devops"],
            },
            "metadata": {},
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
            raise RuntimeError(f"{label}: missing output map")
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
            raise RuntimeError(f"{label}: expected {expected_code}, got {code}")

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
            required = ["container.ps", "container.logs", "container.run", "container.exec"]
            missing = [name for name in required if name not in tools]
            if missing:
                raise RuntimeError(f"catalog missing container tools: {missing}")
            self._record_step("catalog", "passed", {"tool_count": len(tools), "required": required})
            print_success("Catalog exposes container runtime tools")

            print_step(3, "Approval gate for container.run")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="container.run",
                approved=False,
                args={
                    "image_ref": "busybox:1.36",
                    "command": ["sleep", "5"],
                    "detach": True,
                },
            )
            self._assert_error_code(invocation=inv, body=body, label="container.run approval", expected_code="approval_required")
            self._record_step("approval_required", "passed")
            print_success("Approval requirement validated")

            runtime_required_mode = False
            container_id = "sim-e2e-container"

            print_step(4, "container.ps")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="container.ps",
                approved=False,
                args={"all": True, "limit": 20, "strict": False},
            )
            if inv is None:
                raise RuntimeError("container.ps: missing invocation")
            if str(inv.get("status", "")).strip() == "succeeded":
                output = self._assert_succeeded(invocation=inv, body=body, label="container.ps")
                runtime = str(output.get("runtime", "")).strip()
                if not runtime:
                    raise RuntimeError(f"container.ps expected runtime, got: {output}")
                self._record_step("container_ps", "passed", {"runtime": runtime, "simulated": output.get("simulated")})
                print_success("container.ps succeeded")
            else:
                error = self._extract_error(inv, body)
                code = str(error.get("code", "")).strip()
                message = str(error.get("message", "")).strip()
                if code == "execution_failed" and "container runtime not available" in message:
                    runtime_required_mode = True
                    self._record_step(
                        "container_ps",
                        "passed",
                        {"runtime_required_mode": True, "error_code": code, "error_message": message},
                    )
                    print_warning("container runtime unavailable and synthetic fallback is disabled; using strict runtime-required path")
                else:
                    raise RuntimeError(f"container.ps: unexpected failure ({code}): {message}")

            if not runtime_required_mode:
                print_step(5, "container.run")
                _, body, inv = self._invoke(
                    session_id=session_id,
                    tool_name="container.run",
                    approved=True,
                    args={
                        "image_ref": "busybox:1.36",
                        "command": ["sleep", "5"],
                        "detach": True,
                        "strict": False,
                    },
                )
                output = self._assert_succeeded(invocation=inv, body=body, label="container.run")
                container_id = str(output.get("container_id", "")).strip() or "sim-e2e-container"
                self._record_step(
                    "container_run",
                    "passed",
                    {"container_id": container_id, "runtime": output.get("runtime"), "simulated": output.get("simulated")},
                )
                print_success("container.run succeeded")

                print_step(6, "container.logs")
                _, body, inv = self._invoke(
                    session_id=session_id,
                    tool_name="container.logs",
                    approved=False,
                    args={
                        "container_id": container_id,
                        "tail_lines": 20,
                        "strict": False,
                    },
                )
                output = self._assert_succeeded(invocation=inv, body=body, label="container.logs")
                self._record_step("container_logs", "passed", {"simulated": output.get("simulated")})
                print_success("container.logs succeeded")

                print_step(7, "container.exec")
                _, body, inv = self._invoke(
                    session_id=session_id,
                    tool_name="container.exec",
                    approved=True,
                    args={
                        "container_id": container_id,
                        "command": ["echo", "ok"],
                        "strict": False,
                        "timeout_seconds": 30,
                    },
                )
                output = self._assert_succeeded(invocation=inv, body=body, label="container.exec")
                self._record_step("container_exec", "passed", {"simulated": output.get("simulated")})
                print_success("container.exec succeeded")
            else:
                self._record_step("container_runtime_required_mode", "passed")
                print_warning("Skipping run/logs/exec success path because runtime is unavailable in strict mode")

            print_step(8, "Command guardrails")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="container.exec",
                approved=True,
                args={
                    "container_id": container_id,
                    "command": ["rm", "-rf", "/"],
                    "strict": False,
                },
            )
            self._assert_error_code(invocation=inv, body=body, label="container.exec guardrail", expected_code="invalid_argument")
            self._record_step("command_guardrails", "passed")
            print_success("Command guardrails validated")

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
    return WorkspaceContainerRuntimeOpsE2E().run()


if __name__ == "__main__":
    sys.exit(main())
