from core.orchestrator.dto.execution_response_dto import ExecutionResponseDTO


class TestExecutionResponseDTOFactories:
    def test_noop_factory_sets_status_and_reason_only(self) -> None:
        dto = ExecutionResponseDTO.noop(reason="no-tasks")

        assert dto.status == "NOOP"
        assert dto.reason == "no-tasks"
        assert dto.task_id is None
        assert dto.artifacts is None
        assert dto.is_noop is True
        assert dto.is_success is False
        assert dto.is_failed is False

        as_dict = dto.to_dict()
        assert as_dict == {"status": "NOOP", "reason": "no-tasks"}

    def test_success_factory_sets_task_and_artifacts(self) -> None:
        dto = ExecutionResponseDTO.success(task_id="TASK-1", artifacts="/path")

        assert dto.status == "SUCCESS"
        assert dto.reason is None
        assert dto.task_id == "TASK-1"
        assert dto.artifacts == "/path"
        assert dto.is_success is True
        assert dto.is_noop is False
        assert dto.is_failed is False

        as_dict = dto.to_dict()
        assert as_dict == {
            "status": "SUCCESS",
            "task_id": "TASK-1",
            "artifacts": "/path",
        }

    def test_failed_factory_sets_task_and_reason(self) -> None:
        dto = ExecutionResponseDTO.failed(task_id="TASK-1", reason="boom")

        assert dto.status == "FAILED"
        assert dto.reason == "boom"
        assert dto.task_id == "TASK-1"
        assert dto.artifacts is None
        assert dto.is_failed is True
        assert dto.is_noop is False
        assert dto.is_success is False

        as_dict = dto.to_dict()
        assert as_dict == {
            "status": "FAILED",
            "reason": "boom",
            "task_id": "TASK-1",
        }


class TestExecutionResponseDTOProperties:
    def test_to_dict_omits_none_fields(self) -> None:
        dto = ExecutionResponseDTO(status="CUSTOM", reason=None, task_id=None, artifacts=None)

        as_dict = dto.to_dict()

        assert as_dict == {"status": "CUSTOM"}
