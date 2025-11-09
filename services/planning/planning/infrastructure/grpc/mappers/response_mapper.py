"""Common response mapper for gRPC responses.

Infrastructure layer - handles protobuf serialization.
"""

from planning.gen import planning_pb2


class ResponseMapper:
    """Maps domain entities to protobuf responses.

    Centralized mapping logic to avoid duplication across handlers.
    """

    @staticmethod
    def create_project_response(
        success: bool,
        message: str,
        project=None,
    ) -> planning_pb2.CreateProjectResponse:
        """Map to CreateProjectResponse."""
        if not project:
            return planning_pb2.CreateProjectResponse(
                success=success,
                message=message,
            )

        return planning_pb2.CreateProjectResponse(
            success=success,
            message=message,
            project=ResponseMapper._project_to_proto(project),
        )

    @staticmethod
    def project_response(
        success: bool,
        message: str,
        project=None,
    ) -> planning_pb2.ProjectResponse:
        """Map to ProjectResponse."""
        if not project:
            return planning_pb2.ProjectResponse()

        return planning_pb2.ProjectResponse(
            project=ResponseMapper._project_to_proto(project),
        )

    @staticmethod
    def list_projects_response(
        success: bool,
        message: str,
        projects=None,
    ) -> planning_pb2.ListProjectsResponse:
        """Map to ListProjectsResponse."""
        projects = projects or []
        return planning_pb2.ListProjectsResponse(
            success=success,
            message=message,
            projects=[ResponseMapper._project_to_proto(p) for p in projects],
            total_count=len(projects),
        )

    @staticmethod
    def _project_to_proto(project) -> planning_pb2.Project:
        """Convert Project entity to protobuf."""
        return planning_pb2.Project(
            project_id=project.project_id.value,
            name=project.name,
            description=project.description,
            status=project.status.value,
            owner=project.owner,
            created_at=project.created_at.isoformat() + "Z",
            updated_at=project.updated_at.isoformat() + "Z",
        )

    # ========== Epic Mappers ==========

    @staticmethod
    def create_epic_response(
        success: bool,
        message: str,
        epic=None,
    ) -> planning_pb2.CreateEpicResponse:
        """Map to CreateEpicResponse."""
        if not epic:
            return planning_pb2.CreateEpicResponse(
                success=success,
                message=message,
            )

        return planning_pb2.CreateEpicResponse(
            success=success,
            message=message,
            epic=ResponseMapper._epic_to_proto(epic),
        )

    @staticmethod
    def epic_response(epic=None) -> planning_pb2.EpicResponse:
        """Map to EpicResponse."""
        if not epic:
            return planning_pb2.EpicResponse()

        return planning_pb2.EpicResponse(
            epic=ResponseMapper._epic_to_proto(epic),
        )

    @staticmethod
    def list_epics_response(
        success: bool,
        message: str,
        epics=None,
    ) -> planning_pb2.ListEpicsResponse:
        """Map to ListEpicsResponse."""
        epics = epics or []
        return planning_pb2.ListEpicsResponse(
            success=success,
            message=message,
            epics=[ResponseMapper._epic_to_proto(e) for e in epics],
            total_count=len(epics),
        )

    @staticmethod
    def _epic_to_proto(epic) -> planning_pb2.Epic:
        """Convert Epic entity to protobuf."""
        return planning_pb2.Epic(
            epic_id=epic.epic_id.value,
            project_id=epic.project_id.value,
            title=epic.title,
            description=epic.description,
            status=epic.status.value,
            created_at=epic.created_at.isoformat() + "Z",
            updated_at=epic.updated_at.isoformat() + "Z",
        )

    # ========== Task Mappers ==========

    @staticmethod
    def create_task_response(
        success: bool,
        message: str,
        task=None,
    ) -> planning_pb2.CreateTaskResponse:
        """Map to CreateTaskResponse."""
        if not task:
            return planning_pb2.CreateTaskResponse(
                success=success,
                message=message,
            )

        return planning_pb2.CreateTaskResponse(
            success=success,
            message=message,
            task=ResponseMapper._task_to_proto(task),
        )

    @staticmethod
    def task_response(task=None) -> planning_pb2.TaskResponse:
        """Map to TaskResponse."""
        if not task:
            return planning_pb2.TaskResponse()

        return planning_pb2.TaskResponse(
            task=ResponseMapper._task_to_proto(task),
        )

    @staticmethod
    def list_tasks_response(
        success: bool,
        message: str,
        tasks=None,
    ) -> planning_pb2.ListTasksResponse:
        """Map to ListTasksResponse."""
        tasks = tasks or []
        return planning_pb2.ListTasksResponse(
            success=success,
            message=message,
            tasks=[ResponseMapper._task_to_proto(t) for t in tasks],
            total_count=len(tasks),
        )

    @staticmethod
    def _task_to_proto(task) -> planning_pb2.Task:
        """Convert Task entity to protobuf."""
        return planning_pb2.Task(
            task_id=task.task_id.value,
            plan_id=task.plan_id.value,
            story_id=task.story_id.value,
            title=task.title,
            description=task.description,
            type=task.type.value,
            status=task.status.value,
            created_at=task.created_at.isoformat() + "Z",
            updated_at=task.updated_at.isoformat() + "Z",
        )

    # ========== Decision Mappers ==========

    @staticmethod
    def approve_decision_response(
        success: bool,
        message: str,
    ) -> planning_pb2.ApproveDecisionResponse:
        """Map to ApproveDecisionResponse."""
        return planning_pb2.ApproveDecisionResponse(
            success=success,
            message=message,
        )

    @staticmethod
    def reject_decision_response(
        success: bool,
        message: str,
    ) -> planning_pb2.RejectDecisionResponse:
        """Map to RejectDecisionResponse."""
        return planning_pb2.RejectDecisionResponse(
            success=success,
            message=message,
        )

