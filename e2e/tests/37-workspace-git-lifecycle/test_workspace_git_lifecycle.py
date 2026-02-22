#!/usr/bin/env python3
"""E2E test: dedicated Git lifecycle contracts in workspace service."""

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


class WorkspaceGitLifecycleE2E:
    def __init__(self) -> None:
        self.workspace_url = os.getenv(
            "WORKSPACE_URL",
            "http://workspace.swe-ai-fleet.svc.cluster.local:50053",
        ).rstrip("/")
        self.workspace_git_repo_url = os.getenv(
            "WORKSPACE_GIT_REPO_URL",
            "https://github.com/octocat/Hello-World.git",
        ).strip()
        self.workspace_git_repo_ref = os.getenv("WORKSPACE_GIT_REPO_REF", "").strip()
        self.evidence_file = os.getenv("EVIDENCE_FILE", f"/tmp/e2e-37-{int(time.time())}.json")

        self.run_id = f"e2e-ws-git-lifecycle-{int(time.time())}"
        self.feature_branch = f"e2e/ws-gap-001-{int(time.time())}"
        self.commit_target_path = ""

        self.sessions: list[str] = []
        self.invocation_counter = 0
        self.base_branch = ""
        self.commit_hash = ""

        self.evidence: dict[str, Any] = {
            "test_id": "37-workspace-git-lifecycle",
            "run_id": self.run_id,
            "status": "running",
            "started_at": self._now_iso(),
            "workspace_url": self.workspace_url,
            "workspace_git_repo_url": self.workspace_git_repo_url,
            "workspace_git_repo_ref": self.workspace_git_repo_ref,
            "feature_branch": self.feature_branch,
            "commit_target_path": self.commit_target_path,
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
                "actor_id": "e2e-git-lifecycle",
                "roles": ["platform_admin"],
            },
            "metadata": {
                "allowed_git_remotes": "origin",
                "allowed_git_ref_prefixes": "refs/heads/",
            },
            "expires_in_seconds": 3600,
        }
        if self.workspace_git_repo_url:
            payload["repo_url"] = self.workspace_git_repo_url
        if self.workspace_git_repo_ref:
            payload["repo_ref"] = self.workspace_git_repo_ref

        status, body = self._request("POST", "/v1/sessions", payload, timeout=240)
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
        timeout: int = 240,
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

    def _assert_invocation(self, invocation: dict[str, Any] | None, label: str) -> dict[str, Any]:
        if invocation is None:
            raise RuntimeError(f"{label}: missing invocation")
        return invocation

    def _assert_succeeded(self, *, invocation: dict[str, Any] | None, body: dict[str, Any], label: str) -> dict[str, Any]:
        inv = self._assert_invocation(invocation, label)
        status = str(inv.get("status", "")).strip()
        if status != "succeeded":
            raise RuntimeError(f"{label}: expected succeeded, got {status} ({self._extract_error(inv, body)})")
        output = inv.get("output")
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
        inv = self._assert_invocation(invocation, label)
        error = self._extract_error(inv, body)
        code = str(error.get("code", "")).strip()
        if code != expected_code:
            raise RuntimeError(f"{label}: expected {expected_code}, got {code} ({error})")

    def _assert_succeeded_or_exec_failure(
        self,
        *,
        invocation: dict[str, Any] | None,
        body: dict[str, Any],
        label: str,
    ) -> None:
        inv = self._assert_invocation(invocation, label)
        status = str(inv.get("status", "")).strip()
        if status == "succeeded":
            return
        if status != "failed":
            raise RuntimeError(f"{label}: unexpected status {status}")

        error = self._extract_error(inv, body)
        code = str(error.get("code", "")).strip()
        allowed = {"execution_failed", "git_repo_error", "git_usage_error"}
        if code not in allowed:
            raise RuntimeError(f"{label}: unexpected failure code {code} ({error})")

    def _ensure_git_identity(self, session_id: str) -> None:
        _, body, inv = self._invoke(
            session_id=session_id,
            tool_name="fs.read_file",
            args={"path": ".git/config"},
            approved=False,
        )
        output = self._assert_succeeded(invocation=inv, body=body, label="read git config")
        config_text = str(output.get("content", ""))
        if "[user]" in config_text:
            return

        user_block = "\n[user]\n\tname = Workspace E2E\n\temail = workspace-e2e@example.com\n"
        if not config_text.endswith("\n"):
            config_text += "\n"
        patched = config_text + user_block

        _, body, inv = self._invoke(
            session_id=session_id,
            tool_name="fs.write_file",
            args={"path": ".git/config", "content": patched, "encoding": "utf8"},
            approved=True,
        )
        self._assert_succeeded(invocation=inv, body=body, label="write git config")

    def _resolve_base_branch(self, branches: list[dict[str, Any]]) -> str:
        for item in branches:
            if bool(item.get("current")):
                name = str(item.get("name", "")).strip()
                if name:
                    return name
        for item in branches:
            name = str(item.get("name", "")).strip()
            if name:
                return name
        raise RuntimeError("could not resolve base branch from branch list")

    def _pick_commit_target_path(self, entries: list[dict[str, Any]]) -> str:
        preferred = ("README.md", "README", "README.txt", "readme.md", "readme.txt")
        files: list[str] = []
        for entry in entries:
            if str(entry.get("type", "")).strip() != "file":
                continue
            path = str(entry.get("path", "")).strip()
            if not path or path.startswith(".git/") or path == ".git":
                continue
            files.append(path)

        for candidate in preferred:
            if candidate in files:
                return candidate

        if files:
            return files[0]
        raise RuntimeError("could not find a tracked file candidate for git.commit")

    def _write_evidence(self, status: str, error_message: str = "") -> None:
        self.evidence["status"] = status
        self.evidence["ended_at"] = self._now_iso()
        if self.base_branch:
            self.evidence["base_branch"] = self.base_branch
        if self.commit_hash:
            self.evidence["commit_hash"] = self.commit_hash
        if self.commit_target_path:
            self.evidence["commit_target_path"] = self.commit_target_path
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
            print_step(1, "Workspace health and session bootstrap")
            status, body = self._request("GET", "/healthz")
            if status != 200 or body.get("status") != "ok":
                raise RuntimeError(f"health check failed ({status}): {body}")

            if not self.workspace_git_repo_url:
                raise RuntimeError("WORKSPACE_GIT_REPO_URL is required for this test")

            session_id = self._create_session()
            status, body = self._request("GET", f"/v1/sessions/{session_id}/tools")
            if status != 200:
                raise RuntimeError(f"list tools failed ({status}): {body}")
            tools = [str(item.get("name", "")).strip() for item in body.get("tools", []) if isinstance(item, dict)]
            required = [
                "git.checkout",
                "git.log",
                "git.show",
                "git.branch_list",
                "git.commit",
                "git.push",
                "git.fetch",
                "git.pull",
                "fs.read_file",
                "fs.write_file",
                "fs.list",
            ]
            missing = [name for name in required if name not in tools]
            if missing:
                raise RuntimeError(f"catalog missing required tools: {missing}")
            self._record_step("bootstrap", "passed", {"tool_count": len(tools), "required": required})
            print_success("Session created with git-enabled catalog")

            print_step(2, "Resolve base branch and validate ref allowlist deny")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="git.branch_list",
                args={"all": False},
                approved=False,
            )
            output = self._assert_succeeded(invocation=inv, body=body, label="git.branch_list")
            raw_branches = output.get("branches")
            branches = [item for item in raw_branches if isinstance(item, dict)] if isinstance(raw_branches, list) else []
            if not branches:
                raise RuntimeError(f"branch_list returned empty branches: {output}")
            self.base_branch = self._resolve_base_branch(branches)

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="git.checkout",
                args={"ref": "refs/tags/v1.0.0"},
                approved=False,
            )
            self._assert_error_code(
                invocation=inv,
                body=body,
                label="git.checkout deny ref allowlist",
                expected_code="policy_denied",
            )
            self._record_step("branch_and_allowlist", "passed", {"base_branch": self.base_branch})
            print_success(f"Base branch resolved: {self.base_branch}")

            print_step(3, "Checkout feature branch and commit a deterministic change")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="git.checkout",
                args={"ref": self.feature_branch, "create": True, "start_point": self.base_branch},
                approved=False,
            )
            self._assert_succeeded(invocation=inv, body=body, label="git.checkout create")

            self._ensure_git_identity(session_id)

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="fs.list",
                args={"path": ".", "recursive": True, "max_entries": 400},
                approved=False,
            )
            output = self._assert_succeeded(invocation=inv, body=body, label="fs.list")
            raw_entries = output.get("entries")
            entries = [item for item in raw_entries if isinstance(item, dict)] if isinstance(raw_entries, list) else []
            self.commit_target_path = self._pick_commit_target_path(entries)

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="fs.read_file",
                args={"path": self.commit_target_path},
                approved=False,
            )
            output = self._assert_succeeded(invocation=inv, body=body, label="fs.read_file target")
            existing_content = str(output.get("content", ""))
            marker_content = f"\nworkspace git lifecycle marker: {self.run_id}\n"
            updated_content = existing_content + marker_content

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="fs.write_file",
                args={
                    "path": self.commit_target_path,
                    "content": updated_content,
                    "encoding": "utf8",
                },
                approved=True,
            )
            self._assert_succeeded(invocation=inv, body=body, label="fs.write_file target")

            commit_message = f"e2e: git lifecycle {self.run_id}"
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="git.commit",
                args={"message": commit_message, "paths": [self.commit_target_path]},
                approved=True,
            )
            output = self._assert_succeeded(invocation=inv, body=body, label="git.commit")
            self.commit_hash = str(output.get("commit", "")).strip()
            if not self.commit_hash:
                raise RuntimeError(f"git.commit returned empty commit hash: {output}")
            self._record_step(
                "checkout_and_commit",
                "passed",
                {"commit_hash": self.commit_hash, "commit_target_path": self.commit_target_path},
            )
            print_success("Committed change on feature branch")

            print_step(4, "Validate git.log and git.show on committed branch")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="git.log",
                args={"ref": self.feature_branch, "max_count": 10},
                approved=False,
            )
            output = self._assert_succeeded(invocation=inv, body=body, label="git.log")
            raw_entries = output.get("entries")
            entries = [item for item in raw_entries if isinstance(item, dict)] if isinstance(raw_entries, list) else []
            if not entries:
                raise RuntimeError(f"git.log returned empty entries: {output}")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="git.show",
                args={"ref": self.feature_branch, "patch": False, "stat": True},
                approved=False,
            )
            output = self._assert_succeeded(invocation=inv, body=body, label="git.show")
            show_text = str(output.get("show", ""))
            if self.commit_hash[:12] not in show_text and "e2e: git lifecycle" not in show_text:
                raise RuntimeError("git.show output missing commit marker")
            self._record_step("log_and_show", "passed", {"entries_count": len(entries)})
            print_success("git.log and git.show contracts validated")

            print_step(5, "Approval and allowlist gates for git.push")
            push_refspec = f"refs/heads/{self.feature_branch}:refs/heads/{self.feature_branch}"
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="git.push",
                args={"remote": "origin", "refspec": push_refspec, "set_upstream": True},
                approved=False,
            )
            self._assert_error_code(
                invocation=inv,
                body=body,
                label="git.push approval gate",
                expected_code="approval_required",
            )

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="git.push",
                args={"remote": "upstream", "refspec": push_refspec},
                approved=True,
            )
            self._assert_error_code(
                invocation=inv,
                body=body,
                label="git.push remote allowlist",
                expected_code="policy_denied",
            )
            self._record_step("push_gates", "passed")
            print_success("git.push approval and allowlist gates validated")

            print_step(6, "Fetch and pull using allowlisted origin/base branch")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="git.fetch",
                args={"remote": "origin", "refspec": f"refs/heads/{self.base_branch}", "prune": True},
                approved=True,
            )
            self._assert_succeeded_or_exec_failure(invocation=inv, body=body, label="git.fetch")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="git.checkout",
                args={"ref": self.base_branch},
                approved=False,
            )
            self._assert_succeeded(invocation=inv, body=body, label="git.checkout base")

            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="git.pull",
                args={"remote": "origin", "refspec": self.base_branch},
                approved=True,
            )
            self._assert_succeeded_or_exec_failure(invocation=inv, body=body, label="git.pull")
            self._record_step("fetch_and_pull", "passed")
            print_success("git.fetch/git.pull invocation contract validated")

            print_step(7, "Push to allowlisted origin/refspec")
            _, body, inv = self._invoke(
                session_id=session_id,
                tool_name="git.push",
                args={"remote": "origin", "refspec": push_refspec, "set_upstream": True},
                approved=True,
            )
            self._assert_succeeded_or_exec_failure(invocation=inv, body=body, label="git.push origin")
            self._record_step("push_origin", "passed")
            print_success("git.push to allowlisted origin validated")

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
    return WorkspaceGitLifecycleE2E().run()


if __name__ == "__main__":
    sys.exit(main())
