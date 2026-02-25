#!/usr/bin/env python3
"""E2E test 16: vLLM + Workspace catalog over a real Go TODO use case.

Scenario:
1) Start from a local repository path (fixture copied from this workstation into image).
2) vLLM discovers available tools from workspace catalog and returns a phase plan.
3) Phase 1: create Go TODO program + tests and verify with repo.run_tests.
4) Phase 2: modify model adding completion date field and verify again.

Evidence:
- Structured JSON evidence is written to EVIDENCE_FILE.
- Same JSON is emitted to logs between EVIDENCE_JSON_START / EVIDENCE_JSON_END.
"""

from __future__ import annotations

import json
import os
import subprocess
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


class WorkspaceVLLMGoTodoEvolutionE2E:
    def __init__(self) -> None:
        self.workspace_url = os.getenv("WORKSPACE_URL", "http://127.0.0.1:50053").rstrip("/")
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

        self.start_local_workspace = os.getenv("START_LOCAL_WORKSPACE", "true").lower() in (
            "1",
            "true",
            "yes",
        )
        self.workspace_binary = os.getenv("WORKSPACE_BINARY", "/usr/local/bin/workspace-service")
        self.source_repo_path = os.getenv(
            "SOURCE_REPO_PATH",
            "/app/e2e/tests/16-workspace-vllm-go-todo-evolution/fixtures/todo-go-repo",
        )
        self.workspace_port = self._parse_port(os.getenv("WORKSPACE_PORT", "50053"), default=50053)
        self.workspace_log_file = os.getenv("WORKSPACE_LOG_FILE", "/tmp/workspace-local-16.log")

        self.sessions: list[SessionContext] = []
        self.available_tools: list[str] = []
        self.invocation_counter = 0
        self.run_id = f"e2e-ws-vllm-go16-{int(time.time())}"

        self.workspace_process: subprocess.Popen[str] | None = None
        self.workspace_log_handle = None

        self.fs_read_tool = ""
        self.fs_write_tool = ""
        self.fs_list_tool = "fs.list"
        self.fs_search_tool = "fs.search"
        self.repo_test_tool = "repo.test"
        self.repo_build_tool = "repo.build"
        self.repo_detect_tool = "repo.detect_toolchain"
        self.repo_validate_tool = "repo.validate"
        self.go_mod_tidy_tool = "go.mod.tidy"
        self.go_generate_tool = "go.generate"
        self.go_build_tool = "go.build"
        self.go_test_tool = "go.test"

        self.phase1_ordered_tools: list[str] = []
        self.phase2_ordered_tools: list[str] = []

        self.evidence_file = os.getenv("EVIDENCE_FILE", "/tmp/evidence-16.json")
        self.evidence: dict[str, Any] = {
            "test_id": "16-workspace-vllm-go-todo-evolution",
            "run_id": self.run_id,
            "status": "running",
            "started_at": self._now_iso(),
            "configuration": {
                "workspace_url": self.workspace_url,
                "vllm_chat_url": self.vllm_chat_url,
                "vllm_model": self.vllm_model,
                "require_vllm": self.require_vllm,
                "strict_vllm_plan": self.strict_vllm_plan,
                "start_local_workspace": self.start_local_workspace,
                "workspace_binary": self.workspace_binary,
                "source_repo_path": self.source_repo_path,
                "workspace_log_file": self.workspace_log_file,
            },
            "steps": [],
            "sessions": [],
            "tool_catalog": [],
            "phase_plans": {},
            "invocations": [],
        }

    def _parse_port(self, raw: str, default: int) -> int:
        text = (raw or "").strip()
        if not text:
            return default
        if text.isdigit():
            return int(text)
        if ":" in text:
            tail = text.rsplit(":", 1)[-1]
            if tail.isdigit():
                return int(tail)
        return default

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _compact(self, value: Any, max_str: int = 1000) -> Any:
        if isinstance(value, str):
            if len(value) <= max_str:
                return value
            return value[:max_str] + "...<truncated>"
        if isinstance(value, dict):
            return {str(k): self._compact(v, max_str=max_str) for k, v in value.items()}
        if isinstance(value, list):
            limited = value[:80]
            out = [self._compact(item, max_str=max_str) for item in limited]
            if len(value) > 80:
                out.append(f"...<truncated {len(value) - 80} items>")
            return out
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
        phase: str,
        session_id: str,
        tool: str,
        approved: bool,
        args: dict[str, Any],
        http_status: int,
        invocation: dict[str, Any] | None,
    ) -> None:
        error = invocation.get("error") if isinstance(invocation, dict) else None
        output = invocation.get("output") if isinstance(invocation, dict) else None
        self.evidence["invocations"].append(
            {
                "at": self._now_iso(),
                "phase": phase,
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
        )

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

    def _tail_workspace_log(self, lines: int = 40) -> str:
        try:
            with open(self.workspace_log_file, "r", encoding="utf-8", errors="replace") as handle:
                all_lines = handle.readlines()
            return "".join(all_lines[-lines:])
        except Exception:
            return ""

    def _start_local_workspace_service(self) -> None:
        if not self.start_local_workspace:
            self._record_step("workspace_bootstrap", "skipped", message="START_LOCAL_WORKSPACE=false")
            return

        if not os.path.exists(self.workspace_binary):
            raise RuntimeError(f"workspace binary not found: {self.workspace_binary}")
        if not os.path.isdir(self.source_repo_path):
            raise RuntimeError(f"source repo path not found: {self.source_repo_path}")

        os.makedirs("/tmp/swe-workspaces", exist_ok=True)
        os.makedirs("/tmp/swe-artifacts", exist_ok=True)

        env = os.environ.copy()
        env["PORT"] = str(self.workspace_port)
        env["WORKSPACE_BACKEND"] = "local"
        env["WORKSPACE_ROOT"] = "/tmp/swe-workspaces"
        env["ARTIFACT_ROOT"] = "/tmp/swe-artifacts"
        env["INVOCATION_STORE_BACKEND"] = "memory"
        env["LOG_LEVEL"] = "info"

        self.workspace_log_handle = open(self.workspace_log_file, "w", encoding="utf-8")
        self.workspace_process = subprocess.Popen(
            [self.workspace_binary],
            stdout=self.workspace_log_handle,
            stderr=subprocess.STDOUT,
            env=env,
            text=True,
        )

        deadline = time.time() + 40
        health_url = f"http://127.0.0.1:{self.workspace_port}/healthz"
        while time.time() < deadline:
            if self.workspace_process.poll() is not None:
                log_tail = self._tail_workspace_log()
                raise RuntimeError(
                    "local workspace process exited unexpectedly\n"
                    f"last logs:\n{log_tail}"
                )
            try:
                req = urllib.request.Request(health_url, method="GET")
                with urllib.request.urlopen(req, timeout=2) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    if response.status == 200 and payload.get("status") == "ok":
                        self._record_step(
                            "workspace_bootstrap",
                            "passed",
                            data={
                                "workspace_url": self.workspace_url,
                                "workspace_log_file": self.workspace_log_file,
                            },
                        )
                        print_success("Local workspace service started")
                        return
            except Exception:
                pass
            time.sleep(0.5)

        log_tail = self._tail_workspace_log()
        raise RuntimeError(
            "timed out waiting for local workspace service health\n"
            f"last logs:\n{log_tail}"
        )

    def _stop_local_workspace_service(self) -> None:
        if self.workspace_process is None:
            return

        if self.workspace_process.poll() is None:
            self.workspace_process.terminate()
            try:
                self.workspace_process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self.workspace_process.kill()
                self.workspace_process.wait(timeout=5)

        if self.workspace_log_handle is not None:
            self.workspace_log_handle.close()
            self.workspace_log_handle = None

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

    def _create_session(self, actor_id: str) -> SessionContext:
        payload = {
            "principal": {
                "tenant_id": "e2e-tenant",
                "actor_id": actor_id,
                "roles": ["developer"],
            },
            "source_repo_path": self.source_repo_path,
            "allowed_paths": ["."],
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

    def _resolve_aliases(self, tools: set[str]) -> None:
        for candidate in ("fs.read_file", "fs.read"):
            if candidate in tools:
                self.fs_read_tool = candidate
                break
        for candidate in ("fs.write_file", "fs.write"):
            if candidate in tools:
                self.fs_write_tool = candidate
                break

        if not self.fs_read_tool or not self.fs_write_tool:
            raise RuntimeError("catalog missing fs read/write aliases")

        if "repo.test" in tools:
            self.repo_test_tool = "repo.test"
        elif "repo.run_tests" in tools:
            self.repo_test_tool = "repo.run_tests"
        else:
            raise RuntimeError("catalog missing repo.test/repo.run_tests")

        if "repo.detect_toolchain" in tools:
            self.repo_detect_tool = "repo.detect_toolchain"
        elif "repo.detect_project_type" in tools:
            self.repo_detect_tool = "repo.detect_project_type"

    def _invoke(
        self,
        *,
        phase: str,
        session_id: str,
        tool: str,
        args: dict[str, Any],
        approved: bool = False,
        timeout: int = 80,
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
            timeout=timeout,
        )
        invocation = body.get("invocation") if isinstance(body, dict) else None

        self._record_invocation(
            phase=phase,
            session_id=session_id,
            tool=tool,
            approved=approved,
            args=args,
            http_status=status,
            invocation=invocation if isinstance(invocation, dict) else None,
        )

        if not isinstance(invocation, dict):
            raise RuntimeError(f"invoke {tool} failed ({status}): {body}")
        if status not in (200, 500):
            raise RuntimeError(f"invoke {tool} unexpected status ({status}): {body}")
        return invocation

    def _read_text(self, phase: str, session_id: str, path: str) -> str:
        invocation = self._invoke(
            phase=phase,
            session_id=session_id,
            tool=self.fs_read_tool,
            args={"path": path},
            approved=False,
        )
        output = invocation.get("output") or {}
        return str(output.get("content", ""))

    def _build_phase_plan_messages(
        self,
        *,
        phase_name: str,
        goal_text: str,
        available_tools: list[str],
        feedback: str | None,
    ) -> list[dict[str, str]]:
        schema = (
            '{"phase":"' + phase_name + '","ordered_tools":["tool_a","tool_b"],'
            '"notes":"..."}'
        )
        prompt = (
            f"Eres un desarrollador de software Go que usa un catalogo de tools HTTP. "
            f"Tools disponibles: {json.dumps(available_tools)}. "
            f"Objetivo: {goal_text}. "
            f"Devuelve SOLO JSON valido con este schema exacto: {schema}. "
            "ordered_tools debe usar solo tools del catalogo. "
            "Incluye herramientas para implementar y verificar (tests)."
        )
        if feedback:
            prompt += f" Correccion obligatoria: {feedback}"

        return [
            {
                "role": "system",
                "content": "Respondes JSON estricto. No markdown. No texto extra.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]

    def _request_phase_plan_from_vllm(
        self,
        *,
        phase_name: str,
        goal_text: str,
        available_tools: list[str],
    ) -> dict[str, Any]:
        def infer_order(text: str) -> list[str]:
            lowered = text.lower()
            positions: list[tuple[int, str]] = []
            for tool in available_tools:
                idx = lowered.find(tool.lower())
                if idx >= 0:
                    positions.append((idx, tool))
            positions.sort(key=lambda item: item[0])

            out: list[str] = []
            seen: set[str] = set()
            for _, tool in positions:
                if tool not in seen:
                    out.append(tool)
                    seen.add(tool)
            return out

        feedback: str | None = None
        last_raw = ""
        last_parsed: dict[str, Any] | None = None

        for _ in range(2):
            payload = {
                "model": self.vllm_model,
                "temperature": 0,
                "max_tokens": 700,
                "messages": self._build_phase_plan_messages(
                    phase_name=phase_name,
                    goal_text=goal_text,
                    available_tools=available_tools,
                    feedback=feedback,
                ),
            }

            req = urllib.request.Request(
                url=self.vllm_chat_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                body = json.loads(response.read().decode("utf-8"))

            message = body["choices"][0]["message"]
            content = message.get("content") or ""
            reasoning = message.get("reasoning_content") or ""
            raw = content if content.strip() else reasoning
            if not raw.strip():
                raw = content + "\n" + reasoning
            last_raw = raw

            try:
                parsed = self._extract_json_object(raw)
                last_parsed = parsed
            except Exception:
                inferred = infer_order(raw)
                if inferred:
                    plan = {
                        "phase": phase_name,
                        "ordered_tools": inferred,
                        "notes": "derived from text fallback",
                    }
                    self.evidence["phase_plans"][phase_name] = {
                        "source": "text-fallback",
                        "raw": self._compact(raw),
                        "parsed": self._compact(plan),
                    }
                    return plan
                feedback = "No pude parsear JSON. Responde SOLO JSON valido con ordered_tools."
                continue

            ordered = parsed.get("ordered_tools")
            if not isinstance(ordered, list) or not all(isinstance(item, str) for item in ordered):
                feedback = "ordered_tools debe ser array de strings"
                continue

            cleaned = [item.strip() for item in ordered if item and item.strip()]
            if len(cleaned) != len(set(cleaned)):
                feedback = "ordered_tools no debe tener duplicados"
                continue

            unknown = [item for item in cleaned if item not in available_tools]
            if unknown:
                feedback = f"ordered_tools contiene tools invalidos: {unknown}"
                continue

            plan = {
                "phase": str(parsed.get("phase") or phase_name),
                "ordered_tools": cleaned,
                "notes": str(parsed.get("notes") or ""),
            }
            self.evidence["phase_plans"][phase_name] = {
                "source": "json",
                "raw": self._compact(raw),
                "parsed": self._compact(plan),
            }
            return plan

        inferred = infer_order(last_raw)
        if inferred:
            plan = {
                "phase": phase_name,
                "ordered_tools": inferred,
                "notes": "derived from final fallback",
            }
            self.evidence["phase_plans"][phase_name] = {
                "source": "final-text-fallback",
                "raw": self._compact(last_raw),
                "parsed": self._compact(plan),
                "last_parsed": self._compact(last_parsed),
            }
            return plan

        raise RuntimeError(f"vLLM did not return a valid phase plan for {phase_name}")

    def _normalize_phase_order(self, order: list[str], required: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for tool in order:
            if tool not in seen:
                cleaned.append(tool)
                seen.add(tool)

        missing = [tool for tool in required if tool not in cleaned]
        if missing:
            if self.strict_vllm_plan:
                raise RuntimeError(f"phase plan missing required tools: {missing}")
            cleaned.extend(missing)
        return cleaned

    def _execute_contextual_reads(
        self,
        *,
        phase: str,
        session_id: str,
        ordered_tools: list[str],
    ) -> None:
        did_list = False
        did_read = False
        did_search = False

        for tool in ordered_tools:
            if tool == self.fs_list_tool and not did_list:
                self._invoke(
                    phase=phase,
                    session_id=session_id,
                    tool=tool,
                    args={"path": ".", "recursive": False, "max_entries": 200},
                    approved=False,
                )
                did_list = True
            elif tool == self.fs_read_tool and not did_read:
                self._invoke(
                    phase=phase,
                    session_id=session_id,
                    tool=tool,
                    args={"path": "README.md"},
                    approved=False,
                )
                did_read = True
            elif tool == self.fs_search_tool and not did_search:
                self._invoke(
                    phase=phase,
                    session_id=session_id,
                    tool=tool,
                    args={"path": ".", "pattern": "TODO|todo", "max_results": 20},
                    approved=False,
                )
                did_search = True

    def _phase1_main_go(self) -> str:
        return (
            "package main\n\n"
            "import \"fmt\"\n\n"
            "type Todo struct {\n"
            "\tID    int\n"
            "\tTitle string\n"
            "\tDone  bool\n"
            "}\n\n"
            "func AddTodo(list []Todo, title string) []Todo {\n"
            "\titem := Todo{ID: len(list) + 1, Title: title, Done: false}\n"
            "\treturn append(list, item)\n"
            "}\n\n"
            "func CompleteTodo(list []Todo, id int) bool {\n"
            "\tfor i := range list {\n"
            "\t\tif list[i].ID == id {\n"
            "\t\t\tlist[i].Done = true\n"
            "\t\t\treturn true\n"
            "\t\t}\n"
            "\t}\n"
            "\treturn false\n"
            "}\n\n"
            "func PendingCount(list []Todo) int {\n"
            "\tcount := 0\n"
            "\tfor _, item := range list {\n"
            "\t\tif !item.Done {\n"
            "\t\t\tcount++\n"
            "\t\t}\n"
            "\t}\n"
            "\treturn count\n"
            "}\n\n"
            "func main() {\n"
            "\tlist := []Todo{}\n"
            "\tlist = AddTodo(list, \"write tests\")\n"
            "\tfmt.Printf(\"todos=%d pending=%d\\n\", len(list), PendingCount(list))\n"
            "}\n"
        )

    def _phase1_test_go(self) -> str:
        return (
            "package main\n\n"
            "import \"testing\"\n\n"
            "func TestAddTodoAssignsIDAndPending(t *testing.T) {\n"
            "\tlist := []Todo{}\n"
            "\tlist = AddTodo(list, \"first\")\n"
            "\tlist = AddTodo(list, \"second\")\n\n"
            "\tif len(list) != 2 {\n"
            "\t\tt.Fatalf(\"expected 2 todos, got %d\", len(list))\n"
            "\t}\n"
            "\tif list[0].ID != 1 || list[1].ID != 2 {\n"
            "\t\tt.Fatalf(\"unexpected ids: %#v\", list)\n"
            "\t}\n"
            "\tif PendingCount(list) != 2 {\n"
            "\t\tt.Fatalf(\"expected 2 pending, got %d\", PendingCount(list))\n"
            "\t}\n"
            "}\n\n"
            "func TestCompleteTodoMarksDone(t *testing.T) {\n"
            "\tlist := []Todo{}\n"
            "\tlist = AddTodo(list, \"task\")\n\n"
            "\tif ok := CompleteTodo(list, 1); !ok {\n"
            "\t\tt.Fatalf(\"expected complete to return true\")\n"
            "\t}\n"
            "\tif !list[0].Done {\n"
            "\t\tt.Fatalf(\"expected todo to be done\")\n"
            "\t}\n"
            "\tif PendingCount(list) != 0 {\n"
            "\t\tt.Fatalf(\"expected 0 pending, got %d\", PendingCount(list))\n"
            "\t}\n"
            "}\n"
        )

    def _phase2_main_go(self) -> str:
        return (
            "package main\n\n"
            "import (\n"
            "\t\"fmt\"\n"
            "\t\"time\"\n"
            ")\n\n"
            "type Todo struct {\n"
            "\tID          int\n"
            "\tTitle       string\n"
            "\tDone        bool\n"
            "\tCompletedAt *time.Time\n"
            "}\n\n"
            "func AddTodo(list []Todo, title string) []Todo {\n"
            "\titem := Todo{ID: len(list) + 1, Title: title, Done: false, CompletedAt: nil}\n"
            "\treturn append(list, item)\n"
            "}\n\n"
            "func CompleteTodo(list []Todo, id int) bool {\n"
            "\tfor i := range list {\n"
            "\t\tif list[i].ID == id {\n"
            "\t\t\tif !list[i].Done {\n"
            "\t\t\t\tnow := time.Now().UTC()\n"
            "\t\t\t\tlist[i].CompletedAt = &now\n"
            "\t\t\t}\n"
            "\t\t\tlist[i].Done = true\n"
            "\t\t\treturn true\n"
            "\t\t}\n"
            "\t}\n"
            "\treturn false\n"
            "}\n\n"
            "func PendingCount(list []Todo) int {\n"
            "\tcount := 0\n"
            "\tfor _, item := range list {\n"
            "\t\tif !item.Done {\n"
            "\t\t\tcount++\n"
            "\t\t}\n"
            "\t}\n"
            "\treturn count\n"
            "}\n\n"
            "func main() {\n"
            "\tlist := []Todo{}\n"
            "\tlist = AddTodo(list, \"write tests\")\n"
            "\tfmt.Printf(\"todos=%d pending=%d\\n\", len(list), PendingCount(list))\n"
            "}\n"
        )

    def _phase2_test_go(self) -> str:
        return (
            "package main\n\n"
            "import (\n"
            "\t\"testing\"\n"
            "\t\"time\"\n"
            ")\n\n"
            "func TestAddTodoAssignsIDAndPending(t *testing.T) {\n"
            "\tlist := []Todo{}\n"
            "\tlist = AddTodo(list, \"first\")\n"
            "\tlist = AddTodo(list, \"second\")\n\n"
            "\tif len(list) != 2 {\n"
            "\t\tt.Fatalf(\"expected 2 todos, got %d\", len(list))\n"
            "\t}\n"
            "\tif list[0].ID != 1 || list[1].ID != 2 {\n"
            "\t\tt.Fatalf(\"unexpected ids: %#v\", list)\n"
            "\t}\n"
            "\tif PendingCount(list) != 2 {\n"
            "\t\tt.Fatalf(\"expected 2 pending, got %d\", PendingCount(list))\n"
            "\t}\n"
            "\tif list[0].CompletedAt != nil || list[1].CompletedAt != nil {\n"
            "\t\tt.Fatalf(\"expected nil completed_at in new tasks\")\n"
            "\t}\n"
            "}\n\n"
            "func TestCompleteTodoSetsCompletionDate(t *testing.T) {\n"
            "\tlist := []Todo{}\n"
            "\tlist = AddTodo(list, \"task\")\n\n"
            "\tif ok := CompleteTodo(list, 1); !ok {\n"
            "\t\tt.Fatalf(\"expected complete to return true\")\n"
            "\t}\n"
            "\tif !list[0].Done {\n"
            "\t\tt.Fatalf(\"expected todo to be done\")\n"
            "\t}\n"
            "\tif list[0].CompletedAt == nil {\n"
            "\t\tt.Fatalf(\"expected completed_at to be set\")\n"
            "\t}\n"
            "\tif time.Since(*list[0].CompletedAt) > 5*time.Second {\n"
            "\t\tt.Fatalf(\"expected completed_at to be recent, got %v\", *list[0].CompletedAt)\n"
            "\t}\n"
            "\tif PendingCount(list) != 0 {\n"
            "\t\tt.Fatalf(\"expected 0 pending, got %d\", PendingCount(list))\n"
            "\t}\n"
            "}\n"
        )

    def _invoke_repo_tests_strict(self, phase: str, session_id: str) -> None:
        invocation = self._invoke(
            phase=phase,
            session_id=session_id,
            tool=self.repo_test_tool,
            args={"target": "./..."},
            approved=False,
            timeout=120,
        )
        if invocation.get("status") != "succeeded":
            raise RuntimeError(f"{self.repo_test_tool} failed: {invocation}")

    def step_1_bootstrap_session_and_catalog(self) -> SessionContext:
        print_step(1, "Bootstrap session from local repository and discover tool catalog")

        status, body = self._request("GET", "/healthz")
        if status != 200 or body.get("status") != "ok":
            raise RuntimeError(f"workspace health check failed: {status} {body}")

        session = self._create_session("agent-go-todo")
        tools = set(self._list_tools(session.session_id))
        if not tools:
            raise RuntimeError("empty tool catalog")

        self.available_tools = sorted(tools)
        self.evidence["tool_catalog"] = self.available_tools

        self._resolve_aliases(tools)

        self._record_step(
            "catalog_discovered",
            "passed",
            data={
                "tools": self.available_tools,
                "fs_read_tool": self.fs_read_tool,
                "fs_write_tool": self.fs_write_tool,
            },
        )
        print_success(f"Discovered tools: {self.available_tools}")
        return session

    def step_2_phase1_vllm_plan(self) -> None:
        print_step(2, "vLLM phase 1 plan: build TODO app + tests")

        goal = (
            "Crear programa en Go para gestionar lista de TODOs, "
            "agregar tests y verificar ejecucion con tests."
        )
        try:
            plan = self._request_phase_plan_from_vllm(
                phase_name="phase_1_initial",
                goal_text=goal,
                available_tools=self.available_tools,
            )
            order = list(plan.get("ordered_tools") or [])
            self.phase1_ordered_tools = self._normalize_phase_order(
                order,
                required=[self.fs_write_tool, self.repo_test_tool],
            )
            print_success("vLLM returned phase 1 plan")
        except Exception as exc:
            if self.require_vllm:
                raise
            print_warning(f"vLLM unavailable in phase 1, using deterministic fallback: {exc}")
            self.phase1_ordered_tools = self._normalize_phase_order(
                self.available_tools,
                required=[self.fs_write_tool, self.repo_test_tool],
            )

        self._record_step(
            "phase_1_plan",
            "passed",
            data={"ordered_tools": self.phase1_ordered_tools},
        )
        print_info(f"Phase 1 ordered tools: {self.phase1_ordered_tools}")

    def step_3_phase1_implement_and_verify(self, session: SessionContext) -> None:
        print_step(3, "Phase 1 execution: implement TODO app and verify tests")

        self._execute_contextual_reads(
            phase="phase_1",
            session_id=session.session_id,
            ordered_tools=self.phase1_ordered_tools,
        )

        self._invoke(
            phase="phase_1",
            session_id=session.session_id,
            tool=self.fs_write_tool,
            args={
                "path": "main.go",
                "content": self._phase1_main_go(),
                "create_parents": True,
            },
            approved=True,
        )
        self._invoke(
            phase="phase_1",
            session_id=session.session_id,
            tool=self.fs_write_tool,
            args={
                "path": "main_test.go",
                "content": self._phase1_test_go(),
                "create_parents": True,
            },
            approved=True,
        )

        if self.repo_detect_tool in self.available_tools:
            self._invoke(
                phase="phase_1",
                session_id=session.session_id,
                tool=self.repo_detect_tool,
                args={},
                approved=False,
            )
        if self.repo_validate_tool in self.available_tools:
            self._invoke(
                phase="phase_1",
                session_id=session.session_id,
                tool=self.repo_validate_tool,
                args={"target": "./..."},
                approved=False,
                timeout=120,
            )
        if self.go_mod_tidy_tool in self.available_tools:
            self._invoke(
                phase="phase_1",
                session_id=session.session_id,
                tool=self.go_mod_tidy_tool,
                args={},
                approved=False,
                timeout=120,
            )
        if self.go_generate_tool in self.available_tools:
            self._invoke(
                phase="phase_1",
                session_id=session.session_id,
                tool=self.go_generate_tool,
                args={"target": "./..."},
                approved=False,
                timeout=120,
            )
        if self.go_build_tool in self.available_tools:
            self._invoke(
                phase="phase_1",
                session_id=session.session_id,
                tool=self.go_build_tool,
                args={"target": ".", "output_name": "todoapp-phase1", "ldflags": "-s -w", "race": False},
                approved=False,
                timeout=120,
            )
        if self.go_test_tool in self.available_tools:
            self._invoke(
                phase="phase_1",
                session_id=session.session_id,
                tool=self.go_test_tool,
                args={"package": "./...", "coverage": True},
                approved=False,
                timeout=120,
            )
        if self.repo_build_tool in self.available_tools:
            self._invoke(
                phase="phase_1",
                session_id=session.session_id,
                tool=self.repo_build_tool,
                args={"target": "./..."},
                approved=False,
                timeout=120,
            )

        self._invoke_repo_tests_strict("phase_1", session.session_id)

        content = self._read_text("phase_1", session.session_id, "main.go")
        if "CompletedAt" in content:
            raise RuntimeError("phase 1 main.go should not yet include CompletedAt")

        self._record_step(
            "phase_1_execution",
            "passed",
            data={
                "files_written": ["main.go", "main_test.go"],
                "verification": "repo.run_tests succeeded",
            },
        )
        print_success("Phase 1 tests succeeded")

    def step_4_phase2_vllm_plan(self) -> None:
        print_step(4, "vLLM phase 2 plan: add completion date field")

        goal = (
            "Modificar el programa para anadir campo de fecha cuando una tarea se completa, "
            "actualizar tests y volver a verificar."
        )
        try:
            plan = self._request_phase_plan_from_vllm(
                phase_name="phase_2_modification",
                goal_text=goal,
                available_tools=self.available_tools,
            )
            order = list(plan.get("ordered_tools") or [])
            self.phase2_ordered_tools = self._normalize_phase_order(
                order,
                required=[self.fs_write_tool, self.repo_test_tool, self.fs_read_tool],
            )
            print_success("vLLM returned phase 2 plan")
        except Exception as exc:
            if self.require_vllm:
                raise
            print_warning(f"vLLM unavailable in phase 2, using deterministic fallback: {exc}")
            self.phase2_ordered_tools = self._normalize_phase_order(
                self.available_tools,
                required=[self.fs_write_tool, self.repo_test_tool, self.fs_read_tool],
            )

        self._record_step(
            "phase_2_plan",
            "passed",
            data={"ordered_tools": self.phase2_ordered_tools},
        )
        print_info(f"Phase 2 ordered tools: {self.phase2_ordered_tools}")

    def step_5_phase2_modify_and_verify(self, session: SessionContext) -> None:
        print_step(5, "Phase 2 execution: apply modification and verify tests")

        self._execute_contextual_reads(
            phase="phase_2",
            session_id=session.session_id,
            ordered_tools=self.phase2_ordered_tools,
        )

        self._invoke(
            phase="phase_2",
            session_id=session.session_id,
            tool=self.fs_write_tool,
            args={
                "path": "main.go",
                "content": self._phase2_main_go(),
                "create_parents": True,
            },
            approved=True,
        )
        self._invoke(
            phase="phase_2",
            session_id=session.session_id,
            tool=self.fs_write_tool,
            args={
                "path": "main_test.go",
                "content": self._phase2_test_go(),
                "create_parents": True,
            },
            approved=True,
        )

        if self.repo_validate_tool in self.available_tools:
            self._invoke(
                phase="phase_2",
                session_id=session.session_id,
                tool=self.repo_validate_tool,
                args={"target": "./..."},
                approved=False,
                timeout=120,
            )
        if self.go_test_tool in self.available_tools:
            self._invoke(
                phase="phase_2",
                session_id=session.session_id,
                tool=self.go_test_tool,
                args={"package": "./...", "coverage": True},
                approved=False,
                timeout=120,
            )

        self._invoke_repo_tests_strict("phase_2", session.session_id)

        main_go = self._read_text("phase_2", session.session_id, "main.go")
        if "CompletedAt" not in main_go:
            raise RuntimeError("phase 2 main.go is missing CompletedAt field")
        if "time.Time" not in main_go:
            raise RuntimeError("phase 2 main.go is missing time.Time reference")

        if self.fs_search_tool in self.available_tools:
            self._invoke(
                phase="phase_2",
                session_id=session.session_id,
                tool=self.fs_search_tool,
                args={"path": ".", "pattern": "CompletedAt", "max_results": 20},
                approved=False,
            )

        self._record_step(
            "phase_2_execution",
            "passed",
            data={
                "files_modified": ["main.go", "main_test.go"],
                "verification": "repo.run_tests succeeded and CompletedAt found",
            },
        )
        print_success("Phase 2 tests succeeded and CompletedAt change verified")

    def cleanup(self) -> None:
        cleaned = 0
        failed = 0
        for session in self.sessions:
            try:
                self._delete_session(session.session_id)
                cleaned += 1
            except Exception:
                failed += 1

        self._stop_local_workspace_service()

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
        print(f"{Colors.BLUE}Workspace vLLM Go TODO Evolution E2E Test (16){Colors.NC}")
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print()

        print("Configuration:")
        print(f"  WORKSPACE_URL: {self.workspace_url}")
        print(f"  START_LOCAL_WORKSPACE: {self.start_local_workspace}")
        print(f"  WORKSPACE_BINARY: {self.workspace_binary}")
        print(f"  SOURCE_REPO_PATH: {self.source_repo_path}")
        print(f"  VLLM_CHAT_URL: {self.vllm_chat_url}")
        print(f"  VLLM_MODEL: {self.vllm_model}")
        print(f"  REQUIRE_VLLM: {self.require_vllm}")
        print(f"  STRICT_VLLM_PLAN: {self.strict_vllm_plan}")
        print(f"  EVIDENCE_FILE: {self.evidence_file}")
        print()

        final_status = "failed"
        error_message = ""

        try:
            self._execute_step("workspace_bootstrap", self._start_local_workspace_service)
            session = self._execute_step(
                "step_1_bootstrap_session_and_catalog",
                self.step_1_bootstrap_session_and_catalog,
            )
            self._execute_step("step_2_phase1_vllm_plan", self.step_2_phase1_vllm_plan)
            self._execute_step(
                "step_3_phase1_implement_and_verify",
                lambda: self.step_3_phase1_implement_and_verify(session),
            )
            self._execute_step("step_4_phase2_vllm_plan", self.step_4_phase2_vllm_plan)
            self._execute_step(
                "step_5_phase2_modify_and_verify",
                lambda: self.step_5_phase2_modify_and_verify(session),
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
    test = WorkspaceVLLMGoTodoEvolutionE2E()
    return test.run()


if __name__ == "__main__":
    sys.exit(main())
