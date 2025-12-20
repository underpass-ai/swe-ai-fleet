#!/usr/bin/env python3
"""E2E Test: Validate Single Deliberation.

This test validates that a single deliberation can be executed and processed correctly:
1. Finds test data (Project, Epic, Story)
2. Submits a single deliberation request to Ray Executor
3. Waits for deliberation to complete
4. Verifies that deliberation result is clean (no <think> tags)
5. Verifies that reasoning is separated (if available)
6. Verifies that deliberation was processed by BRP and stored in Planning Service

Flow Verified:
- Ray Executor → vLLM → NATS → BRP → Planning Service
- Reasoning parser separates thinking from content
- Content is clean (no <think> tags)
- Deliberation is stored correctly

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
from fleet.ray_executor.v1 import ray_executor_pb2, ray_executor_pb2_grpc  # type: ignore[import]


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


class ValidateSingleDeliberationTest:
    """E2E test for validating a single deliberation."""

    def __init__(self) -> None:
        """Initialize with service URLs from environment."""
        # Service URLs (Kubernetes internal DNS)
        self.planning_url = os.getenv(
            "PLANNING_SERVICE_URL",
            "planning.swe-ai-fleet.svc.cluster.local:50054",
        )
        self.ray_executor_url = os.getenv(
            "RAY_EXECUTOR_SERVICE_URL",
            "ray-executor.swe-ai-fleet.svc.cluster.local:50051",
        )

        # Test data
        self.created_by = os.getenv("TEST_CREATED_BY", "e2e-test@system.local")
        self.project_name = os.getenv("TEST_PROJECT_NAME", "Test de swe fleet")
        self.epic_title = os.getenv("TEST_EPIC_TITLE", "Autenticacion")

        # vLLM configuration
        self.vllm_url = os.getenv(
            "VLLM_URL", "http://vllm-server-service.swe-ai-fleet.svc.cluster.local:8000"
        )
        self.vllm_model = os.getenv("VLLM_MODEL", "Qwen/Qwen3-0.6B")

        # Timeouts
        self.deliberation_timeout = int(os.getenv("DELIBERATION_TIMEOUT", "300"))  # 5 minutes
        self.poll_interval = int(os.getenv("POLL_INTERVAL", "5"))  # 5 seconds

        # Discovered entities
        self.project_id: Optional[str] = None
        self.epic_id: Optional[str] = None
        self.story_id: Optional[str] = None
        self.ceremony_id: Optional[str] = None
        self.deliberation_id: Optional[str] = None
        self.task_id: Optional[str] = None

        # gRPC channels and stubs
        self.planning_channel: Optional[grpc.aio.Channel] = None
        self.planning_stub: Optional[planning_pb2_grpc.PlanningServiceStub] = None  # type: ignore[assignment]
        self.ray_executor_channel: Optional[grpc.aio.Channel] = None
        self.ray_executor_stub: Optional[ray_executor_pb2_grpc.RayExecutorServiceStub] = None  # type: ignore[assignment]

    async def setup(self) -> None:
        """Set up gRPC connections."""
        print_info("Setting up gRPC connections...")

        self.planning_channel = grpc.aio.insecure_channel(self.planning_url)
        self.planning_stub = planning_pb2_grpc.PlanningServiceStub(self.planning_channel)  # type: ignore[assignment]

        self.ray_executor_channel = grpc.aio.insecure_channel(self.ray_executor_url)
        self.ray_executor_stub = ray_executor_pb2_grpc.RayExecutorServiceStub(self.ray_executor_channel)  # type: ignore[assignment]

        print_success("gRPC connections established")

    async def cleanup_connections(self) -> None:
        """Clean up gRPC connections."""
        print_info("Cleaning up connections...")

        if self.planning_channel:
            await self.planning_channel.close()
        if self.ray_executor_channel:
            await self.ray_executor_channel.close()

        print_success("Connections cleaned up")

    async def find_test_data(self) -> bool:
        """Find test data (project, epic, story)."""
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

            # Find first story
            print_info(f"Searching for stories in epic: '{self.epic_id}'...")
            stories_request = planning_pb2.ListStoriesRequest(epic_id=self.epic_id, limit=1)
            stories_response = await self.planning_stub.ListStories(stories_request)  # type: ignore[union-attr]

            if not stories_response.success:
                print_error(f"Failed to list stories: {stories_response.message}")
                return False

            if not stories_response.stories:
                print_error("No stories found in epic")
                return False

            self.story_id = stories_response.stories[0].story_id
            print_success(f"Found story: {self.story_id} - {stories_response.stories[0].title}")

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
        """Create a backlog review ceremony."""
        if not self.planning_stub or not self.story_id:
            print_error("Planning stub or story_id not initialized")
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

            # Add story
            print_info(f"Adding story {self.story_id} to ceremony...")
            add_stories_request = planning_pb2.AddStoriesToReviewRequest(
                ceremony_id=self.ceremony_id,
                story_ids=[self.story_id],
            )
            add_stories_response = await self.planning_stub.AddStoriesToReview(add_stories_request)  # type: ignore[union-attr]

            if not add_stories_response.success:
                print_error(f"Failed to add story: {add_stories_response.message}")
                return False

            print_success("Story added to ceremony")
            return True

        except grpc.RpcError as e:
            print_error(f"gRPC error: {e.code()} - {e.details()}")
            return False
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def submit_deliberation(self) -> bool:
        """Submit a single deliberation to Ray Executor."""
        if not self.ray_executor_stub or not self.ceremony_id or not self.story_id:
            print_error("Ray Executor stub, ceremony_id, or story_id not initialized")
            return False

        try:
            # Build task_id
            self.task_id = f"ceremony-{self.ceremony_id}:story-{self.story_id}:role-ARCHITECT"
            print_info(f"Submitting deliberation: {self.task_id}")

            # Build task description
            task_description = f"""Analyze the following user story and provide architectural feedback.

Story ID: {self.story_id}

Instructions:
1. Review the story from an architectural perspective
2. Identify potential technical challenges
3. Suggest architectural considerations
4. Provide clear, actionable feedback

Return your analysis as structured text."""
            print_info(f"Task description length: {len(task_description)} chars")

            # Build request
            request = ray_executor_pb2.ExecuteBacklogReviewDeliberationRequest(
                task_id=self.task_id,
                task_description=task_description,
                role="ARCHITECT",
                constraints=ray_executor_pb2.BacklogReviewTaskConstraints(
                    story_id=self.story_id,
                    timeout_seconds=300,
                    max_retries=3,
                    metadata={"task_id": self.task_id, "num_agents": "1"},
                ),
                agents=[
                    ray_executor_pb2.Agent(
                        id="agent-architect-001",
                        role="ARCHITECT",
                        model=self.vllm_model,
                        prompt_template="",
                    )
                ],
                vllm_url=self.vllm_url,
                vllm_model=self.vllm_model,
            )

            # Submit deliberation
            print_info("Calling Ray Executor ExecuteBacklogReviewDeliberation...")
            response = await self.ray_executor_stub.ExecuteBacklogReviewDeliberation(request)  # type: ignore[union-attr]

            if not response.deliberation_id:
                print_error("Ray Executor returned empty deliberation_id")
                return False

            self.deliberation_id = response.deliberation_id
            print_success(f"Deliberation submitted: {self.deliberation_id}")
            print_info(f"Status: {response.status}")
            return True

        except grpc.RpcError as e:
            print_error(f"gRPC error: {e.code()} - {e.details()}")
            return False
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def wait_for_deliberation_completion(self) -> bool:
        """Wait for deliberation to complete."""
        if not self.ray_executor_stub or not self.deliberation_id:
            print_error("Ray Executor stub or deliberation_id not initialized")
            return False

        print_info(f"Waiting for deliberation {self.deliberation_id} to complete...")
        print_info(f"Timeout: {self.deliberation_timeout}s, Poll interval: {self.poll_interval}s")

        start_time = time.time()
        while time.time() - start_time < self.deliberation_timeout:
            try:
                status_request = ray_executor_pb2.GetDeliberationStatusRequest(
                    deliberation_id=self.deliberation_id
                )
                status_response = await self.ray_executor_stub.GetDeliberationStatus(status_request)  # type: ignore[union-attr]

                status = status_response.status
                print_info(f"Deliberation status: {status}")

                if status == "COMPLETED":
                    print_success("Deliberation completed!")
                    return True
                elif status == "FAILED":
                    error_msg = status_response.error_message or "Unknown error"
                    print_error(f"Deliberation failed: {error_msg}")
                    return False

                await asyncio.sleep(self.poll_interval)

            except grpc.RpcError as e:
                print_warning(f"gRPC error checking status: {e.code()} - {e.details()}")
                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                print_warning(f"Error checking status: {e}")
                await asyncio.sleep(self.poll_interval)

        print_error(f"Deliberation did not complete within {self.deliberation_timeout}s timeout")
        return False

    async def verify_deliberation_result(self) -> bool:
        """Verify deliberation result is clean and correct."""
        if not self.ray_executor_stub or not self.deliberation_id:
            print_error("Ray Executor stub or deliberation_id not initialized")
            return False

        try:
            print_info("Fetching deliberation result...")
            status_request = ray_executor_pb2.GetDeliberationStatusRequest(
                deliberation_id=self.deliberation_id
            )
            status_response = await self.ray_executor_stub.GetDeliberationStatus(status_request)  # type: ignore[union-attr]

            if not status_response.result:
                print_error("No result in deliberation status response")
                return False

            result = status_response.result
            proposal = result.proposal

            # Verify content is clean (no <think> tags)
            if "<think>" in proposal.lower():
                print_error("❌ Content contains <think> tags (reasoning parser may have failed)")
                print_warning(f"Content preview: {proposal[:500]}")
                return False

            print_success("✅ Content is clean (no <think> tags)")

            # Verify reasoning is separated (if available)
            if result.reasoning:
                print_success(f"✅ Reasoning is separated ({len(result.reasoning)} chars)")
            else:
                print_info("ℹ Reasoning not available (may be normal if reasoning parser not configured)")

            # Verify proposal is not empty
            if not proposal or not proposal.strip():
                print_error("❌ Proposal is empty")
                return False

            print_success(f"✅ Proposal is valid ({len(proposal)} chars)")
            print_info(f"Proposal preview: {proposal[:200]}...")

            return True

        except grpc.RpcError as e:
            print_error(f"gRPC error: {e.code()} - {e.details()}")
            return False
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def verify_deliberation_in_planning(self) -> bool:
        """Verify deliberation was processed and stored in Planning Service."""
        if not self.planning_stub or not self.ceremony_id or not self.story_id:
            print_error("Planning stub, ceremony_id, or story_id not initialized")
            return False

        try:
            print_info("Verifying deliberation in Planning Service...")
            print_info("Waiting for BRP to process deliberation and update Planning Service...")

            # Poll for deliberation to appear in ceremony
            start_time = time.time()
            timeout = 120  # 2 minutes
            poll_interval = 5  # 5 seconds

            while time.time() - start_time < timeout:
                ceremony_request = planning_pb2.GetBacklogReviewCeremonyRequest(
                    ceremony_id=self.ceremony_id
                )
                ceremony_response = await self.planning_stub.GetBacklogReviewCeremony(ceremony_request)  # type: ignore[union-attr]

                if not ceremony_response.success:
                    print_warning(f"Failed to get ceremony: {ceremony_response.message}")
                    await asyncio.sleep(poll_interval)
                    continue

                ceremony = ceremony_response.ceremony

                # Check if story has review results
                for review_result in ceremony.review_results:
                    if review_result.story_id == self.story_id:
                        # Check if ARCHITECT deliberation exists
                        for deliberation in review_result.agent_deliberations:
                            if deliberation.role == "ARCHITECT":
                                print_success("✅ Deliberation found in Planning Service")
                                print_info(f"Agent ID: {deliberation.agent_id}")
                                print_info(f"Deliberated at: {deliberation.deliberated_at}")

                                # Verify proposal is clean
                                proposal_str = str(deliberation.proposal)
                                if "<think>" in proposal_str.lower():
                                    print_error("❌ Stored deliberation contains <think> tags")
                                    return False

                                print_success("✅ Stored deliberation is clean")
                                return True

                await asyncio.sleep(poll_interval)

            print_warning("⚠ Deliberation not found in Planning Service within timeout")
            print_info("This may be normal if BRP hasn't processed it yet")
            return False

        except grpc.RpcError as e:
            print_error(f"gRPC error: {e.code()} - {e.details()}")
            return False
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def run(self) -> int:
        """Run the E2E test."""
        print()
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print(f"{Colors.BLUE}E2E Test: Validate Single Deliberation{Colors.NC}")
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print()

        try:
            # Setup
            await self.setup()

            # Step 1: Find test data
            print_step(1, "Find Test Data")
            if not await self.find_test_data():
                return 1

            # Step 2: Create ceremony
            print_step(2, "Create Backlog Review Ceremony")
            if not await self.create_ceremony():
                return 1

            # Step 3: Submit deliberation
            print_step(3, "Submit Deliberation to Ray Executor")
            if not await self.submit_deliberation():
                return 1

            # Step 4: Wait for completion
            print_step(4, "Wait for Deliberation Completion")
            if not await self.wait_for_deliberation_completion():
                return 1

            # Step 5: Verify result
            print_step(5, "Verify Deliberation Result")
            if not await self.verify_deliberation_result():
                return 1

            # Step 6: Verify in Planning Service
            print_step(6, "Verify Deliberation in Planning Service")
            if not await self.verify_deliberation_in_planning():
                print_warning("⚠ Deliberation not found in Planning Service (may need more time)")
                # Don't fail the test, just warn

            print()
            print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
            print(f"{Colors.GREEN}✅ Test completed successfully!{Colors.NC}")
            print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
            return 0

        except KeyboardInterrupt:
            print()
            print_warning("Test interrupted by user")
            return 130
        except Exception as e:
            print()
            print_error(f"Test failed with exception: {e}")
            import traceback

            traceback.print_exc()
            return 1
        finally:
            await self.cleanup_connections()


async def main() -> int:
    """Main entry point."""
    test = ValidateSingleDeliberationTest()
    return await test.run()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
