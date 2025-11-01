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
        return asyncio.run(coro)

