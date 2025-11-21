"""Unit tests for DependencyInferenceHelper."""



from core.shared.domain.value_objects.content.task_description import TaskDescription
from core.shared.domain.value_objects.task_attributes.duration import Duration
from core.shared.domain.value_objects.task_attributes.priority import Priority
from core.shared.domain.value_objects.task_derivation.keyword import Keyword

from task_derivation.domain.value_objects.content.title import Title
from task_derivation.domain.value_objects.identifiers.task_id import TaskId
from task_derivation.domain.value_objects.task_derivation.dependency.dependency_edge import (
    DependencyEdge,
)
from task_derivation.domain.value_objects.task_derivation.dependency.dependency_graph import (
    DependencyInferenceHelper,
)
from task_derivation.domain.value_objects.task_derivation.dependency.task_node import (
    TaskNode,
)


class TestCheckKeywordMatch:
    """Test DependencyInferenceHelper.check_keyword_match method."""

    def test_matches_single_keyword(self):
        """Test matches when source task title contains keyword."""
        # Given: tasks with keywords
        source_task = TaskNode(
            task_id=TaskId("TASK-001"),
            title=Title("Create API using database"),
            description=TaskDescription("Build API"),
            keywords=(),
            estimated_hours=Duration(8),
            priority=Priority(1),
        )
        target_task = TaskNode(
            task_id=TaskId("TASK-002"),
            title=Title("Setup database"),
            description=TaskDescription("Create database"),
            keywords=(Keyword("database"),),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )

        # When: check keyword match
        result = DependencyInferenceHelper.check_keyword_match(
            source_task=source_task,
            target_task=target_task,
            target_keywords=target_task.keywords,
        )

        # Then: dependency created
        assert result is not None
        assert result.from_task_id == source_task.task_id
        assert result.to_task_id == target_task.task_id
        assert "database" in result.reason.value

    def test_matches_multiple_keywords_first_match(self):
        """Test matches first keyword that appears in title."""
        # Given: tasks with multiple keywords
        source_task = TaskNode(
            task_id=TaskId("TASK-001"),
            title=Title("Create API with schema"),
            description=TaskDescription("Build API"),
            keywords=(),
            estimated_hours=Duration(8),
            priority=Priority(1),
        )
        target_task = TaskNode(
            task_id=TaskId("TASK-002"),
            title=Title("Setup database"),
            description=TaskDescription("Create database"),
            keywords=(Keyword("database"), Keyword("schema")),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )

        # When: check keyword match
        result = DependencyInferenceHelper.check_keyword_match(
            source_task=source_task,
            target_task=target_task,
            target_keywords=target_task.keywords,
        )

        # Then: dependency created with first matching keyword
        assert result is not None
        assert result.from_task_id == source_task.task_id
        assert result.to_task_id == target_task.task_id

    def test_no_match_when_keyword_not_in_title(self):
        """Test returns None when no keywords match."""
        # Given: tasks with non-matching keywords
        source_task = TaskNode(
            task_id=TaskId("TASK-001"),
            title=Title("Create API"),
            description=TaskDescription("Build API"),
            keywords=(),
            estimated_hours=Duration(8),
            priority=Priority(1),
        )
        target_task = TaskNode(
            task_id=TaskId("TASK-002"),
            title=Title("Setup database"),
            description=TaskDescription("Create database"),
            keywords=(Keyword("database"),),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )

        # When: check keyword match
        result = DependencyInferenceHelper.check_keyword_match(
            source_task=source_task,
            target_task=target_task,
            target_keywords=target_task.keywords,
        )

        # Then: no dependency created
        assert result is None

    def test_no_match_when_empty_keywords(self):
        """Test returns None when target has no keywords."""
        # Given: tasks with empty keywords
        source_task = TaskNode(
            task_id=TaskId("TASK-001"),
            title=Title("Create API"),
            description=TaskDescription("Build API"),
            keywords=(),
            estimated_hours=Duration(8),
            priority=Priority(1),
        )
        target_task = TaskNode(
            task_id=TaskId("TASK-002"),
            title=Title("Setup database"),
            description=TaskDescription("Create database"),
            keywords=(),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )

        # When: check keyword match
        result = DependencyInferenceHelper.check_keyword_match(
            source_task=source_task,
            target_task=target_task,
            target_keywords=target_task.keywords,
        )

        # Then: no dependency created
        assert result is None

    def test_match_is_case_insensitive(self):
        """Test keyword matching is case-insensitive."""
        # Given: tasks with different case
        source_task = TaskNode(
            task_id=TaskId("TASK-001"),
            title=Title("Create API using DATABASE"),
            description=TaskDescription("Build API"),
            keywords=(),
            estimated_hours=Duration(8),
            priority=Priority(1),
        )
        target_task = TaskNode(
            task_id=TaskId("TASK-002"),
            title=Title("Setup database"),
            description=TaskDescription("Create database"),
            keywords=(Keyword("database"),),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )

        # When: check keyword match
        result = DependencyInferenceHelper.check_keyword_match(
            source_task=source_task,
            target_task=target_task,
            target_keywords=target_task.keywords,
        )

        # Then: dependency created (case-insensitive match)
        assert result is not None


class TestFindDependencyBetweenTasks:
    """Test DependencyInferenceHelper.find_dependency_between_tasks method."""

    def test_finds_dependency_when_task_b_mentions_task_a_keywords(self):
        """Test finds dependency when task_b mentions task_a's keywords."""
        # Given: tasks where task_b mentions task_a's keywords
        task_a = TaskNode(
            task_id=TaskId("TASK-001"),
            title=Title("Setup database"),
            description=TaskDescription("Create database"),
            keywords=(Keyword("database"),),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )
        task_b = TaskNode(
            task_id=TaskId("TASK-002"),
            title=Title("Create API using database"),
            description=TaskDescription("Build API"),
            keywords=(),
            estimated_hours=Duration(8),
            priority=Priority(1),
        )

        # When: find dependency
        result = DependencyInferenceHelper.find_dependency_between_tasks(task_a, task_b)

        # Then: dependency found (task_b depends on task_a)
        assert result is not None
        assert result.from_task_id == task_b.task_id
        assert result.to_task_id == task_a.task_id

    def test_finds_dependency_when_task_a_mentions_task_b_keywords(self):
        """Test finds dependency when task_a mentions task_b's keywords."""
        # Given: tasks where task_a mentions task_b's keywords
        task_a = TaskNode(
            task_id=TaskId("TASK-001"),
            title=Title("Create API using schema"),
            description=TaskDescription("Build API"),
            keywords=(),
            estimated_hours=Duration(8),
            priority=Priority(1),
        )
        task_b = TaskNode(
            task_id=TaskId("TASK-002"),
            title=Title("Setup database schema"),
            description=TaskDescription("Create schema"),
            keywords=(Keyword("schema"),),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )

        # When: find dependency
        result = DependencyInferenceHelper.find_dependency_between_tasks(task_a, task_b)

        # Then: dependency found (task_a depends on task_b)
        assert result is not None
        assert result.from_task_id == task_a.task_id
        assert result.to_task_id == task_b.task_id

    def test_prefers_task_b_mentions_task_a_over_reverse(self):
        """Test prefers dependency where task_b mentions task_a's keywords."""
        # Given: tasks where both mention each other's keywords
        task_a = TaskNode(
            task_id=TaskId("TASK-001"),
            title=Title("Setup database"),
            description=TaskDescription("Create database"),
            keywords=(Keyword("database"),),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )
        task_b = TaskNode(
            task_id=TaskId("TASK-002"),
            title=Title("Create API using database"),
            description=TaskDescription("Build API with database"),
            keywords=(Keyword("api"),),
            estimated_hours=Duration(8),
            priority=Priority(1),
        )

        # When: find dependency
        result = DependencyInferenceHelper.find_dependency_between_tasks(task_a, task_b)

        # Then: dependency found (task_b depends on task_a - first check wins)
        assert result is not None
        assert result.from_task_id == task_b.task_id
        assert result.to_task_id == task_a.task_id

    def test_returns_none_when_no_dependency_found(self):
        """Test returns None when no keywords match."""
        # Given: tasks with no matching keywords
        task_a = TaskNode(
            task_id=TaskId("TASK-001"),
            title=Title("Setup database"),
            description=TaskDescription("Create database"),
            keywords=(Keyword("database"),),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )
        task_b = TaskNode(
            task_id=TaskId("TASK-002"),
            title=Title("Create API"),
            description=TaskDescription("Build API"),
            keywords=(Keyword("api"),),
            estimated_hours=Duration(8),
            priority=Priority(1),
        )

        # When: find dependency
        result = DependencyInferenceHelper.find_dependency_between_tasks(task_a, task_b)

        # Then: no dependency found
        assert result is None

    def test_returns_none_when_both_tasks_have_empty_keywords(self):
        """Test returns None when both tasks have empty keywords."""
        # Given: tasks with empty keywords
        task_a = TaskNode(
            task_id=TaskId("TASK-001"),
            title=Title("Setup database"),
            description=TaskDescription("Create database"),
            keywords=(),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )
        task_b = TaskNode(
            task_id=TaskId("TASK-002"),
            title=Title("Create API"),
            description=TaskDescription("Build API"),
            keywords=(),
            estimated_hours=Duration(8),
            priority=Priority(1),
        )

        # When: find dependency
        result = DependencyInferenceHelper.find_dependency_between_tasks(task_a, task_b)

        # Then: no dependency found
        assert result is None


class TestInferDependenciesFromKeywords:
    """Test DependencyInferenceHelper.infer_dependencies_from_keywords method."""

    def test_infers_no_dependencies_for_single_task(self):
        """Test infers no dependencies for single task."""
        # Given: single task
        task = TaskNode(
            task_id=TaskId("TASK-001"),
            title=Title("Setup database"),
            description=TaskDescription("Create database"),
            keywords=(Keyword("database"),),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )

        # When: infer dependencies
        result = DependencyInferenceHelper.infer_dependencies_from_keywords((task,))

        # Then: no dependencies
        assert len(result) == 0

    def test_infers_no_dependencies_when_no_keyword_matches(self):
        """Test infers no dependencies when keywords don't match."""
        # Given: tasks with non-matching keywords
        task1 = TaskNode(
            task_id=TaskId("TASK-001"),
            title=Title("Setup database"),
            description=TaskDescription("Create database"),
            keywords=(Keyword("database"),),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )
        task2 = TaskNode(
            task_id=TaskId("TASK-002"),
            title=Title("Create API"),
            description=TaskDescription("Build API"),
            keywords=(Keyword("api"),),
            estimated_hours=Duration(8),
            priority=Priority(1),
        )

        # When: infer dependencies
        result = DependencyInferenceHelper.infer_dependencies_from_keywords((task1, task2))

        # Then: no dependencies
        assert len(result) == 0

    def test_infers_single_dependency_for_two_tasks(self):
        """Test infers single dependency when keyword matches."""
        # Given: tasks where task2 mentions task1's keywords
        task1 = TaskNode(
            task_id=TaskId("TASK-001"),
            title=Title("Setup database"),
            description=TaskDescription("Create database"),
            keywords=(Keyword("database"),),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )
        task2 = TaskNode(
            task_id=TaskId("TASK-002"),
            title=Title("Create API using database"),
            description=TaskDescription("Build API"),
            keywords=(),
            estimated_hours=Duration(8),
            priority=Priority(1),
        )

        # When: infer dependencies
        result = DependencyInferenceHelper.infer_dependencies_from_keywords((task1, task2))

        # Then: single dependency
        assert len(result) == 1
        assert result[0].from_task_id == task2.task_id
        assert result[0].to_task_id == task1.task_id

    def test_infers_multiple_dependencies_for_three_tasks(self):
        """Test infers multiple dependencies for multiple tasks."""
        # Given: tasks with multiple dependencies
        task1 = TaskNode(
            task_id=TaskId("TASK-001"),
            title=Title("Setup database"),
            description=TaskDescription("Create database"),
            keywords=(Keyword("database"),),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )
        task2 = TaskNode(
            task_id=TaskId("TASK-002"),
            title=Title("Create API using database"),
            description=TaskDescription("Build API"),
            keywords=(Keyword("api"),),
            estimated_hours=Duration(8),
            priority=Priority(1),
        )
        task3 = TaskNode(
            task_id=TaskId("TASK-003"),
            title=Title("Create frontend using API"),
            description=TaskDescription("Build frontend"),
            keywords=(),
            estimated_hours=Duration(12),
            priority=Priority(1),
        )

        # When: infer dependencies
        result = DependencyInferenceHelper.infer_dependencies_from_keywords((task1, task2, task3))

        # Then: multiple dependencies
        assert len(result) >= 2
        # task2 depends on task1 (database keyword)
        assert any(
            dep.from_task_id == task2.task_id and dep.to_task_id == task1.task_id
            for dep in result
        )
        # task3 depends on task2 (api keyword)
        assert any(
            dep.from_task_id == task3.task_id and dep.to_task_id == task2.task_id
            for dep in result
        )

    def test_checks_only_ordered_pairs(self):
        """Test only checks pairs in order (avoids duplicate checks)."""
        # Given: tasks where both mention each other's keywords
        task1 = TaskNode(
            task_id=TaskId("TASK-001"),
            title=Title("Setup database"),
            description=TaskDescription("Create database"),
            keywords=(Keyword("database"),),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )
        task2 = TaskNode(
            task_id=TaskId("TASK-002"),
            title=Title("Create API using database"),
            description=TaskDescription("Build API with database"),
            keywords=(Keyword("api"),),
            estimated_hours=Duration(8),
            priority=Priority(1),
        )

        # When: infer dependencies
        result = DependencyInferenceHelper.infer_dependencies_from_keywords((task1, task2))

        # Then: only one dependency (task2 depends on task1 - first match wins)
        assert len(result) == 1
        assert result[0].from_task_id == task2.task_id
        assert result[0].to_task_id == task1.task_id

    def test_returns_empty_tuple_for_empty_tasks(self):
        """Test returns empty tuple for empty task list."""
        # When: infer dependencies from empty list
        result = DependencyInferenceHelper.infer_dependencies_from_keywords(())

        # Then: empty tuple
        assert result == ()

    def test_returns_tuple_type(self):
        """Test returns tuple type (immutable)."""
        # Given: tasks
        task1 = TaskNode(
            task_id=TaskId("TASK-001"),
            title=Title("Setup database"),
            description=TaskDescription("Create database"),
            keywords=(Keyword("database"),),
            estimated_hours=Duration(4),
            priority=Priority(1),
        )
        task2 = TaskNode(
            task_id=TaskId("TASK-002"),
            title=Title("Create API using database"),
            description=TaskDescription("Build API"),
            keywords=(),
            estimated_hours=Duration(8),
            priority=Priority(1),
        )

        # When: infer dependencies
        result = DependencyInferenceHelper.infer_dependencies_from_keywords((task1, task2))

        # Then: returns tuple
        assert isinstance(result, tuple)
        assert len(result) == 1
        assert isinstance(result[0], DependencyEdge)

