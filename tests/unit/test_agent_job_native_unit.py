from __future__ import annotations

import importlib
import json
import sys
import types
from dataclasses import dataclass
from typing import Any


def _load_module_with_fake_ray():
    fake_ray = types.SimpleNamespace(remote=lambda *a, **k: (lambda cls: cls))
    sys.modules.setdefault("ray", fake_ray)

    # Provide stub usecase modules so import in agent_job_native succeeds
    import types as _types

    reh_mod = _types.ModuleType("swe_ai_fleet.context.usecases.rehydrate_context")
    class _StubRehydrate:  # minimal stub; tests will monkeypatch later
        def __init__(self, *a, **k): ...
        def execute(self, **k): return None
    reh_mod.RehydrateContextUseCase = _StubRehydrate
    sys.modules["swe_ai_fleet.context.usecases.rehydrate_context"] = reh_mod

    upd_mod = _types.ModuleType("swe_ai_fleet.context.usecases.update_subtask_status")
    class _StubUpdate:
        def __init__(self, *a, **k): ...
        def execute(self, **k): return None
    upd_mod.UpdateSubtaskStatusUseCase = _StubUpdate
    sys.modules["swe_ai_fleet.context.usecases.update_subtask_status"] = upd_mod

    # Import or reload the module so the decorator applies with the fake ray
    from swe_ai_fleet.orchestrator import agent_job_native as mod  # type: ignore

    importlib.reload(mod)
    return mod


@dataclass
class _Task:
    id: str
    title: str
    status: str


class _FakeRehydrate:
    def __init__(self, gq: Any, pr: Any) -> None:
        self.gq = gq
        self.pr = pr

    def execute(self, *, sprint_id: str, role: str):  # noqa: D401 (simple fake)
        class _Ctx:
            def __init__(self) -> None:
                self.tasks: list[_Task] = []

        return _Ctx()


class _FakeUpdate:
    def __init__(self, gc: Any) -> None:
        self.gc = gc
        # store calls on the bound instance for assertions
        if not hasattr(gc, "calls"):
            gc.calls = []  # type: ignore[attr-defined]

    def execute(self, *, task_id: str, new_status: str) -> None:
        self.gc.calls.append((task_id, new_status))  # type: ignore[attr-defined]


class _FakeRunner:
    def __init__(self, result: dict[str, Any]) -> None:
        self._result = result

    def run(self, spec: dict, workspace: str) -> dict:
        return dict(self._result)


class _DummyPort:
    pass


def test_run_once_no_candidates(capsys):
    mod = _load_module_with_fake_ray()

    # Patch use cases with fakes
    mod.RehydrateContextUseCase = _FakeRehydrate  # type: ignore[attr-defined]
    mod.UpdateSubtaskStatusUseCase = _FakeUpdate  # type: ignore[attr-defined]

    cfg = mod.AgentConfig(sprint_id="S1", role="dev")
    gq = _DummyPort()
    gc = _DummyPort()
    runner = _FakeRunner({"exit_code": 0})

    aw = mod.AgentWorker(
        cfg, gq, gc, runner, planning_read=None
    )

    # Make rehydrate return empty tasks
    result = aw.run_once()
    assert result == {"status": "NOOP", "reason": "no candidate tasks"}
    # No status updates should have occurred
    assert getattr(gc, "calls", []) == []
    # Nothing printed
    out = capsys.readouterr().out
    assert out.strip() == ""


def test_run_once_success_updates_and_event_printed(capsys):
    mod = _load_module_with_fake_ray()
    mod.RehydrateContextUseCase = _FakeRehydrate  # type: ignore[attr-defined]
    mod.UpdateSubtaskStatusUseCase = _FakeUpdate  # type: ignore[attr-defined]

    cfg = mod.AgentConfig(sprint_id="S1", role="dev", workspace="/ws")
    gq = _DummyPort()
    gc = _DummyPort()

    # Runner succeeds
    runner = _FakeRunner({"exit_code": 0, "artifacts_dir": "/tmp/a"})

    # Instantiate worker
    aw = mod.AgentWorker(cfg, gq, gc, runner, planning_read=None)

    # Monkeypatch the rehydrate to return a READY task
    def _fake_execute(self, *, sprint_id: str, role: str):
        class _Ctx:
            def __init__(self) -> None:
                self.tasks = [_Task(id="T1", title="Title", status="READY")]

        return _Ctx()

    mod.RehydrateContextUseCase.execute = _fake_execute  # type: ignore[assignment]

    res = aw.run_once()
    assert res["status"] == "DONE"
    assert res["task_id"] == "T1"
    assert res["artifacts"] == "/tmp/a"

    # Status transitions: IN_PROGRESS -> DONE
    assert getattr(gc, "calls", []) == [("T1", "IN_PROGRESS"), ("T1", "DONE")]

    out = capsys.readouterr().out.strip()
    assert out, "expected event printed"
    payload = json.loads(out)
    assert payload["task_id"] == "T1"
    assert payload["status"] == "DONE"
    assert payload["artifacts"] == "/tmp/a"


def test_run_once_failure_marks_failed_and_event(capsys):
    mod = _load_module_with_fake_ray()
    mod.RehydrateContextUseCase = _FakeRehydrate  # type: ignore[attr-defined]
    mod.UpdateSubtaskStatusUseCase = _FakeUpdate  # type: ignore[attr-defined]

    cfg = mod.AgentConfig(sprint_id="S1", role="dev", workspace="/ws")
    gq = _DummyPort()
    gc = _DummyPort()
    runner = _FakeRunner({"exit_code": 42})  # non-zero -> FAILED

    aw = mod.AgentWorker(cfg, gq, gc, runner, planning_read=None)

    def _fake_execute(self, *, sprint_id: str, role: str):
        class _Ctx:
            def __init__(self) -> None:
                self.tasks = [_Task(id="T2", title="X", status="READY")]

        return _Ctx()

    mod.RehydrateContextUseCase.execute = _fake_execute  # type: ignore[assignment]

    res = aw.run_once()
    assert res["status"] == "FAILED"
    assert res["task_id"] == "T2"
    assert res["artifacts"] is None

    assert getattr(gc, "calls", []) == [("T2", "IN_PROGRESS"), ("T2", "FAILED")]

    out = capsys.readouterr().out.strip()
    payload = json.loads(out)
    assert payload["task_id"] == "T2"
    assert payload["status"] == "FAILED"

