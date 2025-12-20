#!/usr/bin/env python3
"""E2E Test Data Cleanup Script.

This script cleans up test data created by create_test_data.py:
- Project: "Test de swe fleet"
- Epic: "Autenticacion"
- Stories: RBAC, AUTH0, Autenticacion en cliente con conexion a google verificacion mail, Rol Admin y Rol User

Usage:
    Set environment variables:
    - CLEANUP_PROJECT_ID: Project ID to delete (optional, will search by name if not provided)
    - CLEANUP_PROJECT_NAME: Project name to search for (default: "Test de swe fleet")
"""

import asyncio
import os
import sys
from typing import Optional

import grpc
from fleet.planning.v2 import planning_pb2, planning_pb2_grpc  # type: ignore[import]

# Neo4j and Valkey for cleanup
try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False

try:
    import valkey
    VALKEY_AVAILABLE = True
except ImportError:
    VALKEY_AVAILABLE = False


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


class TestDataCleanup:
    """Cleans up test data created by create_test_data.py."""

    def __init__(self) -> None:
        """Initialize with service URLs from environment."""
        # Service URLs (Kubernetes internal DNS)
        self.planning_url = os.getenv(
            "PLANNING_SERVICE_URL",
            "planning.swe-ai-fleet.svc.cluster.local:50054",
        )

        # Neo4j connection
        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j.swe-ai-fleet.svc.cluster.local:7687")
        self.neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "")

        # Valkey connection
        self.valkey_host = os.getenv("VALKEY_HOST", "valkey.swe-ai-fleet.svc.cluster.local")
        self.valkey_port = int(os.getenv("VALKEY_PORT", "6379"))

        # Cleanup targets
        self.project_id = os.getenv("CLEANUP_PROJECT_ID", "").strip()
        self.project_name = os.getenv("CLEANUP_PROJECT_NAME", "Test de swe fleet").strip()

        # gRPC channels and stubs
        self.planning_channel: Optional[grpc.aio.Channel] = None
        self.planning_stub: Optional[planning_pb2_grpc.PlanningServiceStub] = None  # type: ignore[assignment]

        # Neo4j and Valkey clients
        self.neo4j_driver = None
        self.valkey_client = None

        # Discovered entities
        self.discovered_epic_ids: list[str] = []
        self.discovered_story_ids: list[str] = []

    async def setup(self) -> None:
        """Set up connections."""
        print_info("Setting up connections...")

        # Create gRPC channel
        self.planning_channel = grpc.aio.insecure_channel(self.planning_url)
        self.planning_stub = planning_pb2_grpc.PlanningServiceStub(self.planning_channel)  # type: ignore[assignment]

        # Set up Neo4j
        if NEO4J_AVAILABLE and self.neo4j_password:
            try:
                self.neo4j_driver = GraphDatabase.driver(
                    self.neo4j_uri,
                    auth=(self.neo4j_username, self.neo4j_password)
                )
                self.neo4j_driver.verify_connectivity()
                print_success("Neo4j connection established")
            except Exception as e:
                print_warning(f"Neo4j connection failed: {e}")

        # Set up Valkey
        if VALKEY_AVAILABLE:
            try:
                self.valkey_client = valkey.Valkey(
                    host=self.valkey_host,
                    port=self.valkey_port,
                    decode_responses=True
                )
                self.valkey_client.ping()
                print_success("Valkey connection established")
            except Exception as e:
                print_warning(f"Valkey connection failed: {e}")

        print_success("Setup completed")

    async def cleanup_connections(self) -> None:
        """Clean up connections."""
        print_info("Cleaning up connections...")

        if self.planning_channel:
            await self.planning_channel.close()

        if self.neo4j_driver:
            self.neo4j_driver.close()

        if self.valkey_client:
            self.valkey_client.close()

        print_success("Connections cleaned up")

    async def find_project_by_name(self) -> Optional[str]:
        """Find project ID by name using gRPC."""
        if not self.planning_stub:
            return None

        try:
            print_info(f"Searching for project: '{self.project_name}'...")
            request = planning_pb2.ListProjectsRequest(limit=100)
            response = await self.planning_stub.ListProjects(request)  # type: ignore[union-attr]

            if not response.success:
                print_warning(f"Failed to list projects: {response.message}")
                return None

            for project in response.projects:
                if project.name == self.project_name:
                    print_success(f"Found project: {project.project_id} - {project.name}")
                    return project.project_id

            print_warning(f"Project '{self.project_name}' not found")
            return None

        except grpc.RpcError as e:
            print_error(f"gRPC error: {e.code()} - {e.details()}")
            return None
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            return None

    async def discover_related_entities(self) -> bool:
        """Discover epic and story IDs related to the project."""
        if not self.project_id:
            print_error("Project ID not set")
            return False

        if not self.neo4j_driver:
            print_warning("Neo4j not available, cannot discover related entities")
            return False

        try:
            print_info("Discovering related entities from Neo4j...")

            with self.neo4j_driver.session() as session:
                # Find epics
                epic_query = """
                MATCH (p:Project {id: $project_id})<-[:BELONGS_TO]-(e:Epic)
                RETURN e.id AS epic_id
                """
                result = session.run(epic_query, project_id=self.project_id)
                for record in result:
                    epic_id = record["epic_id"]
                    self.discovered_epic_ids.append(epic_id)
                    print_info(f"  Found epic: {epic_id}")

                # Find stories for each epic
                for epic_id in self.discovered_epic_ids:
                    story_query = """
                    MATCH (e:Epic {id: $epic_id})<-[:BELONGS_TO]-(s:Story)
                    RETURN s.id AS story_id
                    """
                    result = session.run(story_query, epic_id=epic_id)
                    for record in result:
                        story_id = record["story_id"]
                        self.discovered_story_ids.append(story_id)
                        print_info(f"  Found story: {story_id}")

            print_success(f"Discovered {len(self.discovered_epic_ids)} epic(s) and {len(self.discovered_story_ids)} story/stories")
            return True

        except Exception as e:
            print_error(f"Failed to discover entities: {e}")
            return False

    def delete_from_neo4j(self, node_type: str, node_id: str) -> bool:
        """Delete a node from Neo4j."""
        if not self.neo4j_driver:
            print_warning("Neo4j not available, skipping deletion")
            return False

        try:
            with self.neo4j_driver.session() as session:
                # Delete node and all its relationships
                query = f"""
                MATCH (n:{node_type} {{id: $id}})
                DETACH DELETE n
                RETURN count(n) AS deleted
                """
                result = session.run(query, id=node_id)
                record = result.single()
                if record and record["deleted"] > 0:
                    print_success(f"Deleted {node_type} from Neo4j: {node_id}")
                    return True
                else:
                    print_warning(f"{node_type} not found in Neo4j: {node_id}")
                    return True  # Already deleted
        except Exception as e:
            print_error(f"Failed to delete {node_type} from Neo4j: {e}")
            return False

    def delete_from_valkey(self, key: str) -> bool:
        """Delete a key from Valkey."""
        if not self.valkey_client:
            print_warning("Valkey not available, skipping deletion")
            return False

        try:
            deleted = self.valkey_client.delete(key)
            if deleted:
                print_success(f"Deleted key from Valkey: {key}")
            else:
                print_warning(f"Key not found in Valkey: {key}")
            return True
        except Exception as e:
            print_error(f"Failed to delete key from Valkey: {e}")
            return False

    async def cleanup_stories(self) -> bool:
        """Clean up stories."""
        print_step(1, "Cleanup Stories")

        if not self.discovered_story_ids:
            print_info("No stories to clean up")
            return True

        success = True
        for story_id in self.discovered_story_ids:
            print_info(f"Deleting story: {story_id}...")
            # Delete from Neo4j
            success = self.delete_from_neo4j("Story", story_id) and success
            # Delete from Valkey
            success = self.delete_from_valkey(f"story:{story_id}") and success
            # Delete FSM state
            success = self.delete_from_valkey(f"story:{story_id}:state") and success

        return success

    async def cleanup_epics(self) -> bool:
        """Clean up epics."""
        print_step(2, "Cleanup Epics")

        if not self.discovered_epic_ids:
            print_info("No epics to clean up")
            return True

        success = True
        for epic_id in self.discovered_epic_ids:
            print_info(f"Deleting epic: {epic_id}...")
            # Delete from Neo4j
            success = self.delete_from_neo4j("Epic", epic_id) and success
            # Delete from Valkey
            success = self.delete_from_valkey(f"epic:{epic_id}") and success

        return success

    async def cleanup_project(self) -> bool:
        """Clean up project."""
        print_step(3, "Cleanup Project")

        if not self.project_id:
            print_error("Project ID not set")
            return False

        print_info(f"Deleting project: {self.project_id}...")
        # Delete from Neo4j
        success = self.delete_from_neo4j("Project", self.project_id)
        # Delete from Valkey
        success = self.delete_from_valkey(f"project:{self.project_id}") and success

        return success

    async def run(self) -> int:
        """Run the cleanup."""
        print()
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print(f"{Colors.BLUE}🧹 E2E Test Data Cleanup{Colors.NC}")
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print()

        print("Configuration:")
        print(f"  Planning Service: {self.planning_url}")
        print(f"  Neo4j:            {self.neo4j_uri}")
        print(f"  Valkey:           {self.valkey_host}:{self.valkey_port}")
        print(f"  Project Name:     {self.project_name}")
        if self.project_id:
            print(f"  Project ID:       {self.project_id}")
        print()

        try:
            # Setup
            await self.setup()

            # Find project if ID not provided
            if not self.project_id:
                self.project_id = await self.find_project_by_name()
                if not self.project_id:
                    print_error("Project not found")
                    return 1

            # Discover related entities
            await self.discover_related_entities()

            # Cleanup in reverse order (stories -> epics -> project)
            steps = [
                ("Cleanup Stories", self.cleanup_stories),
                ("Cleanup Epics", self.cleanup_epics),
                ("Cleanup Project", self.cleanup_project),
            ]

            success = True
            for step_name, step_func in steps:
                result = await step_func()
                if not result:
                    print_warning(f"Step '{step_name}' had issues")
                    success = False

            print()
            print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
            if success:
                print(f"{Colors.GREEN}✅ Cleanup completed successfully{Colors.NC}")
            else:
                print(f"{Colors.YELLOW}⚠ Cleanup completed with warnings{Colors.NC}")
            print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
            print()

            return 0 if success else 1

        except KeyboardInterrupt:
            print()
            print_warning("Cleanup interrupted by user")
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
    cleanup = TestDataCleanup()
    return await cleanup.run()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
