#!/usr/bin/env python3
"""E2E test: minimal Kubernetes read tool catalog."""

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


class WorkspaceK8sReadMinimalE2E:
    def __init__(self) -> None:
        self.workspace_url = os.getenv(
            "WORKSPACE_URL",
            "http://workspace.swe-ai-fleet.svc.cluster.local:50053",
        ).rstrip("/")
        self.target_namespace = os.getenv("TARGET_NAMESPACE", "swe-ai-fleet").strip() or "swe-ai-fleet"
        self.evidence_file = os.getenv("EVIDENCE_FILE", f"/tmp/e2e-29-{int(time.time())}.json")
        self.run_id = f"e2e-ws-k8s-read-minimal-{int(time.time())}"
        self.sessions: list[str] = []
        self.invocation_counter = 0

        self.evidence: dict[str, Any] = {
            "test_id": "29-workspace-k8s-read-minimal",
            "run_id": self.run_id,
            "status": "running",
            "started_at": self._now_iso(),
            "workspace_url": self.workspace_url,
            "target_namespace": self.target_namespace,
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
                "actor_id": "e2e-k8s-read",
                "roles": ["devops"],
            },
            "metadata": {
                "allowed_k8s_namespaces": self.target_namespace,
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
            required_tools = [
                "k8s.get_pods",
                "k8s.get_images",
                "k8s.get_services",
                "k8s.get_deployments",
                "k8s.get_logs",
            ]
            missing = [tool for tool in required_tools if tool not in tools]
            if missing:
                raise RuntimeError(f"catalog missing tools: {missing}")
            self._record_step("catalog", "passed", {"tool_count": len(tools), "required_tools": required_tools})
            print_success("Catalog exposes minimal K8s read tools")

            denied_namespace = "kube-system" if self.target_namespace != "kube-system" else "default"

            print_step(3, "Validate namespace allowlist enforcement")
            status, body, inv = self._invoke(
                session_id=session_id,
                tool_name="k8s.get_pods",
                args={"namespace": denied_namespace, "max_pods": 5},
            )
            if status != 403:
                raise RuntimeError(f"expected 403 for denied namespace, got {status}: {body}")
            error = self._extract_error(inv, body)
            if str(error.get("code", "")).strip() != "policy_denied":
                raise RuntimeError(f"expected policy_denied for namespace deny, got: {error}")
            self._record_step(
                "namespace_allowlist_enforced",
                "passed",
                {"denied_namespace": denied_namespace},
            )
            print_success("Namespace allowlist deny path is enforced")

            print_step(4, "Invoke k8s.get_pods")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="k8s.get_pods",
                args={"namespace": self.target_namespace, "max_pods": 50},
            )
            self._assert_succeeded(invocation=inv, body=body, label="k8s.get_pods")
            pods_output = inv.get("output", {}) if isinstance(inv, dict) else {}
            pods = pods_output.get("pods", []) if isinstance(pods_output, dict) else []
            if not isinstance(pods, list):
                raise RuntimeError(f"k8s.get_pods invalid pods payload: {pods_output}")
            if len(pods) < 1:
                raise RuntimeError(f"k8s.get_pods returned no pods in namespace {self.target_namespace}")
            pod_name = ""
            for item in pods:
                if isinstance(item, dict) and "workspace-" in str(item.get("name", "")):
                    pod_name = str(item.get("name", "")).strip()
                    break
            if not pod_name:
                first = pods[0]
                pod_name = str(first.get("name", "")).strip() if isinstance(first, dict) else ""
            if not pod_name:
                raise RuntimeError("could not resolve pod_name for k8s.get_logs")
            pod_invocation_id = str(inv.get("id", "")).strip() if isinstance(inv, dict) else ""
            self._assert_artifact_present(pod_invocation_id, "k8s-get-pods-report.json")
            self._record_step("k8s_get_pods", "passed", {"count": len(pods), "pod_name_for_logs": pod_name})
            print_success("k8s.get_pods succeeded")

            print_step(5, "Invoke k8s.get_services")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="k8s.get_services",
                args={"namespace": self.target_namespace, "max_services": 50},
            )
            self._assert_succeeded(invocation=inv, body=body, label="k8s.get_services")
            svc_output = inv.get("output", {}) if isinstance(inv, dict) else {}
            services = svc_output.get("services", []) if isinstance(svc_output, dict) else []
            if not isinstance(services, list):
                raise RuntimeError(f"k8s.get_services invalid services payload: {svc_output}")
            svc_invocation_id = str(inv.get("id", "")).strip() if isinstance(inv, dict) else ""
            self._assert_artifact_present(svc_invocation_id, "k8s-get-services-report.json")
            self._record_step("k8s_get_services", "passed", {"count": len(services)})
            print_success("k8s.get_services succeeded")

            print_step(6, "Invoke k8s.get_deployments")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="k8s.get_deployments",
                args={"namespace": self.target_namespace, "max_deployments": 50, "include_containers": True},
            )
            self._assert_succeeded(invocation=inv, body=body, label="k8s.get_deployments")
            dep_output = inv.get("output", {}) if isinstance(inv, dict) else {}
            deployments = dep_output.get("deployments", []) if isinstance(dep_output, dict) else []
            if not isinstance(deployments, list):
                raise RuntimeError(f"k8s.get_deployments invalid deployments payload: {dep_output}")
            dep_invocation_id = str(inv.get("id", "")).strip() if isinstance(inv, dict) else ""
            self._assert_artifact_present(dep_invocation_id, "k8s-get-deployments-report.json")
            self._record_step("k8s_get_deployments", "passed", {"count": len(deployments)})
            print_success("k8s.get_deployments succeeded")

            print_step(7, "Invoke k8s.get_images")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="k8s.get_images",
                args={"namespace": self.target_namespace, "max_images": 200},
            )
            self._assert_succeeded(invocation=inv, body=body, label="k8s.get_images")
            img_output = inv.get("output", {}) if isinstance(inv, dict) else {}
            images = img_output.get("images", []) if isinstance(img_output, dict) else []
            if not isinstance(images, list) or len(images) < 1:
                raise RuntimeError(f"k8s.get_images returned no images: {img_output}")
            img_invocation_id = str(inv.get("id", "")).strip() if isinstance(inv, dict) else ""
            self._assert_artifact_present(img_invocation_id, "k8s-get-images-report.json")
            self._record_step("k8s_get_images", "passed", {"count": len(images)})
            print_success("k8s.get_images succeeded")

            print_step(8, "Invoke k8s.get_logs")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="k8s.get_logs",
                args={
                    "namespace": self.target_namespace,
                    "pod_name": pod_name,
                    "tail_lines": 100,
                    "max_bytes": 65536,
                },
            )
            self._assert_succeeded(invocation=inv, body=body, label="k8s.get_logs")
            logs_output = inv.get("output", {}) if isinstance(inv, dict) else {}
            if str(logs_output.get("pod_name", "")).strip() == "":
                raise RuntimeError(f"k8s.get_logs missing pod_name in output: {logs_output}")
            if int(logs_output.get("bytes", 0)) < 0:
                raise RuntimeError(f"k8s.get_logs bytes must be >= 0: {logs_output}")
            logs_invocation_id = str(inv.get("id", "")).strip() if isinstance(inv, dict) else ""
            self._assert_artifact_present(logs_invocation_id, "k8s-get-logs-report.json")
            self._record_step(
                "k8s_get_logs",
                "passed",
                {
                    "pod_name": logs_output.get("pod_name"),
                    "bytes": logs_output.get("bytes"),
                    "line_count": logs_output.get("line_count"),
                },
            )
            print_success("k8s.get_logs succeeded")

            final_status = "passed"
            self._record_step("test_result", "passed")
            print_success("E2E 29 completed successfully")
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
    test = WorkspaceK8sReadMinimalE2E()
    return test.run()


if __name__ == "__main__":
    sys.exit(main())
