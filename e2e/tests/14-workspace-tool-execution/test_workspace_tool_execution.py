#!/usr/bin/env python3
"""E2E test for workspace execution service.

Validates:
1) API reachability and tool catalog listing.
2) Multi-agent isolation: two sessions run the same tool in independent workspaces.
3) VLLM-driven tool selection prompt: model proposes a structured call that is executed.

This script also emits structured evidence JSON (file + logs) for evaluation.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable


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
    print(f"{Colors.GREEN}✓ {message}{Colors.NC}")


def print_error(message: str) -> None:
    print(f"{Colors.RED}✗ {message}{Colors.NC}")


def print_warning(message: str) -> None:
    print(f"{Colors.YELLOW}⚠ {message}{Colors.NC}")


def print_info(message: str) -> None:
    print(f"{Colors.YELLOW}ℹ {message}{Colors.NC}")


@dataclass
class SessionContext:
    session_id: str
    actor_id: str


class WorkspaceToolExecutionE2E:
    def __init__(self) -> None:
        self.workspace_url = os.getenv(
            "WORKSPACE_URL",
            "http://workspace.swe-ai-fleet.svc.cluster.local:50053",
        ).rstrip("/")
        self.vllm_chat_url = os.getenv(
            "VLLM_CHAT_URL",
            "http://vllm-server-service.swe-ai-fleet.svc.cluster.local:8000/v1/chat/completions",
        )
        self.vllm_model = os.getenv("VLLM_MODEL", "Qwen/Qwen3-0.6B")
        self.require_vllm = os.getenv("REQUIRE_VLLM", "true").lower() in ("1", "true", "yes")

        self.sessions: list[SessionContext] = []
        self.run_id = f"e2e-workspace-14-{int(time.time())}"
        self.correlation_id = self.run_id

        self.fs_read_tool = "fs.read"
        self.fs_write_tool = "fs.write"

        self.evidence_file = os.getenv("EVIDENCE_FILE", f"/tmp/{self.run_id}-evidence.json")
        self.evidence: dict[str, Any] = {
            "test_id": "14-workspace-tool-execution",
            "run_id": self.run_id,
            "status": "running",
            "started_at": self._now_iso(),
            "configuration": {
                "workspace_url": self.workspace_url,
                "vllm_chat_url": self.vllm_chat_url,
                "vllm_model": self.vllm_model,
                "require_vllm": self.require_vllm,
            },
            "steps": [],
            "sessions": [],
            "invocations": [],
            "vllm_plan": None,
        }

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _compact(self, value: Any, max_str: int = 800) -> Any:
        if isinstance(value, str):
            if len(value) <= max_str:
                return value
            return value[:max_str] + "...<truncated>"
        if isinstance(value, dict):
            return {str(k): self._compact(v, max_str=max_str) for k, v in value.items()}
        if isinstance(value, list):
            limited = value[:50]
            compacted = [self._compact(item, max_str=max_str) for item in limited]
            if len(value) > 50:
                compacted.append(f"...<truncated {len(value) - 50} items>")
            return compacted
        return value

    def _record_step(self, step_name: str, status: str, message: str = "", data: Any | None = None) -> None:
        item: dict[str, Any] = {
            "at": self._now_iso(),
            "step": step_name,
            "status": status,
        }
        if message:
            item["message"] = message
        if data is not None:
            item["data"] = self._compact(data)
        self.evidence["steps"].append(item)

    def _record_invocation(
        self,
        *,
        session_id: str,
        tool: str,
        approved: bool,
        args: dict[str, Any],
        http_status: int,
        invocation: dict[str, Any] | None,
    ) -> None:
        error = invocation.get("error") if isinstance(invocation, dict) else None
        output = invocation.get("output") if isinstance(invocation, dict) else None

        entry = {
            "at": self._now_iso(),
            "session_id": session_id,
            "tool": tool,
            "approved": approved,
            "http_status": http_status,
            "args": self._compact(args),
            "invocation_id": invocation.get("id") if isinstance(invocation, dict) else None,
            "invocation_status": invocation.get("status") if isinstance(invocation, dict) else None,
            "exit_code": invocation.get("exit_code") if isinstance(invocation, dict) else None,
            "duration_ms": invocation.get("duration_ms") if isinstance(invocation, dict) else None,
            "error_code": error.get("code") if isinstance(error, dict) else None,
            "error_message": error.get("message") if isinstance(error, dict) else None,
            "output": self._compact(output),
        }
        self.evidence["invocations"].append(entry)

    def _write_evidence(self, final_status: str, error_message: str = "") -> None:
        self.evidence["status"] = final_status
        self.evidence["ended_at"] = self._now_iso()
        self.evidence["session_count"] = len(self.sessions)
        if error_message:
            self.evidence["error_message"] = error_message

        try:
            with open(self.evidence_file, "w", encoding="utf-8") as handle:
                json.dump(self.evidence, handle, ensure_ascii=False, indent=2)
            print_info(f"Evidence file: {self.evidence_file}")
        except Exception as exc:
            print_warning(f"Could not write evidence file: {exc}")

        print("EVIDENCE_JSON_START")
        print(json.dumps(self.evidence, ensure_ascii=False, indent=2))
        print("EVIDENCE_JSON_END")

    def _execute_step(self, step_name: str, fn: Callable[[], Any]) -> Any:
        try:
            result = fn()
            self._record_step(step_name, "passed")
            return result
        except Exception as exc:
            self._record_step(step_name, "failed", message=str(exc))
            raise

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        timeout: int = 30,
    ) -> tuple[int, dict[str, Any]]:
        url = f"{self.workspace_url}{path}"
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
        req = urllib.request.Request(url=url, data=data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = response.read().decode("utf-8")
                parsed = json.loads(body) if body else {}
                return response.status, parsed
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8")
            parsed = json.loads(body) if body else {}
            return exc.code, parsed

    def _resolve_fs_aliases(self, tools: set[str]) -> tuple[str, str]:
        read_tool = ""
        write_tool = ""

        for candidate in ("fs.read_file", "fs.read"):
            if candidate in tools:
                read_tool = candidate
                break

        for candidate in ("fs.write_file", "fs.write"):
            if candidate in tools:
                write_tool = candidate
                break

        if not read_tool or not write_tool:
            raise RuntimeError("catalog missing fs read/write aliases")

        return read_tool, write_tool

    def _create_session(self, actor_id: str, allowed_paths: list[str] | None = None) -> SessionContext:
        payload = {
            "principal": {
                "tenant_id": "e2e-tenant",
                "actor_id": actor_id,
                "roles": ["developer"],
            },
            "expires_in_seconds": 3600,
        }
        if allowed_paths is not None:
            payload["allowed_paths"] = allowed_paths
        status, body = self._request("POST", "/v1/sessions", payload)
        if status != 201:
            raise RuntimeError(f"create session failed ({status}): {body}")

        session_id = body["session"]["id"]
        context = SessionContext(session_id=session_id, actor_id=actor_id)
        self.sessions.append(context)
        self.evidence["sessions"].append(
            {
                "at": self._now_iso(),
                "session_id": session_id,
                "actor_id": actor_id,
            }
        )
        return context

    def _delete_session(self, session_id: str) -> None:
        self._request("DELETE", f"/v1/sessions/{session_id}")

    def _invoke_raw(
        self,
        session_id: str,
        tool: str,
        args: dict[str, Any],
        approved: bool = False,
    ) -> tuple[int, dict[str, Any], dict[str, Any] | None]:
        payload = {
            "correlation_id": self.correlation_id,
            "approved": approved,
            "args": args,
        }
        status, body = self._request("POST", f"/v1/sessions/{session_id}/tools/{tool}/invoke", payload)
        invocation = body.get("invocation") if isinstance(body, dict) else None

        self._record_invocation(
            session_id=session_id,
            tool=tool,
            approved=approved,
            args=args,
            http_status=status,
            invocation=invocation if isinstance(invocation, dict) else None,
        )

        return status, body, invocation if isinstance(invocation, dict) else None

    def _invoke(self, session_id: str, tool: str, args: dict[str, Any], approved: bool = False) -> dict[str, Any]:
        status, body, invocation = self._invoke_raw(session_id, tool, args, approved=approved)
        if status != 200:
            raise RuntimeError(f"invoke {tool} failed ({status}): {body}")
        if invocation is None:
            raise RuntimeError(f"invoke {tool} returned malformed payload: {body}")
        return invocation

    def _read_text(self, session_id: str, path: str) -> str:
        invocation = self._invoke(session_id, self.fs_read_tool, {"path": path}, approved=False)
        return invocation["output"]["content"]

    def _extract_json_object(self, content: str) -> dict[str, Any]:
        text = content.strip()

        if text.startswith("```"):
            text = text.strip("`")
            if "\n" in text:
                text = text.split("\n", 1)[1]

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError(f"no JSON object found in model output: {content!r}")

        candidate = text[start : end + 1]
        return json.loads(candidate)

    def _request_tool_plan_from_vllm(self) -> dict[str, Any]:
        prompt = (
            "Devuelve SOLO JSON valido con este esquema: "
            f'{{"tool":"{self.fs_write_tool}","approved":true,"args":{{"path":"llm/generated.txt","content":"..."}}}}. '
            "No uses markdown, no agregues texto extra."
        )

        payload = {
            "model": self.vllm_model,
            "temperature": 0,
            "max_tokens": 280,
            "messages": [
                {
                    "role": "system",
                    "content": "Eres un planificador de tools. Responde JSON estricto.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url=self.vllm_chat_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8"))

        message = body["choices"][0]["message"]
        content = message.get("content") or ""
        reasoning = message.get("reasoning_content") or ""
        raw = content if content.strip() else reasoning
        if not raw.strip():
            raw = content + "\n" + reasoning

        plan = self._extract_json_object(raw)
        self.evidence["vllm_plan"] = {
            "at": self._now_iso(),
            "raw": self._compact(raw),
            "parsed": self._compact(plan),
        }
        return plan

    def _normalize_write_tool(self, tool_name: str) -> str:
        candidate = (tool_name or "").strip()
        if candidate == self.fs_write_tool:
            return candidate

        if candidate == "fs.write" and self.fs_write_tool == "fs.write_file":
            return self.fs_write_tool
        if candidate == "fs.write_file" and self.fs_write_tool == "fs.write":
            return self.fs_write_tool
        return candidate

    def step_1_health_and_catalog(self) -> None:
        print_step(1, "Workspace API health and tool catalog")

        status, body = self._request("GET", "/healthz")
        if status != 200 or body.get("status") != "ok":
            raise RuntimeError(f"health check failed: {status} {body}")
        print_success("Workspace API is healthy")

        session = self._create_session("agent-health")
        status, body = self._request("GET", f"/v1/sessions/{session.session_id}/tools")
        if status != 200:
            raise RuntimeError(f"tools.list failed: {status} {body}")

        tools = {tool["name"] for tool in body.get("tools", [])}
        self.fs_read_tool, self.fs_write_tool = self._resolve_fs_aliases(tools)

        required = {self.fs_read_tool, self.fs_write_tool, "fs.search", "git.status"}
        missing = required - tools
        if missing:
            raise RuntimeError(f"missing required tools in catalog: {sorted(missing)}")

        self._record_step(
            "catalog_discovered",
            "passed",
            data={
                "available_tools": sorted(tools),
                "fs_read_tool": self.fs_read_tool,
                "fs_write_tool": self.fs_write_tool,
            },
        )
        print_success(f"Tool catalog contains required entries: {sorted(required)}")

    def step_2_multi_agent_isolation(self) -> None:
        print_step(2, "Multi-agent isolated workspaces")

        agent_a = self._create_session("agent-a")
        agent_b = self._create_session("agent-b")

        self._invoke(
            agent_a.session_id,
            self.fs_write_tool,
            {
                "path": "isolation/state.txt",
                "content": "agent-a-value",
                "create_parents": True,
            },
            approved=True,
        )

        self._invoke(
            agent_b.session_id,
            self.fs_write_tool,
            {
                "path": "isolation/state.txt",
                "content": "agent-b-value",
                "create_parents": True,
            },
            approved=True,
        )

        content_a = self._read_text(agent_a.session_id, "isolation/state.txt")
        content_b = self._read_text(agent_b.session_id, "isolation/state.txt")

        if content_a != "agent-a-value":
            raise RuntimeError(f"unexpected content for agent A: {content_a!r}")
        if content_b != "agent-b-value":
            raise RuntimeError(f"unexpected content for agent B: {content_b!r}")
        if content_a == content_b:
            raise RuntimeError("expected isolated workspaces with different file contents")

        self._record_step(
            "multi_agent_isolation",
            "passed",
            data={
                "agent_a_content": content_a,
                "agent_b_content": content_b,
            },
        )
        print_success("Two agents executed tools in independent workspaces")

    def step_3_policy_enforcement(self) -> None:
        print_step(3, "Policy enforcement (approval + allowed_paths)")

        session = self._create_session("agent-policy", allowed_paths=["sandbox"])

        status, body, _ = self._invoke_raw(
            session.session_id,
            self.fs_write_tool,
            {
                "path": "sandbox/no-approval.txt",
                "content": "denied-without-approval",
                "create_parents": True,
            },
            approved=False,
        )
        if status != 428:
            raise RuntimeError(f"expected 428 for missing approval, got {status}: {body}")
        error = body.get("error", {})
        if error.get("code") != "approval_required":
            raise RuntimeError(f"expected approval_required error, got: {body}")

        status, body, _ = self._invoke_raw(
            session.session_id,
            self.fs_read_tool,
            {"path": "outside.txt"},
            approved=False,
        )
        if status != 403:
            raise RuntimeError(f"expected 403 for out-of-scope path, got {status}: {body}")
        error = body.get("error", {})
        if error.get("code") != "policy_denied":
            raise RuntimeError(f"expected policy_denied error, got: {body}")

        self._record_step(
            "policy_enforcement",
            "passed",
            data={
                "approval_required_status": 428,
                "path_policy_denied_status": 403,
            },
        )
        print_success("Policy denied unapproved write and out-of-scope path access")

    def step_4_vllm_prompt_driven_tool_execution(self) -> None:
        print_step(4, "VLLM prompt-driven tool selection and execution")

        session = self._create_session("agent-llm")

        try:
            plan = self._request_tool_plan_from_vllm()
        except Exception as exc:
            if self.require_vllm:
                raise
            self._record_step("vllm_plan", "skipped", message=str(exc))
            print_warning(f"VLLM optional mode, skipping due to error: {exc}")
            return

        tool = self._normalize_write_tool(str(plan.get("tool", "")))
        approved = bool(plan.get("approved", False))
        args = plan.get("args")

        if tool != self.fs_write_tool:
            raise RuntimeError(f"unexpected tool from VLLM: {tool!r}")
        if not isinstance(args, dict):
            raise RuntimeError(f"invalid args from VLLM: {args!r}")
        if "path" not in args or "content" not in args:
            raise RuntimeError(f"VLLM args must include path/content: {args!r}")

        invocation = self._invoke(session.session_id, tool, args, approved=approved)
        if invocation.get("status") != "succeeded":
            raise RuntimeError(f"expected succeeded invocation, got: {invocation}")

        content = self._read_text(session.session_id, args["path"])
        if content != args["content"]:
            raise RuntimeError(
                f"VLLM-driven write mismatch: expected {args['content']!r}, got {content!r}"
            )

        self._record_step(
            "vllm_tool_execution",
            "passed",
            data={
                "tool": tool,
                "approved": approved,
                "path": args.get("path"),
                "content_length": len(str(args.get("content", ""))),
            },
        )
        print_success("VLLM generated a valid structured call and result was verified")

    def cleanup(self) -> None:
        if not self.sessions:
            return
        print_info("Cleaning up workspace sessions...")

        cleaned = 0
        failed = 0
        for session in self.sessions:
            try:
                self._delete_session(session.session_id)
                cleaned += 1
            except Exception:
                failed += 1

        self._record_step(
            "cleanup",
            "passed" if failed == 0 else "partial",
            data={"cleaned_sessions": cleaned, "failed_sessions": failed},
        )
        print_success(f"Cleaned {cleaned} session(s)")
        if failed > 0:
            print_warning(f"Cleanup failures: {failed}")

    def run(self) -> int:
        print()
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print(f"{Colors.BLUE}Workspace Tool Execution E2E Test{Colors.NC}")
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print()

        print("Configuration:")
        print(f"  WORKSPACE_URL: {self.workspace_url}")
        print(f"  VLLM_CHAT_URL: {self.vllm_chat_url}")
        print(f"  VLLM_MODEL: {self.vllm_model}")
        print(f"  REQUIRE_VLLM: {self.require_vllm}")
        print(f"  EVIDENCE_FILE: {self.evidence_file}")
        print()

        final_status = "failed"
        error_message = ""

        try:
            self._execute_step("step_1_health_and_catalog", self.step_1_health_and_catalog)
            self._execute_step("step_2_multi_agent_isolation", self.step_2_multi_agent_isolation)
            self._execute_step("step_3_policy_enforcement", self.step_3_policy_enforcement)
            self._execute_step(
                "step_4_vllm_prompt_driven_tool_execution",
                self.step_4_vllm_prompt_driven_tool_execution,
            )

            print()
            print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
            print(f"{Colors.GREEN}E2E test PASSED{Colors.NC}")
            print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
            print()
            final_status = "passed"
            return 0
        except Exception as exc:
            error_message = str(exc)
            print_error(f"E2E test FAILED: {exc}")
            return 1
        finally:
            self.cleanup()
            self._write_evidence(final_status, error_message=error_message)


def main() -> int:
    test = WorkspaceToolExecutionE2E()
    return test.run()


if __name__ == "__main__":
    sys.exit(main())
