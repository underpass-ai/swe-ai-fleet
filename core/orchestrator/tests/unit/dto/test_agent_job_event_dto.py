from core.orchestrator.dto.agent_job_event_dto import AgentJobEventDTO


class TestAgentJobEventDTO:
    def test_to_dict_maps_fields_and_default_component(self) -> None:
        dto = AgentJobEventDTO(
            timestamp="2025-01-01T00:00:00Z",
            sprint_id="SPR-1",
            task_id="TASK-1",
            role="DEV",
            status="running",
            artifacts="/path/to/artifacts",
        )

        as_dict = dto.to_dict()

        assert as_dict == {
            "ts": "2025-01-01T00:00:00Z",
            "sprint_id": "SPR-1",
            "task_id": "TASK-1",
            "role": "DEV",
            "status": "running",
            "artifacts": "/path/to/artifacts",
            "component": "AgentWorker",
        }

    def test_from_dict_roundtrip_with_explicit_component(self) -> None:
        payload = {
            "ts": "2025-01-01T00:00:00Z",
            "sprint_id": "SPR-1",
            "task_id": "TASK-1",
            "role": "QA",
            "status": "completed",
            "artifacts": "s3://bucket/key",
            "component": "CustomWorker",
        }

        dto = AgentJobEventDTO.from_dict(payload)

        assert dto.timestamp == payload["ts"]
        assert dto.sprint_id == payload["sprint_id"]
        assert dto.task_id == payload["task_id"]
        assert dto.role == payload["role"]
        assert dto.status == payload["status"]
        assert dto.artifacts == payload["artifacts"]
        assert dto.component == "CustomWorker"

        assert dto.to_dict() == payload

    def test_from_dict_defaults_component_when_missing(self) -> None:
        payload = {
            "ts": "2025-01-01T00:00:00Z",
            "sprint_id": "SPR-1",
            "task_id": "TASK-1",
            "role": "DEV",
            "status": "queued",
            "artifacts": "none",
        }

        dto = AgentJobEventDTO.from_dict(payload)

        assert dto.component == "AgentWorker"
        assert dto.to_dict()["component"] == "AgentWorker"
