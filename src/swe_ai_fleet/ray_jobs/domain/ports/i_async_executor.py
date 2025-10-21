"""Port for async execution."""

from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, TypeVar

T = TypeVar('T')


class IAsyncExecutor(ABC):
    """
    Puerto para ejecutar código asíncrono.
    
    Define el contrato para ejecutar coroutines en un event loop.
    Abstrae asyncio.run() para permitir diferentes estrategias
    de ejecución (nuevo event loop, event loop existente, etc.).
    """
    
    @abstractmethod
    def run(self, coro: Awaitable[T]) -> T:
        """
        Ejecutar una coroutine y obtener el resultado.
        
        Args:
            coro: Coroutine a ejecutar
            
        Returns:
            Resultado de la coroutine
            
        Raises:
            Exception: Cualquier excepción propagada por la coroutine
        """
        pass

