from typing import Any


class RedisStore:
    def __init__(self, url: str) -> None:
        self._url = url

    def put(self, key: str, value: dict[str, Any]) -> None:
        # TODO: implement with redis-py
        ...

    def get(self, key: str) -> dict[str, Any] | None: ...
