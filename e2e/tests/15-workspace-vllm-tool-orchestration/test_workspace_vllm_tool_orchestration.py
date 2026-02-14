#!/usr/bin/env python3
"""E2E test: vLLM-driven orchestration over Workspace tool catalog.

Validates a more complex flow where:
1) Tool catalog is obtained from Workspace API.
2) vLLM returns a tool execution order based on the discovered catalog.
3) The runner executes one invocation per available tool (coverage-focused).
4) File-system tools are validated strictly; git/repo tools are validated with
   environment-aware expectations (soft-fail accepted when toolchain is absent).

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
    print(f"{Colors.GREEN}OK {message}{Colors.NC}")


def print_error(message: str) -> None:
    print(f"{Colors.RED}ERROR {message}{Colors.NC}")


def print_warning(message: str) -> None:
    print(f"{Colors.YELLOW}WARN {message}{Colors.NC}")


def print_info(message: str) -> None:
    print(f"{Colors.YELLOW}INFO {message}{Colors.NC}")


@dataclass
class SessionContext:
    session_id: str
    actor_id: str


class WorkspaceVLLMToolOrchestrationE2E:
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
        self.strict_vllm_plan = os.getenv("STRICT_VLLM_PLAN", "false").lower() in (
            "1",
            "true",
            "yes",
        )

        self.sessions: list[SessionContext] = []
        self.available_tools: list[str] = []
        self.execution_order: list[str] = []
        self.invocation_counter = 0
        self.run_id = f"e2e-ws-vllm-{int(time.time())}"

        self.fs_read_tool = ""
        self.fs_write_tool = ""

        self.flow_file_path = "notes/flow.txt"
        self.flow_v1 = "line1\ncoverage-marker\nline3\n"

        self.fs_patch_diff = (
            "diff --git a/notes/flow.txt b/notes/flow.txt\n"
            "--- a/notes/flow.txt\n"
            "+++ b/notes/flow.txt\n"
            "@@ -1,3 +1,3 @@\n"
            " line1\n"
            " coverage-marker\n"
            "-line3\n"
            "+line-three-updated\n"
        )
        self.git_check_patch = (
            "diff --git a/notes/flow.txt b/notes/flow.txt\n"
            "--- a/notes/flow.txt\n"
            "+++ b/notes/flow.txt\n"
            "@@ -1,3 +1,3 @@\n"
            "-line1\n"
            "+line-one\n"
            " coverage-marker\n"
            " line-three-updated\n"
        )

        self.evidence_file = os.getenv("EVIDENCE_FILE", f"/tmp/{self.run_id}-evidence.json")
        self.evidence: dict[str, Any] = {
            "test_id": "15-workspace-vllm-tool-orchestration",
            "run_id": self.run_id,
            "status": "running",
            "started_at": self._now_iso(),
            "configuration": {
                "workspace_url": self.workspace_url,
                "vllm_chat_url": self.vllm_chat_url,
                "vllm_model": self.vllm_model,
                "require_vllm": self.require_vllm,
                "strict_vllm_plan": self.strict_vllm_plan,
            },
            "steps": [],
            "sessions": [],
            "tool_catalog": [],
            "execution_order": [],
            "vllm_plan": None,
            "invocations": [],
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

    def _request_plan_from_vllm(self, available_tools: list[str]) -> list[str]:
        def infer_tool_order_from_text(text: str) -> list[str]:
            lowered = text.lower()
            positions: list[tuple[int, str]] = []
            for tool in available_tools:
                idx = lowered.find(tool.lower())
                if idx >= 0:
                    positions.append((idx, tool))
            positions.sort(key=lambda item: item[0])
            inferred = [name for _, name in positions]

            deduped: list[str] = []
            seen: set[str] = set()
            for item in inferred:
                if item not in seen:
                    deduped.append(item)
                    seen.add(item)
            return deduped

        def build_messages(feedback: str | None) -> list[dict[str, str]]:
            rule_text = (
                '/no_think Devuelve SOLO JSON valido con schema exacto: '
                '{"ordered_tools":["tool_a","tool_b"]}. '
                "Incluye cada tool disponible exactamente una vez. "
                "No texto fuera de JSON."
            )
            user_prompt = (
                f"Tools disponibles (usa exactamente estos nombres): {json.dumps(available_tools)}. "
                "Orden preferido: fs.read/fs.list/fs.search, luego fs.write/fs.patch, despues git/repo. "
                f"{rule_text}"
            )
            if feedback:
                user_prompt += f" Correccion obligatoria: {feedback}"

            return [
                {
                    "role": "system",
                    "content": "Eres un planificador de tools. Respondes JSON estricto.",
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ]

        feedback: str | None = None
        last_output = ""
        last_parsed: dict[str, Any] | None = None

        for _ in range(2):
            payload = {
                "model": self.vllm_model,
                "temperature": 0,
                "max_tokens": 900,
                "messages": build_messages(feedback),
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url=self.vllm_chat_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                body = json.loads(response.read().decode("utf-8"))

            message = body["choices"][0]["message"]
            content = message.get("content") or ""
            reasoning = message.get("reasoning_content") or ""
            raw_model_output = content if content.strip() else reasoning
            if not raw_model_output.strip():
                raw_model_output = content + "\n" + reasoning

            last_output = raw_model_output
            try:
                parsed = self._extract_json_object(raw_model_output)
                last_parsed = parsed
            except Exception:
                inferred = infer_tool_order_from_text(raw_model_output)
                if inferred:
                    self.evidence["vllm_plan"] = {
                        "at": self._now_iso(),
                        "source": "text-inference",
                        "raw": self._compact(raw_model_output),
                        "ordered_tools": inferred,
                    }
                    return inferred
                feedback = "No pude parsear JSON. Responde SOLO JSON valido con ordered_tools."
                continue

            ordered = parsed.get("ordered_tools")
            if not isinstance(ordered, list) or not all(isinstance(item, str) for item in ordered):
                feedback = "ordered_tools debe ser un array de strings"
                continue

            cleaned = [item.strip() for item in ordered if item.strip()]
            if len(cleaned) != len(set(cleaned)):
                feedback = "ordered_tools no debe contener duplicados"
                continue

            unknown = [item for item in cleaned if item not in available_tools]
            if unknown:
                feedback = f"ordered_tools contiene tools no validos: {unknown}"
                continue

            self.evidence["vllm_plan"] = {
                "at": self._now_iso(),
                "source": "json",
                "raw": self._compact(raw_model_output),
                "parsed": self._compact(parsed),
                "ordered_tools": cleaned,
            }
            return cleaned

        inferred = infer_tool_order_from_text(last_output)
        if inferred:
            self.evidence["vllm_plan"] = {
                "at": self._now_iso(),
                "source": "fallback-text-inference",
                "raw": self._compact(last_output),
                "parsed": self._compact(last_parsed),
                "ordered_tools": inferred,
            }
            return inferred

        raise RuntimeError("vLLM did not return a valid ordered_tools plan")

    def _deterministic_order(self, tools: list[str]) -> list[str]:
        preferred = [
            "fs.list",
            "conn.list_profiles",
            "conn.describe_profile",
            "nats.request",
            "nats.subscribe_pull",
            "kafka.topic_metadata",
            "kafka.consume",
            "rabbit.queue_info",
            "rabbit.consume",
            "redis.get",
            "redis.mget",
            "redis.scan",
            "redis.ttl",
            "redis.exists",
            "mongo.find",
            "mongo.aggregate",
            "fs.read_file",
            "fs.read",
            "fs.search",
            "fs.write_file",
            "fs.write",
            "fs.patch",
            "git.status",
            "git.diff",
            "git.apply_patch",
            "repo.detect_project_type",
            "repo.detect_toolchain",
            "repo.validate",
            "repo.build",
            "repo.test",
            "repo.run_tests",
            "repo.coverage_report",
            "repo.static_analysis",
            "repo.package",
            "security.scan_secrets",
            "ci.run_pipeline",
            "go.mod.tidy",
            "go.generate",
            "go.build",
            "go.test",
            "rust.build",
            "rust.test",
            "rust.clippy",
            "rust.format",
            "node.install",
            "node.build",
            "node.test",
            "node.lint",
            "node.typecheck",
            "python.install_deps",
            "python.validate",
            "python.test",
            "c.build",
            "c.test",
        ]
        ordered = [name for name in preferred if name in tools]
        extras = sorted(name for name in tools if name not in ordered)
        return ordered + extras

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

    def _list_tools(self, session_id: str) -> list[str]:
        status, body = self._request("GET", f"/v1/sessions/{session_id}/tools")
        if status != 200:
            raise RuntimeError(f"tools.list failed ({status}): {body}")
        tools = [item.get("name", "").strip() for item in body.get("tools", [])]
        return [item for item in tools if item]

    def _invoke(
        self,
        session_id: str,
        tool: str,
        args: dict[str, Any],
        approved: bool = False,
    ) -> dict[str, Any]:
        self.invocation_counter += 1
        payload = {
            "correlation_id": f"{self.run_id}-{self.invocation_counter:04d}",
            "approved": approved,
            "args": args,
        }
        status, body = self._request(
            "POST",
            f"/v1/sessions/{session_id}/tools/{tool}/invoke",
            payload,
            timeout=80,
        )
        invocation = body.get("invocation") if isinstance(body, dict) else None

        self._record_invocation(
            session_id=session_id,
            tool=tool,
            approved=approved,
            args=args,
            http_status=status,
            invocation=invocation if isinstance(invocation, dict) else None,
        )

        if isinstance(invocation, dict):
            if status not in (200, 500):
                raise RuntimeError(f"invoke {tool} unexpected status ({status}): {body}")
            return invocation
        raise RuntimeError(f"invoke {tool} failed ({status}): {body}")

    def _resolve_fs_aliases(self) -> None:
        for candidate in ("fs.read_file", "fs.read"):
            if candidate in self.available_tools:
                self.fs_read_tool = candidate
                break

        for candidate in ("fs.write_file", "fs.write"):
            if candidate in self.available_tools:
                self.fs_write_tool = candidate
                break

        if not self.fs_read_tool:
            raise RuntimeError("catalog missing fs read tool alias")
        if not self.fs_write_tool:
            raise RuntimeError("catalog missing fs write tool alias")

    def step_1_health_session_and_catalog(self) -> SessionContext:
        print_step(1, "Workspace health, session bootstrap, and tool discovery")

        status, body = self._request("GET", "/healthz")
        if status != 200 or body.get("status") != "ok":
            raise RuntimeError(f"workspace health check failed: {status} {body}")
        print_success("Workspace API is healthy")

        session = self._create_session("agent-vllm-orchestrator")
        self.available_tools = self._list_tools(session.session_id)
        if not self.available_tools:
            raise RuntimeError("tools catalog is empty")

        self._resolve_fs_aliases()

        required_min = {"fs.list", "fs.search", self.fs_read_tool, self.fs_write_tool}
        missing_min = sorted(item for item in required_min if item not in self.available_tools)
        if missing_min:
            raise RuntimeError(f"catalog missing minimum required tools: {missing_min}")

        self.evidence["tool_catalog"] = sorted(self.available_tools)
        self._record_step(
            "catalog_discovered",
            "passed",
            data={
                "tool_count": len(self.available_tools),
                "tools": sorted(self.available_tools),
                "fs_read_tool": self.fs_read_tool,
                "fs_write_tool": self.fs_write_tool,
            },
        )

        print_success(f"Discovered {len(self.available_tools)} tools")
        print_info(f"Tools: {sorted(self.available_tools)}")
        return session

    def step_2_vllm_planning(self) -> None:
        print_step(2, "vLLM planning based on catalog from Workspace API")

        try:
            planned = self._request_plan_from_vllm(self.available_tools)
            print_success("vLLM produced an ordered_tools plan")
            self.execution_order = planned
        except Exception as exc:
            if self.require_vllm:
                raise RuntimeError(f"vLLM planning failed and REQUIRE_VLLM=true: {exc}") from exc
            print_warning(f"vLLM planning unavailable, fallback to deterministic order: {exc}")
            self.execution_order = self._deterministic_order(self.available_tools)
            self._record_step(
                "vllm_planning",
                "fallback",
                message=str(exc),
                data={"execution_order": self.execution_order},
            )
            return

        missing = [item for item in self.available_tools if item not in self.execution_order]
        if missing:
            if self.strict_vllm_plan:
                raise RuntimeError(f"vLLM plan missing tools with STRICT_VLLM_PLAN=true: {missing}")
            print_warning(f"vLLM plan missing tools, appending deterministically: {missing}")
            self.execution_order.extend(missing)

        unknown = [item for item in self.execution_order if item not in self.available_tools]
        if unknown:
            raise RuntimeError(f"vLLM plan contains unknown tools: {unknown}")

        self.evidence["execution_order"] = list(self.execution_order)
        self._record_step(
            "vllm_planning",
            "passed",
            data={
                "execution_order": self.execution_order,
                "missing_after_plan": missing,
            },
        )

        print_info(f"Execution order: {self.execution_order}")

    def _setup_workspace_files(self, session_id: str) -> None:
        self._invoke(
            session_id,
            self.fs_write_tool,
            {
                "path": self.flow_file_path,
                "content": self.flow_v1,
                "create_parents": True,
            },
            approved=True,
        )

        self._invoke(
            session_id,
            self.fs_write_tool,
            {
                "path": "go.mod",
                "content": "module e2e/sample\n\ngo 1.22\n",
                "create_parents": True,
            },
            approved=True,
        )
        self._invoke(
            session_id,
            self.fs_write_tool,
            {
                "path": "sample.go",
                "content": "package sample\n\nfunc Add(a, b int) int {\n\treturn a + b\n}\n",
                "create_parents": True,
            },
            approved=True,
        )
        self._invoke(
            session_id,
            self.fs_write_tool,
            {
                "path": "sample_test.go",
                "content": (
                    "package sample\n\n"
                    "import \"testing\"\n\n"
                    "func TestAdd(t *testing.T) {\n"
                    "\tif got := Add(2, 3); got != 5 {\n"
                    "\t\tt.Fatalf(\"expected 5, got %d\", got)\n"
                    "\t}\n"
                    "}\n"
                ),
                "create_parents": True,
            },
            approved=True,
        )
        self._invoke(
            session_id,
            self.fs_write_tool,
            {
                "path": "csrc/main.c",
                "content": "int main(void){return 0;}\n",
                "create_parents": True,
            },
            approved=True,
        )
        self._invoke(
            session_id,
            self.fs_write_tool,
            {
                "path": "csrc/main_test.c",
                "content": "int main(void){return 0;}\n",
                "create_parents": True,
            },
            approved=True,
        )

    def _tool_input(self, tool_name: str) -> tuple[dict[str, Any], bool, bool]:
        # returns args, approved, strict_success
        if tool_name == "fs.list":
            return {"path": ".", "recursive": True, "max_entries": 200}, False, True
        if tool_name == "conn.list_profiles":
            return {}, False, True
        if tool_name == "conn.describe_profile":
            return {"profile_id": "dev.redis"}, False, True
        if tool_name == "nats.request":
            return {"profile_id": "dev.nats", "subject": "sandbox.echo", "payload": "hello", "timeout_ms": 500}, False, False
        if tool_name == "nats.subscribe_pull":
            return {"profile_id": "dev.nats", "subject": "sandbox.events", "max_messages": 2, "timeout_ms": 500}, False, False
        if tool_name == "kafka.topic_metadata":
            return {"profile_id": "dev.kafka", "topic": "sandbox.events"}, False, False
        if tool_name == "kafka.consume":
            return {
                "profile_id": "dev.kafka",
                "topic": "sandbox.events",
                "partition": 0,
                "offset": "latest",
                "max_messages": 2,
                "timeout_ms": 500,
            }, False, False
        if tool_name == "rabbit.queue_info":
            return {"profile_id": "dev.rabbit", "queue": "sandbox.jobs", "timeout_ms": 500}, False, False
        if tool_name == "rabbit.consume":
            return {"profile_id": "dev.rabbit", "queue": "sandbox.jobs", "max_messages": 2, "timeout_ms": 500}, False, False
        if tool_name == "redis.get":
            return {"profile_id": "dev.redis", "key": "sandbox:e2e:key1", "max_bytes": 256}, False, False
        if tool_name == "redis.mget":
            return {"profile_id": "dev.redis", "keys": ["sandbox:e2e:key1", "sandbox:e2e:key2"], "max_bytes": 512}, False, False
        if tool_name == "redis.scan":
            return {"profile_id": "dev.redis", "prefix": "sandbox:", "max_keys": 20, "count_hint": 20}, False, False
        if tool_name == "redis.ttl":
            return {"profile_id": "dev.redis", "key": "sandbox:e2e:key1"}, False, False
        if tool_name == "redis.exists":
            return {"profile_id": "dev.redis", "keys": ["sandbox:e2e:key1"]}, False, False
        if tool_name == "mongo.find":
            return {
                "profile_id": "dev.mongo",
                "database": "sandbox",
                "collection": "todos",
                "filter": {},
                "limit": 5,
            }, False, False
        if tool_name == "mongo.aggregate":
            return {
                "profile_id": "dev.mongo",
                "database": "sandbox",
                "collection": "todos",
                "pipeline": [{"$match": {"status": "open"}}],
                "limit": 5,
            }, False, False
        if tool_name in ("fs.read", "fs.read_file"):
            return {"path": self.flow_file_path}, False, True
        if tool_name in ("fs.write", "fs.write_file"):
            return {
                "path": self.flow_file_path,
                "content": self.flow_v1,
                "create_parents": True,
            }, True, True
        if tool_name == "fs.search":
            return {"path": ".", "pattern": "coverage-marker", "max_results": 20}, False, True
        if tool_name == "fs.patch":
            return {"unified_diff": self.fs_patch_diff, "strategy": "reject_on_conflict"}, True, False
        if tool_name == "git.status":
            return {"short": True}, False, False
        if tool_name == "git.diff":
            return {"staged": False, "paths": [self.flow_file_path]}, False, False
        if tool_name == "git.apply_patch":
            return {"patch": self.git_check_patch, "check": True}, True, False
        if tool_name == "repo.detect_project_type":
            return {}, False, False
        if tool_name == "repo.detect_toolchain":
            return {}, False, False
        if tool_name == "repo.validate":
            return {"target": "./..."}, False, False
        if tool_name == "repo.build":
            return {"target": "./..."}, False, False
        if tool_name == "repo.test":
            return {"target": "./..."}, False, False
        if tool_name == "repo.run_tests":
            return {"target": "./..."}, False, False
        if tool_name == "repo.coverage_report":
            return {"target": "./..."}, False, False
        if tool_name == "repo.static_analysis":
            return {"target": "./..."}, False, False
        if tool_name == "repo.package":
            return {"target": "."}, False, False
        if tool_name == "security.scan_secrets":
            return {"path": ".", "max_results": 100}, False, False
        if tool_name == "ci.run_pipeline":
            return {
                "target": "./...",
                "include_static_analysis": True,
                "include_coverage": True,
                "fail_fast": True,
            }, False, False
        if tool_name == "go.mod.tidy":
            return {"check": True}, False, False
        if tool_name == "go.generate":
            return {"target": "./..."}, False, False
        if tool_name == "go.build":
            return {"target": "."}, False, False
        if tool_name == "go.test":
            return {"package": "./...", "coverage": True}, False, False
        if tool_name in ("rust.build", "rust.test", "rust.clippy", "rust.format"):
            return {}, False, False
        if tool_name in ("node.install", "node.build", "node.test", "node.lint", "node.typecheck"):
            return {}, False, False
        if tool_name == "python.install_deps":
            return {"use_venv": True}, False, False
        if tool_name in ("python.validate", "python.test"):
            return {"target": "."}, False, False
        if tool_name == "c.build":
            return {"source": "csrc/main.c"}, False, False
        if tool_name == "c.test":
            return {"source": "csrc/main_test.c", "run": False}, False, False

        raise RuntimeError(f"unsupported tool in E2E 15 mapping: {tool_name}")

    def step_3_execute_complex_tool_flow(self, session: SessionContext) -> None:
        print_step(3, "Execute one run per available tool (coverage-oriented flow)")

        self._setup_workspace_files(session.session_id)

        seen: set[str] = set()
        soft_fail_count = 0

        for tool_name in self.execution_order:
            args, approved, strict_success = self._tool_input(tool_name)
            invocation = self._invoke(session.session_id, tool_name, args, approved=approved)
            seen.add(tool_name)

            status = invocation.get("status")
            error = invocation.get("error")
            output = invocation.get("output") or {}

            if strict_success and status != "succeeded":
                raise RuntimeError(
                    f"strict tool {tool_name} failed unexpectedly: status={status}, error={error}"
                )

            if not strict_success and status == "failed":
                soft_fail_count += 1
                if not isinstance(error, dict) or not error.get("code"):
                    raise RuntimeError(f"soft-fail tool {tool_name} returned malformed error: {invocation}")

            if tool_name in ("fs.read", "fs.read_file") and status == "succeeded":
                content = str(output.get("content", ""))
                if "coverage-marker" not in content:
                    raise RuntimeError(f"{tool_name} missing expected marker in output: {output}")

            if tool_name == "fs.search" and status == "succeeded":
                count = output.get("count", 0)
                if not isinstance(count, int) or count < 1:
                    raise RuntimeError(f"fs.search expected at least one match: {output}")

            if tool_name == "repo.detect_project_type" and status == "succeeded":
                project_type = str(output.get("project_type", "")).strip()
                if project_type and project_type not in ("go", "node", "python", "java", "rust", "c", "unknown"):
                    raise RuntimeError(f"unexpected project_type from detect: {project_type}")

            print_info(f"tool={tool_name} status={status}")

        missing = sorted(item for item in self.available_tools if item not in seen)
        if missing:
            raise RuntimeError(f"not all available tools were executed, missing: {missing}")

        self._record_step(
            "tool_execution_coverage",
            "passed",
            data={
                "executed_tools": sorted(seen),
                "executed_count": len(seen),
                "available_count": len(self.available_tools),
                "soft_fail_count": soft_fail_count,
            },
        )

        print_success(
            f"Executed {len(seen)}/{len(self.available_tools)} tools (soft_fail_count={soft_fail_count})"
        )

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
        print(f"{Colors.BLUE}Workspace vLLM Tool Orchestration E2E Test{Colors.NC}")
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print()

        print("Configuration:")
        print(f"  WORKSPACE_URL: {self.workspace_url}")
        print(f"  VLLM_CHAT_URL: {self.vllm_chat_url}")
        print(f"  VLLM_MODEL: {self.vllm_model}")
        print(f"  REQUIRE_VLLM: {self.require_vllm}")
        print(f"  STRICT_VLLM_PLAN: {self.strict_vllm_plan}")
        print(f"  EVIDENCE_FILE: {self.evidence_file}")
        print()

        final_status = "failed"
        error_message = ""

        try:
            session = self._execute_step(
                "step_1_health_session_and_catalog",
                self.step_1_health_session_and_catalog,
            )
            self._execute_step("step_2_vllm_planning", self.step_2_vllm_planning)
            self._execute_step(
                "step_3_execute_complex_tool_flow",
                lambda: self.step_3_execute_complex_tool_flow(session),
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
    test = WorkspaceVLLMToolOrchestrationE2E()
    return test.run()


if __name__ == "__main__":
    sys.exit(main())
