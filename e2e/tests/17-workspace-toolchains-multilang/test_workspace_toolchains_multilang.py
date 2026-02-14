#!/usr/bin/env python3
"""E2E test 17: multi-language toolchains over Workspace catalog.

This test runs a real multi-repo flow using Rust, Node+TypeScript, Python and C:
1) Start local workspace service inside the job container.
2) For each fixture repo, discover the catalog from API.
3) Ask vLLM for an ordered plan of tools.
4) Execute language-specific tools and repo meta-tools.
5) Persist structured evidence to file and logs.
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
    case_name: str


@dataclass
class ToolCallSpec:
    tool: str
    args: dict[str, Any]
    approved: bool = False
    timeout: int = 120


@dataclass
class CaseSpec:
    name: str
    actor_id: str
    source_repo_path: str
    expected_language: str
    objective: str
    required_tools: list[str]
    call_specs: dict[str, ToolCallSpec]


class WorkspaceToolchainsMultilangE2E:
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
        self.workspace_port = self._parse_port(os.getenv("WORKSPACE_PORT", "50053"), default=50053)
        self.workspace_log_file = os.getenv("WORKSPACE_LOG_FILE", "/tmp/workspace-local-17.log")
        self.fixture_root = os.getenv(
            "FIXTURE_ROOT",
            "/app/e2e/tests/17-workspace-toolchains-multilang/fixtures",
        )

        self.sessions: list[SessionContext] = []
        self.invocation_counter = 0
        self.run_id = f"e2e-ws-toolchains-17-{int(time.time())}"

        self.workspace_process: subprocess.Popen[str] | None = None
        self.workspace_log_handle = None

        self.cases = self._build_cases()
        self.evidence_file = os.getenv("EVIDENCE_FILE", "/tmp/evidence-17.json")
        self.evidence: dict[str, Any] = {
            "test_id": "17-workspace-toolchains-multilang",
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
                "workspace_log_file": self.workspace_log_file,
                "fixture_root": self.fixture_root,
            },
            "steps": [],
            "sessions": [],
            "case_runs": [],
            "phase_plans": {},
            "invocations": [],
        }

    def _build_cases(self) -> list[CaseSpec]:
        rust_repo = os.path.join(self.fixture_root, "rust-repo")
        node_repo = os.path.join(self.fixture_root, "node-ts-repo")
        python_repo = os.path.join(self.fixture_root, "python-repo")
        c_repo = os.path.join(self.fixture_root, "c-repo")

        return [
            CaseSpec(
                name="rust",
                actor_id="agent-rust",
                source_repo_path=rust_repo,
                expected_language="rust",
                objective="Validar build/test/lint/format para crate Rust de TODO con campo completed_at.",
                required_tools=[
                    "repo.detect_toolchain",
                    "rust.build",
                    "rust.test",
                    "rust.clippy",
                    "rust.format",
                    "repo.build",
                    "repo.test",
                ],
                call_specs={
                    "repo.detect_toolchain": ToolCallSpec("repo.detect_toolchain", {}),
                    "rust.build": ToolCallSpec("rust.build", {"release": False}, timeout=180),
                    "rust.test": ToolCallSpec("rust.test", {}, timeout=180),
                    "rust.clippy": ToolCallSpec("rust.clippy", {"deny_warnings": True}, timeout=180),
                    "rust.format": ToolCallSpec("rust.format", {"check": True}, timeout=180),
                    "repo.build": ToolCallSpec("repo.build", {}, timeout=180),
                    "repo.test": ToolCallSpec("repo.test", {}, timeout=180),
                },
            ),
            CaseSpec(
                name="node_typescript",
                actor_id="agent-node-ts",
                source_repo_path=node_repo,
                expected_language="node",
                objective="Validar install/build/typecheck/lint/test para repo Node+TypeScript TODO.",
                required_tools=[
                    "repo.detect_toolchain",
                    "node.install",
                    "node.typecheck",
                    "node.build",
                    "repo.build",
                    "node.lint",
                    "node.test",
                    "repo.test",
                ],
                call_specs={
                    "repo.detect_toolchain": ToolCallSpec("repo.detect_toolchain", {}),
                    "node.install": ToolCallSpec(
                        "node.install",
                        {"use_ci": False, "ignore_scripts": True},
                        timeout=180,
                    ),
                    "node.typecheck": ToolCallSpec("node.typecheck", {}, timeout=180),
                    "node.build": ToolCallSpec("node.build", {}, timeout=180),
                    "repo.build": ToolCallSpec("repo.build", {}, timeout=180),
                    "node.lint": ToolCallSpec("node.lint", {}, timeout=180),
                    "node.test": ToolCallSpec("node.test", {}, timeout=180),
                    "repo.test": ToolCallSpec("repo.test", {}, timeout=180),
                },
            ),
            CaseSpec(
                name="python",
                actor_id="agent-python",
                source_repo_path=python_repo,
                expected_language="python",
                objective="Validar install_deps/validate/test y repo meta-tools para proyecto Python TODO.",
                required_tools=[
                    "repo.detect_toolchain",
                    "python.install_deps",
                    "python.validate",
                    "repo.validate",
                    "repo.build",
                    "python.test",
                    "repo.test",
                ],
                call_specs={
                    "repo.detect_toolchain": ToolCallSpec("repo.detect_toolchain", {}),
                    "python.install_deps": ToolCallSpec(
                        "python.install_deps",
                        {"use_venv": True},
                        timeout=240,
                    ),
                    "python.validate": ToolCallSpec("python.validate", {"target": "."}, timeout=180),
                    "repo.validate": ToolCallSpec("repo.validate", {"target": "."}, timeout=180),
                    "repo.build": ToolCallSpec("repo.build", {"target": "."}, timeout=180),
                    "python.test": ToolCallSpec("python.test", {"target": "."}, timeout=180),
                    "repo.test": ToolCallSpec("repo.test", {"target": "."}, timeout=180),
                },
            ),
            CaseSpec(
                name="c",
                actor_id="agent-c",
                source_repo_path=c_repo,
                expected_language="c",
                objective="Validar compilacion y pruebas en C con tools c.* y repo.*.",
                required_tools=[
                    "repo.detect_toolchain",
                    "c.build",
                    "repo.build",
                    "c.test",
                    "repo.test",
                ],
                call_specs={
                    "repo.detect_toolchain": ToolCallSpec("repo.detect_toolchain", {}),
                    "c.build": ToolCallSpec(
                        "c.build",
                        {"source": "main.c", "output_name": "todo-c-app", "standard": "c11"},
                        timeout=180,
                    ),
                    "repo.build": ToolCallSpec("repo.build", {"target": "main.c"}, timeout=180),
                    "c.test": ToolCallSpec(
                        "c.test",
                        {
                            "source": "todo_test.c",
                            "output_name": "todo-c-test",
                            "standard": "c11",
                            "run": True,
                        },
                        timeout=180,
                    ),
                    "repo.test": ToolCallSpec("repo.test", {"target": "todo_test.c"}, timeout=180),
                },
            ),
        ]

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
        case_name: str,
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
                "case": case_name,
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
        for case in self.cases:
            if not os.path.isdir(case.source_repo_path):
                raise RuntimeError(f"fixture path not found: {case.source_repo_path}")

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

        deadline = time.time() + 50
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

    def _create_session(self, case: CaseSpec) -> SessionContext:
        payload = {
            "principal": {
                "tenant_id": "e2e-tenant",
                "actor_id": case.actor_id,
                "roles": ["developer"],
            },
            "source_repo_path": case.source_repo_path,
            "allowed_paths": ["."],
            "expires_in_seconds": 3600,
        }
        status, body = self._request("POST", "/v1/sessions", payload)
        if status != 201:
            raise RuntimeError(f"create session failed ({status}): {body}")

        session_id = body["session"]["id"]
        context = SessionContext(session_id=session_id, actor_id=case.actor_id, case_name=case.name)
        self.sessions.append(context)
        self.evidence["sessions"].append(
            {
                "at": self._now_iso(),
                "session_id": session_id,
                "actor_id": case.actor_id,
                "case": case.name,
                "source_repo_path": case.source_repo_path,
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
        *,
        case_name: str,
        session_id: str,
        tool: str,
        args: dict[str, Any],
        approved: bool = False,
        timeout: int = 120,
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
            case_name=case_name,
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

    def _build_plan_messages(
        self,
        *,
        case: CaseSpec,
        available_tools: list[str],
        feedback: str | None,
    ) -> list[dict[str, str]]:
        schema = (
            '{"case":"' + case.name + '","ordered_tools":["tool_a","tool_b"],'
            '"notes":"..."}'
        )
        prompt = (
            f"Eres un desarrollador de software que usa un catalogo HTTP de tools. "
            f"Tools disponibles: {json.dumps(available_tools)}. "
            f"Objetivo: {case.objective}. "
            f"Debes incluir obligatoriamente estas tools: {json.dumps(case.required_tools)}. "
            f"Devuelve SOLO JSON valido con schema exacto: {schema}. "
            "ordered_tools debe contener un subconjunto de tools disponibles, sin duplicados."
        )
        if feedback:
            prompt += f" Correccion obligatoria: {feedback}"

        return [
            {
                "role": "system",
                "content": "Respondes JSON estricto. Sin markdown. Sin texto extra.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]

    def _request_plan_from_vllm(self, case: CaseSpec, available_tools: list[str]) -> list[str]:
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
                "messages": self._build_plan_messages(
                    case=case,
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
                    self.evidence["phase_plans"][case.name] = {
                        "source": "text-fallback",
                        "raw": self._compact(raw),
                        "parsed": self._compact({"ordered_tools": inferred}),
                    }
                    return inferred
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

            self.evidence["phase_plans"][case.name] = {
                "source": "json",
                "raw": self._compact(raw),
                "parsed": self._compact(parsed),
            }
            return cleaned

        inferred = infer_order(last_raw)
        if inferred:
            self.evidence["phase_plans"][case.name] = {
                "source": "final-text-fallback",
                "raw": self._compact(last_raw),
                "parsed": self._compact({"ordered_tools": inferred}),
                "last_parsed": self._compact(last_parsed),
            }
            return inferred

        raise RuntimeError(f"vLLM did not return a valid plan for case {case.name}")

    def _normalize_order(self, order: list[str], required: list[str], available_tools: set[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for tool in order:
            if tool in available_tools and tool not in seen:
                cleaned.append(tool)
                seen.add(tool)

        missing = [tool for tool in required if tool not in cleaned]
        if missing:
            if self.strict_vllm_plan:
                raise RuntimeError(f"plan missing required tools: {missing}")
            cleaned.extend(missing)
        return cleaned

    def _validate_detected_language(self, case: CaseSpec, invocation: dict[str, Any]) -> None:
        output = invocation.get("output") if isinstance(invocation, dict) else None
        language = ""
        if isinstance(output, dict):
            language = str(output.get("language") or "").strip().lower()
        if language != case.expected_language:
            raise RuntimeError(
                f"repo.detect_toolchain language mismatch for {case.name}: expected {case.expected_language}, got {language}"
            )

    def run_case(self, index: int, case: CaseSpec) -> None:
        print_step(index, f"Case {case.name}: discover + plan + execute required toolchain tools")

        session = self._create_session(case)
        tools = set(self._list_tools(session.session_id))
        if not tools:
            raise RuntimeError(f"empty tool catalog for case {case.name}")

        missing_tools = [tool for tool in case.required_tools if tool not in tools]
        if missing_tools:
            raise RuntimeError(f"case {case.name} missing required tools in catalog: {missing_tools}")

        available_sorted = sorted(tools)
        try:
            planned_order = self._request_plan_from_vllm(case, available_sorted)
            print_success(f"vLLM plan obtained for case {case.name}")
        except Exception as exc:
            if self.require_vllm:
                raise
            print_warning(f"vLLM unavailable for {case.name}, using deterministic plan: {exc}")
            planned_order = []

        execution_order = self._normalize_order(planned_order, case.required_tools, tools)
        print_info(f"Case {case.name} execution order: {execution_order}")

        executed_required: set[str] = set()
        executed_any: list[str] = []

        for tool in execution_order:
            call_spec = case.call_specs.get(tool)
            if call_spec is None:
                continue

            invocation = self._invoke(
                case_name=case.name,
                session_id=session.session_id,
                tool=call_spec.tool,
                args=call_spec.args,
                approved=call_spec.approved,
                timeout=call_spec.timeout,
            )
            if invocation.get("status") != "succeeded":
                raise RuntimeError(
                    f"tool {tool} failed in case {case.name}: "
                    f"status={invocation.get('status')} error={invocation.get('error')}"
                )

            executed_any.append(tool)
            if tool in case.required_tools:
                executed_required.add(tool)
            if tool == "repo.detect_toolchain":
                self._validate_detected_language(case, invocation)

        missing_exec = [tool for tool in case.required_tools if tool not in executed_required]
        if missing_exec:
            raise RuntimeError(f"case {case.name} did not execute required tools: {missing_exec}")

        self.evidence["case_runs"].append(
            {
                "at": self._now_iso(),
                "case": case.name,
                "session_id": session.session_id,
                "expected_language": case.expected_language,
                "required_tools": case.required_tools,
                "execution_order": execution_order,
                "executed_tools": executed_any,
            }
        )
        print_success(f"Case {case.name} completed")

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
        print(f"{Colors.BLUE}Workspace Toolchains Multi-language E2E Test (17){Colors.NC}")
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print()

        print("Configuration:")
        print(f"  WORKSPACE_URL: {self.workspace_url}")
        print(f"  START_LOCAL_WORKSPACE: {self.start_local_workspace}")
        print(f"  WORKSPACE_BINARY: {self.workspace_binary}")
        print(f"  WORKSPACE_PORT: {self.workspace_port}")
        print(f"  FIXTURE_ROOT: {self.fixture_root}")
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

            for idx, case in enumerate(self.cases, start=1):
                step_name = f"case_{idx}_{case.name}"
                self._execute_step(step_name, lambda case=case, idx=idx: self.run_case(idx, case))

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
    test = WorkspaceToolchainsMultilangE2E()
    return test.run()


if __name__ == "__main__":
    sys.exit(main())
