"""Unit tests for DualWriteReconciliationService.

Following repository rules:
- Mock all dependencies (DualWriteLedgerPort, Neo4jAdapter)
- Test happy path, edge cases, and error handling
- No external dependencies
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from planning.application.services.dual_write_reconciliation_service import (
    DualWriteReconciliationService,
)


class TestDualWriteReconciliationService:
    """Test cases for DualWriteReconciliationService."""

    @pytest.fixture
    def mock_ledger(self) -> AsyncMock:
        """Create a mock dual write ledger port."""
        return AsyncMock()

    @pytest.fixture
    def mock_neo4j(self) -> MagicMock:
        """Create a mock Neo4j adapter."""
        return MagicMock()

    @pytest.fixture
    def service(
        self,
        mock_ledger: AsyncMock,
        mock_neo4j: MagicMock,
    ) -> DualWriteReconciliationService:
        """Create reconciliation service with mocked dependencies."""
        return DualWriteReconciliationService(
            dual_write_ledger=mock_ledger,
            neo4j_adapter=mock_neo4j,
        )

    @pytest.mark.asyncio
    async def test_reconcile_save_story_success(
        self,
        service: DualWriteReconciliationService,
        mock_ledger: AsyncMock,
        mock_neo4j: MagicMock,
    ) -> None:
        """Test successful reconciliation of save_story operation."""
        operation_id = "op-123"
        operation_data = {
            "story_id": "ST-1",
            "epic_id": "EP-1",
            "title": "Test Story",
            "created_by": "user1",
            "initial_state": "DRAFT",
        }

        mock_neo4j.create_story_node = AsyncMock()

        await service.reconcile_operation(
            operation_id=operation_id,
            operation_type="save_story",
            operation_data=operation_data,
        )

        # Verify Neo4j operation was called
        mock_neo4j.create_story_node.assert_awaited_once()
        call_args = mock_neo4j.create_story_node.call_args

        # Verify ledger was marked as completed
        mock_ledger.mark_completed.assert_awaited_once_with(operation_id)

    @pytest.mark.asyncio
    async def test_reconcile_save_task_success(
        self,
        service: DualWriteReconciliationService,
        mock_ledger: AsyncMock,
        mock_neo4j: MagicMock,
    ) -> None:
        """Test successful reconciliation of save_task operation."""
        operation_id = "op-456"
        operation_data = {
            "task_id": "T-1",
            "story_id": "ST-1",
            "status": "todo",  # TaskStatus enum uses lowercase
            "task_type": "feature",  # TaskType enum uses lowercase
            "plan_id": "PLAN-1",
        }

        mock_neo4j.create_task_node = AsyncMock()

        await service.reconcile_operation(
            operation_id=operation_id,
            operation_type="save_task",
            operation_data=operation_data,
        )

        mock_neo4j.create_task_node.assert_awaited_once()
        mock_ledger.mark_completed.assert_awaited_once_with(operation_id)

    @pytest.mark.asyncio
    async def test_reconcile_save_task_with_decision_success(
        self,
        service: DualWriteReconciliationService,
        mock_ledger: AsyncMock,
        mock_neo4j: MagicMock,
    ) -> None:
        """Test successful reconciliation of save_task_with_decision operation."""
        operation_id = "op-789"
        operation_data = {
            "task_id": "T-1",
            "story_id": "ST-1",
            "plan_id": "PLAN-1",
            "status": "todo",  # TaskStatus enum uses lowercase
            "task_type": "feature",  # TaskType enum uses lowercase
            "priority": "HIGH",
            "decision_metadata": {
                "decided_by": "ARCHITECT",
                "decision_reason": "Required for feature",
                "council_feedback": "Approved",
                "source": "BACKLOG_REVIEW",
                "decided_at": "2024-01-01T00:00:00Z",
            },
        }

        mock_neo4j.create_task_node_with_semantic_relationship = AsyncMock()

        await service.reconcile_operation(
            operation_id=operation_id,
            operation_type="save_task_with_decision",
            operation_data=operation_data,
        )

        mock_neo4j.create_task_node_with_semantic_relationship.assert_awaited_once()
        mock_ledger.mark_completed.assert_awaited_once_with(operation_id)

    @pytest.mark.asyncio
    async def test_reconcile_update_story_success(
        self,
        service: DualWriteReconciliationService,
        mock_ledger: AsyncMock,
        mock_neo4j: MagicMock,
    ) -> None:
        """Test successful reconciliation of update_story operation."""
        operation_id = "op-update"
        operation_data = {
            "story_id": "ST-1",
            "new_state": "PO_REVIEW",  # Will be converted to StoryStateEnum.PO_REVIEW
        }

        mock_neo4j.update_story_state = AsyncMock()

        await service.reconcile_operation(
            operation_id=operation_id,
            operation_type="update_story",
            operation_data=operation_data,
        )

        mock_neo4j.update_story_state.assert_awaited_once()
        mock_ledger.mark_completed.assert_awaited_once_with(operation_id)

    @pytest.mark.asyncio
    async def test_reconcile_delete_story_success(
        self,
        service: DualWriteReconciliationService,
        mock_ledger: AsyncMock,
        mock_neo4j: MagicMock,
    ) -> None:
        """Test successful reconciliation of delete_story operation."""
        operation_id = "op-delete"
        operation_data = {
            "story_id": "ST-1",
        }

        mock_neo4j.delete_story_node = AsyncMock()

        await service.reconcile_operation(
            operation_id=operation_id,
            operation_type="delete_story",
            operation_data=operation_data,
        )

        mock_neo4j.delete_story_node.assert_awaited_once()
        mock_ledger.mark_completed.assert_awaited_once_with(operation_id)

    @pytest.mark.asyncio
    async def test_reconcile_unsupported_operation_type(
        self,
        service: DualWriteReconciliationService,
    ) -> None:
        """Test that unsupported operation_type raises ValueError."""
        operation_id = "op-invalid"
        operation_data = {}

        with pytest.raises(ValueError, match="Unsupported operation_type"):
            await service.reconcile_operation(
                operation_id=operation_id,
                operation_type="unsupported_operation",
                operation_data=operation_data,
            )

    @pytest.mark.asyncio
    async def test_reconcile_neo4j_error_records_failure(
        self,
        service: DualWriteReconciliationService,
        mock_ledger: AsyncMock,
        mock_neo4j: MagicMock,
    ) -> None:
        """Test that Neo4j errors are recorded as failures."""
        operation_id = "op-error"
        operation_data = {
            "story_id": "ST-1",
            "epic_id": "EP-1",
            "title": "Test Story",
            "created_by": "user1",
            "initial_state": "DRAFT",  # Will be converted to StoryStateEnum.DRAFT
        }

        # Mock the Neo4j call to raise an error AFTER validation
        # We need to mock the actual Neo4j adapter method
        async def create_story_node_side_effect(*args: Any, **kwargs: Any) -> None:
            raise Exception("Neo4j connection failed")

        mock_neo4j.create_story_node = AsyncMock(side_effect=create_story_node_side_effect)

        with pytest.raises(Exception, match="Neo4j connection failed"):
            await service.reconcile_operation(
                operation_id=operation_id,
                operation_type="save_story",
                operation_data=operation_data,
            )

        # Verify failure was recorded
        mock_ledger.record_failure.assert_awaited_once_with(
            operation_id,
            "Neo4j connection failed",
        )

        # Verify it was NOT marked as completed
        mock_ledger.mark_completed.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_reconcile_save_project_success(
        self,
        service: DualWriteReconciliationService,
        mock_ledger: AsyncMock,
        mock_neo4j: MagicMock,
    ) -> None:
        """Test successful reconciliation of save_project operation."""
        operation_id = "op-project"
        operation_data = {
            "project_id": "PROJ-1",
            "name": "Test Project",
            "status": "ACTIVE",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }

        mock_neo4j.create_project_node = AsyncMock()

        await service.reconcile_operation(
            operation_id=operation_id,
            operation_type="save_project",
            operation_data=operation_data,
        )

        mock_neo4j.create_project_node.assert_awaited_once()
        mock_ledger.mark_completed.assert_awaited_once_with(operation_id)

    @pytest.mark.asyncio
    async def test_reconcile_save_epic_success(
        self,
        service: DualWriteReconciliationService,
        mock_ledger: AsyncMock,
        mock_neo4j: MagicMock,
    ) -> None:
        """Test successful reconciliation of save_epic operation."""
        operation_id = "op-epic"
        operation_data = {
            "epic_id": "EP-1",
            "project_id": "PROJ-1",
            "name": "Test Epic",
            "status": "ACTIVE",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }

        mock_neo4j.create_epic_node = AsyncMock()

        await service.reconcile_operation(
            operation_id=operation_id,
            operation_type="save_epic",
            operation_data=operation_data,
        )

        mock_neo4j.create_epic_node.assert_awaited_once()
        mock_ledger.mark_completed.assert_awaited_once_with(operation_id)

    @pytest.mark.asyncio
    async def test_reconcile_delete_project_success(
        self,
        service: DualWriteReconciliationService,
        mock_ledger: AsyncMock,
        mock_neo4j: MagicMock,
    ) -> None:
        """Test successful reconciliation of delete_project operation."""
        operation_id = "op-delete-proj"
        operation_data = {
            "project_id": "PROJ-1",
        }

        mock_neo4j.delete_project_node = AsyncMock()

        await service.reconcile_operation(
            operation_id=operation_id,
            operation_type="delete_project",
            operation_data=operation_data,
        )

        mock_neo4j.delete_project_node.assert_awaited_once()
        mock_ledger.mark_completed.assert_awaited_once_with(operation_id)

    @pytest.mark.asyncio
    async def test_reconcile_delete_epic_success(
        self,
        service: DualWriteReconciliationService,
        mock_ledger: AsyncMock,
        mock_neo4j: MagicMock,
    ) -> None:
        """Test successful reconciliation of delete_epic operation."""
        operation_id = "op-delete-epic"
        operation_data = {
            "epic_id": "EP-1",
        }

        mock_neo4j.delete_epic_node = AsyncMock()

        await service.reconcile_operation(
            operation_id=operation_id,
            operation_type="delete_epic",
            operation_data=operation_data,
        )

        mock_neo4j.delete_epic_node.assert_awaited_once()
        mock_ledger.mark_completed.assert_awaited_once_with(operation_id)
