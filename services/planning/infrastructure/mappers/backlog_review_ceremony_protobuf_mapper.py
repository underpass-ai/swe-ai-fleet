"""BacklogReviewCeremonyProtobufMapper - Convert domain entities to/from protobuf.

Mapper (Infrastructure Layer):
- Converts BacklogReviewCeremony ↔ planning_pb2.BacklogReviewCeremony
- NO business logic (pure data transformation)

Following Hexagonal Architecture:
- Lives in infrastructure layer
- Depends on domain entities
- Used by gRPC handlers
"""

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

# Import generated protobuf
from planning.gen import planning_pb2


class BacklogReviewCeremonyProtobufMapper:
    """
    Mapper for BacklogReviewCeremony ↔ Protobuf messages.

    Responsibilities:
    - Convert domain entity to protobuf message
    - Convert protobuf message to domain entity
    - Handle nested objects (StoryReviewResult, PlanPreliminary)

    NO business logic - pure data transformation.
    """

    @staticmethod
    def to_protobuf(ceremony: BacklogReviewCeremony) -> planning_pb2.BacklogReviewCeremony:
        """
        Convert BacklogReviewCeremony entity to protobuf message.

        Args:
            ceremony: Domain entity

        Returns:
            planning_pb2.BacklogReviewCeremony protobuf message
        """
        # Convert review results
        review_results_pb = [
            BacklogReviewCeremonyProtobufMapper.story_review_result_to_protobuf(result)
            for result in ceremony.review_results
        ]

        return planning_pb2.BacklogReviewCeremony(
            ceremony_id=ceremony.ceremony_id.value,
            created_by=ceremony.created_by.value,
            story_ids=[sid.value for sid in ceremony.story_ids],
            status=ceremony.status.to_string(),
            created_at=ceremony.created_at.isoformat(),
            updated_at=ceremony.updated_at.isoformat(),
            started_at=ceremony.started_at.isoformat() if ceremony.started_at else "",
            completed_at=ceremony.completed_at.isoformat() if ceremony.completed_at else "",
            review_results=review_results_pb,
        )

    @staticmethod
    def from_protobuf(pb: planning_pb2.BacklogReviewCeremony) -> BacklogReviewCeremony:
        """
        Convert protobuf message to BacklogReviewCeremony entity.

        Args:
            pb: Protobuf message

        Returns:
            BacklogReviewCeremony domain entity
        """
        # Convert review results
        review_results = tuple(
            BacklogReviewCeremonyProtobufMapper.story_review_result_from_protobuf(result_pb)
            for result_pb in pb.review_results
        )

        return BacklogReviewCeremony(
            ceremony_id=BacklogReviewCeremonyId(pb.ceremony_id),
            created_by=UserName(pb.created_by),
            story_ids=tuple(StoryId(sid) for sid in pb.story_ids),
            status=BacklogReviewCeremonyStatus(
                BacklogReviewCeremonyStatusEnum(pb.status)
            ),
            created_at=datetime.fromisoformat(pb.created_at),
            updated_at=datetime.fromisoformat(pb.updated_at),
            started_at=datetime.fromisoformat(pb.started_at) if pb.started_at else None,
            completed_at=datetime.fromisoformat(pb.completed_at) if pb.completed_at else None,
            review_results=review_results,
        )

    @staticmethod
    def story_review_result_to_protobuf(
        result: StoryReviewResult,
    ) -> planning_pb2.StoryReviewResult:
        """Convert StoryReviewResult to protobuf."""
        plan_pb = None
        if result.plan_preliminary:
            plan_pb = BacklogReviewCeremonyProtobufMapper.plan_preliminary_to_protobuf(
                result.plan_preliminary
            )

        return planning_pb2.StoryReviewResult(
            story_id=result.story_id.value,
            plan_preliminary=plan_pb,
            architect_feedback=result.architect_feedback,
            qa_feedback=result.qa_feedback,
            devops_feedback=result.devops_feedback,
            recommendations=list(result.recommendations),
            approval_status=result.approval_status.to_string(),
            reviewed_at=result.reviewed_at.isoformat(),
            approved_by=result.approved_by.value if result.approved_by else "",
            approved_at=result.approved_at.isoformat() if result.approved_at else "",
        )

    @staticmethod
    def story_review_result_from_protobuf(
        pb: planning_pb2.StoryReviewResult,
    ) -> StoryReviewResult:
        """Convert protobuf to StoryReviewResult."""
        plan_preliminary = None
        if pb.HasField("plan_preliminary"):
            plan_preliminary = BacklogReviewCeremonyProtobufMapper.plan_preliminary_from_protobuf(
                pb.plan_preliminary
            )

        return StoryReviewResult(
            story_id=StoryId(pb.story_id),
            plan_preliminary=plan_preliminary,
            architect_feedback=pb.architect_feedback,
            qa_feedback=pb.qa_feedback,
            devops_feedback=pb.devops_feedback,
            recommendations=tuple(pb.recommendations),
            approval_status=ReviewApprovalStatus(
                ReviewApprovalStatusEnum(pb.approval_status)
            ),
            reviewed_at=datetime.fromisoformat(pb.reviewed_at),
            approved_by=UserName(pb.approved_by) if pb.approved_by else None,
            approved_at=datetime.fromisoformat(pb.approved_at) if pb.approved_at else None,
        )

    @staticmethod
    def plan_preliminary_to_protobuf(
        plan: PlanPreliminary,
    ) -> planning_pb2.PlanPreliminary:
        """Convert PlanPreliminary to protobuf."""
        return planning_pb2.PlanPreliminary(
            title=plan.title.value,
            description=plan.description.value,
            acceptance_criteria=list(plan.acceptance_criteria),
            technical_notes=plan.technical_notes,
            roles=list(plan.roles),
            estimated_complexity=plan.estimated_complexity,
            dependencies=list(plan.dependencies),
            tasks_outline=list(plan.tasks_outline),
        )

    @staticmethod
    def plan_preliminary_from_protobuf(
        pb: planning_pb2.PlanPreliminary,
    ) -> PlanPreliminary:
        """Convert protobuf to PlanPreliminary."""
        return PlanPreliminary(
            title=Title(pb.title),
            description=Brief(pb.description),
            acceptance_criteria=tuple(pb.acceptance_criteria),
            technical_notes=pb.technical_notes,
            roles=tuple(pb.roles),
            estimated_complexity=pb.estimated_complexity,
            dependencies=tuple(pb.dependencies),
            tasks_outline=tuple(pb.tasks_outline),
        )




