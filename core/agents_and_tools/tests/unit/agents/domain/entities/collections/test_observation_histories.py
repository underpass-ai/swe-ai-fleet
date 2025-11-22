"""Unit tests for ObservationHistories collection."""

from core.agents_and_tools.agents.domain.entities.collections.observation_histories import (
    ObservationHistories,
)
from core.agents_and_tools.agents.domain.entities.core.execution_step import ExecutionStep


class TestObservationHistoriesCreation:
    """Test ObservationHistories collection creation."""

    def test_create_empty_histories(self):
        """Test creating empty observation histories collection."""
        histories = ObservationHistories()

        assert histories.observations == []
        assert histories.count() == 0


class TestObservationHistoriesAdd:
    """Test ObservationHistories.add() method."""

    def test_add_successful_observation(self):
        """Test adding successful observation."""
        histories = ObservationHistories()
        step = ExecutionStep(tool="files", operation="read_file")
        result = {"content": "test"}

        histories.add(iteration=1, action=step, result=result, success=True)

        assert histories.count() == 1
        obs = histories.observations[0]
        assert obs.iteration == 1
        assert obs.action == step
        assert obs.result == result
        assert obs.success is True

    def test_add_failed_observation(self):
        """Test adding failed observation."""
        histories = ObservationHistories()
        step = ExecutionStep(tool="files", operation="read_file")

        histories.add(iteration=1, action=step, result={}, success=False, error="Error")

        obs = histories.observations[0]
        assert obs.success is False
        assert obs.error == "Error"


class TestObservationHistoriesGetAll:
    """Test ObservationHistories.get_all() method."""

    def test_get_all_returns_all_observations(self):
        """Test get_all returns all observations."""
        histories = ObservationHistories()
        step1 = ExecutionStep(tool="files", operation="read_file")
        step2 = ExecutionStep(tool="git", operation="commit")

        histories.add(iteration=1, action=step1, result={}, success=True)
        histories.add(iteration=2, action=step2, result={}, success=True)

        all_obs = histories.get_all()

        assert len(all_obs) == 2


class TestObservationHistoriesGetLast:
    """Test ObservationHistories.get_last() method."""

    def test_get_last_returns_last_observation(self):
        """Test get_last returns last observation."""
        histories = ObservationHistories()
        step1 = ExecutionStep(tool="files", operation="read_file")
        step2 = ExecutionStep(tool="git", operation="commit")

        histories.add(iteration=1, action=step1, result={}, success=True)
        histories.add(iteration=2, action=step2, result={}, success=True)

        last = histories.get_last()

        assert last is not None
        assert last.iteration == 2
        assert last.action.tool == "git"

    def test_get_last_returns_none_when_empty(self):
        """Test get_last returns None when empty."""
        histories = ObservationHistories()

        last = histories.get_last()

        assert last is None


class TestObservationHistoriesGetLastN:
    """Test ObservationHistories.get_last_n() method."""

    def test_get_last_n_returns_last_n_observations(self):
        """Test get_last_n returns last n observations."""
        histories = ObservationHistories()
        for i in range(5):
            step = ExecutionStep(tool="files", operation="read_file")
            histories.add(iteration=i + 1, action=step, result={}, success=True)

        last_3 = histories.get_last_n(3)

        assert len(last_3) == 3
        assert last_3[0].iteration == 3
        assert last_3[2].iteration == 5

    def test_get_last_n_returns_all_when_n_exceeds_count(self):
        """Test get_last_n returns all when n exceeds count."""
        histories = ObservationHistories()
        step = ExecutionStep(tool="files", operation="read_file")
        histories.add(iteration=1, action=step, result={}, success=True)

        last_5 = histories.get_last_n(5)

        assert len(last_5) == 1


class TestObservationHistoriesGetSuccessful:
    """Test ObservationHistories.get_successful() method."""

    def test_get_successful_returns_only_successful(self):
        """Test get_successful returns only successful observations."""
        histories = ObservationHistories()
        step = ExecutionStep(tool="files", operation="read_file")

        histories.add(iteration=1, action=step, result={}, success=True)
        histories.add(iteration=2, action=step, result={}, success=False)
        histories.add(iteration=3, action=step, result={}, success=True)

        successful = histories.get_successful()

        assert len(successful) == 2
        assert all(obs.success for obs in successful)


class TestObservationHistoriesGetFailed:
    """Test ObservationHistories.get_failed() method."""

    def test_get_failed_returns_only_failed(self):
        """Test get_failed returns only failed observations."""
        histories = ObservationHistories()
        step = ExecutionStep(tool="files", operation="read_file")

        histories.add(iteration=1, action=step, result={}, success=True)
        histories.add(iteration=2, action=step, result={}, success=False)
        histories.add(iteration=3, action=step, result={}, success=False)

        failed = histories.get_failed()

        assert len(failed) == 2
        assert all(not obs.success for obs in failed)


class TestObservationHistoriesCount:
    """Test ObservationHistories.count() method."""

    def test_count_returns_correct_number(self):
        """Test count returns correct number."""
        histories = ObservationHistories()
        step = ExecutionStep(tool="files", operation="read_file")

        assert histories.count() == 0

        histories.add(iteration=1, action=step, result={}, success=True)
        assert histories.count() == 1

