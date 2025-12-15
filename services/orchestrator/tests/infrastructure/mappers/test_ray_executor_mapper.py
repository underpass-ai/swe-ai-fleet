from services.orchestrator.domain.entities import DeliberationStatus, DeliberationSubmission
from services.orchestrator.infrastructure.mappers.ray_executor_mapper import RayExecutorMapper


class MockExecuteDeliberationResponse:
    def __init__(self, deliberation_id: str, status: str, message: str, task_id: str = "") -> None:
        self.deliberation_id = deliberation_id
        self.status = status
        self.message = message
        self.task_id = task_id


class MockGetDeliberationStatusResponse:
    def __init__(self, status: str, error_message: str = "", has_result: bool = False) -> None:
        self.status = status
        self.error_message = error_message
        self._has_result = has_result
        self.result = "result-data" if has_result else None

    def HasField(self, field_name: str) -> bool:  # noqa: N802  # NOSONAR - Mocking protobuf interface (must match HasField naming)
        return field_name == "result" and self._has_result


class TestRayExecutorMapper:
    def test_to_execute_request_builds_protobuf_request(self) -> None:
        agents = [
            {"id": "agent-1", "role": "DEV", "model": "test-model"},
            {"id": "agent-2", "role": "DEV", "model": "test-model", "prompt_template": "template"},
        ]
        constraints = {
            "story_id": "story-1",
            "plan_id": "plan-1",
            "timeout": 600,
            "max_retries": 5,
            "metadata": {"key1": "value1", "key2": "value2"},
        }

        request = RayExecutorMapper.to_execute_request(
            task_id="task-1",
            task_description="Test task",
            role="DEV",
            agents=agents,
            constraints=constraints,
            vllm_url="http://vllm:8000",
            vllm_model="test-model",
        )

        assert request.task_id == "task-1"
        assert request.task_description == "Test task"
        assert request.role == "DEV"
        assert len(request.agents) == 2
        assert request.agents[0].id == "agent-1"
        assert request.agents[0].role == "DEV"
        assert request.constraints.story_id == "story-1"
        assert request.constraints.plan_id == "plan-1"
        assert request.constraints.timeout_seconds == 600
        assert request.constraints.max_retries == 5
        assert request.constraints.metadata["key1"] == "value1"
        assert request.constraints.metadata["key2"] == "value2"

    def test_to_execute_request_handles_missing_metadata(self) -> None:
        constraints = {"story_id": "story-1"}

        request = RayExecutorMapper.to_execute_request(
            task_id="task-1",
            task_description="Test",
            role="DEV",
            agents=[],
            constraints=constraints,
            vllm_url="http://vllm:8000",
            vllm_model="model",
        )

        assert request is not None
        assert request.constraints.story_id == "story-1"

    def test_to_deliberation_submission_converts_response(self) -> None:
        response = MockExecuteDeliberationResponse(
            deliberation_id="delib-123",
            status="submitted",
            message="OK",
            task_id="task-1",
        )

        submission = RayExecutorMapper.to_deliberation_submission(response)

        assert isinstance(submission, DeliberationSubmission)
        assert submission.deliberation_id == "delib-123"
        assert submission.status == "submitted"
        assert submission.message == "OK"
        assert submission.task_id == "task-1"

    def test_to_deliberation_submission_handles_empty_task_id(self) -> None:
        response = MockExecuteDeliberationResponse(
            deliberation_id="delib-123",
            status="submitted",
            message="OK",
            task_id="",
        )

        submission = RayExecutorMapper.to_deliberation_submission(response)  # type: ignore[arg-type]

        assert submission.task_id is None

    def test_to_get_status_request_creates_request(self) -> None:
        request = RayExecutorMapper.to_get_status_request("delib-123")

        assert request.deliberation_id == "delib-123"

    def test_to_deliberation_status_with_result(self) -> None:
        response = MockGetDeliberationStatusResponse(status="done", has_result=True)

        status = RayExecutorMapper.to_deliberation_status("delib-123", response)  # type: ignore[arg-type]

        assert isinstance(status, DeliberationStatus)
        assert status.deliberation_id == "delib-123"
        assert status.status == "done"
        assert status.result == "result-data"
        assert status.error_message is None

    def test_to_deliberation_status_without_result(self) -> None:
        response = MockGetDeliberationStatusResponse(status="pending", has_result=False)

        status = RayExecutorMapper.to_deliberation_status("delib-123", response)  # type: ignore[arg-type]

        assert status.result is None
        assert status.error_message is None

    def test_to_deliberation_status_with_error_message(self) -> None:
        response = MockGetDeliberationStatusResponse(
            status="error",
            error_message="Something went wrong",
            has_result=False,
        )

        status = RayExecutorMapper.to_deliberation_status("delib-123", response)  # type: ignore[arg-type]

        assert status.error_message == "Something went wrong"
