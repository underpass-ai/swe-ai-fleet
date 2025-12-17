"""Neo4j Graph Queries - Infrastructure layer queries for graph relationships.

These queries are infrastructure-specific and handle Neo4j-specific details
like dynamic depth and node type matching.

Centralizes all graph relationship queries in one place:
- Easy to version and evolve
- Easy to review for security (injection prevention)
- Easy to optimize
- Easy to test
"""

from enum import Enum

from core.context.domain.node_id_field import NodeIdField


class Neo4jGraphQueries(str, Enum):
    """
    Cypher queries for graph relationship operations in Context Service.

    Centralizes all graph relationship queries in one place:
    - Easy to version and evolve
    - Easy to review for security (injection prevention)
    - Easy to optimize
    - Easy to test

    Note: Some queries require dynamic construction due to Cypher limitations
    (depth and node_type cannot be parameterized).
    """

    @classmethod
    def build_get_graph_relationships_query(cls, node_type: str, depth: int) -> str:
        """Build Cypher query for getting graph relationships.

        This method constructs a query with dynamic node_type and depth.
        These cannot be parameterized in Cypher, so they must be in the query string.

        Args:
            node_type: Node type (Project, Epic, Story, Task)
            depth: Traversal depth (1-3)

        Returns:
            Cypher query string

        Raises:
            ValueError: If node_type is invalid
        """
        # Get ID field Value Object from domain
        id_field = NodeIdField.from_node_type(node_type)

        # Build query with dynamic depth and node_type
        # Note: depth and node_type must be in query string (Cypher limitation)
        return f"""
            MATCH (n:{node_type})
            WHERE n.{id_field.to_string()} = $node_id
               OR n.id = $node_id
               OR n.project_id = $node_id
               OR n.epic_id = $node_id
               OR n.story_id = $node_id
               OR n.task_id = $node_id
            OPTIONAL MATCH path = (n)-[r*1..{depth}]-(neighbor)
            WITH n,
                 collect(DISTINCT {{
                   node: {{
                     id: coalesce(neighbor.project_id, neighbor.epic_id, neighbor.story_id, neighbor.task_id, neighbor.id),
                     labels: labels(neighbor),
                     properties: properties(neighbor),
                     name: coalesce(neighbor.title, neighbor.name)
                   }},
                   relationships: [rel IN relationships(path) | {{
                     type: type(rel),
                     from: coalesce(startNode(rel).project_id, startNode(rel).epic_id, startNode(rel).story_id, startNode(rel).task_id, startNode(rel).id),
                     to: coalesce(endNode(rel).project_id, endNode(rel).epic_id, endNode(rel).story_id, endNode(rel).task_id, endNode(rel).id),
                     properties: properties(rel)
                   }}]
                 }}) AS neighbors_data
            RETURN {{
              node: {{
                id: coalesce(n.project_id, n.epic_id, n.story_id, n.task_id, n.id),
                labels: labels(n),
                properties: properties(n),
                name: coalesce(n.title, n.name)
              }},
              neighbors: neighbors_data
            }} AS result
        """

