"""Mapper: Build protobuf responses."""


from planning.gen import planning_pb2

from planning.domain import Story, StoryList
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

