"""
Model loaders and adapters for LLM communication.

This module provides implementations for different LLM backends:
- VLLMModel: OpenAI-compatible vLLM server
- OllamaModel: Ollama local server
- LlamaCppModel: llama.cpp integration (not yet implemented, raises NotImplementedError)

These are low-level adapters for the Model Protocol.
"""

from .model_loaders import (
    Model,
    OllamaModel,
    VLLMModel,
    get_model_from_env,
)

__all__ = [
    "Model",
    "OllamaModel",
    "VLLMModel",
    "get_model_from_env",
]
