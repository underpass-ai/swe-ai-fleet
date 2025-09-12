from __future__ import annotations

import os
import sys
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock, patch
from urllib.error import URLError


class _StubResponses(ModuleType):
    class HTMLResponse:  # noqa: D401
        pass

    class PlainTextResponse:  # noqa: D401
        pass


class _StubFastAPIModule(ModuleType):
    class HTTPException(Exception):  # noqa: D401
        def __init__(self, status_code: int, detail: str) -> None:  # noqa: D401
            super().__init__(f"{status_code}: {detail}")

    class Query:  # noqa: D401
        def __init__(self, *args, **kwargs) -> None:  # noqa: ANN001, D401
            pass

    class FastAPI:  # noqa: D401
        def __init__(self, *args, **kwargs) -> None:
            self.routes: dict[tuple[str, str], Any] = {}

        def get(self, path: str, response_class: Any | None = None):  # noqa: ANN401
            def decorator(fn):
                self.routes[("GET", path)] = fn
                return fn

            return decorator

        def post(self, path: str):
            def decorator(fn):
                self.routes[("POST", path)] = fn
                return fn

            return decorator


def _install_stubs() -> None:
    # Stub markdown
    md_mod = ModuleType("markdown")
    md_mod.markdown = lambda text, extensions=None: text  # type: ignore
    sys.modules["markdown"] = md_mod

    # Stub fastapi and fastapi.responses
    fastapi_mod = _StubFastAPIModule("fastapi")
    responses_mod = _StubResponses("fastapi.responses")
    sys.modules["fastapi"] = fastapi_mod
    sys.modules["fastapi.responses"] = responses_mod


def test_create_app_and_endpoints_execute():
    _install_stubs()

    # Patch _build_usecase to avoid touching Redis/Neo4j
    class _FakeReport:
        case_id = "CTX-001"
        plan_id = "P-CTX-001"
        generated_at_ms = 1
        markdown = "# Report\nOK"
        stats = {"events": 1}

    class _FakeUc:
        def generate(self, req):  # noqa: ANN001, D401
            return _FakeReport()

    with patch("swe_ai_fleet.web.server._build_usecase", return_value=_FakeUc()):
        # Patch RedisStoreImpl used by seed endpoint
        with patch("swe_ai_fleet.web.server.RedisStoreImpl") as Store:
            store = MagicMock()
            Store.return_value = store

            # Patch urlopen for LLM health
            fake_resp = MagicMock()
            fake_resp.read.return_value = b"{}"
            fake_cm = MagicMock()
            fake_cm.__enter__.return_value = fake_resp
            with patch.dict(os.environ, {"VLLM_ENDPOINT": "https://swe-vllm:8000/v1"}, clear=False):
                with patch("swe_ai_fleet.web.server.urlopen", return_value=fake_cm):
                    from swe_ai_fleet.web import server

                    app = server.create_app()
                    assert hasattr(app, "routes") and len(app.routes) >= 4

                    # Health endpoints
                    fn_h = app.routes[("GET", "/healthz")]
                    assert fn_h() == "ok"
                    fn_hl = app.routes[("GET", "/healthz/llm")]
                    hl = fn_hl()
                    assert isinstance(hl, dict) and hl.get("ok") is True

                    # Home
                    fn_home = app.routes[("GET", "/")]
                    page = fn_home()
                    assert "SWE AI Fleet — Demo" in page

                    # Call API report
                    fn = app.routes[("GET", "/api/report")]
                    data = fn(case_id="CTX-001", persist=False)
                    assert data["case_id"] == "CTX-001"

                    # Call UI report
                    fn_ui = app.routes[("GET", "/ui/report")]
                    html = fn_ui(case_id="CTX-001")
                    assert "Report" in html

                    # Call seed endpoint
                    fn_seed = app.routes[("GET", "/api/demo/seed_llm")]
                    out = fn_seed(case_id="CTX-001")
                    assert out.get("ok") is True


def test_healthz_llm_error_path():
    _install_stubs()

    with patch("swe_ai_fleet.web.server._build_usecase", return_value=MagicMock()):
        # Make urlopen raise URLError
        with patch.dict(os.environ, {"VLLM_ENDPOINT": "https://swe-vllm:8000/v1"}, clear=False):
            with patch("swe_ai_fleet.web.server.urlopen", side_effect=URLError("boom")):
                from swe_ai_fleet.web import server

                app = server.create_app()
                fn_hl = app.routes[("GET", "/healthz/llm")]
                try:
                    fn_hl()
                except server.HTTPException as exc:  # type: ignore[attr-defined]
                    assert "not reachable" in str(exc)


def test_main_invokes_uvicorn():
    _install_stubs()

    # Install a stub uvicorn module so that import inside main() resolves
    uvicorn_stub = ModuleType("uvicorn")

    def _run(app, host=None, port=None):  # noqa: ANN001, D401
        uvicorn_stub._called = True

    uvicorn_stub.run = _run  # type: ignore[attr-defined]
    sys.modules["uvicorn"] = uvicorn_stub

    # Patch usecase and call main
    with patch("swe_ai_fleet.web.server._build_usecase", return_value=MagicMock()):
        from swe_ai_fleet.web import server

        server.main()
        assert getattr(uvicorn_stub, "_called", False) is True


def test_load_config_defaults():
    _install_stubs()
    from swe_ai_fleet.web import server

    cfg = server._load_config_from_env()
    assert cfg.redis_url.endswith("/0")
    assert cfg.neo4j_user == "neo4j"
