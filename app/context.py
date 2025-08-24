from typing import Any, Dict, List, Optional

from .storage import Storage
from .policy import PromptScopePolicy


class ContextAssembler:
    def __init__(self, storage: Storage, policy: PromptScopePolicy) -> None:
        self.storage = storage
        self.policy = policy

    async def assemble(self, *, role: str, session_id: str, task_id: Optional[str], max_chars: int = 4000) -> Dict[str, Any]:
        chat_window: List[Dict[str, Any]] = await self.storage.get_context_window(session_id=session_id, task_id=task_id, max_chars=max_chars)
        graph_bits: Dict[str, Any] = {}
        if task_id:
            graph_bits["decisions"] = await self.storage.get_task_decisions(task_id)
        context = {
            "chat": chat_window,
            "graph": graph_bits,
        }
        return self.policy.filter_context(role, context)