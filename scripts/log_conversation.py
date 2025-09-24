#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from swe_ai_fleet.context.adapters.redis_store import (
    LlmCallDTO,
    LlmResponseDTO,
    RedisStoreImpl,
)
from swe_ai_fleet.models.loaders import get_model_from_env


def _ping_vllm(endpoint: str) -> None:
    try:
        req = Request(url=f"{endpoint.rstrip('/')}/models", method="GET")
        with urlopen(req, timeout=5) as resp:
            _ = resp.read()
    except (HTTPError, URLError) as e:
        raise SystemExit(
            f"ERROR: vLLM endpoint not reachable at {endpoint}: {e}"
        ) from e


def main() -> int:
    ap = argparse.ArgumentParser(description="Log a real LLM conversation to Redis for a case")
    ap.add_argument("--case-id", default="demo-case-3")
    ap.add_argument("--session-id", default=f"sess-{int(time.time())}")
    ap.add_argument("--role", default="agent:dev-1")
    ap.add_argument("--task-id", default="S1")
    args = ap.parse_args()

    backend = os.getenv("LLM_BACKEND", "vllm").lower()
    if backend == "vllm":
        endpoint = os.getenv("VLLM_ENDPOINT", "http://127.0.0.1:8000/v1")
        _ping_vllm(endpoint)

    redis_url = os.getenv("REDIS_URL", "redis://:swefleet-dev@localhost:6379/0")
    store = RedisStoreImpl(redis_url)
    model = get_model_from_env()

    # Tag session with case_id and role
    store.set_session_meta(args.session_id, {"case_id": args.case_id, "role": args.role})

    prompt = (
        f"[{args.case_id}] Propose a concise OTP refactor for auth/otp.py and 2 tests for lockout."
        " Reply with a short bullet list of risks and mitigations."
    )

    t0 = time.time()
    text = model.infer(prompt, temperature=0.2)
    dt_ms = int((time.time() - t0) * 1000)

    store.save_llm_call(
        LlmCallDTO(
            session_id=args.session_id,
            task_id=args.task_id,
            requester=args.role,
            model=os.getenv("VLLM_MODEL") or os.getenv("OLLAMA_MODEL", "unknown"),
            params={"temperature": 0.2},
            content=prompt,
        )
    )
    store.save_llm_response(
        LlmResponseDTO(
            session_id=args.session_id,
            task_id=args.task_id,
            responder="agent:qa-1",
            model=os.getenv("VLLM_MODEL") or os.getenv("OLLAMA_MODEL", "unknown"),
            content=text,
            usage={"tokens": 0, "latency_ms": dt_ms},
        )
    )

    print(json.dumps({
        "case_id": args.case_id,
        "session_id": args.session_id,
        "backend": backend,
        "latency_ms": dt_ms,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())








