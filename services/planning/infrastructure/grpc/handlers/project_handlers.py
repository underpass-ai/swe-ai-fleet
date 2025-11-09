"""Project management gRPC handlers.

Handles Project-related RPCs following Hexagonal Architecture.
"""

import logging

import grpc

from planning.application.usecases.create_project_usecase import CreateProjectUseCase
from planning.application.usecases.get_project_usecase import GetProjectUseCase
from planning.application.usecases.list_projects_usecase import ListProjectsUseCase
from planning.domain.value_objects.project_id import ProjectId
from planning.gen import planning_pb2
from services.planning.infrastructure.grpc.mappers.response_mapper import ResponseMapper

logger = logging.getLogger(__name__)


class ProjectHandlers:
    """Handlers for Project aggregate (3 RPCs).

    Responsibility: Handle gRPC requests for Project management.

    Following Hexagonal Architecture:
    - Receives gRPC requests (presentation)
    - Delegates to use cases (application)
    - Maps responses via mapper (infrastructure)
    - No business logic here
    """

    def __init__(
        self,
        create_project_uc: CreateProjectUseCase,
        get_project_uc: GetProjectUseCase,
        list_projects_uc: ListProjectsUseCase,
    ):
        """Initialize with use case injection (DI).
        
        Args:
            create_project_uc: Use case for creating projects
            get_project_uc: Use case for retrieving a project
            list_projects_uc: Use case for listing projects
        """
        self._create_project_uc = create_project_uc
        self._get_project_uc = get_project_uc
        self._list_projects_uc = list_projects_uc

    async def create_project(self, request, context) -> planning_pb2.CreateProjectResponse:
        """Handle CreateProject RPC.

        Args:
            request: CreateProjectRequest
            context: gRPC context

        Returns:
            CreateProjectResponse
        """
        try:
            logger.info(f"CreateProject: name={request.name}")

            # Delegate to use case (application layer)
            project = await self._create_project_uc.execute(
                name=request.name,
                description=request.description,
                owner=request.owner,
            )

            # Map response (infrastructure)
            return ResponseMapper.create_project_response(
                success=True,
                message=f"Project created: {project.project_id.value}",
                project=project,
            )

        except ValueError as e:
            logger.warning(f"CreateProject validation error: {e}")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            return ResponseMapper.create_project_response(
                success=False,
                message=str(e),
            )

        except Exception as e:
            logger.error(f"CreateProject error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            return ResponseMapper.create_project_response(
                success=False,
                message=f"Internal error: {str(e)}",
            )

    async def get_project(self, request, context) -> planning_pb2.ProjectResponse:
        """Handle GetProject RPC."""
        try:
            logger.info(f"GetProject: project_id={request.project_id}")

            project_id = ProjectId(value=request.project_id)
            
            # Delegate to use case (application layer)
            project = await self._get_project_uc.execute(project_id)

            if not project:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return ResponseMapper.project_response(
                    success=False,
                    message=f"Project not found: {request.project_id}",
                )

            return ResponseMapper.project_response(
                success=True,
                message="Project retrieved successfully",
                project=project,
            )

        except Exception as e:
            logger.error(f"GetProject error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            return ResponseMapper.project_response(
                success=False,
                message=f"Internal error: {str(e)}",
            )

    async def list_projects(self, request, context) -> planning_pb2.ListProjectsResponse:
        """Handle ListProjects RPC."""
        try:
            limit = request.limit if request.limit > 0 else 100
            offset = request.offset if request.offset >= 0 else 0
            
            logger.info(f"ListProjects: limit={limit}, offset={offset}")

            # Delegate to use case (application layer)
            projects = await self._list_projects_uc.execute(limit=limit, offset=offset)

            return ResponseMapper.list_projects_response(
                success=True,
                message=f"Retrieved {len(projects)} projects",
                projects=projects,
            )

        except Exception as e:
            logger.error(f"ListProjects error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            return ResponseMapper.list_projects_response(
                success=False,
                message=f"Internal error: {str(e)}",
            )

