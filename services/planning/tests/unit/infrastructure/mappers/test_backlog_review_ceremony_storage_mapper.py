"""Unit tests for BacklogReviewCeremonyStorageMapper."""

from datetime import UTC, datetime

import pytest
from planning.domain.entities.backlog_review_ceremony import BacklogReviewCeremony
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.content.brief import Brief
from planning.domain.value_objects.content.title import Title
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.review.plan_preliminary import PlanPreliminary
from planning.domain.value_objects.review.story_review_result import StoryReviewResult
from planning.domain.value_objects.statuses.backlog_review_ceremony_status import (
    BacklogReviewCeremonyStatus,
    BacklogReviewCeremonyStatusEnum,
)
from planning.domain.value_objects.statuses.review_approval_status import (
    ReviewApprovalStatus,
    ReviewApprovalStatusEnum,
)
from planning.infrastructure.mappers.backlog_review_ceremony_storage_mapper import (
    BacklogReviewCeremonyStorageMapper,
)


@pytest.fixture
def sample_plan_preliminary():
    """Create sample PlanPreliminary."""
    return PlanPreliminary(
        title=Title("Test Plan"),
        description=Brief("Test description"),
        acceptance_criteria=("Criterion 1", "Criterion 2"),
        technical_notes="Technical notes",
        roles=("ARCHITECT", "QA"),
        estimated_complexity="MEDIUM",
        dependencies=("dep1", "dep2"),
        tasks_outline=("Task 1", "Task 2"),
    )


@pytest.fixture
def sample_review_result(sample_plan_preliminary):
    """Create sample StoryReviewResult."""
    return StoryReviewResult(
        story_id=StoryId("ST-001"),
        plan_preliminary=sample_plan_preliminary,
        architect_feedback="Architect feedback",
        qa_feedback="QA feedback",
        devops_feedback="DevOps feedback",
        recommendations=("Rec 1", "Rec 2"),
        approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
        reviewed_at=datetime.now(UTC),
        agent_deliberations=(),
    )


@pytest.fixture
def sample_ceremony(sample_review_result):
    """Create sample BacklogReviewCeremony."""
    now = datetime.now(UTC)
    return BacklogReviewCeremony(
        ceremony_id=BacklogReviewCeremonyId("BRC-001"),
        created_by=UserName("test-po"),
        story_ids=(StoryId("ST-001"), StoryId("ST-002")),
        status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.REVIEWING),
        created_at=now,
        updated_at=now,
        started_at=now,
        completed_at=None,
        review_results=(sample_review_result,),
    )


def test_to_neo4j_dict(sample_ceremony):
    """Test conversion of BacklogReviewCeremony to Neo4j dict."""
    result = BacklogReviewCeremonyStorageMapper.to_neo4j_dict(sample_ceremony)

    assert result["ceremony_id"] == "BRC-001"
    assert result["created_by"] == "test-po"
    assert result["status"] == "REVIEWING"
    assert result["story_count"] == 2
    assert "review_results_json" in result
    assert result["created_at"] == sample_ceremony.created_at.isoformat()
    assert result["updated_at"] == sample_ceremony.updated_at.isoformat()
    assert result["started_at"] == sample_ceremony.started_at.isoformat()
    assert result["completed_at"] is None


def test_to_neo4j_dict_with_completed_at(sample_ceremony):
    """Test conversion with completed_at set."""
    completed_at = datetime.now(UTC)
    ceremony = sample_ceremony.complete(completed_at)

    result = BacklogReviewCeremonyStorageMapper.to_neo4j_dict(ceremony)

    assert result["completed_at"] == completed_at.isoformat()


def test_to_neo4j_dict_without_started_at(sample_ceremony):
    """Test conversion without started_at."""
    from planning.domain.value_objects.statuses.backlog_review_ceremony_status import (
        BacklogReviewCeremonyStatus,
        BacklogReviewCeremonyStatusEnum,
    )

    # Create ceremony in DRAFT state (doesn't require started_at)
    ceremony = BacklogReviewCeremony(
        ceremony_id=sample_ceremony.ceremony_id,
        created_by=sample_ceremony.created_by,
        story_ids=sample_ceremony.story_ids,
        status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT),
        created_at=sample_ceremony.created_at,
        updated_at=sample_ceremony.updated_at,
        started_at=None,
        completed_at=None,
        review_results=sample_ceremony.review_results,
    )

    result = BacklogReviewCeremonyStorageMapper.to_neo4j_dict(ceremony)

    assert result["started_at"] is None


def test_from_neo4j_dict(sample_ceremony):
    """Test conversion from Neo4j dict to BacklogReviewCeremony."""
    neo4j_dict = BacklogReviewCeremonyStorageMapper.to_neo4j_dict(sample_ceremony)
    story_ids = [sid.value for sid in sample_ceremony.story_ids]
    review_results_json = neo4j_dict["review_results_json"]

    result = BacklogReviewCeremonyStorageMapper.from_neo4j_dict(
        data=neo4j_dict,
        story_ids=tuple(story_ids),
        review_results_json=review_results_json,
        po_approvals=None,
    )

    assert result.ceremony_id == sample_ceremony.ceremony_id
    assert result.created_by == sample_ceremony.created_by
    assert result.story_ids == sample_ceremony.story_ids
    assert result.status == sample_ceremony.status
    assert len(result.review_results) == 1
    assert result.review_results[0].story_id == StoryId("ST-001")


def test_from_neo4j_dict_with_po_approvals(sample_ceremony):
    """Test conversion from Neo4j dict with po_approvals from Valkey."""
    neo4j_dict = BacklogReviewCeremonyStorageMapper.to_neo4j_dict(sample_ceremony)
    story_ids = [sid.value for sid in sample_ceremony.story_ids]
    review_results_json = neo4j_dict["review_results_json"]

    po_approvals = {
        "ST-001": {
            "po_notes": "Approved with notes",
            "approved_by": "po-user",
            "approved_at": datetime.now(UTC).isoformat(),
            "po_concerns": "Some concerns",
            "priority_adjustment": "HIGH",
            "po_priority_reason": "Critical",
        }
    }

    result = BacklogReviewCeremonyStorageMapper.from_neo4j_dict(
        data=neo4j_dict,
        story_ids=tuple(story_ids),
        review_results_json=review_results_json,
        po_approvals=po_approvals,
    )

    assert len(result.review_results) == 1
    review_result = result.review_results[0]
    assert review_result.po_notes == "Approved with notes"
    assert review_result.po_concerns == "Some concerns"
    assert review_result.priority_adjustment == "HIGH"
    assert review_result.po_priority_reason == "Critical"


def test_from_neo4j_dict_with_completed_at():
    """Test conversion from Neo4j dict with completed_at."""
    now = datetime.now(UTC)
    completed_at = datetime.now(UTC)
    ceremony = BacklogReviewCeremony(
        ceremony_id=BacklogReviewCeremonyId("BRC-002"),
        created_by=UserName("test-po"),
        story_ids=(StoryId("ST-001"),),
        status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.COMPLETED),
        created_at=now,
        updated_at=now,
        started_at=now,
        completed_at=completed_at,
        review_results=(),
    )

    neo4j_dict = BacklogReviewCeremonyStorageMapper.to_neo4j_dict(ceremony)
    story_ids = [sid.value for sid in ceremony.story_ids]

    result = BacklogReviewCeremonyStorageMapper.from_neo4j_dict(
        data=neo4j_dict,
        story_ids=tuple(story_ids),
        review_results_json="[]",
        po_approvals=None,
    )

    assert result.completed_at == completed_at


def test_to_redis_json(sample_ceremony):
    """Test conversion of BacklogReviewCeremony to Redis JSON."""
    import json

    result_str = BacklogReviewCeremonyStorageMapper.to_redis_json(sample_ceremony)
    result = json.loads(result_str)

    assert result["ceremony_id"] == "BRC-001"
    assert result["created_by"] == "test-po"
    assert result["status"] == "REVIEWING"
    assert len(result["story_ids"]) == 2
    assert "review_results" in result
    assert len(result["review_results"]) == 1


def test_from_redis_json(sample_ceremony):
    """Test conversion from Redis JSON to BacklogReviewCeremony."""
    json_str = BacklogReviewCeremonyStorageMapper.to_redis_json(sample_ceremony)

    result = BacklogReviewCeremonyStorageMapper.from_redis_json(json_str)

    assert result.ceremony_id == sample_ceremony.ceremony_id
    assert result.created_by == sample_ceremony.created_by
    assert result.story_ids == sample_ceremony.story_ids
    assert result.status == sample_ceremony.status
    assert len(result.review_results) == 1


def test_from_redis_json_with_completed_at():
    """Test conversion from Redis JSON with completed_at."""
    now = datetime.now(UTC)
    completed_at = datetime.now(UTC)
    ceremony = BacklogReviewCeremony(
        ceremony_id=BacklogReviewCeremonyId("BRC-003"),
        created_by=UserName("test-po"),
        story_ids=(StoryId("ST-001"),),
        status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.COMPLETED),
        created_at=now,
        updated_at=now,
        started_at=now,
        completed_at=completed_at,
        review_results=(),
    )

    json_str = BacklogReviewCeremonyStorageMapper.to_redis_json(ceremony)
    result = BacklogReviewCeremonyStorageMapper.from_redis_json(json_str)

    assert result.completed_at == completed_at


def test_review_result_to_dict(sample_review_result):
    """Test conversion of StoryReviewResult to dict."""
    result = BacklogReviewCeremonyStorageMapper._review_result_to_dict(sample_review_result)

    assert result["story_id"] == "ST-001"
    assert result["architect_feedback"] == "Architect feedback"
    assert result["qa_feedback"] == "QA feedback"
    assert result["devops_feedback"] == "DevOps feedback"
    assert result["recommendations"] == ["Rec 1", "Rec 2"]
    assert result["approval_status"] == "PENDING"
    assert "plan_preliminary" in result
    assert "po_notes" not in result  # po_notes NOT stored in Neo4j
    assert "po_concerns" not in result  # po_concerns NOT stored in Neo4j


def test_review_result_to_dict_with_plan_preliminary(sample_review_result):
    """Test conversion with plan_preliminary."""
    result = BacklogReviewCeremonyStorageMapper._review_result_to_dict(sample_review_result)

    assert result["plan_preliminary"] is not None
    assert result["plan_preliminary"]["title"] == "Test Plan"
    assert result["plan_preliminary"]["description"] == "Test description"


def test_review_result_to_dict_without_plan_preliminary():
    """Test conversion without plan_preliminary."""
    review_result = StoryReviewResult(
        story_id=StoryId("ST-002"),
        plan_preliminary=None,
        architect_feedback="Feedback",
        qa_feedback="",
        devops_feedback="",
        recommendations=(),
        approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
        reviewed_at=datetime.now(UTC),
        agent_deliberations=(),
    )

    result = BacklogReviewCeremonyStorageMapper._review_result_to_dict(review_result)

    assert result["plan_preliminary"] is None


def test_review_result_to_dict_with_approved_status():
    """Test conversion with approved status and approved_by/approved_at."""
    approved_at = datetime.now(UTC)
    review_result = StoryReviewResult(
        story_id=StoryId("ST-003"),
        plan_preliminary=None,
        architect_feedback="",
        qa_feedback="",
        devops_feedback="",
        recommendations=(),
        approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.APPROVED),
        reviewed_at=datetime.now(UTC),
        approved_by=UserName("po-user"),
        approved_at=approved_at,
        plan_id=PlanId("PL-001"),
        po_notes="Approved with notes",  # Required for APPROVED status
        agent_deliberations=(),
    )

    result = BacklogReviewCeremonyStorageMapper._review_result_to_dict(review_result)

    assert result["approval_status"] == "APPROVED"
    assert result["approved_by"] == "po-user"
    assert result["approved_at"] == approved_at.isoformat()
    assert result["plan_id"] == "PL-001"


def test_dict_to_review_result(sample_review_result):
    """Test conversion from dict to StoryReviewResult."""
    data = BacklogReviewCeremonyStorageMapper._review_result_to_dict(sample_review_result)

    result = BacklogReviewCeremonyStorageMapper._dict_to_review_result(data, po_approval=None)

    assert result.story_id == StoryId("ST-001")
    assert result.architect_feedback == "Architect feedback"
    assert result.qa_feedback == "QA feedback"
    assert result.devops_feedback == "DevOps feedback"
    assert result.recommendations == ("Rec 1", "Rec 2")
    assert result.approval_status.is_pending()
    assert result.plan_preliminary is not None


def test_dict_to_review_result_with_po_approval():
    """Test conversion with po_approval from Valkey."""
    data = {
        "story_id": "ST-001",
        "plan_preliminary": {
            "title": "Test Plan",
            "description": "Test description",
            "acceptance_criteria": ["Criterion 1"],
            "technical_notes": "",
            "roles": ["ARCHITECT"],
            "estimated_complexity": "MEDIUM",
            "dependencies": [],
            "tasks_outline": [],
        },
        "architect_feedback": "Feedback",
        "qa_feedback": "",
        "devops_feedback": "",
        "recommendations": [],
        "approval_status": "PENDING",
        "reviewed_at": datetime.now(UTC).isoformat(),
    }

    po_approval = {
        "po_notes": "Approved with notes",
        "approved_by": "po-user",
        "approved_at": datetime.now(UTC).isoformat(),
        "po_concerns": "Some concerns",
        "priority_adjustment": "HIGH",
        "po_priority_reason": "Critical",
    }

    result = BacklogReviewCeremonyStorageMapper._dict_to_review_result(
        data, po_approval=po_approval
    )

    assert result.po_notes == "Approved with notes"
    assert result.po_concerns == "Some concerns"
    assert result.priority_adjustment == "HIGH"
    assert result.po_priority_reason == "Critical"


def test_dict_to_review_result_without_po_approval_fallback():
    """Test conversion without po_approval (fallback to data dict)."""
    data = {
        "story_id": "ST-001",
        "plan_preliminary": None,
        "architect_feedback": "Feedback",
        "qa_feedback": "",
        "devops_feedback": "",
        "recommendations": [],
        "approval_status": "PENDING",
        "reviewed_at": datetime.now(UTC).isoformat(),
        "po_notes": "Old notes",  # Backward compatibility
        "po_concerns": "Old concerns",
    }

    result = BacklogReviewCeremonyStorageMapper._dict_to_review_result(data, po_approval=None)

    assert result.po_notes == "Old notes"
    assert result.po_concerns == "Old concerns"


def test_dict_to_review_result_with_approved_by():
    """Test conversion with approved_by and approved_at."""
    data = {
        "story_id": "ST-001",
        "plan_preliminary": None,
        "architect_feedback": "",
        "qa_feedback": "",
        "devops_feedback": "",
        "recommendations": [],
        "approval_status": "APPROVED",
        "reviewed_at": datetime.now(UTC).isoformat(),
        "approved_by": "po-user",
        "approved_at": datetime.now(UTC).isoformat(),
        "plan_id": "PL-001",
    }

    # Provide po_approval with required po_notes for APPROVED status
    po_approval = {
        "po_notes": "Approved with notes",
        "approved_by": "po-user",
        "approved_at": data["approved_at"],
    }

    result = BacklogReviewCeremonyStorageMapper._dict_to_review_result(data, po_approval=po_approval)

    assert result.approval_status.is_approved()
    assert result.approved_by == UserName("po-user")
    assert result.approved_at is not None
    assert result.plan_id == PlanId("PL-001")
    assert result.po_notes == "Approved with notes"


def test_dict_to_review_result_without_approved_by():
    """Test conversion without approved_by."""
    data = {
        "story_id": "ST-001",
        "plan_preliminary": None,
        "architect_feedback": "",
        "qa_feedback": "",
        "devops_feedback": "",
        "recommendations": [],
        "approval_status": "PENDING",
        "reviewed_at": datetime.now(UTC).isoformat(),
    }

    result = BacklogReviewCeremonyStorageMapper._dict_to_review_result(data, po_approval=None)

    assert result.approved_by is None
    assert result.approved_at is None
    assert result.plan_id is None


def test_plan_preliminary_to_dict(sample_plan_preliminary):
    """Test conversion of PlanPreliminary to dict."""
    result = BacklogReviewCeremonyStorageMapper._plan_preliminary_to_dict(sample_plan_preliminary)

    assert result["title"] == "Test Plan"
    assert result["description"] == "Test description"
    assert result["acceptance_criteria"] == ["Criterion 1", "Criterion 2"]
    assert result["technical_notes"] == "Technical notes"
    assert result["roles"] == ["ARCHITECT", "QA"]
    assert result["estimated_complexity"] == "MEDIUM"
    assert result["dependencies"] == ["dep1", "dep2"]
    assert result["tasks_outline"] == ["Task 1", "Task 2"]


def test_dict_to_plan_preliminary(sample_plan_preliminary):
    """Test conversion from dict to PlanPreliminary."""
    data = BacklogReviewCeremonyStorageMapper._plan_preliminary_to_dict(sample_plan_preliminary)

    result = BacklogReviewCeremonyStorageMapper._dict_to_plan_preliminary(data)

    assert result.title == sample_plan_preliminary.title
    assert result.description == sample_plan_preliminary.description
    assert result.acceptance_criteria == sample_plan_preliminary.acceptance_criteria
    assert result.technical_notes == sample_plan_preliminary.technical_notes
    assert result.roles == sample_plan_preliminary.roles
    assert result.estimated_complexity == sample_plan_preliminary.estimated_complexity
    assert result.dependencies == sample_plan_preliminary.dependencies
    assert result.tasks_outline == sample_plan_preliminary.tasks_outline


def test_dict_to_plan_preliminary_without_tasks_outline():
    """Test conversion without tasks_outline (backward compatibility)."""
    data = {
        "title": "Test Plan",
        "description": "Test description",
        "acceptance_criteria": ["Criterion 1"],  # Required: at least one
        "technical_notes": "",
        "roles": [],
        "estimated_complexity": "LOW",
        "dependencies": [],
    }

    result = BacklogReviewCeremonyStorageMapper._dict_to_plan_preliminary(data)

    assert result.tasks_outline == ()  # tasks_outline defaults to empty tuple


def test_parse_review_results_empty():
    """Test parsing empty review results."""
    result = BacklogReviewCeremonyStorageMapper._parse_review_results("", po_approvals=None)

    assert result == ()


def test_parse_review_results_without_po_approvals():
    """Test parsing review results without po_approvals."""
    review_results_json = """[
        {
            "story_id": "ST-001",
            "plan_preliminary": null,
            "architect_feedback": "Feedback",
            "qa_feedback": "",
            "devops_feedback": "",
            "recommendations": [],
            "approval_status": "PENDING",
            "reviewed_at": "2024-01-01T00:00:00+00:00"
        }
    ]"""

    result = BacklogReviewCeremonyStorageMapper._parse_review_results(
        review_results_json, po_approvals=None
    )

    assert len(result) == 1
    assert result[0].story_id == StoryId("ST-001")


def test_parse_review_results_with_po_approvals():
    """Test parsing review results with po_approvals."""
    review_results_json = """[
        {
            "story_id": "ST-001",
            "plan_preliminary": null,
            "architect_feedback": "",
            "qa_feedback": "",
            "devops_feedback": "",
            "recommendations": [],
            "approval_status": "PENDING",
            "reviewed_at": "2024-01-01T00:00:00+00:00"
        }
    ]"""

    po_approvals = {
        "ST-001": {
            "po_notes": "Approved",
            "approved_by": "po-user",
            "approved_at": "2024-01-01T00:00:00+00:00",
        }
    }

    result = BacklogReviewCeremonyStorageMapper._parse_review_results(
        review_results_json, po_approvals=po_approvals
    )

    assert len(result) == 1
    assert result[0].po_notes == "Approved"


def test_parse_review_results_partial_po_approvals():
    """Test parsing review results with partial po_approvals."""
    review_results_json = """[
        {
            "story_id": "ST-001",
            "plan_preliminary": null,
            "architect_feedback": "",
            "qa_feedback": "",
            "devops_feedback": "",
            "recommendations": [],
            "approval_status": "PENDING",
            "reviewed_at": "2024-01-01T00:00:00+00:00"
        },
        {
            "story_id": "ST-002",
            "plan_preliminary": null,
            "architect_feedback": "",
            "qa_feedback": "",
            "devops_feedback": "",
            "recommendations": [],
            "approval_status": "PENDING",
            "reviewed_at": "2024-01-01T00:00:00+00:00"
        }
    ]"""

    po_approvals = {
        "ST-001": {
            "po_notes": "Approved ST-001",
            "approved_by": "po-user",
            "approved_at": "2024-01-01T00:00:00+00:00",
        }
    }

    result = BacklogReviewCeremonyStorageMapper._parse_review_results(
        review_results_json, po_approvals=po_approvals
    )

    assert len(result) == 2
    assert result[0].po_notes == "Approved ST-001"
    assert result[1].po_notes is None  # No po_approval for ST-002


def test_extract_po_approval_fields_with_po_approval():
    """Test _extract_po_approval_fields when po_approval is provided."""
    data = {"story_id": "ST-001"}
    po_approval = {
        "po_notes": "Approved from Valkey",
        "po_concerns": "Monitor closely",
        "priority_adjustment": "HIGH",
        "po_priority_reason": "Critical for Q1",
    }

    po_notes, po_concerns, priority_adjustment, po_priority_reason = (
        BacklogReviewCeremonyStorageMapper._extract_po_approval_fields(data, po_approval)
    )

    assert po_notes == "Approved from Valkey"
    assert po_concerns == "Monitor closely"
    assert priority_adjustment == "HIGH"
    assert po_priority_reason == "Critical for Q1"


def test_extract_po_approval_fields_without_po_approval():
    """Test _extract_po_approval_fields when po_approval is None (fallback to data)."""
    data = {
        "story_id": "ST-001",
        "po_notes": "Approved from Neo4j",
        "po_concerns": "Some concerns",
        "priority_adjustment": "MEDIUM",
        "po_priority_reason": "Some reason",
    }

    po_notes, po_concerns, priority_adjustment, po_priority_reason = (
        BacklogReviewCeremonyStorageMapper._extract_po_approval_fields(data, None)
    )

    assert po_notes == "Approved from Neo4j"
    assert po_concerns == "Some concerns"
    assert priority_adjustment == "MEDIUM"
    assert po_priority_reason == "Some reason"


def test_determine_approval_status_and_metadata_with_po_approval():
    """Test _determine_approval_status_and_metadata when PO approval exists in Valkey."""
    data = {
        "approval_status": "PENDING",
        "approved_by": "old-user",
        "approved_at": "2024-01-01T00:00:00+00:00",
        "story_id": "ST-001",
    }
    po_approval = {
        "approved_by": "new-user",
        "approved_at": "2024-01-02T00:00:00+00:00",
    }

    approval_status_str, approved_by, approved_at = (
        BacklogReviewCeremonyStorageMapper._determine_approval_status_and_metadata(
            data, po_approval
        )
    )

    # Should override status to APPROVED when PO approval exists
    assert approval_status_str == "APPROVED"
    assert approved_by == "new-user"
    assert approved_at == "2024-01-02T00:00:00+00:00"


def test_determine_approval_status_and_metadata_without_po_approval():
    """Test _determine_approval_status_and_metadata when no PO approval (use Neo4j data)."""
    data = {
        "approval_status": "PENDING",
        "approved_by": "user",
        "approved_at": "2024-01-01T00:00:00+00:00",
        "story_id": "ST-001",
    }

    approval_status_str, approved_by, approved_at = (
        BacklogReviewCeremonyStorageMapper._determine_approval_status_and_metadata(
            data, None
        )
    )

    # Should use Neo4j data when no PO approval
    assert approval_status_str == "PENDING"
    assert approved_by == "user"
    assert approved_at == "2024-01-01T00:00:00+00:00"


def test_extract_plan_id_prefers_valkey():
    """Test _extract_plan_id prefers Valkey over Neo4j."""
    data = {"plan_id": "PL-NEO4J-123"}
    po_approval = {"plan_id": "PL-VALKEY-456"}

    plan_id = BacklogReviewCeremonyStorageMapper._extract_plan_id(data, po_approval)

    # Should prefer Valkey (source-of-truth)
    assert plan_id == "PL-VALKEY-456"


def test_extract_plan_id_fallback_to_neo4j():
    """Test _extract_plan_id falls back to Neo4j when Valkey has no plan_id."""
    data = {"plan_id": "PL-NEO4J-123"}
    po_approval = {}  # No plan_id in Valkey

    plan_id = BacklogReviewCeremonyStorageMapper._extract_plan_id(data, po_approval)

    # Should fallback to Neo4j
    assert plan_id == "PL-NEO4J-123"


def test_extract_plan_id_none_when_both_missing():
    """Test _extract_plan_id returns None when both missing."""
    data = {}
    po_approval = {}

    plan_id = BacklogReviewCeremonyStorageMapper._extract_plan_id(data, po_approval)

    assert plan_id is None


def test_dict_to_review_result_with_po_approval_and_plan_id():
    """Test _dict_to_review_result uses plan_id from Valkey PO approval."""
    data = {
        "story_id": "ST-001",
        "plan_preliminary": None,
        "architect_feedback": "",
        "qa_feedback": "",
        "devops_feedback": "",
        "recommendations": [],
        "approval_status": "PENDING",
        "reviewed_at": "2024-01-01T00:00:00+00:00",
        "plan_id": "PL-NEO4J-123",  # Neo4j has old plan_id
    }
    po_approval = {
        "approved_by": "po-user",
        "approved_at": "2024-01-02T00:00:00+00:00",
        "po_notes": "Approved",
        "plan_id": "PL-VALKEY-456",  # Valkey has correct plan_id
    }

    result = BacklogReviewCeremonyStorageMapper._dict_to_review_result(data, po_approval)

    # Should use plan_id from Valkey (source-of-truth)
    assert result.plan_id == PlanId("PL-VALKEY-456")
    # Should override approval_status to APPROVED when PO approval exists
    assert result.approval_status.is_approved()
    assert result.approved_by == UserName("po-user")

