"""Unit tests for DependencyInference utility class."""

import pytest
from core.shared.domain.value_objects.content.task_description import TaskDescription
from core.shared.domain.value_objects.task_attributes.duration import Duration
from core.shared.domain.value_objects.task_attributes.priority import Priority
from core.shared.domain.value_objects.task_derivation.keyword import Keyword
from planning.domain.value_objects.content.dependency_reason import DependencyReason
from planning.domain.value_objects.content.title import Title
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.task_derivation.dependency_edge import DependencyEdge
from planning.domain.value_objects.task_derivation.dependency_inference import (
    DependencyInference,
)
from planning.domain.value_objects.task_derivation.task_node import TaskNode


@pytest.fixture
def task_a() -> TaskNode:
    """Create task A with 'database' keyword."""
    return TaskNode(
        task_id=TaskId("task-a"),
        title=Title("Create database schema"),
        description=TaskDescription("Create the database schema"),
        keywords=(Keyword("database"), Keyword("schema")),
        estimated_hours=Duration(4),
        priority=Priority(1),
    )


@pytest.fixture
def task_b() -> TaskNode:
    """Create task B with 'api' keyword."""
    return TaskNode(
        task_id=TaskId("task-b"),
        title=Title("Create API endpoints"),
        description=TaskDescription("Create REST API endpoints"),
        keywords=(Keyword("api"), Keyword("endpoints")),
        estimated_hours=Duration(6),
        priority=Priority(2),
    )


@pytest.fixture
def task_c() -> TaskNode:
    """Create task C that mentions 'database' in title."""
    return TaskNode(
        task_id=TaskId("task-c"),
        title=Title("Connect to database"),
        description=TaskDescription("Connect application to database"),
        keywords=(Keyword("connection"),),
        estimated_hours=Duration(2),
        priority=Priority(3),
    )


@pytest.fixture
def task_d() -> TaskNode:
    """Create task D with no matching keywords."""
    return TaskNode(
        task_id=TaskId("task-d"),
        title=Title("Write documentation"),
        description=TaskDescription("Write user documentation"),
        keywords=(Keyword("docs"),),
        estimated_hours=Duration(1),
        priority=Priority(4),
    )


class TestFindMatchingKeyword:
    """Tests for find_matching_keyword method."""

    def test_find_matching_keyword_success(self, task_a: TaskNode, task_c: TaskNode) -> None:
        """Test finding matching keyword when keyword exists in title."""
        result = DependencyInference.find_matching_keyword(task_a, task_c)
        assert result == "database"

    def test_find_matching_keyword_case_insensitive(
        self, task_a: TaskNode
    ) -> None:
        """Test keyword matching is case-insensitive."""
        task_with_uppercase = TaskNode(
            task_id=TaskId("task-upper"),
            title=Title("Create DATABASE connection"),
            description=TaskDescription("Test"),
            keywords=(Keyword("test"),),
            estimated_hours=Duration(1),
            priority=Priority(1),
        )
        result = DependencyInference.find_matching_keyword(task_a, task_with_uppercase)
        assert result == "database"

    def test_find_matching_keyword_no_match(
        self, task_a: TaskNode, task_d: TaskNode
    ) -> None:
        """Test finding keyword when no match exists."""
        result = DependencyInference.find_matching_keyword(task_a, task_d)
        assert result is None

    def test_find_matching_keyword_empty_keywords(self, task_d: TaskNode) -> None:
        """Test finding keyword when source task has no keywords."""
        task_no_keywords = TaskNode(
            task_id=TaskId("task-empty"),
            title=Title("Some task"),
            description=TaskDescription("Test"),
            keywords=(),
            estimated_hours=Duration(1),
            priority=Priority(1),
        )
        result = DependencyInference.find_matching_keyword(task_no_keywords, task_d)
        assert result is None

    def test_find_matching_keyword_multiple_keywords_first_match(
        self, task_c: TaskNode
    ) -> None:
        """Test that first matching keyword is returned."""
        task_multiple = TaskNode(
            task_id=TaskId("task-multi"),
            title=Title("Database and schema setup"),
            description=TaskDescription("Test"),
            keywords=(Keyword("database"), Keyword("schema")),
            estimated_hours=Duration(1),
            priority=Priority(1),
        )
        result = DependencyInference.find_matching_keyword(task_multiple, task_c)
        assert result == "database"  # First match

    def test_find_matching_keyword_partial_match(self) -> None:
        """Test keyword matching with substring matches."""
        task_source = TaskNode(
            task_id=TaskId("task-source"),
            title=Title("Setup database"),
            description=TaskDescription("Test"),
            keywords=(Keyword("data"),),
            estimated_hours=Duration(1),
            priority=Priority(1),
        )
        task_target = TaskNode(
            task_id=TaskId("task-target"),
            title=Title("Create database connection"),
            description=TaskDescription("Test"),
            keywords=(Keyword("test"),),
            estimated_hours=Duration(1),
            priority=Priority(1),
        )
        result = DependencyInference.find_matching_keyword(task_source, task_target)
        assert result == "data"  # "data" is found in "database"


class TestFindKeywordMatch:
    """Tests for find_keyword_match method."""

    def test_find_keyword_match_success(self, task_a: TaskNode, task_c: TaskNode) -> None:
        """Test finding keyword match and creating DependencyEdge."""
        result = DependencyInference.find_keyword_match(task_a, task_c)
        assert result is not None
        assert isinstance(result, DependencyEdge)
        assert result.from_task_id.value == "task-c"
        assert result.to_task_id.value == "task-a"
        assert "database" in result.reason.value

    def test_find_keyword_match_no_match(
        self, task_a: TaskNode, task_d: TaskNode
    ) -> None:
        """Test finding keyword match when no match exists."""
        result = DependencyInference.find_keyword_match(task_a, task_d)
        assert result is None

    def test_find_keyword_match_reason_contains_keyword(
        self, task_a: TaskNode, task_c: TaskNode
    ) -> None:
        """Test that DependencyEdge reason contains the matched keyword."""
        result = DependencyInference.find_keyword_match(task_a, task_c)
        assert result is not None
        assert "database" in result.reason.value
        assert "prerequisite" in result.reason.value


class TestCheckKeywordDependency:
    """Tests for check_keyword_dependency method."""

    def test_check_keyword_dependency_b_to_a(
        self, task_a: TaskNode, task_c: TaskNode
    ) -> None:
        """Test dependency when task_b mentions task_a's keywords."""
        result = DependencyInference.check_keyword_dependency(task_a, task_c)
        assert result is not None
        assert result.from_task_id.value == "task-c"
        assert result.to_task_id.value == "task-a"

    def test_check_keyword_dependency_a_to_b(self) -> None:
        """Test dependency when task_a mentions task_b's keywords (reverse direction)."""
        # task_a has title that mentions task_b's keyword
        task_a = TaskNode(
            task_id=TaskId("task-a"),
            title=Title("Setup database connection"),
            description=TaskDescription("Test"),
            keywords=(Keyword("connection"),),
            estimated_hours=Duration(1),
            priority=Priority(1),
        )
        # task_b has keyword "database"
        task_b = TaskNode(
            task_id=TaskId("task-b"),
            title=Title("Create database"),
            description=TaskDescription("Test"),
            keywords=(Keyword("database"),),
            estimated_hours=Duration(1),
            priority=Priority(1),
        )
        result = DependencyInference.check_keyword_dependency(task_a, task_b)
        assert result is not None
        # task_a mentions "database" from task_b, so task_a depends on task_b
        assert result.from_task_id.value == "task-a"
        assert result.to_task_id.value == "task-b"

    def test_check_keyword_dependency_no_match(
        self, task_a: TaskNode, task_d: TaskNode
    ) -> None:
        """Test dependency check when no keywords match."""
        result = DependencyInference.check_keyword_dependency(task_a, task_d)
        assert result is None

    def test_check_keyword_dependency_bidirectional_both_match(self) -> None:
        """Test dependency check when both directions match (returns first)."""
        task_1 = TaskNode(
            task_id=TaskId("task-1"),
            title=Title("Create database"),
            description=TaskDescription("Test"),
            keywords=(Keyword("database"),),
            estimated_hours=Duration(1),
            priority=Priority(1),
        )
        task_2 = TaskNode(
            task_id=TaskId("task-2"),
            title=Title("Setup database connection"),
            description=TaskDescription("Test"),
            keywords=(Keyword("connection"),),
            estimated_hours=Duration(1),
            priority=Priority(1),
        )
        # task_2 mentions "database" from task_1, so task_2 depends on task_1
        result = DependencyInference.check_keyword_dependency(task_1, task_2)
        assert result is not None
        assert result.from_task_id.value == "task-2"
        assert result.to_task_id.value == "task-1"


class TestInferDependenciesFromKeywords:
    """Tests for infer_dependencies_from_keywords method."""

    def test_infer_dependencies_single_dependency(
        self, task_a: TaskNode, task_c: TaskNode
    ) -> None:
        """Test inferring dependencies with one match."""
        tasks = (task_a, task_c)
        result = DependencyInference.infer_dependencies_from_keywords(tasks)
        assert len(result) == 1
        assert result[0].from_task_id.value == "task-c"
        assert result[0].to_task_id.value == "task-a"

    def test_infer_dependencies_no_dependencies(
        self, task_a: TaskNode, task_d: TaskNode
    ) -> None:
        """Test inferring dependencies when no matches exist."""
        tasks = (task_a, task_d)
        result = DependencyInference.infer_dependencies_from_keywords(tasks)
        assert len(result) == 0

    def test_infer_dependencies_multiple_tasks(
        self, task_a: TaskNode, task_b: TaskNode, task_c: TaskNode, task_d: TaskNode
    ) -> None:
        """Test inferring dependencies with multiple tasks."""
        tasks = (task_a, task_b, task_c, task_d)
        result = DependencyInference.infer_dependencies_from_keywords(tasks)
        # task_c mentions "database" from task_a
        assert len(result) == 1
        assert result[0].from_task_id.value == "task-c"
        assert result[0].to_task_id.value == "task-a"

    def test_infer_dependencies_empty_tuple(self) -> None:
        """Test inferring dependencies with empty task tuple."""
        tasks: tuple[TaskNode, ...] = ()
        result = DependencyInference.infer_dependencies_from_keywords(tasks)
        assert len(result) == 0

    def test_infer_dependencies_single_task(self, task_a: TaskNode) -> None:
        """Test inferring dependencies with single task."""
        tasks = (task_a,)
        result = DependencyInference.infer_dependencies_from_keywords(tasks)
        assert len(result) == 0

    def test_infer_dependencies_multiple_matches(self) -> None:
        """Test inferring dependencies with multiple matches."""
        task_db = TaskNode(
            task_id=TaskId("task-db"),
            title=Title("Create database"),
            description=TaskDescription("Test"),
            keywords=(Keyword("database"),),
            estimated_hours=Duration(1),
            priority=Priority(1),
        )
        task_api = TaskNode(
            task_id=TaskId("task-api"),
            title=Title("Create API"),
            description=TaskDescription("Test"),
            keywords=(Keyword("api"),),
            estimated_hours=Duration(1),
            priority=Priority(1),
        )
        task_db_conn = TaskNode(
            task_id=TaskId("task-db-conn"),
            title=Title("Connect to database"),
            description=TaskDescription("Test"),
            keywords=(Keyword("connection"),),
            estimated_hours=Duration(1),
            priority=Priority(1),
        )
        task_api_impl = TaskNode(
            task_id=TaskId("task-api-impl"),
            title=Title("Implement API endpoints"),
            description=TaskDescription("Test"),
            keywords=(Keyword("endpoints"),),
            estimated_hours=Duration(1),
            priority=Priority(1),
        )
        tasks = (task_db, task_api, task_db_conn, task_api_impl)
        result = DependencyInference.infer_dependencies_from_keywords(tasks)
        # task_db_conn depends on task_db
        # task_api_impl depends on task_api
        assert len(result) == 2
        task_ids = {(dep.from_task_id.value, dep.to_task_id.value) for dep in result}
        assert ("task-db-conn", "task-db") in task_ids
        assert ("task-api-impl", "task-api") in task_ids

    def test_infer_dependencies_returns_tuple(self, task_a: TaskNode, task_c: TaskNode) -> None:
        """Test that result is a tuple (immutable)."""
        tasks = (task_a, task_c)
        result = DependencyInference.infer_dependencies_from_keywords(tasks)
        assert isinstance(result, tuple)
        assert not isinstance(result, list)

    def test_infer_dependencies_dependency_edge_structure(
        self, task_a: TaskNode, task_c: TaskNode
    ) -> None:
        """Test that returned DependencyEdges have correct structure."""
        tasks = (task_a, task_c)
        result = DependencyInference.infer_dependencies_from_keywords(tasks)
        assert len(result) == 1
        edge = result[0]
        assert isinstance(edge, DependencyEdge)
        assert isinstance(edge.from_task_id, TaskId)
        assert isinstance(edge.to_task_id, TaskId)
        assert isinstance(edge.reason, DependencyReason)

    def test_infer_dependencies_reason_format(
        self, task_a: TaskNode, task_c: TaskNode
    ) -> None:
        """Test that DependencyEdge reason has correct format."""
        tasks = (task_a, task_c)
        result = DependencyInference.infer_dependencies_from_keywords(tasks)
        assert len(result) == 1
        reason = result[0].reason.value
        assert "Task references" in reason
        assert "prerequisite" in reason
        assert "database" in reason

