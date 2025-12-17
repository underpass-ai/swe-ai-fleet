from typing import Any

from services.orchestrator.infrastructure.mappers.orchestrate_response_mapper import (
    OrchestrateResponseMapper,
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


class TestOrchestrateResponseMapper:
    def test_domain_to_proto_converts_winner_and_candidates(self, mocker) -> None:
        mock_pb2 = mocker.MagicMock()
        mock_proto_winner = mocker.MagicMock()
        mock_proto_candidate = mocker.MagicMock()
        mock_proto_metadata = mocker.MagicMock()
        mock_pb2.DeliberationResult.return_value = mock_proto_winner
        mock_pb2.OrchestrateResponse.return_value = mocker.MagicMock()

        def mock_deliberation_result_mapper(vo: Any, pb2: Any) -> Any:
            return mock_proto_winner if vo.rank == 1 else mock_proto_candidate

        mocker.patch(
            "services.orchestrator.infrastructure.mappers.orchestrate_response_mapper.DeliberationResultMapper.to_proto",
            side_effect=mock_deliberation_result_mapper,
        )
        mocker.patch(
            "services.orchestrator.infrastructure.mappers.orchestrate_response_mapper.MetadataMapper.create",
            return_value=mocker.MagicMock(),
        )
        mocker.patch(
            "services.orchestrator.infrastructure.mappers.orchestrate_response_mapper.MetadataMapper.to_proto",
            return_value=mock_proto_metadata,
        )

        author_winner = MockAuthor(agent_id="agent-1", role="DEV")
        proposal_winner = MockProposal(author=author_winner, content="winner")
        winner = MockDeliberationResult(proposal=proposal_winner, checks=mocker.MagicMock(), score=1.0)

        candidates = [
            {
                "proposal": {
                    "author": MockAuthor(agent_id="agent-2", role="QA"),
                    "content": "candidate-1",
                },
                "checks": mocker.MagicMock(),
                "score": 0.9,
            },
        ]

        result = {"winner": winner, "candidates": candidates}

        OrchestrateResponseMapper.domain_to_proto(
            result=result,
            task_id="task-1",
            duration_ms=2000,
            execution_id="exec-1",
            orchestrator_pb2=mock_pb2,
            domain_checks_converter=lambda x: mocker.MagicMock(),
        )
        mock_pb2.OrchestrateResponse.assert_called_once()
        call_kwargs = mock_pb2.OrchestrateResponse.call_args.kwargs
        assert call_kwargs["execution_id"] == "exec-1"
        assert call_kwargs["duration_ms"] == 2000
        assert call_kwargs["winner"] is mock_proto_winner
        assert len(call_kwargs["candidates"]) == 1

    def test_domain_to_proto_handles_empty_candidates(self, mocker) -> None:
        mock_pb2 = mocker.MagicMock()
        mock_proto_winner = mocker.MagicMock()
        mock_pb2.DeliberationResult.return_value = mock_proto_winner
        mock_pb2.OrchestrateResponse.return_value = mocker.MagicMock()

        mocker.patch(
            "services.orchestrator.infrastructure.mappers.orchestrate_response_mapper.DeliberationResultMapper.to_proto",
            return_value=mock_proto_winner,
        )
        mocker.patch(
            "services.orchestrator.infrastructure.mappers.orchestrate_response_mapper.MetadataMapper.create",
            return_value=mocker.MagicMock(),
        )
        mocker.patch(
            "services.orchestrator.infrastructure.mappers.orchestrate_response_mapper.MetadataMapper.to_proto",
            return_value=mocker.MagicMock(),
        )

        author = MockAuthor(agent_id="agent-1", role="DEV")
        proposal = MockProposal(author=author, content="winner")
        winner = MockDeliberationResult(proposal=proposal, checks=mocker.MagicMock(), score=1.0)

        result = {"winner": winner, "candidates": []}

        OrchestrateResponseMapper.domain_to_proto(
            result=result,
            task_id="task-1",
            duration_ms=1000,
            execution_id="exec-2",
            orchestrator_pb2=mock_pb2,
            domain_checks_converter=lambda x: mocker.MagicMock(),
        )

        call_kwargs = mock_pb2.OrchestrateResponse.call_args.kwargs
        assert call_kwargs["candidates"] == []
