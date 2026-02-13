#!/usr/bin/env python3
"""E2E test for workspace execution service.

Validates:
1) API reachability and tool catalog listing.
2) Multi-agent isolation: two sessions run the same tool in independent workspaces.
3) VLLM-driven tool selection prompt: model proposes a structured call that is executed.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
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
        self.correlation_id = f"e2e-workspace-{int(time.time())}"

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None, timeout: int = 30) -> tuple[int, dict[str, Any]]:
        url = f"{self.workspace_url}{path}"
        data = None
        headers = {"Content-Type": "application/json"}
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

    def _create_session(self, actor_id: str) -> SessionContext:
        payload = {
            "principal": {
                "tenant_id": "e2e-tenant",
                "actor_id": actor_id,
                "roles": ["developer"],
            },
            "expires_in_seconds": 3600,
        }
        status, body = self._request("POST", "/v1/sessions", payload)
        if status != 201:
            raise RuntimeError(f"create session failed ({status}): {body}")

        session_id = body["session"]["id"]
        context = SessionContext(session_id=session_id, actor_id=actor_id)
        self.sessions.append(context)
        return context

    def _delete_session(self, session_id: str) -> None:
        self._request("DELETE", f"/v1/sessions/{session_id}")

    def _invoke(self, session_id: str, tool: str, args: dict[str, Any], approved: bool = False) -> dict[str, Any]:
        payload = {
            "correlation_id": self.correlation_id,
            "approved": approved,
            "args": args,
        }
        status, body = self._request("POST", f"/v1/sessions/{session_id}/tools/{tool}/invoke", payload)
        if status != 200:
            raise RuntimeError(f"invoke {tool} failed ({status}): {body}")
        return body["invocation"]

    def _read_text(self, session_id: str, path: str) -> str:
        invocation = self._invoke(session_id, "fs.read", {"path": path}, approved=False)
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
            '{"tool":"fs.write","approved":true,"args":{"path":"llm/generated.txt","content":"..."}}. '
            "No uses markdown, no agregues texto extra."
        )

        payload = {
            "model": self.vllm_model,
            "temperature": 0,
            "max_tokens": 220,
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

        content = body["choices"][0]["message"]["content"]
        return self._extract_json_object(content)

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
        required = {"fs.read", "fs.write", "fs.search", "git.status"}
        missing = required - tools
        if missing:
            raise RuntimeError(f"missing required tools in catalog: {sorted(missing)}")

        print_success(f"Tool catalog contains required entries: {sorted(required)}")

    def step_2_multi_agent_isolation(self) -> None:
        print_step(2, "Multi-agent isolated workspaces")

        agent_a = self._create_session("agent-a")
        agent_b = self._create_session("agent-b")

        self._invoke(agent_a.session_id, "fs.write", {
            "path": "isolation/state.txt",
            "content": "agent-a-value",
            "create_parents": True,
        }, approved=True)

        self._invoke(agent_b.session_id, "fs.write", {
            "path": "isolation/state.txt",
            "content": "agent-b-value",
            "create_parents": True,
        }, approved=True)

        content_a = self._read_text(agent_a.session_id, "isolation/state.txt")
        content_b = self._read_text(agent_b.session_id, "isolation/state.txt")

        if content_a != "agent-a-value":
            raise RuntimeError(f"unexpected content for agent A: {content_a!r}")
        if content_b != "agent-b-value":
            raise RuntimeError(f"unexpected content for agent B: {content_b!r}")
        if content_a == content_b:
            raise RuntimeError("expected isolated workspaces with different file contents")

        print_success("Two agents executed tools in independent workspaces")

    def step_3_vllm_prompt_driven_tool_execution(self) -> None:
        print_step(3, "VLLM prompt-driven tool selection and execution")

        session = self._create_session("agent-llm")

        try:
            plan = self._request_tool_plan_from_vllm()
        except Exception as exc:
            if self.require_vllm:
                raise
            print_warning(f"VLLM optional mode, skipping due to error: {exc}")
            return

        tool = plan.get("tool")
        approved = bool(plan.get("approved", False))
        args = plan.get("args")

        if tool != "fs.write":
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

        print_success("VLLM generated a valid structured call and result was verified")

    def cleanup(self) -> None:
        if not self.sessions:
            return
        print_info("Cleaning up workspace sessions...")
        for session in self.sessions:
            self._delete_session(session.session_id)
        print_success(f"Cleaned {len(self.sessions)} session(s)")

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
        print()

        try:
            self.step_1_health_and_catalog()
            self.step_2_multi_agent_isolation()
            self.step_3_vllm_prompt_driven_tool_execution()

            print()
            print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
            print(f"{Colors.GREEN}E2E test PASSED{Colors.NC}")
            print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
            print()
            return 0
        except Exception as exc:
            print_error(f"E2E test FAILED: {exc}")
            return 1
        finally:
            self.cleanup()


def main() -> int:
    test = WorkspaceToolExecutionE2E()
    return test.run()


if __name__ == "__main__":
    sys.exit(main())
