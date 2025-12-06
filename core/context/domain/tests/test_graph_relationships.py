"""Unit tests for GraphRelationships Aggregate Root.

Very intensive test coverage for all methods, edge cases, and validations.
Target: ≥90% coverage with comprehensive edge case testing.
"""

import pytest
from core.context.domain.graph_neighbors import GraphNeighbors
from core.context.domain.graph_relation_type import GraphRelationType
from core.context.domain.graph_relationship_edges import GraphRelationshipEdges
from core.context.domain.graph_relationships import GraphRelationships
from core.context.domain.relationship_error import RelationshipError
from core.context.domain.value_objects.graph_node import GraphNode
from core.context.domain.value_objects.graph_relationship_edge import GraphRelationshipEdge
from core.context.domain.value_objects.graph_relationship_edge_properties import (
    GraphRelationshipEdgeProperties,
)
from core.context.domain.value_objects.node_id import NodeId
from core.context.domain.value_objects.node_label import NodeLabel
from core.context.domain.value_objects.node_properties import NodeProperties
from core.context.domain.value_objects.node_title import NodeTitle
from core.context.domain.value_objects.node_type import NodeType


# Test fixture helpers to reduce duplication
def create_project_node(
    node_id: str = "project-1",
    title: str = "Project",
    properties: dict | None = None,
) -> GraphNode:
    """Create a Project GraphNode for testing."""
    return GraphNode(
        id=NodeId(value=node_id),
        labels=[NodeLabel(value="Project")],
        properties=NodeProperties(properties=properties or {}),
        node_type=NodeType(value="Project"),
        title=NodeTitle(value=title),
    )


def create_epic_node(
    node_id: str = "epic-1",
    title: str = "Epic",
    properties: dict | None = None,
) -> GraphNode:
    """Create an Epic GraphNode for testing."""
    return GraphNode(
        id=NodeId(value=node_id),
        labels=[NodeLabel(value="Epic")],
        properties=NodeProperties(properties=properties or {}),
        node_type=NodeType(value="Epic"),
        title=NodeTitle(value=title),
    )


def create_story_node(
    node_id: str = "story-1",
    title: str = "Story",
    properties: dict | None = None,
) -> GraphNode:
    """Create a Story GraphNode for testing."""
    return GraphNode(
        id=NodeId(value=node_id),
        labels=[NodeLabel(value="Story")],
        properties=NodeProperties(properties=properties or {}),
        node_type=NodeType(value="Story"),
        title=NodeTitle(value=title),
    )


def create_relationship_edge(
    from_node: GraphNode,
    to_node: GraphNode,
    relationship_type: GraphRelationType = GraphRelationType.HAS_EPIC,
    properties: dict | None = None,
) -> GraphRelationshipEdge:
    """Create a GraphRelationshipEdge for testing."""
    return GraphRelationshipEdge(
        from_node=from_node,
        to_node=to_node,
        relationship_type=relationship_type,
        properties=GraphRelationshipEdgeProperties(properties=properties or {}),
    )


def create_graph_relationships(
    main_node: GraphNode,
    neighbors: list[GraphNode] | None = None,
    relationships: list[GraphRelationshipEdge] | None = None,
) -> GraphRelationships:
    """Create a GraphRelationships aggregate for testing."""
    neighbors_list = neighbors or []
    relationships_list = relationships or []
    return GraphRelationships(
        node=main_node,
        neighbors=GraphNeighbors(nodes=neighbors_list),
        relationships=GraphRelationshipEdges(edges=relationships_list),
    )


class TestGraphRelationshipsAggregateRoot:
    """Tests for GraphRelationships Aggregate Root validation and behavior."""

    def test_create_valid_aggregate(self) -> None:
        """Test creating a valid GraphRelationships aggregate."""
        # Arrange
        main_node = create_project_node(
            node_id="project-1",
            title="Test Project",
            properties={"name": "Test Project"},
        )
        neighbor = create_epic_node(
            node_id="epic-1",
            title="Test Epic",
            properties={"name": "Test Epic"},
        )
        relationship = create_relationship_edge(
            from_node=main_node,
            to_node=neighbor,
            relationship_type=GraphRelationType.HAS_EPIC,
        )

        neighbors = GraphNeighbors(nodes=[neighbor])
        relationships = GraphRelationshipEdges(edges=[relationship])

        # Act
        aggregate = GraphRelationships(
            node=main_node,
            neighbors=neighbors,
            relationships=relationships,
        )

        # Assert
        assert aggregate.node == main_node
        assert aggregate.neighbors == neighbors
        assert aggregate.relationships == relationships

    def test_aggregate_rejects_none_node(self) -> None:
        """Test that aggregate rejects None node."""
        # Arrange
        neighbor = create_epic_node()
        neighbors = GraphNeighbors(nodes=[neighbor])
        relationships = GraphRelationshipEdges(edges=[])

        # Act & Assert
        with pytest.raises(ValueError, match="node cannot be None"):
            GraphRelationships(
                node=None,  # type: ignore
                neighbors=neighbors,
                relationships=relationships,
            )

    def test_aggregate_rejects_none_neighbors(self) -> None:
        """Test that aggregate rejects None neighbors."""
        # Arrange
        main_node = create_project_node()
        relationships = GraphRelationshipEdges(edges=[])

        # Act & Assert
        with pytest.raises(ValueError, match="neighbors cannot be None"):
            GraphRelationships(
                node=main_node,
                neighbors=None,  # type: ignore
                relationships=relationships,
            )

    def test_aggregate_rejects_none_relationships(self) -> None:
        """Test that aggregate rejects None relationships."""
        # Arrange
        main_node = create_project_node()
        neighbors = GraphNeighbors(nodes=[])

        # Act & Assert
        with pytest.raises(ValueError, match="relationships cannot be None"):
            GraphRelationships(
                node=main_node,
                neighbors=neighbors,
                relationships=None,  # type: ignore
            )

    def test_aggregate_validates_relationships_connect_valid_nodes(self) -> None:
        """Test that aggregate validates relationships connect existing nodes."""
        # Arrange
        main_node = create_project_node()
        neighbor = create_epic_node()
        invalid_node = create_story_node(node_id="invalid-1", title="Invalid")

        # Create relationship connecting to invalid node
        invalid_relationship = create_relationship_edge(
            from_node=main_node,
            to_node=invalid_node,  # Not in neighbors
            relationship_type=GraphRelationType.HAS_EPIC,
        )

        neighbors = GraphNeighbors(nodes=[neighbor])
        relationships = GraphRelationshipEdges(edges=[invalid_relationship])

        # Act & Assert
        with pytest.raises(RelationshipError):
            GraphRelationships(
                node=main_node,
                neighbors=neighbors,
                relationships=relationships,
            )

    def test_get_neighbor_by_id_found(self) -> None:
        """Test getting neighbor by ID when found."""
        # Arrange
        main_node = create_project_node()
        neighbor = create_epic_node()
        aggregate = create_graph_relationships(main_node, neighbors=[neighbor])

        # Act
        result = aggregate.get_neighbor_by_id("epic-1")

        # Assert
        assert result == neighbor

    def test_get_neighbor_by_id_not_found(self) -> None:
        """Test getting neighbor by ID when not found."""
        # Arrange
        main_node = create_project_node()
        aggregate = create_graph_relationships(main_node, neighbors=[])

        # Act
        result = aggregate.get_neighbor_by_id("epic-1")

        # Assert
        assert result is None

    def test_get_relationships_for_node(self) -> None:
        """Test getting relationships for a specific node."""
        # Arrange
        main_node = create_project_node()
        neighbor1 = create_epic_node(node_id="epic-1", title="Epic 1")
        neighbor2 = create_epic_node(node_id="epic-2", title="Epic 2")

        rel1 = create_relationship_edge(
            from_node=main_node,
            to_node=neighbor1,
            relationship_type=GraphRelationType.HAS_EPIC,
        )
        rel2 = create_relationship_edge(
            from_node=main_node,
            to_node=neighbor2,
            relationship_type=GraphRelationType.HAS_EPIC,
        )
        rel3 = create_relationship_edge(
            from_node=neighbor1,
            to_node=neighbor2,
            relationship_type=GraphRelationType.RELATES_TO,
        )

        aggregate = create_graph_relationships(
            main_node,
            neighbors=[neighbor1, neighbor2],
            relationships=[rel1, rel2, rel3],
        )

        # Act
        result = aggregate.get_relationships_for_node("project-1")

        # Assert
        assert len(result) == 2
        assert rel1 in result
        assert rel2 in result
        assert rel3 not in result

    def test_get_outgoing_relationships(self) -> None:
        """Test getting outgoing relationships from a node."""
        # Arrange
        main_node = create_project_node()
        neighbor = create_epic_node()

        outgoing = create_relationship_edge(
            from_node=main_node,
            to_node=neighbor,
            relationship_type=GraphRelationType.HAS_EPIC,
        )
        incoming = create_relationship_edge(
            from_node=neighbor,
            to_node=main_node,
            relationship_type=GraphRelationType.RELATES_TO,
        )

        aggregate = create_graph_relationships(
            main_node,
            neighbors=[neighbor],
            relationships=[outgoing, incoming],
        )

        # Act
        result = aggregate.get_outgoing_relationships("project-1")

        # Assert
        assert len(result) == 1
        assert outgoing in result
        assert incoming not in result

    def test_get_incoming_relationships(self) -> None:
        """Test getting incoming relationships to a node."""
        # Arrange
        main_node = create_project_node()
        neighbor = create_epic_node()

        outgoing = create_relationship_edge(
            from_node=main_node,
            to_node=neighbor,
            relationship_type=GraphRelationType.HAS_EPIC,
        )
        incoming = create_relationship_edge(
            from_node=neighbor,
            to_node=main_node,
            relationship_type=GraphRelationType.RELATES_TO,
        )

        aggregate = create_graph_relationships(
            main_node,
            neighbors=[neighbor],
            relationships=[outgoing, incoming],
        )

        # Act
        result = aggregate.get_incoming_relationships("project-1")

        # Assert
        assert len(result) == 1
        assert incoming in result
        assert outgoing not in result

    def test_has_neighbor_true(self) -> None:
        """Test has_neighbor returns True when neighbor exists."""
        # Arrange
        main_node = create_project_node()
        neighbor = create_epic_node()
        aggregate = create_graph_relationships(main_node, neighbors=[neighbor])

        # Act
        result = aggregate.has_neighbor("epic-1")

        # Assert
        assert result is True

    def test_has_neighbor_false(self) -> None:
        """Test has_neighbor returns False when neighbor does not exist."""
        # Arrange
        main_node = create_project_node()
        aggregate = create_graph_relationships(main_node, neighbors=[])

        # Act
        result = aggregate.has_neighbor("epic-1")

        # Assert
        assert result is False

    def test_neighbor_count(self) -> None:
        """Test neighbor_count returns correct count."""
        # Arrange
        main_node = create_project_node()
        neighbor1 = create_epic_node(node_id="epic-1", title="Epic 1")
        neighbor2 = create_epic_node(node_id="epic-2", title="Epic 2")
        aggregate = create_graph_relationships(
            main_node,
            neighbors=[neighbor1, neighbor2],
        )

        # Act
        result = aggregate.neighbor_count()

        # Assert
        assert result == 2

    def test_relationship_count(self) -> None:
        """Test relationship_count returns correct count."""
        # Arrange
        main_node = create_project_node()
        neighbor = create_epic_node()

        rel1 = create_relationship_edge(
            from_node=main_node,
            to_node=neighbor,
            relationship_type=GraphRelationType.HAS_EPIC,
        )
        rel2 = create_relationship_edge(
            from_node=neighbor,
            to_node=main_node,
            relationship_type=GraphRelationType.RELATES_TO,
        )

        aggregate = create_graph_relationships(
            main_node,
            neighbors=[neighbor],
            relationships=[rel1, rel2],
        )

        # Act
        result = aggregate.relationship_count()

        # Assert
        assert result == 2

    def test_str_representation(self) -> None:
        """Test string representation of aggregate."""
        # Arrange
        main_node = create_project_node()
        neighbor = create_epic_node()
        relationship = create_relationship_edge(
            from_node=main_node,
            to_node=neighbor,
            relationship_type=GraphRelationType.HAS_EPIC,
        )

        aggregate = create_graph_relationships(
            main_node,
            neighbors=[neighbor],
            relationships=[relationship],
        )

        # Act
        result = str(aggregate)

        # Assert
        assert "project-1" in result
        assert "1" in result  # 1 neighbor, 1 relationship


class TestGraphRelationshipsFromNeo4jResult:
    """Tests for from_neo4j_result factory method."""

    def test_from_neo4j_result_valid_data(self) -> None:
        """Test building aggregate from valid Neo4j data."""
        # Arrange
        node_data = {
            "id": "project-1",
            "labels": ["Project"],
            "properties": {"name": "Test Project"},
            "title": "Test Project",
        }
        neighbors_data = [
            {
                "node": {
                    "id": "epic-1",
                    "labels": ["Epic"],
                    "properties": {"name": "Test Epic"},
                    "title": "Test Epic",
                },
                "relationships": [
                    {
                        "type": "HAS_EPIC",
                        "from": "project-1",
                        "to": "epic-1",
                        "properties": {},
                    }
                ],
            }
        ]

        # Act
        result = GraphRelationships.from_neo4j_result(
            node_data=node_data,
            neighbors_data=neighbors_data,
            node_type="Project",
        )

        # Assert
        assert result.node.get_id_string() == "project-1"
        assert result.neighbor_count() == 1
        assert result.relationship_count() == 1

    def test_from_neo4j_result_missing_title_raises(self) -> None:
        """Test that missing title raises ValueError."""
        # Arrange
        node_data = {
            "id": "project-1",
            "labels": ["Project"],
            "properties": {"name": "Test Project"},
            # title missing
        }
        neighbors_data = []

        # Act & Assert
        with pytest.raises(ValueError, match="title is required"):
            GraphRelationships.from_neo4j_result(
                node_data=node_data,
                neighbors_data=neighbors_data,
                node_type="Project",
            )

    def test_from_neo4j_result_empty_neighbors(self) -> None:
        """Test building aggregate with no neighbors."""
        # Arrange
        node_data = {
            "id": "project-1",
            "labels": ["Project"],
            "properties": {"name": "Test Project"},
            "title": "Test Project",
        }
        neighbors_data = []

        # Act
        result = GraphRelationships.from_neo4j_result(
            node_data=node_data,
            neighbors_data=neighbors_data,
            node_type="Project",
        )

        # Assert
        assert result.node.get_id_string() == "project-1"
        assert result.neighbor_count() == 0
        assert result.relationship_count() == 0

    def test_from_neo4j_result_skips_neighbor_without_node(self) -> None:
        """Test that neighbors without node data are skipped."""
        # Arrange
        node_data = {
            "id": "project-1",
            "labels": ["Project"],
            "properties": {},
            "title": "Test Project",
        }
        neighbors_data = [
            {
                "node": None,  # Missing node
                "relationships": [],
            }
        ]

        # Act
        result = GraphRelationships.from_neo4j_result(
            node_data=node_data,
            neighbors_data=neighbors_data,
            node_type="Project",
        )

        # Assert
        assert result.neighbor_count() == 0

    def test_from_neo4j_result_skips_neighbor_with_unknown_type(self) -> None:
        """Test that neighbors with unknown types are skipped."""
        # Arrange
        node_data = {
            "id": "project-1",
            "labels": ["Project"],
            "properties": {},
            "title": "Test Project",
        }
        neighbors_data = [
            {
                "node": {
                    "id": "unknown-1",
                    "labels": ["UnknownType"],  # Not in GraphNodeType enum
                    "properties": {},
                    "title": "Unknown",
                },
                "relationships": [],
            }
        ]

        # Act
        result = GraphRelationships.from_neo4j_result(
            node_data=node_data,
            neighbors_data=neighbors_data,
            node_type="Project",
        )

        # Assert
        assert result.neighbor_count() == 0

    def test_from_neo4j_result_skips_duplicate_neighbors(self) -> None:
        """Test that duplicate neighbors are skipped."""
        # Arrange
        node_data = {
            "id": "project-1",
            "labels": ["Project"],
            "properties": {},
            "title": "Test Project",
        }
        neighbors_data = [
            {
                "node": {
                    "id": "epic-1",
                    "epic_id": "epic-1",
                    "labels": ["Epic"],
                    "properties": {},
                    "title": "Epic 1",
                },
                "relationships": [],
            },
            {
                "node": {
                    "id": "epic-1",  # Duplicate
                    "epic_id": "epic-1",
                    "labels": ["Epic"],
                    "properties": {},
                    "title": "Epic 1",
                },
                "relationships": [],
            },
        ]

        # Act
        result = GraphRelationships.from_neo4j_result(
            node_data=node_data,
            neighbors_data=neighbors_data,
            node_type="Project",
        )

        # Assert
        assert result.neighbor_count() == 1

    def test_from_neo4j_result_neighbor_missing_title_raises(self) -> None:
        """Test that neighbor missing title raises ValueError."""
        # Arrange
        node_data = {
            "id": "project-1",
            "labels": ["Project"],
            "properties": {},
            "title": "Test Project",
        }
        neighbors_data = [
            {
                "node": {
                    "id": "epic-1",
                    "epic_id": "epic-1",
                    "labels": ["Epic"],
                    "properties": {},
                    # title missing
                },
                "relationships": [],
            }
        ]

        # Act & Assert
        with pytest.raises(ValueError, match="Neighbor title is required"):
            GraphRelationships.from_neo4j_result(
                node_data=node_data,
                neighbors_data=neighbors_data,
                node_type="Project",
            )

    def test_from_neo4j_result_with_multiple_relationship_types(self) -> None:
        """Test building aggregate with multiple relationship types."""
        # Arrange
        node_data = {
            "id": "story-1",
            "labels": ["Story"],
            "properties": {},
            "title": "Test Story",
        }
        neighbors_data = [
            {
                "node": {
                    "id": "epic-1",
                    "epic_id": "epic-1",
                    "labels": ["Epic"],
                    "properties": {},
                    "title": "Epic",
                },
                "relationships": [
                    {
                        "type": "CONTAINS",
                        "from": "epic-1",
                        "to": "story-1",
                        "properties": {},
                    },
                    {
                        "type": "RELATES_TO",
                        "from": "story-1",
                        "to": "epic-1",
                        "properties": {},
                    },
                ],
            }
        ]

        # Act
        result = GraphRelationships.from_neo4j_result(
            node_data=node_data,
            neighbors_data=neighbors_data,
            node_type="Story",
        )

        # Assert
        assert result.relationship_count() == 2

    def test_from_neo4j_result_skips_invalid_relationships(self) -> None:
        """Test that relationships with missing nodes are skipped."""
        # Arrange
        node_data = {
            "id": "project-1",
            "labels": ["Project"],
            "properties": {},
            "title": "Test Project",
        }
        neighbors_data = [
            {
                "node": {
                    "id": "epic-1",
                    "epic_id": "epic-1",
                    "labels": ["Epic"],
                    "properties": {},
                    "title": "Epic",
                },
                "relationships": [
                    {
                        "type": "HAS_EPIC",
                        "from": "project-1",
                        "to": "invalid-node",  # Node not in aggregate
                        "properties": {},
                    }
                ],
            }
        ]

        # Act
        result = GraphRelationships.from_neo4j_result(
            node_data=node_data,
            neighbors_data=neighbors_data,
            node_type="Project",
        )

        # Assert
        assert result.relationship_count() == 0  # Invalid relationship skipped

    def test_from_neo4j_result_uses_default_ids_for_relationships(self) -> None:
        """Test that relationships use default IDs when not specified."""
        # Arrange
        node_data = {
            "id": "project-1",
            "labels": ["Project"],
            "properties": {},
            "title": "Test Project",
        }
        neighbors_data = [
            {
                "node": {
                    "id": "epic-1",
                    "epic_id": "epic-1",
                    "labels": ["Epic"],
                    "properties": {},
                    "title": "Epic",
                },
                "relationships": [
                    {
                        "type": "HAS_EPIC",
                        # from and to not specified, should use defaults
                        "properties": {},
                    }
                ],
            }
        ]

        # Act
        result = GraphRelationships.from_neo4j_result(
            node_data=node_data,
            neighbors_data=neighbors_data,
            node_type="Project",
        )

        # Assert
        assert result.relationship_count() == 1

    def test_from_neo4j_result_all_node_types(self) -> None:
        """Test building aggregate with all node types."""
        # Arrange
        node_data = {
            "id": "project-1",
            "project_id": "project-1",
            "labels": ["Project"],
            "properties": {},
            "title": "Project",
        }
        neighbors_data = [
            {
                "node": {
                    "id": "epic-1",
                    "epic_id": "epic-1",
                    "labels": ["Epic"],
                    "properties": {},
                    "title": "Epic",
                },
                "relationships": [],
            },
            {
                "node": {
                    "id": "story-1",
                    "story_id": "story-1",
                    "labels": ["Story"],
                    "properties": {},
                    "title": "Story",
                },
                "relationships": [],
            },
            {
                "node": {
                    "id": "task-1",
                    "task_id": "task-1",
                    "labels": ["Task"],
                    "properties": {},
                    "title": "Task",
                },
                "relationships": [],
            },
        ]

        # Act
        result = GraphRelationships.from_neo4j_result(
            node_data=node_data,
            neighbors_data=neighbors_data,
            node_type="Project",
        )

        # Assert
        assert result.neighbor_count() == 3

    def test_from_neo4j_result_handles_empty_relationships_list(self) -> None:
        """Test building aggregate when neighbor has empty relationships list."""
        # Arrange
        node_data = {
            "id": "project-1",
            "labels": ["Project"],
            "properties": {},
            "title": "Test Project",
        }
        neighbors_data = [
            {
                "node": {
                    "id": "epic-1",
                    "epic_id": "epic-1",
                    "labels": ["Epic"],
                    "properties": {},
                    "title": "Epic",
                },
                "relationships": [],  # Empty list
            }
        ]

        # Act
        result = GraphRelationships.from_neo4j_result(
            node_data=node_data,
            neighbors_data=neighbors_data,
            node_type="Project",
        )

        # Assert
        assert result.neighbor_count() == 1
        assert result.relationship_count() == 0

    def test_from_neo4j_result_handles_missing_relationships_key(self) -> None:
        """Test building aggregate when relationships key is missing."""
        # Arrange
        node_data = {
            "id": "project-1",
            "labels": ["Project"],
            "properties": {},
            "title": "Test Project",
        }
        neighbors_data = [
            {
                "node": {
                    "id": "epic-1",
                    "epic_id": "epic-1",
                    "labels": ["Epic"],
                    "properties": {},
                    "title": "Epic",
                },
                # relationships key missing
            }
        ]

        # Act
        result = GraphRelationships.from_neo4j_result(
            node_data=node_data,
            neighbors_data=neighbors_data,
            node_type="Project",
        )

        # Assert
        assert result.neighbor_count() == 1
        assert result.relationship_count() == 0

