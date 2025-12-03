"""BacklogReviewCeremonyStorageMapper - Convert domain entities to/from storage formats.

Mapper (Infrastructure Layer):
- Converts BacklogReviewCeremony ↔ Neo4j dict
- Converts BacklogReviewCeremony ↔ Redis JSON
- NO business logic (pure data transformation)

Following Hexagonal Architecture:
- Lives in infrastructure layer
- Depends on domain entities
- Used by storage adapters
"""

import json
from datetime import datetime

from planning.domain.entities.backlog_review_ceremony import BacklogReviewCeremony
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.content.brief import Brief
from planning.domain.value_objects.content.title import Title
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
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


class BacklogReviewCeremonyStorageMapper:
    """
    Mapper for BacklogReviewCeremony ↔ Storage formats.

    Responsibilities:
    - Convert domain entity to Neo4j dict format
    - Convert Neo4j dict to domain entity
    - Convert domain entity to Redis JSON string
    - Convert Redis JSON to domain entity

    NO business logic - pure data transformation.
    """

    @staticmethod
    def to_neo4j_dict(ceremony: BacklogReviewCeremony) -> dict:
        """
        Convert BacklogReviewCeremony to Neo4j node properties.

        Args:
            ceremony: Domain entity to convert

        Returns:
            Dict with Neo4j node properties
        """
        return {
            "ceremony_id": ceremony.ceremony_id.value,
            "created_by": ceremony.created_by.value,
            "status": ceremony.status.to_string(),
            "created_at": ceremony.created_at.isoformat(),
            "updated_at": ceremony.updated_at.isoformat(),
            "started_at": ceremony.started_at.isoformat() if ceremony.started_at else None,
            "completed_at": ceremony.completed_at.isoformat() if ceremony.completed_at else None,
            "story_count": len(ceremony.story_ids),
        }

    @staticmethod
    def from_neo4j_dict(data: dict, story_ids: tuple[str, ...], review_results_json: str) -> BacklogReviewCeremony:
        """
        Convert Neo4j dict to BacklogReviewCeremony entity.

        Args:
            data: Neo4j node properties
            story_ids: Story IDs (from REVIEWS relationships)
            review_results_json: JSON string of review results

        Returns:
            BacklogReviewCeremony domain entity
        """
        # Parse review results
        review_results = BacklogReviewCeremonyStorageMapper._parse_review_results(
            review_results_json
        )

        return BacklogReviewCeremony(
            ceremony_id=BacklogReviewCeremonyId(data["ceremony_id"]),
            created_by=UserName(data["created_by"]),
            story_ids=tuple(StoryId(sid) for sid in story_ids),
            status=BacklogReviewCeremonyStatus(
                BacklogReviewCeremonyStatusEnum(data["status"])
            ),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            review_results=review_results,
        )

    @staticmethod
    def to_redis_json(ceremony: BacklogReviewCeremony) -> str:
        """
        Convert BacklogReviewCeremony to Redis JSON string.

        Args:
            ceremony: Domain entity to convert

        Returns:
            JSON string for Redis storage
        """
        ceremony_dict = {
            "ceremony_id": ceremony.ceremony_id.value,
            "created_by": ceremony.created_by.value,
            "story_ids": [sid.value for sid in ceremony.story_ids],
            "status": ceremony.status.to_string(),
            "created_at": ceremony.created_at.isoformat(),
            "updated_at": ceremony.updated_at.isoformat(),
            "started_at": ceremony.started_at.isoformat() if ceremony.started_at else None,
            "completed_at": ceremony.completed_at.isoformat() if ceremony.completed_at else None,
            "review_results": [
                BacklogReviewCeremonyStorageMapper._review_result_to_dict(result)
                for result in ceremony.review_results
            ],
        }

        return json.dumps(ceremony_dict)

    @staticmethod
    def from_redis_json(json_str: str) -> BacklogReviewCeremony:
        """
        Convert Redis JSON to BacklogReviewCeremony entity.

        Args:
            json_str: JSON string from Redis

        Returns:
            BacklogReviewCeremony domain entity
        """
        data = json.loads(json_str)

        # Parse review results
        review_results = tuple(
            BacklogReviewCeremonyStorageMapper._dict_to_review_result(result_dict)
            for result_dict in data["review_results"]
        )

        return BacklogReviewCeremony(
            ceremony_id=BacklogReviewCeremonyId(data["ceremony_id"]),
            created_by=UserName(data["created_by"]),
            story_ids=tuple(StoryId(sid) for sid in data["story_ids"]),
            status=BacklogReviewCeremonyStatus(
                BacklogReviewCeremonyStatusEnum(data["status"])
            ),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            review_results=review_results,
        )

    @staticmethod
    def _review_result_to_dict(result: StoryReviewResult) -> dict:
        """Convert StoryReviewResult to dict."""
        return {
            "story_id": result.story_id.value,
            "plan_preliminary": BacklogReviewCeremonyStorageMapper._plan_preliminary_to_dict(
                result.plan_preliminary
            ) if result.plan_preliminary else None,
            "architect_feedback": result.architect_feedback,
            "qa_feedback": result.qa_feedback,
            "devops_feedback": result.devops_feedback,
            "recommendations": list(result.recommendations),
            "approval_status": result.approval_status.to_string(),
            "reviewed_at": result.reviewed_at.isoformat(),
            "approved_by": result.approved_by.value if result.approved_by else None,
            "approved_at": result.approved_at.isoformat() if result.approved_at else None,
        }

    @staticmethod
    def _dict_to_review_result(data: dict) -> StoryReviewResult:
        """Convert dict to StoryReviewResult."""
        plan_preliminary = None
        if data.get("plan_preliminary"):
            plan_preliminary = BacklogReviewCeremonyStorageMapper._dict_to_plan_preliminary(
                data["plan_preliminary"]
            )

        return StoryReviewResult(
            story_id=StoryId(data["story_id"]),
            plan_preliminary=plan_preliminary,
            architect_feedback=data["architect_feedback"],
            qa_feedback=data["qa_feedback"],
            devops_feedback=data["devops_feedback"],
            recommendations=tuple(data["recommendations"]),
            approval_status=ReviewApprovalStatus(
                ReviewApprovalStatusEnum(data["approval_status"])
            ),
            reviewed_at=datetime.fromisoformat(data["reviewed_at"]),
            approved_by=UserName(data["approved_by"]) if data.get("approved_by") else None,
            approved_at=datetime.fromisoformat(data["approved_at"]) if data.get("approved_at") else None,
        )

    @staticmethod
    def _plan_preliminary_to_dict(plan: PlanPreliminary) -> dict:
        """Convert PlanPreliminary to dict."""
        return {
            "title": plan.title.value,
            "description": plan.description.value,
            "acceptance_criteria": list(plan.acceptance_criteria),
            "technical_notes": plan.technical_notes,
            "roles": list(plan.roles),
            "estimated_complexity": plan.estimated_complexity,
            "dependencies": list(plan.dependencies),
            "tasks_outline": list(plan.tasks_outline),
        }

    @staticmethod
    def _dict_to_plan_preliminary(data: dict) -> PlanPreliminary:
        """Convert dict to PlanPreliminary."""
        return PlanPreliminary(
            title=Title(data["title"]),
            description=Brief(data["description"]),
            acceptance_criteria=tuple(data["acceptance_criteria"]),
            technical_notes=data["technical_notes"],
            roles=tuple(data["roles"]),
            estimated_complexity=data["estimated_complexity"],
            dependencies=tuple(data["dependencies"]),
            tasks_outline=tuple(data.get("tasks_outline", [])),
        )

    @staticmethod
    def _parse_review_results(json_str: str) -> tuple[StoryReviewResult, ...]:
        """Parse review results from JSON string."""
        if not json_str:
            return ()

        results_list = json.loads(json_str)
        return tuple(
            BacklogReviewCeremonyStorageMapper._dict_to_review_result(result_dict)
            for result_dict in results_list
        )




