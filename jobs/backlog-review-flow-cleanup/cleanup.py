#!/usr/bin/env python3
"""Cleanup script for Backlog Review Flow E2E test data.

This script cleans up test data created during E2E tests:
- Backlog Review Ceremonies
- Stories
- Epics
- Projects
- Related data in Neo4j and Valkey

Usage:
    Set environment variables to identify what to clean:
    - CLEANUP_CEREMONY_ID: Ceremony ID to cancel/delete
    - CLEANUP_STORY_ID: Story ID to delete
    - CLEANUP_EPIC_ID: Epic ID to delete
    - CLEANUP_PROJECT_ID: Project ID to delete
    - CLEANUP_ALL_E2E: If set to "true", cleans all E2E test data
"""

import os
import sys
from typing import Optional

import grpc
from fleet.planning.v2 import planning_pb2, planning_pb2_grpc

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
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color


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


class BacklogReviewFlowCleanup:
    """Cleanup utility for Backlog Review Flow E2E test data."""

    def __init__(self):
        """Initialize cleanup with service URLs from environment."""
        # Service URLs (Kubernetes internal DNS)
        self.planning_url = os.getenv(
            "PLANNING_SERVICE_URL",
            "planning.swe-ai-fleet.svc.cluster.local:50054"
        )

        # Neo4j connection
        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j.swe-ai-fleet.svc.cluster.local:7687")
        self.neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "")

        # Valkey connection
        self.valkey_host = os.getenv("VALKEY_HOST", "valkey.swe-ai-fleet.svc.cluster.local")
        self.valkey_port = int(os.getenv("VALKEY_PORT", "6379"))

        # Cleanup targets
        self.ceremony_id = os.getenv("CLEANUP_CEREMONY_ID", "").strip()
        self.story_id = os.getenv("CLEANUP_STORY_ID", "").strip()
        self.epic_id = os.getenv("CLEANUP_EPIC_ID", "").strip()
        self.project_id = os.getenv("CLEANUP_PROJECT_ID", "").strip()
        self.cleanup_all_e2e = os.getenv("CLEANUP_ALL_E2E", "false").lower() == "true"
        self.cancelled_by = os.getenv("CLEANUP_CANCELLED_BY", "e2e-cleanup@system.local")

        # gRPC channel and stub
        self.planning_channel: Optional[grpc.aio.Channel] = None
        self.planning_stub: Optional[planning_pb2_grpc.PlanningServiceStub] = None

        # Neo4j and Valkey clients
        self.neo4j_driver = None
        self.valkey_client = None

    def setup(self) -> None:
        """Set up connections."""
        print_info("Setting up connections...")

        # Create gRPC channel
        self.planning_channel = grpc.aio.insecure_channel(self.planning_url)
        self.planning_stub = planning_pb2_grpc.PlanningServiceStub(self.planning_channel)

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

    async def cleanup(self) -> None:
        """Clean up connections."""
        print_info("Cleaning up connections...")

        if self.planning_channel:
            await self.planning_channel.close()

        if self.neo4j_driver:
            self.neo4j_driver.close()

        if self.valkey_client:
            self.valkey_client.close()

        print_success("Cleanup completed")

    async def cancel_ceremony(self, ceremony_id: str) -> bool:
        """Cancel a backlog review ceremony."""
        print_info(f"Cancelling ceremony: {ceremony_id}")

        try:
            request = planning_pb2.CancelBacklogReviewCeremonyRequest(
                ceremony_id=ceremony_id,
                cancelled_by=self.cancelled_by
            )

            response = await self.planning_stub.CancelBacklogReviewCeremony(request)

            if response.success:
                print_success(f"Ceremony cancelled: {ceremony_id}")
                return True
            else:
                print_warning(f"Failed to cancel ceremony: {response.message}")
                return False

        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.NOT_FOUND:
                print_warning(f"Ceremony not found: {ceremony_id}")
                return True  # Already cleaned up
            print_error(f"gRPC error: {e.code()} - {e.details()}")
            return False
        except Exception as e:
            print_error(f"Unexpected error: {e}")
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

    def cleanup_all_e2e_data(self) -> bool:
        """Clean up all E2E test data from Neo4j."""
        if not self.neo4j_driver:
            print_warning("Neo4j not available, skipping cleanup")
            return False

        print_info("Cleaning up all E2E test data...")

        try:
            with self.neo4j_driver.session() as session:
                # Delete ceremonies with E2E test pattern
                ceremonies_query = """
                MATCH (c:BacklogReviewCeremony)
                WHERE c.id STARTS WITH 'BRC-' OR c.id STARTS WITH 'BRC-TEST-'
                DETACH DELETE c
                RETURN count(c) AS deleted
                """
                result = session.run(ceremonies_query)
                record = result.single()
                if record:
                    count = record["deleted"]
                    if count > 0:
                        print_success(f"Deleted {count} ceremony/ceremonies")

                # Delete stories with E2E test pattern
                stories_query = """
                MATCH (s:Story)
                WHERE s.story_id STARTS WITH 'STORY-E2E-' OR s.story_id STARTS WITH 's-E2E-'
                DETACH DELETE s
                RETURN count(s) AS deleted
                """
                result = session.run(stories_query)
                record = result.single()
                if record:
                    count = record["deleted"]
                    if count > 0:
                        print_success(f"Deleted {count} story/stories")

                # Delete epics with E2E test pattern
                epics_query = """
                MATCH (e:Epic)
                WHERE e.epic_id STARTS WITH 'E-E2E-' OR e.title CONTAINS 'E2E Test Epic'
                DETACH DELETE e
                RETURN count(e) AS deleted
                """
                result = session.run(epics_query)
                record = result.single()
                if record:
                    count = record["deleted"]
                    if count > 0:
                        print_success(f"Deleted {count} epic/epics")

                # Delete projects with E2E test pattern
                projects_query = """
                MATCH (p:Project)
                WHERE p.project_id STARTS WITH 'PROJECT-E2E-' OR p.name CONTAINS 'E2E Test Project'
                DETACH DELETE p
                RETURN count(p) AS deleted
                """
                result = session.run(projects_query)
                record = result.single()
                if record:
                    count = record["deleted"]
                    if count > 0:
                        print_success(f"Deleted {count} project/projects")

                return True

        except Exception as e:
            print_error(f"Failed to cleanup E2E data: {e}")
            return False

    def cleanup_valkey_e2e_data(self) -> bool:
        """Clean up all E2E test data from Valkey."""
        if not self.valkey_client:
            print_warning("Valkey not available, skipping cleanup")
            return False

        print_info("Cleaning up E2E test data from Valkey...")

        try:
            # Scan all keys and filter for E2E test patterns
            deleted_count = 0
            cursor = 0
            patterns = [
                "ceremony:BRC-",
                "ceremony:BRC-TEST-",
                "story:STORY-E2E-",
                "story:s-E2E-",
                "epic:E-E2E-",
                "project:PROJECT-E2E-",
            ]

            while True:
                cursor, keys = self.valkey_client.scan(cursor, count=1000)
                for key in keys:
                    # Check if key matches any E2E test pattern
                    if any(key.startswith(pattern) for pattern in patterns):
                        self.valkey_client.delete(key)
                        deleted_count += 1
                        print_info(f"  Deleted: {key}")

                if cursor == 0:
                    break

            if deleted_count > 0:
                print_success(f"Deleted {deleted_count} key(s) from Valkey")
            else:
                print_info("No E2E test keys found in Valkey")

            return True

        except Exception as e:
            print_error(f"Failed to cleanup Valkey data: {e}")
            return False

    def _print_header(self) -> None:
        """Print cleanup header."""
        print()
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print(f"{Colors.BLUE}🧹 Backlog Review Flow E2E Test Data Cleanup{Colors.NC}")
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print()

    def _print_configuration(self) -> None:
        """Print configuration information."""
        print("Configuration:")
        print(f"  Planning Service:  {self.planning_url}")
        print(f"  Neo4j:             {self.neo4j_uri}")
        print(f"  Valkey:            {self.valkey_host}:{self.valkey_port}")
        print()

    def _print_targets(self) -> bool:
        """Print cleanup targets and validate. Returns True if there are targets."""
        print("Cleanup Targets:")
        if self.cleanup_all_e2e:
            print("  Mode:             CLEAN ALL E2E TEST DATA")
            return True

        if self.ceremony_id:
            print(f"  Ceremony ID:      {self.ceremony_id}")
        if self.story_id:
            print(f"  Story ID:         {self.story_id}")
        if self.epic_id:
            print(f"  Epic ID:          {self.epic_id}")
        if self.project_id:
            print(f"  Project ID:       {self.project_id}")

        if not any([self.ceremony_id, self.story_id, self.epic_id, self.project_id]):
            print("  No specific targets - nothing to clean")
            return False
        return True

    def _print_section_header(self, title: str) -> None:
        """Print a section header."""
        print()
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print(f"{Colors.BLUE}{title}{Colors.NC}")
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print()

    async def _cleanup_ceremony(self) -> bool:
        """Clean up a ceremony. Returns True if successful."""
        self._print_section_header(f"Cleaning Ceremony: {self.ceremony_id}")
        await self.cancel_ceremony(self.ceremony_id)
        self.delete_from_neo4j("BacklogReviewCeremony", self.ceremony_id)
        self.delete_from_valkey(f"ceremony:{self.ceremony_id}")
        return True

    def _cleanup_entity(self, entity_type: str, entity_id: str, valkey_prefix: str) -> bool:
        """Clean up an entity (story, epic, project). Returns True if successful."""
        self._print_section_header(f"Cleaning {entity_type}: {entity_id}")
        self.delete_from_neo4j(entity_type, entity_id)
        self.delete_from_valkey(f"{valkey_prefix}:{entity_id}")
        return True

    async def _cleanup_specific_targets(self) -> bool:
        """Clean up specific targets. Returns True if successful."""
        success = True
        if self.ceremony_id:
            await self._cleanup_ceremony()
        if self.story_id:
            self._cleanup_entity("Story", self.story_id, "story")
        if self.epic_id:
            self._cleanup_entity("Epic", self.epic_id, "epic")
        if self.project_id:
            self._cleanup_entity("Project", self.project_id, "project")
        return success

    def _print_summary(self, success: bool) -> None:
        """Print cleanup summary."""
        print()
        print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
        if success:
            print(f"{Colors.GREEN}✅ Cleanup completed successfully{Colors.NC}")
        else:
            print(f"{Colors.YELLOW}⚠ Cleanup completed with warnings{Colors.NC}")
        print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
        print()

    async def run(self) -> int:
        """Run the cleanup."""
        self._print_header()
        self._print_configuration()

        if not self._print_targets():
            return 0

        try:
            self.setup()
            success = True

            if self.cleanup_all_e2e:
                print_info("Cleaning all E2E test data...")
                success = self.cleanup_all_e2e_data() and success
                success = self.cleanup_valkey_e2e_data() and success
            else:
                await self._cleanup_specific_targets()

            self._print_summary(success)
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
            await self.cleanup()


async def main() -> int:
    """Main entry point."""
    cleanup = BacklogReviewFlowCleanup()
    return await cleanup.run()


if __name__ == "__main__":
    import asyncio
    exit_code = asyncio.run(main())
    sys.exit(exit_code)









