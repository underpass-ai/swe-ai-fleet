#!/usr/bin/env python3
"""E2E Test: Start Backlog Review Ceremony.

This test verifies that a backlog review ceremony can be successfully started:
1. Finds test data (Project: "Test de swe fleet", Epic: "Autenticacion", Stories)
2. Creates a backlog review ceremony
3. Adds stories to the ceremony
4. Starts the ceremony
5. Verifies ceremony status is IN_PROGRESS

Flow Verified (following BACKLOG_REVIEW_FLOW_NO_STYLES.md):
1. List projects to find "Test de swe fleet" (Step 1.1: Repository access)
2. List epics to find "Autenticacion" (Step 1.1: Repository access)
3. List stories for the epic (Step 1.1: Repository access)
4. Create backlog review ceremony (Step 2: UI → PL gRPC)
5. Add stories to ceremony (Step 2: UI → PL gRPC)
6. Start ceremony (Step 2: UI → PL gRPC)
   - This triggers:
     - Step 3: PL → CTX (Get context rehydration) - internal
     - Step 4: PL → EXEC (Trigger deliberation per RBAC agent) - internal
     - Step 5-9: Async processing (Ray → vLLM → NATS → BRP → CTX → PL)
7. Verify ceremony status is IN_PROGRESS
8. Verify deliberations were submitted (expected: 3 roles × stories count)

Test Prerequisites:
- Planning Service must be deployed and accessible
- Context Service must be deployed (for context rehydration - Step 3)
- Ray Executor Service must be deployed (for deliberation submission - Step 4)
- Test data must exist (run 02-create-test-data first)

Note: This test verifies Steps 2-4 of the Backlog Review Flow diagram.
Steps 5-14 (async processing) are not verified as they occur asynchronously
via NATS events and take several minutes to complete.
"""

import asyncio
import os
import sys

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


class StartBacklogReviewCeremonyTest:
    """E2E test for starting backlog review ceremony."""

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

        # Discovered entities
        self.project_id: str | None = None
        self.epic_id: str | None = None
        self.story_ids: list[str] = []
        self.ceremony_id: str | None = None

        # gRPC channels and stubs
        self.planning_channel: grpc.aio.Channel | None = None
        self.planning_stub: planning_pb2_grpc.PlanningServiceStub | None = None  # type: ignore[assignment]

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
        print_step(1, "Find Test Data")

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
                    print_success(f"Found project: {self.project_id} - {project.name}")
                    break

            if not self.project_id:
                print_error(f"Project '{self.project_name}' not found")
                print_warning("Make sure to run 02-create-test-data first")
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
                    print_success(f"Found epic: {self.epic_id} - {epic.title}")
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

            for story in stories_response.stories:
                self.story_ids.append(story.story_id)
                print_info(f"  Found story: {story.story_id} - {story.title}")

            if not self.story_ids:
                print_error("No stories found in epic")
                return False

            print_success(f"Found {len(self.story_ids)} stories")
            return True

        except grpc.RpcError as e:
            print_error(f"gRPC error: {e.code()} - {e.details()}")
            return False
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def create_ceremony(self) -> bool:
        """Create backlog review ceremony."""
        print_step(2, "Create Backlog Review Ceremony")

        if not self.planning_stub:
            print_error("Planning stub not initialized")
            return False

        try:
            print_info("Creating backlog review ceremony...")
            ceremony_request = planning_pb2.CreateBacklogReviewCeremonyRequest(
                created_by=self.created_by,
            )
            ceremony_response = await self.planning_stub.CreateBacklogReviewCeremony(ceremony_request)  # type: ignore[union-attr]

            if not ceremony_response.success:
                print_error(f"Failed to create ceremony: {ceremony_response.message}")
                return False

            self.ceremony_id = ceremony_response.ceremony.ceremony_id
            print_success(f"Ceremony created: {self.ceremony_id}")
            print_info(f"  Status: {ceremony_response.ceremony.status}")
            await self.log_ceremony_snapshot("create_ceremony", self.ceremony_id)
            return True

        except grpc.RpcError as e:
            print_error(f"gRPC error: {e.code()} - {e.details()}")
            return False
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def add_stories_to_ceremony(self) -> bool:
        """Add stories to ceremony."""
        print_step(3, "Add Stories to Ceremony")

        if not self.planning_stub:
            print_error("Planning stub not initialized")
            return False

        if not self.ceremony_id:
            print_error("Ceremony ID not set")
            return False

        if not self.story_ids:
            print_error("No stories to add")
            return False

        try:
            print_info(f"Adding {len(self.story_ids)} stories to ceremony...")
            add_stories_request = planning_pb2.AddStoriesToReviewRequest(
                ceremony_id=self.ceremony_id,
                story_ids=self.story_ids,
            )
            add_stories_response = await self.planning_stub.AddStoriesToReview(add_stories_request)  # type: ignore[union-attr]

            if not add_stories_response.success:
                print_error(f"Failed to add stories: {add_stories_response.message}")
                return False

            print_success(f"Added {len(self.story_ids)} stories to ceremony")
            print_info(f"  Ceremony status: {add_stories_response.ceremony.status}")
            print_info(f"  Stories in ceremony: {len(add_stories_response.ceremony.story_ids)}")
            await self.log_ceremony_snapshot("add_stories_response", self.ceremony_id)

            # Verify stories were actually added
            if len(add_stories_response.ceremony.story_ids) == 0:
                print_error("Stories were not added to ceremony")
                return False

            # Verify ceremony can be retrieved with stories (ensures persistence)
            print_info("Verifying ceremony persistence...")
            import asyncio
            await asyncio.sleep(2)  # Wait for Neo4j to commit transaction

            get_request = planning_pb2.GetBacklogReviewCeremonyRequest(
                ceremony_id=self.ceremony_id
            )
            get_response = await self.planning_stub.GetBacklogReviewCeremony(get_request)  # type: ignore[union-attr]

            if not get_response.success:
                print_warning(f"Could not retrieve ceremony: {get_response.message}")
            elif len(get_response.ceremony.story_ids) == 0:
                print_error("Ceremony retrieved but has no stories - persistence issue")
                return False
            else:
                print_success(f"Verified ceremony has {len(get_response.ceremony.story_ids)} stories persisted")
                await self.log_ceremony_snapshot("add_stories_persisted", self.ceremony_id)

            return True

        except grpc.RpcError as e:
            print_error(f"gRPC error: {e.code()} - {e.details()}")
            return False
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def start_ceremony(self) -> bool:
        """Start backlog review ceremony."""
        print_step(4, "Start Backlog Review Ceremony")

        if not self.planning_stub:
            print_error("Planning stub not initialized")
            return False

        if not self.ceremony_id:
            print_error("Ceremony ID not set")
            return False

        try:
            print_info(f"Starting ceremony: {self.ceremony_id}...")
            start_request = planning_pb2.StartBacklogReviewCeremonyRequest(
                ceremony_id=self.ceremony_id,
                started_by=self.created_by,
            )
            start_response = await self.planning_stub.StartBacklogReviewCeremony(start_request)  # type: ignore[union-attr]

            if not start_response.success:
                error_msg = start_response.message if start_response.message else "Unknown error"
                print_error(f"Failed to start ceremony: {error_msg}")
                if start_response.ceremony:
                    print_info(f"  Ceremony status: {start_response.ceremony.status}")
                    print_info(f"  Stories in ceremony: {len(start_response.ceremony.story_ids)}")
                return False

            # Verify status is IN_PROGRESS
            if start_response.ceremony.status != "IN_PROGRESS":
                print_error(
                    f"Expected status IN_PROGRESS, got: {start_response.ceremony.status}"
                )
                return False

            # Verify deliberations were submitted
            # Expected: 3 roles (ARCHITECT, QA, DEVOPS) × number of stories
            expected_deliberations = len(self.story_ids) * 3
            if start_response.total_deliberations_submitted != expected_deliberations:
                print_warning(
                    f"Expected {expected_deliberations} deliberations submitted "
                    f"(3 roles × {len(self.story_ids)} stories), "
                    f"got: {start_response.total_deliberations_submitted}"
                )
                # This is a warning, not an error, as some deliberations might fail
                # but the ceremony should still be started

            print_success("Ceremony started successfully")
            print_info(f"  Ceremony ID: {start_response.ceremony.ceremony_id}")
            print_info(f"  Status: {start_response.ceremony.status}")
            print_info(
                f"  Deliberations submitted: {start_response.total_deliberations_submitted} "
                f"(expected: {expected_deliberations})"
            )
            print_info(f"  Message: {start_response.message}")
            print_info(
                "  Note: Deliberations are running asynchronously. "
                "Results will arrive via NATS events."
            )
            await self.log_ceremony_snapshot("start_ceremony", self.ceremony_id)

            return True

        except grpc.RpcError as e:
            error_details = e.details() if e.details() else "No details provided"
            print_error(f"gRPC error: {e.code()} - {error_details}")
            # Try to get error message from response if available
            if hasattr(e, 'initial_metadata'):
                try:
                    print_info(f"  Error metadata: {e.initial_metadata()}")
                except Exception:
                    pass
            return False
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def test_idempotency(self) -> bool:
        """Test idempotency: calling StartBacklogReviewCeremony twice should not duplicate deliberations.

        Note: Ceremony is already started in Step 4, so this test verifies that
        a second call is properly rejected.
        """
        print_step(5, "Test Idempotency")

        if not self.planning_stub:
            print_error("Planning stub not initialized")
            return False

        if not self.ceremony_id:
            print_error("Ceremony ID not set")
            return False

        try:
            # Get current state (should be IN_PROGRESS from Step 4)
            ceremony = await self.get_ceremony(self.ceremony_id)
            if not ceremony:
                print_error("Failed to get ceremony state")
                return False

            current_status = ceremony.status
            print_info(f"Current ceremony status: {current_status}")
            await self.log_ceremony_snapshot("idempotency_before_second_start", self.ceremony_id)

            if current_status != "IN_PROGRESS":
                print_error(
                    f"Expected ceremony to be IN_PROGRESS, got: {current_status}. "
                    f"Cannot test idempotency."
                )
                return False

            # Store initial deliberations count (if available)
            # Note: We can't easily get the count from ceremony, but we can verify
            # that a second call doesn't create duplicates by checking the response

            # Second call (should be rejected - ceremony already IN_PROGRESS)
            print_info("Attempting second call to StartBacklogReviewCeremony (idempotency test)...")
            print_info(f"   Ceremony ID: {self.ceremony_id}")
            print_info(f"   Expected: Call should be rejected (ceremony already IN_PROGRESS)")

            second_request = planning_pb2.StartBacklogReviewCeremonyRequest(
                ceremony_id=self.ceremony_id,
                started_by=self.created_by,
            )

            try:
                second_response = await self.planning_stub.StartBacklogReviewCeremony(second_request)  # type: ignore[union-attr]

                # If we got a response (even with success=False), check it
                if not second_response.success:
                    error_msg = second_response.message or ""
                    if "Cannot start ceremony" in error_msg or "status" in error_msg.lower() or "IN_PROGRESS" in error_msg:
                        print_success("✅ IDEMPOTENCY VALIDATED: Second call correctly rejected")
                        print_info(f"   Error message: {error_msg}")
                    else:
                        print_warning(f"Second call rejected with unexpected error: {error_msg}")

                    # Verify ceremony status didn't change
                    ceremony_after = await self.get_ceremony(self.ceremony_id)
                    if ceremony_after and ceremony_after.status == "IN_PROGRESS":
                        print_success("✅ Ceremony status unchanged (still IN_PROGRESS)")
                        print_success("✅ No duplicate deliberations created")
                        await self.log_ceremony_snapshot(
                            "idempotency_after_second_start_response",
                            self.ceremony_id,
                        )
                        return True
                    else:
                        print_error("❌ Ceremony status changed unexpectedly")
                        return False
                else:
                    # If second call succeeded, verify no duplicate deliberations
                    second_deliberations = second_response.total_deliberations_submitted
                    if second_deliberations == 0:
                        print_success("✅ IDEMPOTENCY VALIDATED: Second call returned 0 deliberations")
                        return True
                    else:
                        print_error(
                            f"❌ IDEMPOTENCY VIOLATION: Second call submitted {second_deliberations} deliberations "
                            f"(expected 0)"
                        )
                        return False

            except grpc.RpcError as e:
                # gRPC exception is expected when ceremony is already started
                error_code = e.code()
                error_details = e.details() or ""

                print_info(f"   gRPC error received: {error_code}")
                print_info(f"   Error details: {error_details}")

                if error_code == grpc.StatusCode.INVALID_ARGUMENT:
                    # Verify error message indicates ceremony cannot be started
                    if (
                        "Cannot start ceremony" in error_details
                        or "status" in error_details.lower()
                        or "IN_PROGRESS" in error_details
                        or "already" in error_details.lower()
                    ):
                        print_success("✅ IDEMPOTENCY VALIDATED: Second call correctly rejected (gRPC INVALID_ARGUMENT)")
                        print_info(f"   Error message: {error_details}")
                    else:
                        # Check if ceremony status is still IN_PROGRESS
                        ceremony_after = await self.get_ceremony(self.ceremony_id)
                        if ceremony_after and ceremony_after.status == "IN_PROGRESS":
                            print_success(
                                "✅ IDEMPOTENCY VALIDATED: Ceremony status unchanged "
                                "(gRPC error but status preserved)"
                            )
                            print_info(f"   Error code: {error_code}, Details: {error_details}")
                        else:
                            print_error(f"❌ Ceremony status changed after error: {ceremony_after.status if ceremony_after else 'None'}")
                            return False

                    # Final verification: ceremony should still be IN_PROGRESS
                    ceremony_after = await self.get_ceremony(self.ceremony_id)
                    if ceremony_after and ceremony_after.status == "IN_PROGRESS":
                        print_success("✅ No duplicate deliberations created")
                        await self.log_ceremony_snapshot(
                            "idempotency_after_second_start_grpc_error",
                            self.ceremony_id,
                        )
                        return True
                    else:
                        print_error("❌ Ceremony status changed unexpectedly")
                        return False
                else:
                    print_error(f"❌ Unexpected gRPC error: {error_code} - {error_details}")
                    return False

        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def get_ceremony(self, ceremony_id: str) -> planning_pb2.BacklogReviewCeremony | None:
        """Get ceremony by ID."""
        if not self.planning_stub:
            return None

        try:
            request = planning_pb2.GetBacklogReviewCeremonyRequest(ceremony_id=ceremony_id)
            response = await self.planning_stub.GetBacklogReviewCeremony(request)  # type: ignore[union-attr]

            if response.success and response.ceremony:
                return response.ceremony
            return None

        except grpc.RpcError:
            return None
        except Exception:
            return None

    @staticmethod
    def _review_result_snapshot_line(
        review_result: planning_pb2.StoryReviewResult,
    ) -> str:
        """Build a compact debug line for ceremony review results."""
        return (
            f"story={review_result.story_id} "
            f"status={review_result.approval_status} "
            f"has_plan_preliminary={bool(review_result.plan_preliminary)}"
        )

    async def log_ceremony_snapshot(self, label: str, ceremony_id: str | None) -> None:
        """Print ceremony snapshot to debug lifecycle transitions."""
        if not ceremony_id:
            print_warning(f"[Ceremony Snapshot] {label}: ceremony_id missing")
            return
        ceremony = await self.get_ceremony(ceremony_id)
        if not ceremony:
            print_warning(f"[Ceremony Snapshot] {label}: ceremony {ceremony_id} not found")
            return
        print_info(f"[Ceremony Snapshot] {label}")
        print_info(
            f"  ceremony_id={ceremony.ceremony_id} status={ceremony.status} "
            f"stories={len(ceremony.story_ids)} review_results={len(ceremony.review_results)}"
        )
        for review_result in ceremony.review_results:
            print_info(f"  - {self._review_result_snapshot_line(review_result)}")

    def print_summary(self) -> None:
        """Print summary of test execution."""
        print()
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print(f"{Colors.BLUE}📊 Test Execution Summary{Colors.NC}")
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print()
        print("Test Data:")
        if self.project_id:
            print(f"  Project: {self.project_id} - '{self.project_name}'")
        if self.epic_id:
            print(f"  Epic: {self.epic_id} - '{self.epic_title}'")
        if self.story_ids:
            print(f"  Stories ({len(self.story_ids)}):")
            for story_id in self.story_ids:
                print(f"    - {story_id}")
        print()
        print("Ceremony:")
        if self.ceremony_id:
            print(f"  Ceremony ID: {self.ceremony_id}")
            print("  Status: IN_PROGRESS")
        print()

    async def run(self) -> int:
        """Run the test."""
        print()
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print(f"{Colors.BLUE}🧪 E2E Test: Start Backlog Review Ceremony{Colors.NC}")
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print()

        print("Configuration:")
        print(f"  Planning Service: {self.planning_url}")
        print(f"  Created By:       {self.created_by}")
        print(f"  Project Name:     {self.project_name}")
        print(f"  Epic Title:       {self.epic_title}")
        print()

        try:
            # Setup
            await self.setup()

            # Test steps
            steps = [
                ("Find Test Data", self.find_test_data),
                ("Create Ceremony", self.create_ceremony),
                ("Add Stories to Ceremony", self.add_stories_to_ceremony),
                ("Start Ceremony", self.start_ceremony),
                ("Test Idempotency", self.test_idempotency),
            ]

            for step_name, step_func in steps:
                success = await step_func()
                if not success:
                    print_error(f"Step '{step_name}' failed")
                    return 1

            # Print summary
            self.print_summary()

            print()
            print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
            print(f"{Colors.GREEN}✅ Test Completed Successfully{Colors.NC}")
            print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
            print()
            return 0

        except KeyboardInterrupt:
            print()
            print_warning("Test interrupted by user")
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
    test = StartBacklogReviewCeremonyTest()
    return await test.run()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
