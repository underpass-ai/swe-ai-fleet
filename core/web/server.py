from __future__ import annotations

import html as html_lib
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import markdown as md
from core.memory.adapters.redis_store import LlmCallDTO, LlmResponseDTO, RedisStoreImpl
from core.reports.adapters.neo4j_decision_graph_read_adapter import (
    Neo4jDecisionGraphReadAdapter,
)
from core.reports.adapters.neo4j_query_store import Neo4jConfig, Neo4jQueryStore
from core.reports.adapters.redis_planning_read_adapter import RedisPlanningReadAdapter
from core.reports.decision_enriched_report import DecisionEnrichedReportUseCase
from core.reports.domain.report_request import ReportRequest
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, PlainTextResponse


@dataclass(frozen=True)
class AppConfig:
    redis_url: str
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    neo4j_database: str | None


def _load_config_from_env() -> AppConfig:
    return AppConfig(
        redis_url=os.getenv("REDIS_URL", "redis://:swefleet-dev@localhost:6379/0"),
        neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD", "swefleet-dev"),
        neo4j_database=os.getenv("NEO4J_DATABASE") or None,
    )


def _build_usecase(cfg: AppConfig) -> DecisionEnrichedReportUseCase:
    redis_client = RedisStoreImpl(cfg.redis_url).client

    # lightweight shim to satisfy PersistenceKvPort expected by RedisPlanningReadAdapter
    class _KvShim:
        def __init__(self, client: Any):
            self._c = client

        def get(self, key: str) -> str | None:
            return self._c.get(key)

        def xrevrange(self, key: str, count: int | None = None):
            return self._c.xrevrange(key, count=count)

        def pipeline(self):
            return self._c.pipeline()

        # Optional methods for LLM session listing helpers
        def scan(self, cursor: int = 0, match: str | None = None, count: int | None = None):
            return self._c.scan(cursor=cursor, match=match, count=count)

        def hgetall(self, key: str) -> dict[str, Any]:
            return self._c.hgetall(key)

    redis_adapter = RedisPlanningReadAdapter(_KvShim(redis_client))

    neo_cfg = Neo4jConfig(
        uri=cfg.neo4j_uri,
        user=cfg.neo4j_user,
        password=cfg.neo4j_password,
        database=cfg.neo4j_database,
    )
    graph_store = Neo4jQueryStore(neo_cfg)
    graph_adapter = Neo4jDecisionGraphReadAdapter(graph_store)

    return DecisionEnrichedReportUseCase(redis_adapter, graph_adapter)


def create_app() -> FastAPI:
    cfg = _load_config_from_env()
    uc = _build_usecase(cfg)

    app = FastAPI(title="SWE AI Fleet Demo UI", version="0.1.0")

    @app.get("/healthz", response_class=PlainTextResponse)
    def healthz() -> str:  # noqa: D401
        return "ok"

    @app.get("/healthz/llm")
    def healthz_llm() -> dict[str, Any]:
        endpoint = os.getenv("VLLM_ENDPOINT")
        if not endpoint:
            raise HTTPException(status_code=503, detail="VLLM_ENDPOINT not set")
        url = f"{endpoint.rstrip('/')}/models"
        try:
            req = Request(url=url, method="GET")
            with urlopen(req, timeout=3) as resp:
                _ = resp.read()
            return {"ok": True, "backend": "vllm", "endpoint": endpoint}
        except (HTTPError, URLError) as e:
            raise HTTPException(status_code=503, detail=f"vLLM not reachable at {url}: {e}") from e

    @app.get("/", response_class=HTMLResponse)
    def home() -> str:
        return (
            "<html><head><title>SWE AI Fleet</title>"
            "<style>body{font-family:sans-serif;max-width:920px;margin:2rem auto;padding:0 1rem}"
            "input,button{font-size:1rem;padding:.4rem .6rem;margin:.2rem}"
            "pre{background:#f6f8fa;padding:1rem;border-radius:6px;overflow:auto}"
            "</style></head><body>"
            "<h1>SWE AI Fleet — Demo</h1>"
            "<p>LLM health: <a href='/healthz/llm'>/healthz/llm</a></p>"
            "<p>Enter a case_id to render the Decision‑Enriched Report.</p>"
            "<form onsubmit=\"event.preventDefault();"
            + "window.location='/ui/report?case_id='+document.getElementById('cid').value\">"
            "<input id='cid' name='case_id' placeholder='CASE-123'/>"
            "<button type='submit'>View report</button>"
            "</form>"
            "<p>Need sample LLM conversations? Seed them: "
            "<code>/api/demo/seed_llm?case_id=CTX-001</code></p>"
            "<p>API: <code>/api/report?case_id=...&persist=false</code></p>"
            "</body></html>"
        )

    @app.get("/api/report")
    def api_report(
        case_id: str = Query(..., min_length=1),
        include_constraints: bool = True,
        include_acceptance: bool = True,
        include_timeline: bool = True,
        include_dependencies: bool = True,
        max_events: int = 200,
        persist: bool = False,
        ttl_seconds: int = 7 * 24 * 3600,
    ) -> dict[str, Any]:
        try:
            req = ReportRequest(
                case_id=case_id,
                include_constraints=include_constraints,
                include_acceptance=include_acceptance,
                include_timeline=include_timeline,
                include_dependencies=include_dependencies,
                max_events=max_events,
                persist_to_redis=persist,
                ttl_seconds=ttl_seconds,
            )
            report = uc.generate(req)
            return {
                "case_id": report.case_id,
                "plan_id": report.plan_id,
                "generated_at_ms": report.generated_at_ms,
                "markdown": report.markdown,
                "stats": report.stats,
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    @app.post("/api/demo/seed_llm")
    @app.get("/api/demo/seed_llm")
    def api_demo_seed_llm(
        case_id: str = Query(..., min_length=1),
    ) -> dict[str, Any]:
        """Seed two example LLM sessions and messages into Redis for this case.

        This enables the report to include the "LLM Conversations (recent)" section without
        requiring a live LLM backend.
        """
        try:
            store = RedisStoreImpl(cfg.redis_url)
            # Session 1
            sid1 = f"sess-{int(time.time()*1000)}-1"
            store.set_session_meta(sid1, {"case_id": case_id, "role": "agent:dev-1"})
            store.save_llm_call(
                LlmCallDTO(
                    session_id=sid1,
                    task_id="S1",
                    requester="agent:dev-1",
                    model="demo-llm",
                    params={"temperature": 0.2},
                    content="Propose OTP refactor and tests.",
                )
            )
            store.save_llm_response(
                LlmResponseDTO(
                    session_id=sid1,
                    task_id="S1",
                    responder="model:qwen3-coder",
                    model="demo-llm",
                    content=(
                        "- Extract OTP verification to a pure function\n"
                        "- Add tests for lockout after 5 attempts"
                    ),
                    usage={"tokens": 128, "latency_ms": 40},
                )
            )

            # Session 2
            sid2 = f"sess-{int(time.time()*1000)}-2"
            store.set_session_meta(sid2, {"case_id": case_id, "role": "agent:qa-1"})
            store.save_llm_call(
                LlmCallDTO(
                    session_id=sid2,
                    task_id="S2",
                    requester="agent:qa-1",
                    model="demo-llm",
                    params={"temperature": 0.1},
                    content="Generate additional test cases.",
                )
            )
            store.save_llm_response(
                LlmResponseDTO(
                    session_id=sid2,
                    task_id="S2",
                    responder="model:qwen3-coder",
                    model="demo-llm",
                    content=(
                        "- Case: expired OTP\n"
                        "- Case: system clock desynchronized"
                    ),
                    usage={"tokens": 96, "latency_ms": 35},
                )
            )
            return {"ok": True, "sessions": [sid1, sid2]}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    @app.get("/ui/report", response_class=HTMLResponse)
    def ui_report(
        case_id: str = Query(..., min_length=1),
        include_constraints: bool = True,
        include_acceptance: bool = True,
        include_timeline: bool = True,
        include_dependencies: bool = True,
        max_events: int = 200,
        persist: bool = False,
        ttl_seconds: int = 7 * 24 * 3600,
    ) -> str:
        try:
            req = ReportRequest(
                case_id=case_id,
                include_constraints=include_constraints,
                include_acceptance=include_acceptance,
                include_timeline=include_timeline,
                include_dependencies=include_dependencies,
                max_events=max_events,
                persist_to_redis=persist,
                ttl_seconds=ttl_seconds,
            )
            report = uc.generate(req)
            html_body = md.markdown(report.markdown, extensions=["fenced_code", "tables"])  # type: ignore
            return (
                "<html><head><title>Report - "
                + html_lib.escape(case_id)
                + "</title><style>"
                + "body{font-family:sans-serif;max-width:920px;margin:2rem auto;padding:0 1rem}"
                + "table{border-collapse:collapse;width:100%;}th,td{border:1px solid #ddd;padding:6px}"
                + "code{background:#f6f8fa;padding:2px 4px;border-radius:4px}"
                + "pre{background:#f6f8fa;padding:1rem;border-radius:6px;overflow:auto}"
                + "</style></head><body>"
                + f"<a href='/'>&larr; Home</a> | Case <code>{html_lib.escape(case_id)}</code>"
                + "<hr/>"
                + html_body
                + "</body></html>"
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    return app


def main() -> None:
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    app = create_app()
    uvicorn.run(app, host=host, port=port)


