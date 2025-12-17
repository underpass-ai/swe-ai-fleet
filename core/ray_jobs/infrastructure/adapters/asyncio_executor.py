"""Asyncio executor adapter."""

import asyncio
from collections.abc import Awaitable
from typing import TypeVar

from ...domain.ports import IAsyncExecutor

T = TypeVar('T')


class AsyncioExecutor(IAsyncExecutor):
    """
    Implementación de IAsyncExecutor usando asyncio.run().
    
    Crea un nuevo event loop para ejecutar la coroutine.
    Esta es la estrategia por defecto y la requerida por Ray
    (Ray workers no tienen event loop activo).
    """
    
    def run(self, coro: Awaitable[T]) -> T:
        """
        Ejecutar coroutine usando asyncio.run().
        
        Crea un nuevo event loop, ejecuta la coroutine, y cierra el loop.
        
        Args:
            coro: Coroutine a ejecutar
            
        Returns:
            Resultado de la coroutine
            
        Raises:
            Exception: Cualquier excepción propagada por la coroutine
        """
        try:
            result = asyncio.run(coro)
            # Validate that we got a real result, not a sentinel
            if result is None:
                raise ValueError("Coroutine returned None")
            return result
        except RuntimeError as e:
            # Handle case where asyncio.run() is called from within an event loop
            if "asyncio.run() cannot be called from a running event loop" in str(e):
                # This shouldn't happen in Ray workers, but handle gracefully
                raise RuntimeError(
                    "asyncio.run() cannot be called from a running event loop. "
                    "This may indicate a configuration issue with Ray workers."
                ) from e
            raise

