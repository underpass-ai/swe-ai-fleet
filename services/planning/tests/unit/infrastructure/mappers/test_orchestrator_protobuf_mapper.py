"""Unit tests for OrchestratorProtobufMapper.

Tests the mapper in isolation following hexagonal architecture testing principles.
"""

import pytest

from planning.application.ports.orchestrator_port import (
    DeliberationRequest,
    TaskConstraints,
)
from planning.infrastructure.mappers.orchestrator_protobuf_mapper import (
    OrchestratorProtobufMapper,
)


def test_to_deliberate_request_with_complete_data() -> None:
    """Test mapping from complete DeliberationRequest DTO to protobuf."""
    # Arrange
    request = DeliberationRequest(
        task_id="ceremony-123:story-456:role-ARCHITECT",
        task_description="Review user story for technical feasibility",
        role="ARCHITECT",
        constraints=TaskConstraints(
            rubric="Evaluate architecture and design",
            requirements=("Identify components", "List dependencies"),
            metadata={"priority": "high", "category": "backend"},
            max_iterations=3,
            timeout_seconds=180,
        ),
        rounds=2,
        num_agents=5,
    )

    # Act
    pb_request = OrchestratorProtobufMapper.to_deliberate_request(request)

    # Assert
    assert pb_request.task_description == "Review user story for technical feasibility"
    assert pb_request.role == "ARCHITECT"
    assert pb_request.rounds == 2
    assert pb_request.num_agents == 5

    # Verify constraints
    assert pb_request.constraints.rubric == "Evaluate architecture and design"
    assert list(pb_request.constraints.requirements) == ["Identify components", "List dependencies"]
    assert pb_request.constraints.metadata["priority"] == "high"
    assert pb_request.constraints.metadata["category"] == "backend"
    assert pb_request.constraints.max_iterations == 3
    assert pb_request.constraints.timeout_seconds == 180


def test_to_deliberate_request_without_constraints() -> None:
    """Test mapping without constraints (optional field)."""
    # Arrange
    request = DeliberationRequest(
        task_id="ceremony-123:story-456:role-QA",
        task_description="Simple review task",
        role="QA",
        constraints=None,
        rounds=1,
        num_agents=3,
    )

    # Act
    pb_request = OrchestratorProtobufMapper.to_deliberate_request(request)

    # Assert
    assert pb_request.task_description == "Simple review task"
    assert pb_request.role == "QA"
    assert pb_request.rounds == 1
    assert pb_request.num_agents == 3
    assert not pb_request.HasField("constraints")


def test_to_deliberate_request_with_minimal_constraints() -> None:
    """Test mapping with minimal constraints (using defaults)."""
    # Arrange
    request = DeliberationRequest(
        task_id="ceremony-123:story-456:role-DEVOPS",
        task_description="Review with minimal constraints",
        role="DEVOPS",
        constraints=TaskConstraints(),  # All defaults
        rounds=1,
        num_agents=3,
    )

    # Act
    pb_request = OrchestratorProtobufMapper.to_deliberate_request(request)

    # Assert
    assert pb_request.constraints.rubric == ""
    assert len(pb_request.constraints.requirements) == 0
    assert len(pb_request.constraints.metadata) == 0
    assert pb_request.constraints.max_iterations == 3  # Default from TaskConstraints
    assert pb_request.constraints.timeout_seconds == 180  # Default from TaskConstraints


def test_to_deliberate_request_preserves_all_roles() -> None:
    """Test that all valid roles are correctly mapped."""
    roles = ["ARCHITECT", "QA", "DEVOPS", "DEV", "DATA"]

    for role in roles:
        # Arrange
        request = DeliberationRequest(
            task_id=f"ceremony-123:story-456:role-{role}",
            task_description=f"Task for {role}",
            role=role,
            rounds=1,
            num_agents=3,
        )

        # Act
        pb_request = OrchestratorProtobufMapper.to_deliberate_request(request)

        # Assert
        assert pb_request.role == role


def test_to_deliberate_request_with_empty_metadata() -> None:
    """Test mapping with None metadata (should default to empty dict)."""
    # Arrange
    request = DeliberationRequest(
        task_id="ceremony-123:story-456:role-QA",
        task_description="Task with no metadata",
        role="QA",
        constraints=TaskConstraints(
            rubric="Test rubric",
            requirements=("Req 1",),
            metadata=None,  # Explicitly None
        ),
        rounds=1,
        num_agents=3,
    )

    # Act
    pb_request = OrchestratorProtobufMapper.to_deliberate_request(request)

    # Assert
    assert len(pb_request.constraints.metadata) == 0


def test_to_deliberate_request_with_multiple_requirements() -> None:
    """Test mapping with multiple requirements."""
    # Arrange
    requirements = (
        "Identify all microservices",
        "Define API contracts",
        "Specify data models",
        "Document error handling",
    )
    request = DeliberationRequest(
        task_id="ceremony-123:story-456:role-ARCHITECT",
        task_description="Complex architecture review",
        role="ARCHITECT",
        constraints=TaskConstraints(requirements=requirements),
        rounds=1,
        num_agents=3,
    )

    # Act
    pb_request = OrchestratorProtobufMapper.to_deliberate_request(request)

    # Assert
    assert list(pb_request.constraints.requirements) == list(requirements)


def test_to_deliberate_request_with_variable_rounds_and_agents() -> None:
    """Test mapping with different rounds and num_agents values."""
    test_cases = [
        (1, 3),
        (2, 5),
        (3, 7),
        (1, 1),  # Edge case: single agent, single round
    ]

    for rounds, num_agents in test_cases:
        # Arrange
        request = DeliberationRequest(
            task_id="ceremony-123:story-456:role-DEV",
            task_description="Variable config test",
            role="DEV",
            rounds=rounds,
            num_agents=num_agents,
        )

        # Act
        pb_request = OrchestratorProtobufMapper.to_deliberate_request(request)

        # Assert
        assert pb_request.rounds == rounds
        assert pb_request.num_agents == num_agents


def test_mapper_is_stateless() -> None:
    """Test that mapper does not maintain state between calls."""
    # Arrange
    request1 = DeliberationRequest(
        task_id="ceremony-123:story-456:role-ARCHITECT",
        task_description="First task",
        role="ARCHITECT",
        rounds=1,
        num_agents=3,
    )
    request2 = DeliberationRequest(
        task_id="ceremony-123:story-456:role-QA",
        task_description="Second task",
        role="QA",
        rounds=2,
        num_agents=5,
    )

    # Act
    pb1 = OrchestratorProtobufMapper.to_deliberate_request(request1)
    pb2 = OrchestratorProtobufMapper.to_deliberate_request(request2)

    # Assert - results are independent
    assert pb1.task_description == "First task"
    assert pb2.task_description == "Second task"
    assert pb1.role == "ARCHITECT"
    assert pb2.role == "QA"
    assert pb1.rounds == 1
    assert pb2.rounds == 2

