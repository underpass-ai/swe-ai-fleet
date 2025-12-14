#!/usr/bin/env python3
"""E2E Test Data Creation Script.

This script creates valuable test data for E2E tests:
- Project: "Test de swe fleet"
- Epic: "Autenticacion"
- Stories:
  - RBAC
  - AUTH0
  - Autenticacion en cliente con conexion a google verificacion mail
  - Rol Admin y Rol User

Usage:
    Set PRESERVE_DATA=true to keep the data (default: true)
"""

import asyncio
import os
import sys
from typing import Optional

import grpc
from fleet.planning.v2 import planning_pb2, planning_pb2_grpc  # type: ignore[import]


class Colors:
    """ANSI color codes for terminal output."""

    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"  # No Color


def print_success(message: str) -> None:
    """Print success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.NC}")


def print_error(message: str) -> None:
    """Print error message."""
    print(f"{Colors.RED}✗ {message}{Colors.NC}")


def print_warning(message: str) -> None:
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.NC}")


def print_info(message: str) -> None:
    """Print info message."""
    print(f"{Colors.YELLOW}ℹ {message}{Colors.NC}")


def print_step(step: int, description: str) -> None:
    """Print step header."""
    print()
    print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
    print(f"{Colors.BLUE}Step {step}: {description}{Colors.NC}")
    print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
    print()


class TestDataCreator:
    """Creates valuable test data for E2E tests."""

    def __init__(self) -> None:
        """Initialize with service URLs from environment."""
        # Service URLs (Kubernetes internal DNS)
        self.planning_url = os.getenv(
            "PLANNING_SERVICE_URL",
            "planning.swe-ai-fleet.svc.cluster.local:50054",
        )

        # Test data
        self.created_by = os.getenv("TEST_CREATED_BY", "e2e-test@system.local")

        # Created entities
        self.project_id: Optional[str] = None
        self.epic_id: Optional[str] = None
        self.story_ids: list[str] = []

        # gRPC channels and stubs
        self.planning_channel: Optional[grpc.aio.Channel] = None
        self.planning_stub: Optional[planning_pb2_grpc.PlanningServiceStub] = None  # type: ignore[assignment]

    async def setup(self) -> None:
        """Set up gRPC connections."""
        print_info("Setting up gRPC connections...")

        self.planning_channel = grpc.aio.insecure_channel(self.planning_url)
        self.planning_stub = planning_pb2_grpc.PlanningServiceStub(self.planning_channel)  # type: ignore[assignment]

        print_success("gRPC connections established")

    async def cleanup_connections(self) -> None:
        """Clean up gRPC connections."""
        print_info("Cleaning up connections...")

        if self.planning_channel:
            await self.planning_channel.close()

        print_success("Connections cleaned up")

    async def create_project(self) -> bool:
        """Create Project: 'Test de swe fleet'."""
        print_step(1, "Create Project: Test de swe fleet")

        try:
            print_info("Creating project: 'Test de swe fleet'...")
            project_request = planning_pb2.CreateProjectRequest(
                name="Test de swe fleet",
                description="Proyecto de prueba para tests E2E del sistema SWE Fleet",
                owner=self.created_by,
            )
            project_response = await self.planning_stub.CreateProject(project_request)  # type: ignore[union-attr]

            if not project_response.success:
                print_error(f"Failed to create project: {project_response.message}")
                return False

            self.project_id = project_response.project.project_id
            print_success(f"Project created: {self.project_id}")
            print_info(f"  Name: Test de swe fleet")
            return True

        except grpc.RpcError as e:
            print_error(f"gRPC error: {e.code()} - {e.details()}")
            return False
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def create_epic(self) -> bool:
        """Create Epic: 'Autenticacion'."""
        print_step(2, "Create Epic: Autenticacion")

        if not self.project_id:
            print_error("Project ID not set")
            return False

        try:
            print_info("Creating epic: 'Autenticacion'...")
            epic_request = planning_pb2.CreateEpicRequest(
                project_id=self.project_id,
                title="Autenticacion",
                description="Épica de autenticación y autorización para el sistema",
            )
            epic_response = await self.planning_stub.CreateEpic(epic_request)  # type: ignore[union-attr]

            if not epic_response.success:
                print_error(f"Failed to create epic: {epic_response.message}")
                return False

            self.epic_id = epic_response.epic.epic_id
            print_success(f"Epic created: {self.epic_id}")
            print_info(f"  Title: Autenticacion")
            return True

        except grpc.RpcError as e:
            print_error(f"gRPC error: {e.code()} - {e.details()}")
            return False
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def create_stories(self) -> bool:
        """Create Stories for the Epic."""
        print_step(3, "Create Stories")

        if not self.epic_id:
            print_error("Epic ID not set")
            return False

        stories_to_create = [
            {
                "title": "RBAC",
                "brief": "Implementar sistema de control de acceso basado en roles (Role-Based Access Control)",
            },
            {
                "title": "AUTH0",
                "brief": "Integración con Auth0 para autenticación y gestión de usuarios",
            },
            {
                "title": "Autenticacion en cliente con conexion a google verificacion mail",
                "brief": "Implementar autenticación en el cliente con conexión a Google y verificación de email",
            },
            {
                "title": "Rol Admin y Rol User",
                "brief": "Definir e implementar roles de administrador y usuario en el sistema",
            },
        ]

        try:
            print_info(f"Creating {len(stories_to_create)} stories...")
            for story_data in stories_to_create:
                print_info(f"Creating story: '{story_data['title']}'...")
                story_request = planning_pb2.CreateStoryRequest(
                    epic_id=self.epic_id,
                    title=story_data["title"],
                    brief=story_data["brief"],
                    created_by=self.created_by,
                )
                story_response = await self.planning_stub.CreateStory(story_request)  # type: ignore[union-attr]

                if not story_response.success:
                    print_error(f"Failed to create story '{story_data['title']}': {story_response.message}")
                    continue

                story_id = story_response.story.story_id
                self.story_ids.append(story_id)
                print_success(f"Story created: {story_id} - {story_data['title']}")

            if not self.story_ids:
                print_error("Failed to create any stories")
                return False

            print_success(f"Created {len(self.story_ids)} stories successfully")
            return True

        except grpc.RpcError as e:
            print_error(f"gRPC error: {e.code()} - {e.details()}")
            return False
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def print_summary(self) -> None:
        """Print summary of created entities."""
        print()
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print(f"{Colors.BLUE}📊 Created Test Data Summary{Colors.NC}")
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print()
        print("Created entities (preserved for E2E tests):")
        if self.project_id:
            print(f"  Project: {self.project_id} - 'Test de swe fleet'")
        if self.epic_id:
            print(f"  Epic: {self.epic_id} - 'Autenticacion'")
        if self.story_ids:
            print(f"  Stories ({len(self.story_ids)}):")
            for story_id in self.story_ids:
                print(f"    - {story_id}")
        print()
        print(f"{Colors.GREEN}✓ Test data created successfully and preserved{Colors.NC}")
        print()

    async def run(self) -> int:
        """Run the test data creation."""
        print()
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print(f"{Colors.BLUE}📦 E2E Test Data Creation{Colors.NC}")
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print()

        print("Configuration:")
        print(f"  Planning Service: {self.planning_url}")
        print(f"  Created By:       {self.created_by}")
        print()

        try:
            # Setup
            await self.setup()

            # Create entities
            steps = [
                ("Create Project", self.create_project),
                ("Create Epic", self.create_epic),
                ("Create Stories", self.create_stories),
            ]

            for step_name, step_func in steps:
                success = await step_func()
                if not success:
                    print_error(f"Step '{step_name}' failed")
                    return 1

            # Print summary
            await self.print_summary()

            print()
            print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
            print(f"{Colors.GREEN}✅ Test Data Creation Completed{Colors.NC}")
            print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
            print()
            return 0

        except KeyboardInterrupt:
            print()
            print_warning("Creation interrupted by user")
            return 130
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback

            traceback.print_exc()
            return 1
        finally:
            await self.cleanup_connections()


async def main() -> int:
    """Main entry point."""
    creator = TestDataCreator()
    return await creator.run()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
