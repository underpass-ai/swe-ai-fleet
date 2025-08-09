from typing import Optional, Dict, Any

class RedisStore:
    def __init__(self, url: str) -> None:
        self._url = url

    def put(self, key: str, value: Dict[str, Any]) -> None:
        # TODO: implement with redis-py
        ...

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        ...
