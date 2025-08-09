from typing import Protocol, Dict, Any

class Model(Protocol):
    def infer(self, prompt: str, **kwargs) -> str: ...

class LlamaCppModel:
    def __init__(self, gguf_path: str, n_ctx: int = 8192) -> None:
        self._gguf_path = gguf_path
        self._n_ctx = n_ctx

    def infer(self, prompt: str, **kwargs) -> str:
        # TODO: integrate llama.cpp bindings
        return "TODO: inference result"
