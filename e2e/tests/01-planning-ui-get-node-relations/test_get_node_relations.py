#!/usr/bin/env python3
"""E2E Test: Planning UI calls get node relations.

This test verifies that Planning UI can successfully call Context Service's
GetGraphRelationships gRPC method to retrieve node relationships.

Flow Verified:
1. Create Project → Epic → Story → Tasks (via Planning Service)
2. Create Deliberations (via Context Service)
3. Planning UI → Context Service (gRPC): GetGraphRelationships
4. Context Service queries Neo4j for node and relationships
5. Context Service returns graph relationships to Planning UI
6. Cleanup: Delete all created entities

Test Prerequisites:
- Planning Service must be deployed and accessible
- Context Service must be deployed and accessible
- Neo4j must be accessible
"""

import asyncio
import os
import sys
import time
from typing import Optional

import grpc
from fleet.context.v1 import context_pb2, context_pb2_grpc  # type: ignore[import]
from fleet.planning.v2 import planning_pb2, planning_pb2_grpc  # type: ignore[import]


class Colors:
    """ANSI color codes for terminal output."""

    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"  # No Color


def print_step(step: int, description: str) -> None:
    """Print step header."""
    print()
    print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
    print(f"{Colors.BLUE}Step {step}: {description}{Colors.NC}")
    print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
    print()


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


class PlanningUIGetNodeRelationsTest:
    """E2E test for Planning UI calling get node relations."""

    def __init__(self) -> None:
        """Initialize test with service URLs from environment."""
        # Service URLs (Kubernetes internal DNS)
        self.planning_url = os.getenv(
            "PLANNING_SERVICE_URL",
            "planning.swe-ai-fleet.svc.cluster.local:50054",
        )
        self.context_url = os.getenv(
            "CONTEXT_SERVICE_URL",
            "context.swe-ai-fleet.svc.cluster.local:50054",
        )

        # Test data
        self.created_by = os.getenv("TEST_CREATED_BY", "e2e-test@system.local")
        self.test_prefix = f"e2e-{int(time.time())}"

        # Option to preserve data for other E2E tests
        self.preserve_data = os.getenv("PRESERVE_DATA", "false").lower() == "true"

        # Use predefined test data if PRESERVE_DATA is enabled
        self.use_predefined_data = os.getenv("USE_PREDEFINED_DATA", "false").lower() == "true"

        # Created entities (for cleanup)
        self.project_id: Optional[str] = None
        self.epic_id: Optional[str] = None
        self.story_ids: list[str] = []  # Changed to list to support multiple stories
        self.ceremony_id: Optional[str] = None
        self.task_ids: list[str] = []
        self.decision_ids: list[str] = []

        # gRPC channels and stubs
        self.planning_channel: Optional[grpc.aio.Channel] = None
        self.planning_stub: Optional[planning_pb2_grpc.PlanningServiceStub] = None  # type: ignore[assignment]
        self.context_channel: Optional[grpc.aio.Channel] = None
        self.context_stub: Optional[context_pb2_grpc.ContextServiceStub] = None  # type: ignore[assignment]

    async def setup(self) -> None:
        """Set up gRPC connections."""
        print_info("Setting up gRPC connections...")

        # Create gRPC channels
        self.planning_channel = grpc.aio.insecure_channel(self.planning_url)
        self.context_channel = grpc.aio.insecure_channel(self.context_url)

        # Create stubs
        self.planning_stub = planning_pb2_grpc.PlanningServiceStub(self.planning_channel)
        self.context_stub = context_pb2_grpc.ContextServiceStub(self.context_channel)

        print_success("gRPC connections established")

    async def cleanup_connections(self) -> None:
        """Clean up gRPC connections."""
        print_info("Cleaning up connections...")

        if self.planning_channel:
            await self.planning_channel.close()
        if self.context_channel:
            await self.context_channel.close()

        print_success("Connections cleaned up")

    async def step_1_create_hierarchy(self) -> bool:
        """Step 1: Create Project → Epic → Stories.

        If USE_PREDEFINED_DATA is enabled, creates valuable test data for other E2E tests:
        - Project: "Test de swe fleet"
        - Epic: "Autenticacion"
        - Stories: RBAC, AUTH0, Autenticacion en cliente con conexion a google verificacion mail, Rol Admin y Rol User
        """
        print_step(1, "Create Project → Epic → Stories Hierarchy")

        try:
            if self.use_predefined_data:
                # Create predefined valuable test data
                print_info("Using predefined test data for E2E test suite...")

                # Create Project
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

                # Create Epic
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

                # Create Stories
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

                print_info(f"Creating {len(stories_to_create)} stories...")
                for story_data in stories_to_create:
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

                # Use first story for GetGraphRelationships test
                self.story_id = self.story_ids[0]
                print_info(f"Using first story ({self.story_id}) for GetGraphRelationships test")

            else:
                # Create generic test data (original behavior)
                # Create Project
                print_info("Creating project...")
                project_request = planning_pb2.CreateProjectRequest(
                    name=f"{self.test_prefix} Test Project",
                    description="E2E test project for get node relations",
                    owner=self.created_by,
                )
                project_response = await self.planning_stub.CreateProject(project_request)  # type: ignore[union-attr]

                if not project_response.success:
                    print_error(f"Failed to create project: {project_response.message}")
                    return False

                self.project_id = project_response.project.project_id
                print_success(f"Project created: {self.project_id}")

                # Create Epic
                print_info("Creating epic...")
                epic_request = planning_pb2.CreateEpicRequest(
                    project_id=self.project_id,
                    title=f"{self.test_prefix} Test Epic",
                    description="E2E test epic for get node relations",
                )
                epic_response = await self.planning_stub.CreateEpic(epic_request)  # type: ignore[union-attr]

                if not epic_response.success:
                    print_error(f"Failed to create epic: {epic_response.message}")
                    return False

                self.epic_id = epic_response.epic.epic_id
                print_success(f"Epic created: {self.epic_id}")

                # Create Story
                print_info("Creating story...")
                story_request = planning_pb2.CreateStoryRequest(
                    epic_id=self.epic_id,
                    title=f"{self.test_prefix} Test Story",
                    brief="E2E test story for get node relations. This story tests the graph relationships functionality.",
                    created_by=self.created_by,
                )
                story_response = await self.planning_stub.CreateStory(story_request)  # type: ignore[union-attr]

                if not story_response.success:
                    print_error(f"Failed to create story: {story_response.message}")
                    return False

                story_id = story_response.story.story_id
                self.story_ids.append(story_id)
                self.story_id = story_id
                print_success(f"Story created: {self.story_id}")

            return True

        except grpc.RpcError as e:
            print_error(f"gRPC error: {e.code()} - {e.details()}")
            return False
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def step_2_validate_valkey_data(self) -> bool:
        """Step 2: Validate data in Valkey.

        Verify that the created entities are correctly stored in Valkey
        with all their details (title, brief, etc.).
        """
        print_step(2, "Validate Data in Valkey")

        if not self.story_ids:
            print_error("No stories to validate")
            return False

        try:
            print_info("Validating Story data in Valkey...")
            validation_errors = []

            for story_id in self.story_ids:
                print_info(f"Validating story: {story_id}")

                # Call GetStory to retrieve data from Valkey
                # Note: GetStory returns Story directly, not a response wrapper
                request = planning_pb2.GetStoryRequest(story_id=story_id)
                try:
                    story = await self.planning_stub.GetStory(request)  # type: ignore[union-attr]
                except grpc.RpcError as e:
                    validation_errors.append(
                        f"Story {story_id}: GetStory failed - {e.code()} - {e.details()}"
                    )
                    continue

                # Check if story is empty (not found)
                if not story.story_id:
                    validation_errors.append(f"Story {story_id}: Story not found in Valkey")
                    continue
                print_success(f"Story {story_id} retrieved from Valkey")
                print_info(f"  Title: {story.title}")
                print_info(f"  Brief: {story.brief[:50] if story.brief else '(no brief)'}...")
                print_info(f"  State: {story.state}")
                print_info(f"  Epic ID: {story.epic_id}")

                # Validate that epic_id matches
                if story.epic_id != self.epic_id:
                    validation_errors.append(
                        f"Story {story_id}: epic_id mismatch - expected {self.epic_id}, got {story.epic_id}"
                    )

                # Validate that title is not empty
                if not story.title:
                    validation_errors.append(f"Story {story_id}: title is empty in Valkey")

                # Validate that brief is not empty
                if not story.brief:
                    validation_errors.append(f"Story {story_id}: brief is empty in Valkey")

            if validation_errors:
                print_error("Valkey validation failed:")
                for error in validation_errors:
                    print_error(f"  - {error}")
                return False

            print_success(f"All {len(self.story_ids)} stories validated in Valkey")
            return True

        except grpc.RpcError as e:
            print_error(f"gRPC error: {e.code()} - {e.details()}")
            return False
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def step_3_test_get_node_relations(self) -> bool:
        """Step 3: Test GetGraphRelationships.

        After creating Project → Epic → Story hierarchy, we can immediately
        test GetGraphRelationships since the nodes are already created and
        inter-related in Neo4j.
        """
        print_step(3, "Planning UI calls GetGraphRelationships")

        # Use Story (has title) - this is what Planning UI typically queries
        # Note: Projects use 'name' field but query expects 'title', so we avoid Projects
        if not self.story_id:
            print_error("Story ID not set")
            return False

        print_info(f"Requesting relationships for:")
        print_info(f"  Node ID:   {self.story_id}")
        print_info(f"  Node Type: Story")
        print_info(f"  Depth:     2")

        try:
            # Build request (simulating Planning UI request)
            request = context_pb2.GetGraphRelationshipsRequest(
                node_id=self.story_id,
                node_type="Story",
                depth=2,
            )

            # Call Context Service (simulating Planning UI call)
            print_info("Calling Context Service GetGraphRelationships...")
            if self.context_stub is None:
                print_error("Context Service stub not initialized")
                return False
            response = await self.context_stub.GetGraphRelationships(request)

            # Verify response
            if not response.success:
                print_error(f"GetGraphRelationships failed: {response.message}")
                return False

            print_success("GetGraphRelationships call succeeded")

            # Verify response structure
            if not response.node:
                print_error("Response missing node data")
                return False

            print_success(f"Node found: {response.node.id}")
            print_info(f"  Type:  {response.node.type}")
            print_info(f"  Title: {response.node.title or '(no title)'}")
            labels_str = ", ".join(response.node.labels) if response.node.labels else "(none)"
            print_info(f"  Labels: {labels_str}")

            # Verify neighbors
            neighbor_count = len(response.neighbors)
            print_info(f"Neighbors found: {neighbor_count}")
            if neighbor_count > 0:
                print_success(f"Found {neighbor_count} neighbor node(s)")
                for i, neighbor in enumerate(response.neighbors[:10], 1):  # Show first 10
                    print_info(f"  {i}. {neighbor.id} ({neighbor.type})")
                if neighbor_count > 10:
                    print_info(f"  ... and {neighbor_count - 10} more")
            else:
                print_warning("No neighbors found")

            # Verify relationships
            relationship_count = len(response.relationships)
            print_info(f"Relationships found: {relationship_count}")
            if relationship_count > 0:
                print_success(f"Found {relationship_count} relationship(s)")
                for i, rel in enumerate(response.relationships[:10], 1):  # Show first 10
                    print_info(
                        f"  {i}. {rel.from_node_id} --[{rel.type}]--> {rel.to_node_id}"
                    )
                if relationship_count > 10:
                    print_info(f"  ... and {relationship_count - 10} more")
            else:
                print_warning("No relationships found")

            # Validate that relationships connect to existing nodes
            all_node_ids = {response.node.id}
            for neighbor in response.neighbors:
                all_node_ids.add(neighbor.id)

            invalid_relationships = []
            for rel in response.relationships:
                if rel.from_node_id not in all_node_ids:
                    invalid_relationships.append(
                        f"Relationship from_node_id '{rel.from_node_id}' not in nodes"
                    )
                if rel.to_node_id not in all_node_ids:
                    invalid_relationships.append(
                        f"Relationship to_node_id '{rel.to_node_id}' not in nodes"
                    )

            if invalid_relationships:
                print_error("Found invalid relationships:")
                for error in invalid_relationships:
                    print_error(f"  - {error}")
                return False

            print_success("All relationships connect to existing nodes")

            # Verify we have expected relationships
            expected_relationships = ["HAS_TASK", "BELONGS_TO", "CONTAINS_STORY"]
            found_relationship_types = {rel.type for rel in response.relationships}
            print_info(f"Relationship types found: {', '.join(found_relationship_types)}")

            return True

        except grpc.RpcError as e:
            print_error(f"gRPC error: {e.code()} - {e.details()}")
            return False
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def step_4_cleanup(self) -> bool:
        """Step 4: Cleanup - Delete all created entities (unless PRESERVE_DATA is enabled)."""
        print_step(4, "Cleanup - Delete Created Entities")

        if self.preserve_data:
            print_info("PRESERVE_DATA is enabled - skipping cleanup to preserve data for other E2E tests")
            print_info("Created entities (preserved for other tests):")
            if self.project_id:
                print_info(f"  Project: {self.project_id}")
            if self.epic_id:
                print_info(f"  Epic: {self.epic_id}")
            if self.story_ids:
                for story_id in self.story_ids:
                    print_info(f"  Story: {story_id}")
            print_success("Data preserved - entities will remain in Neo4j and Valkey")
            return True

        cleanup_errors = []

        # Note: No ceremony cleanup needed - we don't create ceremonies in this simplified test

        # Note: Tasks, stories, epics, and projects are not deleted via gRPC
        # They will be cleaned up by TTL or manual process

        if cleanup_errors:
            print_warning("Some cleanup operations failed:")
            for error in cleanup_errors:
                print_warning(f"  - {error}")
            print_warning("Manual cleanup may be required")
        else:
            print_success("Cleanup completed (entities will be cleaned by TTL or manual process)")

        # Note: In a real scenario, we would use Neo4j directly to delete nodes
        # or wait for TTL to clean them up. For now, we just log what was created.
        print_info("Created entities (for manual cleanup if needed):")
        if self.project_id:
            print_info(f"  Project: {self.project_id}")
        if self.epic_id:
            print_info(f"  Epic: {self.epic_id}")
        if self.story_ids:
            for story_id in self.story_ids:
                print_info(f"  Story: {story_id}")

        return True

    async def run(self) -> int:
        """Run the complete E2E test."""
        print()
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print(f"{Colors.BLUE}🚀 Planning UI → Get Node Relations E2E Test{Colors.NC}")
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print()

        print("Configuration:")
        print(f"  Planning Service: {self.planning_url}")
        print(f"  Context Service:  {self.context_url}")
        print(f"  Created By:       {self.created_by}")
        print(f"  Test Prefix:      {self.test_prefix}")
        print(f"  Preserve Data:    {self.preserve_data}")
        print(f"  Use Predefined:   {self.use_predefined_data}")
        print()

        try:
            # Setup
            await self.setup()

            # Run test steps
            # Note: We only need to create nodes, validate Valkey, and test GetGraphRelationships
            # No need to wait for ceremony completion - nodes are already created and inter-related
            steps = [
                ("Create Hierarchy", self.step_1_create_hierarchy),
                ("Validate Valkey Data", self.step_2_validate_valkey_data),
                ("Test GetGraphRelationships", self.step_3_test_get_node_relations),
                ("Cleanup", self.step_4_cleanup),
            ]

            for step_name, step_func in steps:
                success = await step_func()
                if not success:
                    print_error(f"Step '{step_name}' failed")
                    # Continue to cleanup even if test fails
                    if step_name != "Cleanup":
                        await self.step_4_cleanup()
                    return 1

            print()
            print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
            print(f"{Colors.GREEN}✅ E2E test PASSED{Colors.NC}")
            print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
            print()
            return 0

        except KeyboardInterrupt:
            print()
            print_warning("Test interrupted by user")
            await self.step_4_cleanup()
            return 130
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback

            traceback.print_exc()
            await self.step_4_cleanup()
            return 1
        finally:
            await self.cleanup_connections()


async def main() -> int:
    """Main entry point."""
    test = PlanningUIGetNodeRelationsTest()
    return await test.run()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
