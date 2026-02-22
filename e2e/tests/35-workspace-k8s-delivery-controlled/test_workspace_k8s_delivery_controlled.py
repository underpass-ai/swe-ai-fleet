#!/usr/bin/env python3
"""E2E test: controlled Kubernetes delivery tools."""

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


class WorkspaceK8sDeliveryControlledE2E:
    def __init__(self) -> None:
        self.workspace_url = os.getenv(
            "WORKSPACE_URL",
            "http://workspace.swe-ai-fleet.svc.cluster.local:50053",
        ).rstrip("/")
        self.target_namespace = os.getenv("TARGET_NAMESPACE", "swe-ai-fleet").strip() or "swe-ai-fleet"
        self.denied_namespace = os.getenv("DENIED_NAMESPACE", "kube-system").strip() or "kube-system"
        self.require_delivery_tools = os.getenv("REQUIRE_K8S_DELIVERY_TOOLS", "false").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.evidence_file = os.getenv("EVIDENCE_FILE", f"/tmp/e2e-35-{int(time.time())}.json")
        self.run_id = f"e2e-ws-k8s-delivery-{int(time.time())}"
        self.sessions: list[str] = []
        self.invocation_counter = 0

        self.configmap_name = "workspace-e2e-k8s-delivery-cm"
        self.deployment_name = "workspace-e2e-k8s-delivery-dep"

        self.evidence: dict[str, Any] = {
            "test_id": "35-workspace-k8s-delivery-controlled",
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
        timeout: int = 120,
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
                "actor_id": "e2e-k8s-delivery",
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
        approved: bool = True,
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
            raise RuntimeError(f"{label}: expected {expected_code}, got {code}")

    def _build_apply_manifest(self) -> str:
        return f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: {self.configmap_name}
  labels:
    app.kubernetes.io/managed-by: workspace-e2e
    app.kubernetes.io/component: k8s-delivery
data:
  run_id: {self.run_id}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {self.deployment_name}
  labels:
    app.kubernetes.io/managed-by: workspace-e2e
    app.kubernetes.io/component: k8s-delivery
spec:
  replicas: 0
  selector:
    matchLabels:
      app: {self.deployment_name}
  template:
    metadata:
      labels:
        app: {self.deployment_name}
        app.kubernetes.io/managed-by: workspace-e2e
    spec:
      containers:
      - name: app
        image: busybox:1.36
        command: [\"sh\", \"-lc\", \"sleep 3600\"]
"""

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
            required = ["k8s.apply_manifest", "k8s.rollout_status", "k8s.restart_deployment"]
            missing = [name for name in required if name not in tools]
            if missing:
                if self.require_delivery_tools:
                    raise RuntimeError(f"catalog missing tools: {missing}")
                self._record_step(
                    "catalog",
                    "skipped",
                    {
                        "reason": "k8s delivery tools disabled",
                        "missing": missing,
                        "required": required,
                    },
                )
                print_warning("K8s delivery tools are disabled; skipping test 35 by configuration")
                final_status = "skipped"
                self._record_step("final", "skipped")
                return 0
            self._record_step("catalog", "passed", {"tool_count": len(tools), "required": required})
            print_success("Catalog exposes controlled K8s delivery tools")

            print_step(3, "Apply manifest (allowed namespace)")
            apply_manifest = self._build_apply_manifest()
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="k8s.apply_manifest",
                args={
                    "namespace": self.target_namespace,
                    "manifest": apply_manifest,
                    "max_objects": 5,
                    "dry_run": False,
                },
                timeout=180,
            )
            output = self._assert_succeeded(invocation=inv, body=body, label="k8s.apply_manifest")
            applied_count = output.get("applied_count", 0)
            if not isinstance(applied_count, int) or applied_count < 2:
                raise RuntimeError(f"apply expected applied_count>=2, got: {applied_count}")
            self._record_step("apply_manifest", "passed", {"applied_count": applied_count})
            print_success("k8s.apply_manifest succeeded")

            print_step(4, "Rollout status")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="k8s.rollout_status",
                args={
                    "namespace": self.target_namespace,
                    "deployment_name": self.deployment_name,
                    "timeout_seconds": 30,
                    "poll_interval_ms": 500,
                },
                timeout=120,
            )
            output = self._assert_succeeded(invocation=inv, body=body, label="k8s.rollout_status")
            rollout = output.get("rollout", {})
            if not isinstance(rollout, dict) or rollout.get("completed") is not True:
                raise RuntimeError(f"rollout expected completed=true, got: {rollout}")
            self._record_step("rollout_status", "passed")
            print_success("k8s.rollout_status succeeded")

            print_step(5, "Restart deployment")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="k8s.restart_deployment",
                args={
                    "namespace": self.target_namespace,
                    "deployment_name": self.deployment_name,
                    "wait_for_rollout": False,
                },
                timeout=120,
            )
            output = self._assert_succeeded(invocation=inv, body=body, label="k8s.restart_deployment")
            restarted_at = str(output.get("restarted_at", "")).strip()
            if not restarted_at:
                raise RuntimeError(f"restart expected restarted_at, got: {output}")
            self._record_step("restart_deployment", "passed", {"restarted_at": restarted_at})
            print_success("k8s.restart_deployment succeeded")

            print_step(6, "Policy deny (namespace allowlist)")
            deny_manifest = f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: workspace-e2e-k8s-delivery-denied
"""
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="k8s.apply_manifest",
                args={
                    "namespace": self.denied_namespace,
                    "manifest": deny_manifest,
                },
                timeout=60,
            )
            self._assert_error_code(
                invocation=inv,
                body=body,
                label="k8s.apply_manifest denied namespace",
                expected_code="policy_denied",
            )
            self._record_step("policy_denied_namespace", "passed")
            print_success("Namespace allowlist deny validated")

            print_step(7, "Kind allowlist deny")
            kind_deny_manifest = """apiVersion: v1
kind: Secret
metadata:
  name: workspace-e2e-k8s-delivery-secret
type: Opaque
stringData:
  k: v
"""
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="k8s.apply_manifest",
                args={
                    "namespace": self.target_namespace,
                    "manifest": kind_deny_manifest,
                },
                timeout=60,
            )
            self._assert_error_code(
                invocation=inv,
                body=body,
                label="k8s.apply_manifest denied kind",
                expected_code="policy_denied",
            )
            self._record_step("policy_denied_kind", "passed")
            print_success("Kind allowlist deny validated")

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
    return WorkspaceK8sDeliveryControlledE2E().run()


if __name__ == "__main__":
    sys.exit(main())
