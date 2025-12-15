from typing import Any

from services.orchestrator.infrastructure.mappers.deliberate_response_mapper import (
    DeliberateResponseMapper,
)


class MockDeliberationResult:
    def __init__(self, proposal: Any, checks: Any, score: float) -> None:
        self.proposal = proposal
        self.checks = checks
        self.score = score


class MockProposal:
    def __init__(self, author: Any, content: str) -> None:
        self.author = author
        self.content = content


class MockAuthor:
    def __init__(self, agent_id: str, role: str) -> None:
        self.agent_id = agent_id
        self.role = role


class TestDeliberateResponseMapper:
    def test_domain_to_proto_converts_results(self, mocker) -> None:
        mock_pb2 = mocker.MagicMock()
        mock_proto_result = mocker.MagicMock()
        mock_proto_metadata = mocker.MagicMock()
        mock_pb2.DeliberationResult.return_value = mock_proto_result
        mock_pb2.DeliberateResponse.return_value = mocker.MagicMock()

        def mock_domain_checks_converter(checks: Any) -> Any:
            return mocker.MagicMock()

        def mock_deliberation_result_mapper(vo: Any, pb2: Any) -> Any:
            return mock_proto_result

        mocker.patch(
            "services.orchestrator.infrastructure.mappers.deliberate_response_mapper.DeliberationResultMapper.to_proto",
            side_effect=mock_deliberation_result_mapper,
        )
        mocker.patch(
            "services.orchestrator.infrastructure.mappers.deliberate_response_mapper.MetadataMapper.create",
            return_value=mocker.MagicMock(),
        )
        mocker.patch(
            "services.orchestrator.infrastructure.mappers.deliberate_response_mapper.MetadataMapper.to_proto",
            return_value=mock_proto_metadata,
        )

        author = MockAuthor(agent_id="agent-1", role="DEV")
        proposal = MockProposal(author=author, content="proposal content")
        result = MockDeliberationResult(proposal=proposal, checks=mocker.MagicMock(), score=0.95)

        DeliberateResponseMapper.domain_to_proto(
            results=[result],
            duration_ms=1000,
            execution_id="exec-1",
            orchestrator_pb2=mock_pb2,
            domain_checks_converter=mock_domain_checks_converter,
            task_id="task-1",
        )
        mock_pb2.DeliberateResponse.assert_called_once()
        call_kwargs = mock_pb2.DeliberateResponse.call_args.kwargs
        assert call_kwargs["task_id"] == "task-1"
        assert call_kwargs["duration_ms"] == 1000

    def test_domain_to_proto_uses_empty_task_id_when_none(self, mocker) -> None:
        mock_pb2 = mocker.MagicMock()
        mock_pb2.DeliberationResult.return_value = mocker.MagicMock()
        mock_pb2.DeliberateResponse.return_value = mocker.MagicMock()

        mocker.patch(
            "services.orchestrator.infrastructure.mappers.deliberate_response_mapper.DeliberationResultMapper.to_proto",
            return_value=mocker.MagicMock(),
        )
        mocker.patch(
            "services.orchestrator.infrastructure.mappers.deliberate_response_mapper.MetadataMapper.create",
            return_value=mocker.MagicMock(),
        )
        mocker.patch(
            "services.orchestrator.infrastructure.mappers.deliberate_response_mapper.MetadataMapper.to_proto",
            return_value=mocker.MagicMock(),
        )

        author = MockAuthor(agent_id="agent-1", role="DEV")
        proposal = MockProposal(author=author, content="content")
        result = MockDeliberationResult(proposal=proposal, checks=mocker.MagicMock(), score=0.9)

        DeliberateResponseMapper.domain_to_proto(
            results=[result],
            duration_ms=500,
            execution_id="exec-2",
            orchestrator_pb2=mock_pb2,
            domain_checks_converter=lambda x: mocker.MagicMock(),
            task_id=None,
        )

        call_kwargs = mock_pb2.DeliberateResponse.call_args.kwargs
        assert call_kwargs["task_id"] == ""

    def test_domain_to_proto_sets_winner_id_from_first_result(self, mocker) -> None:
        mock_pb2 = mocker.MagicMock()
        mock_proto_result = mocker.MagicMock()
        mock_proto_result.proposal.author_id = "agent-1"
        mock_pb2.DeliberationResult.return_value = mock_proto_result
        mock_pb2.DeliberateResponse.return_value = mocker.MagicMock()

        mocker.patch(
            "services.orchestrator.infrastructure.mappers.deliberate_response_mapper.DeliberationResultMapper.to_proto",
            return_value=mock_proto_result,
        )
        mocker.patch(
            "services.orchestrator.infrastructure.mappers.deliberate_response_mapper.MetadataMapper.create",
            return_value=mocker.MagicMock(),
        )
        mocker.patch(
            "services.orchestrator.infrastructure.mappers.deliberate_response_mapper.MetadataMapper.to_proto",
            return_value=mocker.MagicMock(),
        )

        author = MockAuthor(agent_id="agent-1", role="DEV")
        proposal = MockProposal(author=author, content="content")
        result = MockDeliberationResult(proposal=proposal, checks=mocker.MagicMock(), score=1.0)

        DeliberateResponseMapper.domain_to_proto(
            results=[result],
            duration_ms=100,
            execution_id="exec-3",
            orchestrator_pb2=mock_pb2,
            domain_checks_converter=lambda x: mocker.MagicMock(),
        )

        call_kwargs = mock_pb2.DeliberateResponse.call_args.kwargs
        assert call_kwargs["winner_id"] == "agent-1"

    def test_domain_to_proto_handles_empty_results(self, mocker) -> None:
        mock_pb2 = mocker.MagicMock()
        mock_pb2.DeliberateResponse.return_value = mocker.MagicMock()

        mocker.patch(
            "services.orchestrator.infrastructure.mappers.deliberate_response_mapper.MetadataMapper.create",
            return_value=mocker.MagicMock(),
        )
        mocker.patch(
            "services.orchestrator.infrastructure.mappers.deliberate_response_mapper.MetadataMapper.to_proto",
            return_value=mocker.MagicMock(),
        )

        DeliberateResponseMapper.domain_to_proto(
            results=[],
            duration_ms=0,
            execution_id="exec-4",
            orchestrator_pb2=mock_pb2,
            domain_checks_converter=lambda x: mocker.MagicMock(),
        )

        call_kwargs = mock_pb2.DeliberateResponse.call_args.kwargs
        assert call_kwargs["winner_id"] == ""
