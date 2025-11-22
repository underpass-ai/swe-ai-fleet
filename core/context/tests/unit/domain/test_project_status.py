"""Unit tests for ProjectStatus enum."""


from core.context.domain.project_status import ProjectStatus


class TestProjectStatus:
    """Test suite for ProjectStatus enum."""

    def test_project_status_values(self) -> None:
        """Test that all project status values are correct."""
        assert ProjectStatus.ACTIVE.value == "active"
        assert ProjectStatus.PLANNING.value == "planning"
        assert ProjectStatus.IN_PROGRESS.value == "in_progress"
        assert ProjectStatus.ON_HOLD.value == "on_hold"
        assert ProjectStatus.COMPLETED.value == "completed"
        assert ProjectStatus.ARCHIVED.value == "archived"
        assert ProjectStatus.CANCELLED.value == "cancelled"

    def test_project_status_str(self) -> None:
        """Test string representation."""
        assert str(ProjectStatus.ACTIVE) == "active"
        assert str(ProjectStatus.COMPLETED) == "completed"

    def test_is_terminal_completed(self) -> None:
        """Test is_terminal() for completed status."""
        assert ProjectStatus.COMPLETED.is_terminal() is True

    def test_is_terminal_archived(self) -> None:
        """Test is_terminal() for archived status."""
        assert ProjectStatus.ARCHIVED.is_terminal() is True

    def test_is_terminal_cancelled(self) -> None:
        """Test is_terminal() for cancelled status."""
        assert ProjectStatus.CANCELLED.is_terminal() is True

    def test_is_not_terminal_active(self) -> None:
        """Test is_terminal() for active status."""
        assert ProjectStatus.ACTIVE.is_terminal() is False

    def test_is_not_terminal_in_progress(self) -> None:
        """Test is_terminal() for in_progress status."""
        assert ProjectStatus.IN_PROGRESS.is_terminal() is False

    def test_is_active_work_active(self) -> None:
        """Test is_active_work() for active status."""
        assert ProjectStatus.ACTIVE.is_active_work() is True

    def test_is_active_work_planning(self) -> None:
        """Test is_active_work() for planning status."""
        assert ProjectStatus.PLANNING.is_active_work() is True

    def test_is_active_work_in_progress(self) -> None:
        """Test is_active_work() for in_progress status."""
        assert ProjectStatus.IN_PROGRESS.is_active_work() is True

    def test_is_not_active_work_completed(self) -> None:
        """Test is_active_work() for completed status."""
        assert ProjectStatus.COMPLETED.is_active_work() is False

    def test_is_not_active_work_on_hold(self) -> None:
        """Test is_active_work() for on_hold status."""
        assert ProjectStatus.ON_HOLD.is_active_work() is False

