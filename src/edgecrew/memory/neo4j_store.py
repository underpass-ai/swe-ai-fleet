from typing import Dict, Any, List

class Neo4jStore:
    def __init__(self, uri: str, user: str, password: str) -> None:
        self._uri = uri
        self._user = user
        self._password = password

    def upsert_entity(self, label: str, props: Dict[str, Any]) -> None:
        ...

    def relate(self, src_id: str, rel: str, dst_id: str, props: Dict[str, Any]) -> None:
        ...

    def query(self, cypher: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        ...
