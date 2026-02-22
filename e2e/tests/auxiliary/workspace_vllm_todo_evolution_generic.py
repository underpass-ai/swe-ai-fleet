#!/usr/bin/env python3
"""Generic E2E integration test: vLLM + workspace todo evolution by language.

Supported languages:
- rust
- node
- c

Flow:
1) Bootstrap local workspace service in-job.
2) Discover tool catalog for session.
3) Ask vLLM for phase plan per phase.
4) Phase 1: create TODO app + tests and validate.
5) Phase 2: add completion date field and validate.
6) Emit structured evidence JSON (file + logs).
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


class WorkspaceVLLMTodoEvolutionGenericE2E:
    def __init__(self) -> None:
        self.language = os.getenv("TODO_LANGUAGE", "rust").strip().lower()
        if self.language not in ("rust", "node", "c"):
            raise ValueError(f"unsupported TODO_LANGUAGE: {self.language}")

        self.test_id = os.getenv("TEST_ID", f"workspace-vllm-{self.language}-todo-evolution")
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
        self.source_repo_path = os.getenv("SOURCE_REPO_PATH", "").strip()
        if not self.source_repo_path:
            raise ValueError("SOURCE_REPO_PATH is required")
        self.workspace_port = self._parse_port(os.getenv("WORKSPACE_PORT", "50053"), default=50053)
        self.workspace_log_file = os.getenv("WORKSPACE_LOG_FILE", f"/tmp/workspace-local-{self.language}.log")

        self.sessions: list[SessionContext] = []
        self.available_tools: list[str] = []
        self.invocation_counter = 0
        self.run_id = f"e2e-ws-vllm-{self.language}-todo-{int(time.time())}"

        self.workspace_process: subprocess.Popen[str] | None = None
        self.workspace_log_handle = None

        self.fs_read_tool = ""
        self.fs_write_tool = ""
        self.fs_list_tool = "fs.list"
        self.fs_search_tool = "fs.search"
        self.repo_test_tool = "repo.test"
        self.repo_build_tool = "repo.build"
        self.repo_detect_tool = "repo.detect_toolchain"

        self.phase1_ordered_tools: list[str] = []
        self.phase2_ordered_tools: list[str] = []

        self.evidence_file = os.getenv("EVIDENCE_FILE", f"/tmp/evidence-{self.language}.json")
        self.evidence: dict[str, Any] = {
            "test_id": self.test_id,
            "language": self.language,
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

    def _language_goal(self, phase: int) -> str:
        if phase == 1:
            return (
                f"Crear programa TODO en {self.language} con tests y verificar que funcionen."
            )
        return (
            "Modificar el programa para añadir fecha de completado en cada tarea y "
            "actualizar tests para verificarlo."
        )

    def _language_required_tools(self) -> list[str]:
        if self.language == "rust":
            return [self.fs_write_tool, "rust.build", "rust.test", self.repo_test_tool]
        if self.language == "node":
            return [self.fs_write_tool, "node.build", "node.test", self.repo_test_tool]
        return [self.fs_write_tool, "c.build", "c.test", self.repo_test_tool]

    def _language_primary_file(self) -> str:
        if self.language == "rust":
            return "src/lib.rs"
        if self.language == "node":
            return "todo.js"
        return "main.c"

    def _language_phase1_marker(self) -> str:
        if self.language == "node":
            return "completedAt"
        return "completed_at"

    def _language_phase1_files(self) -> dict[str, str]:
        if self.language == "rust":
            return {
                "src/lib.rs": (
                    "#[derive(Debug, Clone, PartialEq, Eq)]\n"
                    "pub struct Todo {\n"
                    "    pub id: usize,\n"
                    "    pub title: String,\n"
                    "    pub done: bool,\n"
                    "}\n\n"
                    "pub fn add_todo(list: &mut Vec<Todo>, title: &str) -> usize {\n"
                    "    let next_id = list.len() + 1;\n"
                    "    list.push(Todo {\n"
                    "        id: next_id,\n"
                    "        title: title.to_string(),\n"
                    "        done: false,\n"
                    "    });\n"
                    "    next_id\n"
                    "}\n\n"
                    "pub fn complete_todo(list: &mut [Todo], id: usize) -> bool {\n"
                    "    for item in list {\n"
                    "        if item.id == id {\n"
                    "            item.done = true;\n"
                    "            return true;\n"
                    "        }\n"
                    "    }\n"
                    "    false\n"
                    "}\n\n"
                    "pub fn pending_count(list: &[Todo]) -> usize {\n"
                    "    list.iter().filter(|item| !item.done).count()\n"
                    "}\n\n"
                    "#[cfg(test)]\n"
                    "mod tests {\n"
                    "    use super::{add_todo, complete_todo, pending_count, Todo};\n\n"
                    "    #[test]\n"
                    "    fn add_assigns_ids() {\n"
                    "        let mut list: Vec<Todo> = Vec::new();\n"
                    "        assert_eq!(add_todo(&mut list, \"one\"), 1);\n"
                    "        assert_eq!(add_todo(&mut list, \"two\"), 2);\n"
                    "        assert_eq!(pending_count(&list), 2);\n"
                    "    }\n\n"
                    "    #[test]\n"
                    "    fn complete_marks_done() {\n"
                    "        let mut list = vec![Todo { id: 1, title: String::from(\"task\"), done: false }];\n"
                    "        assert!(complete_todo(&mut list, 1));\n"
                    "        assert!(list[0].done);\n"
                    "        assert_eq!(pending_count(&list), 0);\n"
                    "    }\n"
                    "}\n"
                )
            }

        if self.language == "node":
            return {
                "todo.js": (
                    "export function addTodo(list, title) {\n"
                    "  const item = { id: list.length + 1, title, done: false };\n"
                    "  return [...list, item];\n"
                    "}\n\n"
                    "export function completeTodo(list, id) {\n"
                    "  for (const item of list) {\n"
                    "    if (item.id === id) {\n"
                    "      item.done = true;\n"
                    "      return true;\n"
                    "    }\n"
                    "  }\n"
                    "  return false;\n"
                    "}\n\n"
                    "export function pendingCount(list) {\n"
                    "  return list.filter((item) => !item.done).length;\n"
                    "}\n"
                ),
                "todo.test.mjs": (
                    "import test from 'node:test';\n"
                    "import assert from 'node:assert/strict';\n"
                    "import { addTodo, completeTodo, pendingCount } from './todo.js';\n\n"
                    "test('addTodo assigns id and pending count', () => {\n"
                    "  let list = [];\n"
                    "  list = addTodo(list, 'one');\n"
                    "  list = addTodo(list, 'two');\n"
                    "  assert.equal(list[0].id, 1);\n"
                    "  assert.equal(list[1].id, 2);\n"
                    "  assert.equal(pendingCount(list), 2);\n"
                    "});\n\n"
                    "test('completeTodo marks task done', () => {\n"
                    "  let list = [];\n"
                    "  list = addTodo(list, 'task');\n"
                    "  assert.equal(completeTodo(list, 1), true);\n"
                    "  assert.equal(list[0].done, true);\n"
                    "  assert.equal(pendingCount(list), 0);\n"
                    "});\n"
                ),
                "scripts/build.mjs": (
                    "import { mkdirSync, copyFileSync } from 'node:fs';\n"
                    "mkdirSync('dist', { recursive: true });\n"
                    "copyFileSync('todo.js', 'dist/todo.js');\n"
                    "console.log('build ok');\n"
                ),
            }

        return {
            "main.c": (
                "#include <stdio.h>\n\n"
                "typedef struct Todo {\n"
                "    int id;\n"
                "    const char *title;\n"
                "    int done;\n"
                "} Todo;\n\n"
                "int main(void) {\n"
                "    Todo item = {1, \"task\", 0};\n"
                "    printf(\"%d:%s:%d\\n\", item.id, item.title, item.done);\n"
                "    return 0;\n"
                "}\n"
            ),
            "todo_test.c": (
                "#include <assert.h>\n\n"
                "typedef struct Todo {\n"
                "    int id;\n"
                "    const char *title;\n"
                "    int done;\n"
                "} Todo;\n\n"
                "static int complete_todo(Todo *item) {\n"
                "    item->done = 1;\n"
                "    return 1;\n"
                "}\n\n"
                "int main(void) {\n"
                "    Todo item = {1, \"task\", 0};\n"
                "    assert(complete_todo(&item) == 1);\n"
                "    assert(item.done == 1);\n"
                "    return 0;\n"
                "}\n"
            ),
        }

    def _language_phase2_files(self) -> dict[str, str]:
        if self.language == "rust":
            return {
                "src/lib.rs": (
                    "#[derive(Debug, Clone, PartialEq, Eq)]\n"
                    "pub struct Todo {\n"
                    "    pub id: usize,\n"
                    "    pub title: String,\n"
                    "    pub done: bool,\n"
                    "    pub completed_at: Option<String>,\n"
                    "}\n\n"
                    "pub fn add_todo(list: &mut Vec<Todo>, title: &str) -> usize {\n"
                    "    let next_id = list.len() + 1;\n"
                    "    list.push(Todo {\n"
                    "        id: next_id,\n"
                    "        title: title.to_string(),\n"
                    "        done: false,\n"
                    "        completed_at: None,\n"
                    "    });\n"
                    "    next_id\n"
                    "}\n\n"
                    "pub fn complete_todo(list: &mut [Todo], id: usize, completed_at: &str) -> bool {\n"
                    "    for item in list {\n"
                    "        if item.id == id {\n"
                    "            item.done = true;\n"
                    "            if item.completed_at.is_none() {\n"
                    "                item.completed_at = Some(completed_at.to_string());\n"
                    "            }\n"
                    "            return true;\n"
                    "        }\n"
                    "    }\n"
                    "    false\n"
                    "}\n\n"
                    "pub fn pending_count(list: &[Todo]) -> usize {\n"
                    "    list.iter().filter(|item| !item.done).count()\n"
                    "}\n\n"
                    "#[cfg(test)]\n"
                    "mod tests {\n"
                    "    use super::{add_todo, complete_todo, pending_count, Todo};\n\n"
                    "    #[test]\n"
                    "    fn add_assigns_ids() {\n"
                    "        let mut list: Vec<Todo> = Vec::new();\n"
                    "        assert_eq!(add_todo(&mut list, \"one\"), 1);\n"
                    "        assert_eq!(add_todo(&mut list, \"two\"), 2);\n"
                    "        assert_eq!(pending_count(&list), 2);\n"
                    "        assert_eq!(list[0].completed_at, None);\n"
                    "    }\n\n"
                    "    #[test]\n"
                    "    fn complete_sets_date() {\n"
                    "        let mut list = vec![Todo { id: 1, title: String::from(\"task\"), done: false, completed_at: None }];\n"
                    "        assert!(complete_todo(&mut list, 1, \"2026-02-14T00:00:00Z\"));\n"
                    "        assert!(list[0].done);\n"
                    "        assert_eq!(list[0].completed_at.as_deref(), Some(\"2026-02-14T00:00:00Z\"));\n"
                    "        assert_eq!(pending_count(&list), 0);\n"
                    "    }\n"
                    "}\n"
                )
            }

        if self.language == "node":
            return {
                "todo.js": (
                    "export function addTodo(list, title) {\n"
                    "  const item = { id: list.length + 1, title, done: false, completedAt: undefined };\n"
                    "  return [...list, item];\n"
                    "}\n\n"
                    "export function completeTodo(list, id, completedAt) {\n"
                    "  for (const item of list) {\n"
                    "    if (item.id === id) {\n"
                    "      item.done = true;\n"
                    "      item.completedAt = completedAt;\n"
                    "      return true;\n"
                    "    }\n"
                    "  }\n"
                    "  return false;\n"
                    "}\n\n"
                    "export function pendingCount(list) {\n"
                    "  return list.filter((item) => !item.done).length;\n"
                    "}\n"
                ),
                "todo.test.mjs": (
                    "import test from 'node:test';\n"
                    "import assert from 'node:assert/strict';\n"
                    "import { addTodo, completeTodo, pendingCount } from './todo.js';\n\n"
                    "test('addTodo assigns id and pending count', () => {\n"
                    "  let list = [];\n"
                    "  list = addTodo(list, 'one');\n"
                    "  list = addTodo(list, 'two');\n"
                    "  assert.equal(list[0].id, 1);\n"
                    "  assert.equal(list[1].id, 2);\n"
                    "  assert.equal(pendingCount(list), 2);\n"
                    "  assert.equal(list[0].completedAt, undefined);\n"
                    "});\n\n"
                    "test('completeTodo marks task done and sets date', () => {\n"
                    "  let list = [];\n"
                    "  list = addTodo(list, 'task');\n"
                    "  assert.equal(completeTodo(list, 1, '2026-02-14T00:00:00Z'), true);\n"
                    "  assert.equal(list[0].done, true);\n"
                    "  assert.equal(list[0].completedAt, '2026-02-14T00:00:00Z');\n"
                    "  assert.equal(pendingCount(list), 0);\n"
                    "});\n"
                ),
                "scripts/build.mjs": (
                    "import { mkdirSync, copyFileSync } from 'node:fs';\n"
                    "mkdirSync('dist', { recursive: true });\n"
                    "copyFileSync('todo.js', 'dist/todo.js');\n"
                    "console.log('build ok');\n"
                ),
            }

        return {
            "main.c": (
                "#include <stdio.h>\n\n"
                "typedef struct Todo {\n"
                "    int id;\n"
                "    const char *title;\n"
                "    int done;\n"
                "    const char *completed_at;\n"
                "} Todo;\n\n"
                "int main(void) {\n"
                "    Todo item = {1, \"task\", 0, NULL};\n"
                "    printf(\"%d:%s:%d:%s\\n\", item.id, item.title, item.done, item.completed_at ? item.completed_at : \"\");\n"
                "    return 0;\n"
                "}\n"
            ),
            "todo_test.c": (
                "#include <assert.h>\n"
                "#include <string.h>\n\n"
                "typedef struct Todo {\n"
                "    int id;\n"
                "    const char *title;\n"
                "    int done;\n"
                "    const char *completed_at;\n"
                "} Todo;\n\n"
                "static int complete_todo(Todo *item, const char *completed_at) {\n"
                "    item->done = 1;\n"
                "    item->completed_at = completed_at;\n"
                "    return 1;\n"
                "}\n\n"
                "int main(void) {\n"
                "    Todo item = {1, \"task\", 0, NULL};\n"
                "    assert(complete_todo(&item, \"2026-02-14T00:00:00Z\") == 1);\n"
                "    assert(item.done == 1);\n"
                "    assert(strcmp(item.completed_at, \"2026-02-14T00:00:00Z\") == 0);\n"
                "    return 0;\n"
                "}\n"
            ),
        }

    def _language_validate_toolchain(self, invocation: dict[str, Any]) -> None:
        output = invocation.get("output") if isinstance(invocation, dict) else None
        detected = ""
        if isinstance(output, dict):
            detected = str(output.get("language") or "").strip().lower()
        if detected != self.language:
            raise RuntimeError(
                f"repo.detect_toolchain language mismatch: expected {self.language}, got {detected}"
            )

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
        else:
            self.repo_detect_tool = ""

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
            f"Eres un desarrollador de software {self.language} usando un catalogo de tools HTTP. "
            f"Tools disponibles: {json.dumps(available_tools)}. "
            f"Objetivo: {goal_text}. "
            f"Devuelve SOLO JSON valido con este schema exacto: {schema}. "
            "ordered_tools debe usar solo tools del catalogo y no repetir elementos. "
            "Incluye herramientas para implementar y verificar tests."
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

    def _invoke_repo_detect_toolchain_strict(self, phase: str, session_id: str) -> None:
        if not self.repo_detect_tool:
            return
        invocation = self._invoke(
            phase=phase,
            session_id=session_id,
            tool=self.repo_detect_tool,
            args={},
            approved=False,
        )
        if self.repo_detect_tool == "repo.detect_toolchain":
            self._language_validate_toolchain(invocation)

    def _invoke_repo_tests_strict(self, phase: str, session_id: str) -> None:
        args: dict[str, Any] = {}
        if self.language == "c":
            args["target"] = "todo_test.c"
        invocation = self._invoke(
            phase=phase,
            session_id=session_id,
            tool=self.repo_test_tool,
            args=args,
            approved=False,
            timeout=180,
        )
        if invocation.get("status") != "succeeded":
            raise RuntimeError(f"{self.repo_test_tool} failed: {invocation}")

    def _invoke_language_validations(self, phase: str, session_id: str) -> None:
        if self.language == "rust":
            if "rust.build" in self.available_tools:
                self._invoke(phase=phase, session_id=session_id, tool="rust.build", args={"release": False}, approved=False, timeout=180)
            if "rust.test" in self.available_tools:
                self._invoke(phase=phase, session_id=session_id, tool="rust.test", args={}, approved=False, timeout=180)
        elif self.language == "node":
            if "node.build" in self.available_tools:
                self._invoke(phase=phase, session_id=session_id, tool="node.build", args={}, approved=False, timeout=180)
            if "node.test" in self.available_tools:
                self._invoke(phase=phase, session_id=session_id, tool="node.test", args={}, approved=False, timeout=180)
        else:
            if "c.build" in self.available_tools:
                self._invoke(
                    phase=phase,
                    session_id=session_id,
                    tool="c.build",
                    args={"source": "main.c", "output_name": "todo-c-app", "standard": "c11"},
                    approved=False,
                    timeout=180,
                )
            if "c.test" in self.available_tools:
                self._invoke(
                    phase=phase,
                    session_id=session_id,
                    tool="c.test",
                    args={"source": "todo_test.c", "output_name": "todo-c-test", "standard": "c11", "run": True},
                    approved=False,
                    timeout=180,
                )

        if self.repo_build_tool in self.available_tools:
            build_args: dict[str, Any] = {}
            if self.language == "c":
                build_args["target"] = "main.c"
            self._invoke(
                phase=phase,
                session_id=session_id,
                tool=self.repo_build_tool,
                args=build_args,
                approved=False,
                timeout=180,
            )

        self._invoke_repo_tests_strict(phase, session_id)

    def step_1_bootstrap_session_and_catalog(self) -> SessionContext:
        print_step(1, f"Bootstrap session from local {self.language} repository and discover tool catalog")

        status, body = self._request("GET", "/healthz")
        if status != 200 or body.get("status") != "ok":
            raise RuntimeError(f"workspace health check failed: {status} {body}")

        session = self._create_session(f"agent-{self.language}-todo")
        tools = set(self._list_tools(session.session_id))
        if not tools:
            raise RuntimeError("empty tool catalog")

        self.available_tools = sorted(tools)
        self.evidence["tool_catalog"] = self.available_tools
        self._resolve_aliases(tools)

        missing_required = [tool for tool in self._language_required_tools() if tool not in tools]
        if missing_required:
            raise RuntimeError(f"catalog missing required tools for {self.language}: {missing_required}")

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
        print_step(2, "vLLM phase 1 plan: implement TODO + tests")

        goal = self._language_goal(1)
        try:
            plan = self._request_phase_plan_from_vllm(
                phase_name="phase_1_initial",
                goal_text=goal,
                available_tools=self.available_tools,
            )
            order = list(plan.get("ordered_tools") or [])
            self.phase1_ordered_tools = self._normalize_phase_order(order, required=self._language_required_tools())
            print_success("vLLM returned phase 1 plan")
        except Exception as exc:
            if self.require_vllm:
                raise
            print_warning(f"vLLM unavailable in phase 1, using deterministic fallback: {exc}")
            self.phase1_ordered_tools = self._normalize_phase_order(
                self.available_tools,
                required=self._language_required_tools(),
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

        for path, content in self._language_phase1_files().items():
            self._invoke(
                phase="phase_1",
                session_id=session.session_id,
                tool=self.fs_write_tool,
                args={"path": path, "content": content, "create_parents": True},
                approved=True,
            )

        self._invoke_repo_detect_toolchain_strict("phase_1", session.session_id)
        self._invoke_language_validations("phase_1", session.session_id)

        primary_file = self._language_primary_file()
        marker = self._language_phase1_marker()
        content = self._read_text("phase_1", session.session_id, primary_file)
        if marker in content:
            raise RuntimeError(f"phase 1 {primary_file} should not include marker {marker}")

        self._record_step(
            "phase_1_execution",
            "passed",
            data={"files_written": list(self._language_phase1_files().keys()), "verification": "tests succeeded"},
        )
        print_success("Phase 1 tests succeeded")

    def step_4_phase2_vllm_plan(self) -> None:
        print_step(4, "vLLM phase 2 plan: add completion date field")

        goal = self._language_goal(2)
        required = [self.fs_write_tool, self.repo_test_tool, self.fs_read_tool]
        try:
            plan = self._request_phase_plan_from_vllm(
                phase_name="phase_2_modification",
                goal_text=goal,
                available_tools=self.available_tools,
            )
            order = list(plan.get("ordered_tools") or [])
            self.phase2_ordered_tools = self._normalize_phase_order(order, required=required)
            print_success("vLLM returned phase 2 plan")
        except Exception as exc:
            if self.require_vllm:
                raise
            print_warning(f"vLLM unavailable in phase 2, using deterministic fallback: {exc}")
            self.phase2_ordered_tools = self._normalize_phase_order(self.available_tools, required=required)

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

        for path, content in self._language_phase2_files().items():
            self._invoke(
                phase="phase_2",
                session_id=session.session_id,
                tool=self.fs_write_tool,
                args={"path": path, "content": content, "create_parents": True},
                approved=True,
            )

        self._invoke_repo_detect_toolchain_strict("phase_2", session.session_id)
        self._invoke_language_validations("phase_2", session.session_id)

        primary_file = self._language_primary_file()
        marker = self._language_phase1_marker()
        content = self._read_text("phase_2", session.session_id, primary_file)
        if marker not in content:
            raise RuntimeError(f"phase 2 {primary_file} missing marker {marker}")

        if self.fs_search_tool in self.available_tools:
            self._invoke(
                phase="phase_2",
                session_id=session.session_id,
                tool=self.fs_search_tool,
                args={"path": ".", "pattern": marker, "max_results": 20},
                approved=False,
            )

        self._record_step(
            "phase_2_execution",
            "passed",
            data={"files_modified": list(self._language_phase2_files().keys()), "verification": "tests succeeded + marker found"},
        )
        print_success("Phase 2 tests succeeded and modification verified")

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
        print(f"{Colors.BLUE}{self.test_id} ({self.language}){Colors.NC}")
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print()

        print("Configuration:")
        print(f"  TEST_ID: {self.test_id}")
        print(f"  TODO_LANGUAGE: {self.language}")
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
    test = WorkspaceVLLMTodoEvolutionGenericE2E()
    return test.run()


if __name__ == "__main__":
    sys.exit(main())
