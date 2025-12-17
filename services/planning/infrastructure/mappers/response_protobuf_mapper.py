"""Mapper: Build protobuf responses."""


from planning.domain import Story, StoryList
from planning.domain.entities.backlog_review_ceremony import BacklogReviewCeremony
from planning.gen import planning_pb2
from planning.infrastructure.mappers.backlog_review_ceremony_protobuf_mapper import (
    BacklogReviewCeremonyProtobufMapper,
)
from planning.infrastructure.mappers.story_protobuf_mapper import StoryProtobufMapper


class ResponseProtobufMapper:
    """
    Mapper: Build protobuf response messages.

    Infrastructure Layer Responsibility:
    - Construct gRPC response messages
    - Delegate Story conversion to StoryProtobufMapper
    """

    @staticmethod
    def create_story_response(
        success: bool,
        message: str,
        story: Story | None = None,
    ) -> planning_pb2.CreateStoryResponse:
        """
        Build CreateStoryResponse.

        Args:
            success: Operation success flag.
            message: Response message.
            story: Created story (if successful).

        Returns:
            CreateStoryResponse protobuf message.
        """
        if story is not None:
            return planning_pb2.CreateStoryResponse(
                story=StoryProtobufMapper.to_protobuf(story),
                success=success,
                message=message,
            )
        else:
            return planning_pb2.CreateStoryResponse(
                success=success,
                message=message,
            )

    @staticmethod
    def list_stories_response(
        success: bool,
        message: str,
        stories: StoryList,
        total_count: int,
    ) -> planning_pb2.ListStoriesResponse:
        """
        Build ListStoriesResponse.

        Args:
            success: Operation success flag.
            message: Response message.
            stories: StoryList collection.
            total_count: Total count of stories.

        Returns:
            ListStoriesResponse protobuf message.
        """
        return planning_pb2.ListStoriesResponse(
            stories=[
                StoryProtobufMapper.to_protobuf(s) for s in stories
            ],  # __iter__ works directly
            total_count=total_count,
            success=success,
            message=message,
        )

    @staticmethod
    def transition_story_response(
        success: bool,
        message: str,
        story: Story | None = None,
    ) -> planning_pb2.TransitionStoryResponse:
        """
        Build TransitionStoryResponse.

        Args:
            success: Operation success flag.
            message: Response message.
            story: Transitioned story (if successful).

        Returns:
            TransitionStoryResponse protobuf message.
        """
        if story is not None:
            return planning_pb2.TransitionStoryResponse(
                story=StoryProtobufMapper.to_protobuf(story),
                success=success,
                message=message,
            )
        else:
            return planning_pb2.TransitionStoryResponse(
                success=success,
                message=message,
            )

    @staticmethod
    def approve_decision_response(
        success: bool,
        message: str,
    ) -> planning_pb2.ApproveDecisionResponse:
        """
        Build ApproveDecisionResponse.

        Args:
            success: Operation success flag.
            message: Response message.

        Returns:
            ApproveDecisionResponse protobuf message.
        """
        return planning_pb2.ApproveDecisionResponse(
            success=success,
            message=message,
        )

    @staticmethod
    def reject_decision_response(
        success: bool,
        message: str,
    ) -> planning_pb2.RejectDecisionResponse:
        """
        Build RejectDecisionResponse.

        Args:
            success: Operation success flag.
            message: Response message.

        Returns:
            RejectDecisionResponse protobuf message.
        """
        return planning_pb2.RejectDecisionResponse(
            success=success,
            message=message,
        )

    @staticmethod
    def get_backlog_review_ceremony_response(
        success: bool,
        message: str,
        ceremony: BacklogReviewCeremony | None = None,
    ) -> planning_pb2.BacklogReviewCeremonyResponse:
        """
        Build BacklogReviewCeremonyResponse.

        Args:
            success: Operation success flag.
            message: Response message.
            ceremony: Backlog review ceremony (if successful).

        Returns:
            BacklogReviewCeremonyResponse protobuf message.
        """
        if ceremony is not None:
            return planning_pb2.BacklogReviewCeremonyResponse(
                success=success,
                message=message,
                ceremony=BacklogReviewCeremonyProtobufMapper.to_protobuf(ceremony),
            )
        else:
            return planning_pb2.BacklogReviewCeremonyResponse(
                success=success,
                message=message,
            )

    @staticmethod
    def create_backlog_review_ceremony_response(
        success: bool,
        message: str,
        ceremony: BacklogReviewCeremony | None = None,
    ) -> planning_pb2.CreateBacklogReviewCeremonyResponse:
        """
        Build CreateBacklogReviewCeremonyResponse.

        Args:
            success: Operation success flag.
            message: Response message.
            ceremony: Created backlog review ceremony (if successful).

        Returns:
            CreateBacklogReviewCeremonyResponse protobuf message.
        """
        if ceremony is not None:
            return planning_pb2.CreateBacklogReviewCeremonyResponse(
                success=success,
                message=message,
                ceremony=BacklogReviewCeremonyProtobufMapper.to_protobuf(ceremony),
            )
        else:
            return planning_pb2.CreateBacklogReviewCeremonyResponse(
                success=success,
                message=message,
            )

    @staticmethod
    def approve_review_plan_response(
        success: bool,
        message: str,
        ceremony: BacklogReviewCeremony | None = None,
        plan_id: str = "",
    ) -> planning_pb2.ApproveReviewPlanResponse:
        """
        Build ApproveReviewPlanResponse.

        Args:
            success: Operation success flag.
            message: Response message.
            ceremony: Updated ceremony (if successful).
            plan_id: Created plan ID (if successful).

        Returns:
            ApproveReviewPlanResponse protobuf message.
        """
        if ceremony is not None:
            return planning_pb2.ApproveReviewPlanResponse(
                success=success,
                message=message,
                ceremony=BacklogReviewCeremonyProtobufMapper.to_protobuf(ceremony),
                plan_id=plan_id,
            )
        else:
            return planning_pb2.ApproveReviewPlanResponse(
                success=success,
                message=message,
            )

    @staticmethod
    def add_stories_to_review_response(
        success: bool,
        message: str,
        ceremony: BacklogReviewCeremony | None = None,
    ) -> planning_pb2.AddStoriesToReviewResponse:
        """
        Build AddStoriesToReviewResponse.

        Args:
            success: Operation success flag.
            message: Response message.
            ceremony: Updated ceremony (if successful).

        Returns:
            AddStoriesToReviewResponse protobuf message.
        """
        if ceremony is not None:
            return planning_pb2.AddStoriesToReviewResponse(
                success=success,
                message=message,
                ceremony=BacklogReviewCeremonyProtobufMapper.to_protobuf(ceremony),
            )
        else:
            return planning_pb2.AddStoriesToReviewResponse(
                success=success,
                message=message,
            )

    @staticmethod
    def reject_review_plan_response(
        success: bool,
        message: str,
        ceremony: BacklogReviewCeremony | None = None,
    ) -> planning_pb2.RejectReviewPlanResponse:
        """
        Build RejectReviewPlanResponse.

        Args:
            success: Operation success flag.
            message: Response message.
            ceremony: Updated ceremony (if successful).

        Returns:
            RejectReviewPlanResponse protobuf message.
        """
        if ceremony is not None:
            return planning_pb2.RejectReviewPlanResponse(
                success=success,
                message=message,
                ceremony=BacklogReviewCeremonyProtobufMapper.to_protobuf(ceremony),
            )
        else:
            return planning_pb2.RejectReviewPlanResponse(
                success=success,
                message=message,
            )

    @staticmethod
    def start_backlog_review_ceremony_response(
        success: bool,
        message: str,
        ceremony: BacklogReviewCeremony | None = None,
        total_deliberations_submitted: int = 0,
    ) -> planning_pb2.StartBacklogReviewCeremonyResponse:
        """
        Build StartBacklogReviewCeremonyResponse.

        Args:
            success: Operation success flag.
            message: Response message.
            ceremony: Updated ceremony (if successful).
            total_deliberations_submitted: Number of deliberations submitted to orchestrator.

        Returns:
            StartBacklogReviewCeremonyResponse protobuf message.
        """
        if ceremony is not None:
            return planning_pb2.StartBacklogReviewCeremonyResponse(
                success=success,
                message=message,
                ceremony=BacklogReviewCeremonyProtobufMapper.to_protobuf(ceremony),
                total_deliberations_submitted=total_deliberations_submitted,
            )
        else:
            return planning_pb2.StartBacklogReviewCeremonyResponse(
                success=success,
                message=message,
                total_deliberations_submitted=total_deliberations_submitted,
            )

    @staticmethod
    def complete_backlog_review_ceremony_response(
        success: bool,
        message: str,
        ceremony: BacklogReviewCeremony | None = None,
    ) -> planning_pb2.CompleteBacklogReviewCeremonyResponse:
        """
        Build CompleteBacklogReviewCeremonyResponse.

        Args:
            success: Operation success flag.
            message: Response message.
            ceremony: Completed ceremony (if successful).

        Returns:
            CompleteBacklogReviewCeremonyResponse protobuf message.
        """
        if ceremony is not None:
            return planning_pb2.CompleteBacklogReviewCeremonyResponse(
                success=success,
                message=message,
                ceremony=BacklogReviewCeremonyProtobufMapper.to_protobuf(ceremony),
            )
        else:
            return planning_pb2.CompleteBacklogReviewCeremonyResponse(
                success=success,
                message=message,
            )

    @staticmethod
    def cancel_backlog_review_ceremony_response(
        success: bool,
        message: str,
        ceremony: BacklogReviewCeremony | None = None,
    ) -> planning_pb2.CancelBacklogReviewCeremonyResponse:
        """
        Build CancelBacklogReviewCeremonyResponse.

        Args:
            success: Operation success flag.
            message: Response message.
            ceremony: Cancelled ceremony (if successful).

        Returns:
            CancelBacklogReviewCeremonyResponse protobuf message.
        """
        if ceremony is not None:
            return planning_pb2.CancelBacklogReviewCeremonyResponse(
                success=success,
                message=message,
                ceremony=BacklogReviewCeremonyProtobufMapper.to_protobuf(ceremony),
            )
        else:
            return planning_pb2.CancelBacklogReviewCeremonyResponse(
                success=success,
                message=message,
            )

    @staticmethod
    def list_backlog_review_ceremonies_response(
        success: bool,
        message: str,
        ceremonies: list[BacklogReviewCeremony],
        total_count: int,
    ) -> planning_pb2.ListBacklogReviewCeremoniesResponse:
        """
        Build ListBacklogReviewCeremoniesResponse.

        Args:
            success: Operation success flag.
            message: Response message.
            ceremonies: List of backlog review ceremonies.
            total_count: Total count of ceremonies.

        Returns:
            ListBacklogReviewCeremoniesResponse protobuf message.
        """
        return planning_pb2.ListBacklogReviewCeremoniesResponse(
            success=success,
            message=message,
            ceremonies=[
                BacklogReviewCeremonyProtobufMapper.to_protobuf(c) for c in ceremonies
            ],
            total_count=total_count,
        )

    @staticmethod
    def add_agent_deliberation_response(
        success: bool,
        message: str,
        ceremony: BacklogReviewCeremony | None = None,
    ) -> planning_pb2.AddAgentDeliberationResponse:
        """
        Build AddAgentDeliberationResponse.

        Args:
            success: Operation success flag.
            message: Response message.
            ceremony: Updated ceremony (if successful).

        Returns:
            AddAgentDeliberationResponse protobuf message.
        """
        if ceremony is not None:
            return planning_pb2.AddAgentDeliberationResponse(
                success=success,
                message=message,
                ceremony=BacklogReviewCeremonyProtobufMapper.to_protobuf(ceremony),
            )
        else:
            return planning_pb2.AddAgentDeliberationResponse(
                success=success,
                message=message,
            )

