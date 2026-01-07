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
        # Serialize review_results to JSON for Neo4j storage
        review_results_list = [
            BacklogReviewCeremonyStorageMapper._review_result_to_dict(result)
            for result in ceremony.review_results
        ]
        review_results_json = json.dumps(review_results_list)

        return {
            "ceremony_id": ceremony.ceremony_id.value,
            "created_by": ceremony.created_by.value,
            "status": ceremony.status.to_string(),
            "created_at": ceremony.created_at.isoformat(),
            "updated_at": ceremony.updated_at.isoformat(),
            "started_at": ceremony.started_at.isoformat() if ceremony.started_at else None,
            "completed_at": ceremony.completed_at.isoformat() if ceremony.completed_at else None,
            "story_count": len(ceremony.story_ids),
            "review_results_json": review_results_json,
        }

    @staticmethod
    def from_neo4j_dict(
        data: dict,
        story_ids: tuple[str, ...],
        review_results_json: str,
        po_approvals: dict[str, dict[str, str]] | None = None,
    ) -> BacklogReviewCeremony:
        """
        Convert Neo4j dict to BacklogReviewCeremony entity.

        Args:
            data: Neo4j node properties
            story_ids: Story IDs (from REVIEWS relationships)
            review_results_json: JSON string of review results (does NOT contain po_notes)
            po_approvals: Optional dict mapping story_id -> po_approval data from Valkey.
                         Format: {story_id: {"po_notes": "...", "approved_by": "...", ...}}

        Returns:
            BacklogReviewCeremony domain entity
        """
        # Parse review results (combine Neo4j data with Valkey po_approvals)
        review_results = BacklogReviewCeremonyStorageMapper._parse_review_results(
            review_results_json, po_approvals=po_approvals
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
        """Convert StoryReviewResult to dict for Neo4j storage.

        NOTE: po_notes, po_concerns, priority_adjustment, and po_priority_reason
        are NOT stored in Neo4j. They are stored in Valkey separately via
        save_ceremony_story_po_approval() to follow the dual persistence pattern:
        - Neo4j: Graph structure, relationships, state
        - Valkey: Detailed content, semantic context (po_notes, etc.)
        """
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
            "plan_id": result.plan_id.value if result.plan_id else None,
            # NOTE: po_notes, po_concerns, priority_adjustment, po_priority_reason
            # are stored in Valkey, not in Neo4j (dual persistence pattern)
        }

    @staticmethod
    def _dict_to_review_result(
        data: dict, po_approval: dict[str, str] | None = None
    ) -> StoryReviewResult:
        """Convert dict to StoryReviewResult.

        Args:
            data: Dict from Neo4j review_results_json (does NOT contain po_notes, etc.)
            po_approval: Optional dict from Valkey with po_notes, po_concerns, etc.
                        If provided, these values will be used instead of data.get().
        """
        import logging

        logger = logging.getLogger(__name__)

        plan_preliminary = None
        if data.get("plan_preliminary"):
            plan_preliminary = BacklogReviewCeremonyStorageMapper._dict_to_plan_preliminary(
                data["plan_preliminary"]
            )

        # Get po_approval fields from Valkey if available, otherwise from data (backward compatibility)
        po_notes = None
        po_concerns = None
        priority_adjustment = None
        po_priority_reason = None

        if po_approval:
            # Use values from Valkey (preferred source)
            po_notes = po_approval.get("po_notes")
            po_concerns = po_approval.get("po_concerns")
            priority_adjustment = po_approval.get("priority_adjustment")
            po_priority_reason = po_approval.get("po_priority_reason")
            logger.info(
                f"Mapped po_approval from Valkey for story {data.get('story_id')}: "
                f"po_notes={'present' if po_notes else 'missing'}, "
                f"po_notes_value='{po_notes[:50] if po_notes and len(po_notes) > 50 else po_notes}'"
            )
        else:
            # Fallback to data (for backward compatibility with old data)
            po_notes = data.get("po_notes")
            po_concerns = data.get("po_concerns")
            priority_adjustment = data.get("priority_adjustment")
            po_priority_reason = data.get("po_priority_reason")
            logger.info(
                f"No po_approval from Valkey for story {data.get('story_id')}, "
                f"using fallback from Neo4j data"
            )

        # Determine approval_status and approval metadata
        # If PO approval exists in Valkey, status should be APPROVED (source-of-truth)
        # This handles race conditions where Neo4j hasn't been updated yet but Valkey has the approval
        approval_status_str = data["approval_status"]
        approved_by_from_data = data.get("approved_by")
        approved_at_from_data = data.get("approved_at")
        
        if po_approval and po_approval.get("approved_by"):
            # PO approval exists in Valkey - override status to APPROVED
            # This is the source-of-truth check for dual persistence
            approval_status_str = ReviewApprovalStatusEnum.APPROVED.value
            # Use approved_by and approved_at from Valkey if available (more up-to-date)
            if po_approval.get("approved_by"):
                approved_by_from_data = po_approval.get("approved_by")
            if po_approval.get("approved_at"):
                approved_at_from_data = po_approval.get("approved_at")
            logger.info(
                f"PO approval found in Valkey for story {data.get('story_id')}, "
                f"overriding approval_status from '{data['approval_status']}' to 'APPROVED'"
            )

        # Get plan_id: prefer from Valkey PO approval (source-of-truth), fallback to Neo4j
        plan_id_str = None
        if po_approval and po_approval.get("plan_id"):
            plan_id_str = po_approval.get("plan_id")
        elif data.get("plan_id"):
            plan_id_str = data["plan_id"]

        return StoryReviewResult(
            story_id=StoryId(data["story_id"]),
            plan_preliminary=plan_preliminary,
            architect_feedback=data["architect_feedback"],
            qa_feedback=data["qa_feedback"],
            devops_feedback=data["devops_feedback"],
            recommendations=tuple(data["recommendations"]),
            approval_status=ReviewApprovalStatus(
                ReviewApprovalStatusEnum(approval_status_str)
            ),
            reviewed_at=datetime.fromisoformat(data["reviewed_at"]),
            approved_by=UserName(approved_by_from_data) if approved_by_from_data else None,
            approved_at=datetime.fromisoformat(approved_at_from_data) if approved_at_from_data else None,
            po_notes=po_notes,
            po_concerns=po_concerns,
            priority_adjustment=priority_adjustment,
            po_priority_reason=po_priority_reason,
            plan_id=PlanId(plan_id_str) if plan_id_str else None,
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
    def _parse_review_results(
        json_str: str, po_approvals: dict[str, dict[str, str]] | None = None
    ) -> tuple[StoryReviewResult, ...]:
        """Parse review results from JSON string.

        Args:
            json_str: JSON string from Neo4j review_results_json.
            po_approvals: Optional dict mapping story_id -> po_approval data from Valkey.
                         Format: {story_id: {"po_notes": "...", "approved_by": "...", ...}}
        """
        if not json_str:
            return ()

        import logging

        logger = logging.getLogger(__name__)

        results_list = json.loads(json_str)
        logger.info(
            f"Parsing {len(results_list)} review results, "
            f"po_approvals available for {len(po_approvals) if po_approvals else 0} stories"
        )
        if po_approvals:
            logger.info(f"po_approvals keys: {list(po_approvals.keys())}")
            for result_dict in results_list:
                story_id = result_dict.get("story_id")
                logger.info(
                    f"Review result story_id: {story_id}, "
                    f"po_approval available: {story_id in po_approvals if po_approvals else False}"
                )

        return tuple(
            BacklogReviewCeremonyStorageMapper._dict_to_review_result(
                result_dict,
                po_approval=po_approvals.get(result_dict["story_id"]) if po_approvals else None,
            )
            for result_dict in results_list
        )






