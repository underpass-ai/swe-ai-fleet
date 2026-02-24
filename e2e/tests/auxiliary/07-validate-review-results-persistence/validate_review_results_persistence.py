#!/usr/bin/env python3
"""E2E Test: Validate Review Results Persistence.

This test validates that review results are correctly persisted in Planning Service:
1. Creates a new backlog review ceremony
2. Waits for deliberations from all 3 roles (ARCHITECT, QA, DEVOPS) for each story
3. Verifies that Planning Service receives AddAgentDeliberation calls
4. Verifies that review results appear in the ceremony
5. Verifies that ceremony transitions to REVIEWING when all stories have complete review results

Flow Verified:
- BRP receives agent.response.completed events
- BRP calls Planning Service AddAgentDeliberation gRPC
- Planning Service persists review results in ceremony
- DeliberationsCompleteProgressConsumer updates ceremony status to REVIEWING

Test Prerequisites:
- Planning Service must be deployed
- Backlog Review Processor must be deployed
- Ray Executor Service must be deployed
- vLLM Service must be accessible
- NATS must be accessible
- Test data must exist (run 02-create-test-data first)
"""

import asyncio
import os
import sys
import time
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


class ValidateReviewResultsPersistenceTest:
    """E2E test for validating review results persistence."""

    def __init__(self) -> None:
        """Initialize with service URLs from environment."""
        # Service URLs (Kubernetes internal DNS)
        self.planning_url = os.getenv(
            "PLANNING_SERVICE_URL",
            "planning.swe-ai-fleet.svc.cluster.local:50054",
        )

        # Test data
        self.created_by = os.getenv("TEST_CREATED_BY", "e2e-test@system.local")
        self.project_name = os.getenv("TEST_PROJECT_NAME", "Test de swe fleet")
        self.epic_title = os.getenv("TEST_EPIC_TITLE", "Autenticacion")

        # Timeouts
        self.review_results_timeout = int(os.getenv("REVIEW_RESULTS_TIMEOUT", "600"))  # 10 minutes
        self.poll_interval = int(os.getenv("POLL_INTERVAL", "10"))  # 10 seconds

        # Discovered entities
        self.project_id: Optional[str] = None
        self.epic_id: Optional[str] = None
        self.story_ids: list[str] = []
        self.ceremony_id: Optional[str] = None

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

    async def find_test_data(self) -> bool:
        """Find test data (project, epic, stories)."""
        if not self.planning_stub:
            print_error("Planning stub not initialized")
            return False

        try:
            # Find project
            print_info(f"Searching for project: '{self.project_name}'...")
            projects_request = planning_pb2.ListProjectsRequest(limit=100)
            projects_response = await self.planning_stub.ListProjects(projects_request)  # type: ignore[union-attr]

            if not projects_response.success:
                print_error(f"Failed to list projects: {projects_response.message}")
                return False

            for project in projects_response.projects:
                if project.name == self.project_name:
                    self.project_id = project.project_id
                    print_success(f"Found project: {self.project_id}")
                    break

            if not self.project_id:
                print_error(f"Project '{self.project_name}' not found")
                return False

            # Find epic
            print_info(f"Searching for epic: '{self.epic_title}'...")
            epics_request = planning_pb2.ListEpicsRequest(project_id=self.project_id, limit=100)
            epics_response = await self.planning_stub.ListEpics(epics_request)  # type: ignore[union-attr]

            if not epics_response.success:
                print_error(f"Failed to list epics: {epics_response.message}")
                return False

            for epic in epics_response.epics:
                if epic.title == self.epic_title:
                    self.epic_id = epic.epic_id
                    print_success(f"Found epic: {self.epic_id}")
                    break

            if not self.epic_id:
                print_error(f"Epic '{self.epic_title}' not found")
                return False

            # Find stories
            print_info(f"Searching for stories in epic: '{self.epic_id}'...")
            stories_request = planning_pb2.ListStoriesRequest(epic_id=self.epic_id, limit=100)
            stories_response = await self.planning_stub.ListStories(stories_request)  # type: ignore[union-attr]

            if not stories_response.success:
                print_error(f"Failed to list stories: {stories_response.message}")
                return False

            self.story_ids = [story.story_id for story in stories_response.stories]
            print_success(f"Found {len(self.story_ids)} stories")

            if len(self.story_ids) == 0:
                print_error("No stories found in epic")
                return False

            return True

        except grpc.RpcError as e:
            print_error(f"gRPC error: {e.code()} - {e.details()}")
            return False
        except Exception as e:
            print_error(f"Error finding test data: {e}")
            return False

    async def create_ceremony(self) -> bool:
        """Create a new backlog review ceremony."""
        if not self.planning_stub:
            print_error("Planning stub not initialized")
            return False

        try:
            print_info("Creating new ceremony for fresh test run...")
            ceremony_request = planning_pb2.CreateBacklogReviewCeremonyRequest(
                created_by=self.created_by,
            )
            ceremony_response = await self.planning_stub.CreateBacklogReviewCeremony(ceremony_request)  # type: ignore[union-attr]

            if not ceremony_response.success:
                print_error(f"Failed to create ceremony: {ceremony_response.message}")
                return False

            self.ceremony_id = ceremony_response.ceremony.ceremony_id
            print_success(f"Ceremony created: {self.ceremony_id}")

            # Add stories to ceremony
            print_info(f"Adding {len(self.story_ids)} stories to ceremony...")
            for story_id in self.story_ids:
                add_story_request = planning_pb2.AddStoriesToReviewRequest(
                    ceremony_id=self.ceremony_id,
                    story_ids=[story_id],
                )
                add_story_response = await self.planning_stub.AddStoriesToReview(add_story_request)  # type: ignore[union-attr]

                if not add_story_response.success:
                    print_warning(f"Failed to add story {story_id}: {add_story_response.message}")

            # Start ceremony
            print_info("Starting ceremony...")
            start_request = planning_pb2.StartBacklogReviewCeremonyRequest(
                ceremony_id=self.ceremony_id,
                started_by=self.created_by,
            )
            start_response = await self.planning_stub.StartBacklogReviewCeremony(start_request)  # type: ignore[union-attr]

            if not start_response.success:
                print_error(f"Failed to start ceremony: {start_response.message}")
                return False

            print_success("Ceremony started successfully")
            return True

        except grpc.RpcError as e:
            print_error(f"gRPC error: {e.code()} - {e.details()}")
            return False
        except Exception as e:
            print_error(f"Error creating ceremony: {e}")
            return False

    async def get_ceremony_status(self) -> Optional[tuple[str, int, int]]:
        """Get ceremony status and review results count.

        Returns:
            Tuple of (status, review_results_count, total_stories) or None if error
        """
        if not self.planning_stub or not self.ceremony_id:
            return None

        try:
            request = planning_pb2.GetBacklogReviewCeremonyRequest(
                ceremony_id=self.ceremony_id
            )
            response = await self.planning_stub.GetBacklogReviewCeremony(request)  # type: ignore[union-attr]

            if not response.success:
                return None

            ceremony = response.ceremony
            status = ceremony.status
            review_results_count = len(ceremony.review_results)
            total_stories = len(ceremony.story_ids)

            return (status, review_results_count, total_stories)

        except grpc.RpcError as e:
            print_warning(f"gRPC error getting ceremony: {e.code()} - {e.details()}")
            return None
        except Exception as e:
            print_warning(f"Error getting ceremony: {e}")
            return None

    async def wait_for_review_results(self) -> bool:
        """Wait for review results to appear in ceremony.

        Returns:
            True if review results appear, False on timeout
        """
        if not self.ceremony_id:
            print_error("Ceremony ID not initialized")
            return False

        print_info(f"Waiting for review results to appear (timeout: {self.review_results_timeout}s)...")
        print_info(f"Poll interval: {self.poll_interval}s")

        start_time = time.time()
        attempt = 0
        max_attempts = self.review_results_timeout // self.poll_interval

        while time.time() - start_time < self.review_results_timeout:
            attempt += 1
            status_info = await self.get_ceremony_status()

            if status_info is None:
                print_warning(f"Could not get ceremony status (attempt {attempt}/{max_attempts})")
                await asyncio.sleep(self.poll_interval)
                continue

            status, review_results_count, total_stories = status_info

            print_info(
                f"Polling ceremony status (attempt {attempt}/{max_attempts})... "
                f"Status: {status}, Review Results: {review_results_count}/{total_stories}"
            )

            # Check if we have review results
            if review_results_count > 0:
                print_success(
                    f"Review results found! Status: {status}, "
                    f"Review Results: {review_results_count}/{total_stories}"
                )
                return True

            # Check if ceremony is in REVIEWING (all stories have review results)
            if status == "REVIEWING":
                print_success(
                    f"Ceremony transitioned to REVIEWING! "
                    f"Review Results: {review_results_count}/{total_stories}"
                )
                return True

            await asyncio.sleep(self.poll_interval)

        print_error(
            f"Timeout: Review results did not appear within {self.review_results_timeout}s timeout"
        )
        return False

    async def verify_review_results_complete(self) -> bool:
        """Verify that all stories have complete review results (all 3 roles).

        Returns:
            True if all stories have complete review results, False otherwise
        """
        if not self.planning_stub or not self.ceremony_id:
            print_error("Planning stub or ceremony_id not initialized")
            return False

        try:
            request = planning_pb2.GetBacklogReviewCeremonyRequest(
                ceremony_id=self.ceremony_id
            )
            response = await self.planning_stub.GetBacklogReviewCeremony(request)  # type: ignore[union-attr]

            if not response.success:
                print_error(f"Failed to get ceremony: {response.message}")
                return False

            ceremony = response.ceremony
            review_results = ceremony.review_results

            print_info(f"Verifying review results for {len(review_results)} stories...")

            # Verify each review result has all 3 roles (check feedback fields)
            for review_result in review_results:
                story_id = review_result.story_id
                architect_feedback = review_result.architect_feedback
                qa_feedback = review_result.qa_feedback
                devops_feedback = review_result.devops_feedback

                # Check that all 3 roles have provided feedback
                missing_roles = []
                if not architect_feedback or not architect_feedback.strip():
                    missing_roles.append("ARCHITECT")
                if not qa_feedback or not qa_feedback.strip():
                    missing_roles.append("QA")
                if not devops_feedback or not devops_feedback.strip():
                    missing_roles.append("DEVOPS")

                print_info(
                    f"Story {story_id}: "
                    f"ARCHITECT={'✓' if architect_feedback and architect_feedback.strip() else '✗'}, "
                    f"QA={'✓' if qa_feedback and qa_feedback.strip() else '✗'}, "
                    f"DEVOPS={'✓' if devops_feedback and devops_feedback.strip() else '✗'}"
                )

                if missing_roles:
                    print_warning(
                        f"Story {story_id} missing feedback from roles: {missing_roles}"
                    )
                    return False

            print_success(
                f"All {len(review_results)} stories have complete review results "
                f"(all 3 roles: ARCHITECT, QA, DEVOPS)"
            )
            return True

        except grpc.RpcError as e:
            print_error(f"gRPC error: {e.code()} - {e.details()}")
            return False
        except Exception as e:
            print_error(f"Error verifying review results: {e}")
            return False

    async def verify_ceremony_status_reviewing(self) -> bool:
        """Verify that ceremony status is REVIEWING.

        Returns:
            True if ceremony is in REVIEWING status, False otherwise
        """
        if not self.ceremony_id:
            print_error("Ceremony ID not initialized")
            return False

        status_info = await self.get_ceremony_status()

        if status_info is None:
            print_error("Could not get ceremony status")
            return False

        status, review_results_count, total_stories = status_info

        if status == "REVIEWING":
            print_success(
                f"Ceremony is in REVIEWING status! "
                f"Review Results: {review_results_count}/{total_stories}"
            )
            return True
        else:
            print_warning(
                f"Ceremony status is {status} (expected: REVIEWING). "
                f"Review Results: {review_results_count}/{total_stories}"
            )
            return False

    async def run(self) -> int:
        """Run the E2E test.

        Returns:
            0 on success, 1 on failure
        """
        print()
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print(f"{Colors.BLUE}🧪 E2E Test: Validate Review Results Persistence{Colors.NC}")
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print()

        print("Configuration:")
        print(f"  Planning Service: {self.planning_url}")
        print(f"  Review Results Timeout: {self.review_results_timeout}s")
        print(f"  Poll Interval: {self.poll_interval}s")
        print()

        try:
            # Setup
            await self.setup()

            # Step 1: Find test data
            print_step(1, "Find Test Data")
            if not await self.find_test_data():
                print_error("Failed to find test data")
                return 1

            # Step 2: Create ceremony
            print_step(2, "Create and Start Ceremony")
            if not await self.create_ceremony():
                print_error("Failed to create ceremony")
                return 1

            # Step 3: Wait for review results
            print_step(3, "Wait for Review Results")
            if not await self.wait_for_review_results():
                print_error("Review results did not appear")
                return 1

            # Step 4: Verify review results are complete
            print_step(4, "Verify Review Results Complete")
            if not await self.verify_review_results_complete():
                print_error("Review results are not complete")
                return 1

            # Step 5: Verify ceremony status is REVIEWING
            print_step(5, "Verify Ceremony Status is REVIEWING")
            if not await self.verify_ceremony_status_reviewing():
                print_error("Ceremony status is not REVIEWING")
                return 1

            print()
            print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
            print(f"{Colors.GREEN}✅ Test completed successfully!{Colors.NC}")
            print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
            print()

            return 0

        except KeyboardInterrupt:
            print()
            print_warning("Test interrupted by user")
            return 1
        except Exception as e:
            print()
            print_error(f"Test failed with exception: {e}")
            import traceback

            traceback.print_exc()
            return 1
        finally:
            await self.cleanup_connections()


async def main() -> None:
    """Main entry point."""
    test = ValidateReviewResultsPersistenceTest()
    exit_code = await test.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
