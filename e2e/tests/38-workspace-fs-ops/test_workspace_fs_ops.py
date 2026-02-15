#!/usr/bin/env python3
"""E2E test: dedicated workspace filesystem operations contract."""

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


class WorkspaceFSOpsE2E:
    def __init__(self) -> None:
        self.workspace_url = os.getenv(
            "WORKSPACE_URL",
            "http://workspace.swe-ai-fleet.svc.cluster.local:50053",
        ).rstrip("/")
        self.evidence_file = os.getenv("EVIDENCE_FILE", f"/tmp/e2e-38-{int(time.time())}.json")
        self.run_id = f"e2e-ws-fs-ops-{int(time.time())}"
        self.sessions: list[str] = []
        self.invocation_counter = 0

        suffix = str(int(time.time()))
        self.base_dir = f"e2e/fs-ops-{suffix}"
        self.source_dir = f"{self.base_dir}/src"
        self.stage_dir = f"{self.base_dir}/stage"
        self.archive_dir = f"{self.base_dir}/archive"
        self.source_file = f"{self.source_dir}/note.txt"
        self.copied_file = f"{self.stage_dir}/note.copy.txt"
        self.moved_file = f"{self.archive_dir}/note.moved.txt"
        self.marker = f"workspace fs ops marker {self.run_id}"

        self.evidence: dict[str, Any] = {
            "test_id": "38-workspace-fs-ops",
            "run_id": self.run_id,
            "status": "running",
            "started_at": self._now_iso(),
            "workspace_url": self.workspace_url,
            "paths": {
                "base_dir": self.base_dir,
                "source_file": self.source_file,
                "copied_file": self.copied_file,
                "moved_file": self.moved_file,
            },
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
                "actor_id": "e2e-fs-ops",
                "roles": ["platform_admin"],
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

    def _assert_error_code_in(
        self,
        *,
        invocation: dict[str, Any] | None,
        body: dict[str, Any],
        label: str,
        expected_codes: set[str],
    ) -> None:
        if invocation is None:
            raise RuntimeError(f"{label}: missing invocation")
        error = self._extract_error(invocation, body)
        code = str(error.get("code", "")).strip()
        if code not in expected_codes:
            raise RuntimeError(f"{label}: expected one of {sorted(expected_codes)}, got {code} ({error})")

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
            print_step(1, "Workspace health and fs tool catalog")
            status, body = self._request("GET", "/healthz")
            if status != 200 or body.get("status") != "ok":
                raise RuntimeError(f"health check failed ({status}): {body}")

            session_id = self._create_session()
            status, body = self._request("GET", f"/v1/sessions/{session_id}/tools")
            if status != 200:
                raise RuntimeError(f"list tools failed ({status}): {body}")
            tools = [str(item.get("name", "")).strip() for item in body.get("tools", []) if isinstance(item, dict)]
            required = [
                "fs.mkdir",
                "fs.write_file",
                "fs.copy",
                "fs.move",
                "fs.stat",
                "fs.read_file",
                "fs.delete",
            ]
            missing = [name for name in required if name not in tools]
            if missing:
                raise RuntimeError(f"catalog missing fs tools: {missing}")
            self._record_step("catalog", "passed", {"tool_count": len(tools), "required": required})
            print_success("Catalog exposes required fs tools")

            print_step(2, "Approval gate for fs.delete")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="fs.delete",
                args={"path": self.base_dir, "recursive": True, "force": True},
                approved=False,
            )
            self._assert_error_code(
                invocation=inv,
                body=body,
                label="fs.delete approval gate",
                expected_code="approval_required",
            )
            self._record_step("delete_approval_gate", "passed")
            print_success("fs.delete requires explicit approval")

            print_step(3, "Create and populate fs fixture")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="fs.mkdir",
                args={"path": self.source_dir, "create_parents": True, "exist_ok": True},
                approved=False,
            )
            self._assert_succeeded(invocation=inv, body=body, label="fs.mkdir")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="fs.write_file",
                args={
                    "path": self.source_file,
                    "content": self.marker + "\n",
                    "encoding": "utf8",
                    "create_parents": True,
                },
                approved=True,
            )
            output = self._assert_succeeded(invocation=inv, body=body, label="fs.write_file")
            bytes_written = int(output.get("bytes_written", 0))
            if bytes_written <= 0:
                raise RuntimeError(f"fs.write_file returned invalid bytes_written: {output}")
            self._record_step("fixture_setup", "passed", {"bytes_written": bytes_written})
            print_success("Fixture file created")

            print_step(4, "Copy, stat, move and read lifecycle")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="fs.copy",
                args={
                    "source_path": self.source_file,
                    "destination_path": self.copied_file,
                    "overwrite": True,
                    "create_parents": True,
                },
                approved=False,
            )
            output = self._assert_succeeded(invocation=inv, body=body, label="fs.copy")
            if not bool(output.get("copied")):
                raise RuntimeError(f"fs.copy did not report copied=true: {output}")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="fs.stat",
                args={"path": self.copied_file},
                approved=False,
            )
            output = self._assert_succeeded(invocation=inv, body=body, label="fs.stat copied")
            if not bool(output.get("exists")):
                raise RuntimeError(f"fs.stat copied returned exists=false: {output}")
            if str(output.get("type", "")).strip() != "file":
                raise RuntimeError(f"fs.stat copied expected type=file: {output}")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="fs.move",
                args={
                    "source_path": self.copied_file,
                    "destination_path": self.moved_file,
                    "overwrite": True,
                    "create_parents": True,
                },
                approved=False,
            )
            output = self._assert_succeeded(invocation=inv, body=body, label="fs.move")
            if not bool(output.get("moved")):
                raise RuntimeError(f"fs.move did not report moved=true: {output}")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="fs.read_file",
                args={"path": self.moved_file},
                approved=False,
            )
            output = self._assert_succeeded(invocation=inv, body=body, label="fs.read_file moved")
            content = str(output.get("content", ""))
            if self.marker not in content:
                raise RuntimeError("fs.read_file content missing expected marker")
            self._record_step("copy_move_read", "passed")
            print_success("fs.copy/fs.move/fs.stat/fs.read_file lifecycle validated")

            print_step(5, "Policy and safety denies")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="fs.stat",
                args={"path": "../outside.txt"},
                approved=False,
            )
            self._assert_error_code(
                invocation=inv,
                body=body,
                label="fs.stat path traversal deny",
                expected_code="policy_denied",
            )

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="fs.delete",
                args={"path": ".", "recursive": True, "force": True},
                approved=True,
            )
            self._assert_error_code(
                invocation=inv,
                body=body,
                label="fs.delete workspace root guard",
                expected_code="policy_denied",
            )

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="fs.delete",
                args={"path": self.base_dir, "recursive": False, "force": False},
                approved=True,
            )
            self._assert_error_code_in(
                invocation=inv,
                body=body,
                label="fs.delete directory recursive required",
                expected_codes={"invalid_argument", "execution_failed"},
            )
            self._record_step("policy_denies", "passed")
            print_success("Policy/safety deny paths validated")

            print_step(6, "Delete lifecycle and post-delete stat")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="fs.delete",
                args={"path": self.base_dir, "recursive": True, "force": True},
                approved=True,
            )
            output = self._assert_succeeded(invocation=inv, body=body, label="fs.delete recursive")
            if not bool(output.get("deleted")):
                raise RuntimeError(f"fs.delete recursive did not report deleted=true: {output}")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="fs.stat",
                args={"path": self.base_dir},
                approved=False,
            )
            output = self._assert_succeeded(invocation=inv, body=body, label="fs.stat deleted")
            if bool(output.get("exists")):
                raise RuntimeError(f"fs.stat deleted expected exists=false: {output}")

            self._record_step("delete_and_stat", "passed")
            print_success("fs.delete + fs.stat post-delete contract validated")

            final_status = "passed"
            return 0

        except Exception as exc:
            error_message = str(exc)
            print_error(error_message)
            return 1
        finally:
            self.cleanup()
            self._write_evidence(final_status, error_message)


def main() -> int:
    return WorkspaceFSOpsE2E().run()


if __name__ == "__main__":
    sys.exit(main())
