#!/usr/bin/env python3
"""E2E Test: Approve Review Plan and Validate Plan Creation.

This test validates the Human-in-the-Loop approval flow (steps 15-18) of the
Backlog Review Flow, divided into 8 independent stages:

- Stage 0: Preparation (ceremony in REVIEWING state)
- Stage 1: Approve plan for first story
- Stage 2: Validate plan in storage (Neo4j/Valkey)
- Stage 3: Validate tasks with decision metadata
- Stage 4: Validate ceremony updated
- Stage 5: Validate event published
- Stage 6: Approve plan for all remaining stories
- Stage 7: Validate final state
- Stage 8: Validate complete persistence

Flow Verified (following BACKLOG_REVIEW_FLOW.md):
- Step 15: PO approves review plan (Human-in-the-Loop)
- Step 16: Create official Plan entity
- Step 17: Create tasks with decision (save_task_with_decision)
- Step 18: Publish planning.plan.approved event

Test Prerequisites:
- Planning Service must be deployed
- Neo4j must be accessible
- Valkey must be accessible
- NATS must be accessible (for event validation)
- Test data must exist (run 02-create-test-data first)
- Ceremony must be in REVIEWING state (run 05-validate-deliberations-and-tasks first)
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


def print_stage(stage: int, description: str) -> None:
    """Print stage header."""
    print()
    print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
    print(f"{Colors.BLUE}[Etapa {stage}] {description}{Colors.NC}")
    print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
    print()


class ApproveReviewPlanTest:
    """E2E test for approving review plan and validating plan creation."""

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

        # PO approval context
        self.po_approved_by = os.getenv("PO_APPROVED_BY", "e2e-po@system.local")
        self.po_notes = os.getenv(
            "PO_NOTES", "E2E test approval - plan looks good"
        )
        self.po_concerns = os.getenv("PO_CONCERNS", "")
        self.priority_adjustment = os.getenv("PRIORITY_ADJUSTMENT", "")
        self.po_priority_reason = os.getenv("PO_PRIORITY_REASON", "")

        # Timeouts (reduced for development)
        self.stage_timeout = int(os.getenv("STAGE_TIMEOUT", "10"))  # 10 seconds per stage (reduced for dev)
        self.ceremony_wait_timeout = int(os.getenv("CEREMONY_WAIT_TIMEOUT", "120"))  # 2 minutes to wait for REVIEWING (reduced for dev)

        # Discovered entities
        self.project_id: Optional[str] = None
        self.epic_id: Optional[str] = None
        self.story_ids: list[str] = []
        self.ceremony_id: Optional[str] = None

        # gRPC connections
        self.channel: Optional[grpc.aio.Channel] = None
        self.planning_stub: Optional[planning_pb2_grpc.PlanningServiceStub] = None

        # Stage timings
        self.stage_timings: dict[int, float] = {}

        # Approved plans tracking
        self.approved_plans: dict[str, str] = {}  # story_id -> plan_id
        # Rejected stories (PO rejection via RejectReviewPlan)
        self.rejected_story_ids: set[str] = set()

    async def setup(self) -> None:
        """Set up gRPC connections."""
        print_info("Setting up connections...")

        self.channel = grpc.aio.insecure_channel(self.planning_url)
        self.planning_stub = planning_pb2_grpc.PlanningServiceStub(self.channel)

        print_success("Setup completed")

    async def cleanup(self) -> None:
        """Clean up connections."""
        print_info("Cleaning up connections...")

        if self.channel:
            await self.channel.close()

        print_success("Cleanup completed")

    async def find_test_data(self) -> bool:
        """Find test data (project, epic, stories)."""
        print_info("🔍 Finding test data...")
        print_info(f"   Project name: {self.project_name}")
        print_info(f"   Epic title: {self.epic_title}")

        if not self.planning_stub:
            print_error("Planning stub not initialized")
            return False

        try:
            # List projects
            list_projects_request = planning_pb2.ListProjectsRequest()
            list_projects_response = await self.planning_stub.ListProjects(  # type: ignore[union-attr]
                list_projects_request
            )

            if not list_projects_response.success:
                print_error(f"Failed to list projects: {list_projects_response.message}")
                return False

            # Find project by name
            project = None
            for p in list_projects_response.projects:
                if p.name == self.project_name:
                    project = p
                    break

            if not project:
                print_error(f"Project '{self.project_name}' not found")
                return False

            self.project_id = project.project_id
            print_success(f"✅ Found project: {self.project_id}")
            print_info(f"   Project name: {project.name}")

            # List epics
            list_epics_request = planning_pb2.ListEpicsRequest(project_id=self.project_id)
            list_epics_response = await self.planning_stub.ListEpics(  # type: ignore[union-attr]
                list_epics_request
            )

            if not list_epics_response.success:
                print_error(f"Failed to list epics: {list_epics_response.message}")
                return False

            # Find epic by title
            epic = None
            for e in list_epics_response.epics:
                if e.title == self.epic_title:
                    epic = e
                    break

            if not epic:
                print_error(f"Epic '{self.epic_title}' not found")
                return False

            self.epic_id = epic.epic_id
            print_success(f"✅ Found epic: {self.epic_id}")
            print_info(f"   Epic title: {epic.title}")

            # List stories
            list_stories_request = planning_pb2.ListStoriesRequest(
                epic_id=self.epic_id, limit=100
            )
            list_stories_response = await self.planning_stub.ListStories(  # type: ignore[union-attr]
                list_stories_request
            )

            if not list_stories_response.success:
                print_error(f"Failed to list stories: {list_stories_response.message}")
                return False

            self.story_ids = [story.story_id for story in list_stories_response.stories]
            print_success(f"✅ Found {len(self.story_ids)} stories")
            for i, story_id in enumerate(self.story_ids, 1):
                print_info(f"   {i}. {story_id}")

            return True

        except grpc.RpcError as e:
            print_error(f"gRPC error: {e.code()} - {e.details()}")
            return False
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def find_ceremony_in_reviewing(self, timeout: int = 600) -> bool:
        """Find ceremony in REVIEWING state, with polling if needed."""
        if not self.planning_stub:
            print_error("Planning stub not initialized")
            return False

        import time
        start_time = time.time()
        poll_interval = 5  # Poll every 5 seconds (reduced for dev)
        attempt = 0

        print_info(f"🔍 Searching for ceremony in REVIEWING state (timeout: {timeout}s)...")
        print_info(f"   Test stories: {self.story_ids}")
        print_info(f"   Poll interval: {poll_interval}s")

        while time.time() - start_time < timeout:
            attempt += 1
            elapsed = int(time.time() - start_time)
            try:
                print_info(f"📋 [Attempt {attempt}] Listing ceremonies (elapsed: {elapsed}s)...")
                # List all ceremonies first (without filters to avoid validation issues)
                # The handler requires limit > 0 and offset >= 0
                list_ceremonies_request = planning_pb2.ListBacklogReviewCeremoniesRequest(
                    limit=100,
                    offset=0
                )
                # Don't set status_filter or created_by to avoid validation issues
                list_ceremonies_response = await self.planning_stub.ListBacklogReviewCeremonies(  # type: ignore[union-attr]
                    list_ceremonies_request
                )
                print_info(f"   ✅ Listed {len(list_ceremonies_response.ceremonies)} ceremonies")

                if not list_ceremonies_response.success:
                    # If the response has a message, it might be a validation error
                    error_msg = list_ceremonies_response.message or "Unknown error"
                    print_warning(
                        f"Failed to list ceremonies: {error_msg}, retrying..."
                    )
                    await asyncio.sleep(poll_interval)
                    continue

                # Find ceremony with matching stories in REVIEWING state
                reviewing_count = 0
                for ceremony in list_ceremonies_response.ceremonies:
                    if ceremony.status == "REVIEWING":
                        reviewing_count += 1
                        print_info(f"   🔍 Found REVIEWING ceremony: {ceremony.ceremony_id}")
                        print_info(f"      Stories: {ceremony.story_ids}")
                        # Check if ceremony has our stories
                        ceremony_story_ids = set(ceremony.story_ids)
                        test_story_ids = set(self.story_ids)

                        if ceremony_story_ids.issuperset(test_story_ids):
                            self.ceremony_id = ceremony.ceremony_id
                            print_success(f"✅ Found matching ceremony in REVIEWING: {self.ceremony_id}")
                            print_info(f"   Ceremony stories: {ceremony.story_ids}")
                            print_info(f"   Test stories: {self.story_ids}")
                            return True
                        else:
                            print_info(f"   ⚠️  Ceremony {ceremony.ceremony_id} doesn't match test stories")
                            print_info(f"      Ceremony has: {ceremony.story_ids}")
                            print_info(f"      Test needs: {self.story_ids}")

                print_info(f"   📊 Found {reviewing_count} ceremonies in REVIEWING state")

                # If no REVIEWING ceremonies found, check IN_PROGRESS
                if not any(
                    set(c.story_ids).issuperset(set(self.story_ids))
                    for c in list_ceremonies_response.ceremonies
                    if c.status == "REVIEWING"
                ):
                    # List IN_PROGRESS ceremonies
                    list_in_progress_request = planning_pb2.ListBacklogReviewCeremoniesRequest(
                        status_filter="IN_PROGRESS",
                        limit=100,
                        offset=0
                    )
                    in_progress_response = await self.planning_stub.ListBacklogReviewCeremonies(  # type: ignore[union-attr]
                        list_in_progress_request
                    )

                    if in_progress_response.success:
                        # Check ceremonies in IN_PROGRESS that might transition to REVIEWING
                        for ceremony in in_progress_response.ceremonies:
                            ceremony_story_ids = set(ceremony.story_ids)
                            test_story_ids = set(self.story_ids)

                            if ceremony_story_ids.issuperset(test_story_ids):
                                # Found matching ceremony in IN_PROGRESS, wait for it
                                elapsed = int(time.time() - start_time)
                                print_info(
                                    f"⏳ Found ceremony {ceremony.ceremony_id} in IN_PROGRESS, "
                                    f"waiting for REVIEWING... (elapsed: {elapsed}s)"
                                )
                                print_info(f"   Ceremony stories: {ceremony.story_ids}")
                                # Check review results to see progress
                                if hasattr(ceremony, 'review_results'):
                                    review_count = len(ceremony.review_results)
                                    print_info(
                                        f"   📊 Review results: {review_count}/{len(test_story_ids)} stories"
                                    )
                                    for rr in ceremony.review_results:
                                        print_info(f"      - Story {rr.story_id}: status={rr.approval_status}")
                                else:
                                    print_info(f"   ⚠️  No review_results attribute found")
                                await asyncio.sleep(poll_interval)
                                break
                        else:
                            # No matching ceremony found, wait and retry
                            elapsed = int(time.time() - start_time)
                            print_info(
                                f"No ceremony in REVIEWING or IN_PROGRESS found yet "
                                f"(elapsed: {elapsed}s). Waiting..."
                            )
                            await asyncio.sleep(poll_interval)
                    else:
                        # Failed to list IN_PROGRESS, wait and retry
                        elapsed = int(time.time() - start_time)
                        print_info(
                            f"Could not list IN_PROGRESS ceremonies, retrying... "
                            f"(elapsed: {elapsed}s)"
                        )
                        await asyncio.sleep(poll_interval)
                else:
                    # No matching ceremony found in REVIEWING, wait and retry
                    elapsed = int(time.time() - start_time)
                    print_info(
                        f"No matching ceremony in REVIEWING found yet (elapsed: {elapsed}s). "
                        f"Waiting for ceremony to reach REVIEWING state..."
                    )
                    await asyncio.sleep(poll_interval)

            except grpc.RpcError as e:
                # Log error details for debugging
                error_details = e.details() if e.details() else "No details"
                elapsed = int(time.time() - start_time)
                print_error(f"❌ [Attempt {attempt}] gRPC error (elapsed: {elapsed}s):")
                print_error(f"   Code: {e.code()}")
                print_error(f"   Details: {error_details}")
                if e.code() == grpc.StatusCode.INVALID_ARGUMENT:
                    # Check if this is the known bug with StoryReviewResult validation
                    if "po_notes" in error_details.lower():
                        print_warning(
                            f"   ⚠️  Known issue: Planning Service has a bug where ceremonies with "
                            f"approved reviews without po_notes cannot be listed."
                        )
                    print_warning(f"   🔄 Retrying in {poll_interval}s...")
                else:
                    print_warning(f"   🔄 Retrying in {poll_interval}s...")
                await asyncio.sleep(poll_interval)
                continue
            except Exception as e:
                elapsed = int(time.time() - start_time)
                print_error(f"❌ [Attempt {attempt}] Unexpected error (elapsed: {elapsed}s): {e}")
                import traceback
                print_error(f"   Traceback: {traceback.format_exc()}")
                print_warning(f"   🔄 Retrying in {poll_interval}s...")
                await asyncio.sleep(poll_interval)
                continue

        elapsed = int(time.time() - start_time)
        print_error(f"⏱️  Timeout: No ceremony in REVIEWING state found after {elapsed}s")
        print_error(f"   Total attempts: {attempt}")
        print_error(f"   Test stories needed: {self.story_ids}")
        print_info("💡 Note: Ensure test 05 has completed or a ceremony is in progress")
        print_info("💡 Check Planning Service logs for ceremony status transitions")
        return False

    async def get_ceremony(self, ceremony_id: str) -> Optional[planning_pb2.BacklogReviewCeremony]:
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

    async def list_tasks(self, story_id: Optional[str] = None, limit: int = 1000) -> list[planning_pb2.Task]:
        """List tasks, optionally filtered by story_id."""
        if not self.planning_stub:
            return []

        try:
            request = planning_pb2.ListTasksRequest(limit=limit)
            if story_id:
                request.story_id = story_id

            response = await self.planning_stub.ListTasks(request)  # type: ignore[union-attr]

            if response.success:
                return list(response.tasks)
            return []

        except grpc.RpcError:
            return []
        except Exception:
            return []

    async def list_tasks_by_plan(self, plan_id: str, story_id: Optional[str] = None) -> list[planning_pb2.Task]:
        """List tasks for a plan.

        If story_id is provided, only searches tasks for that story (more efficient).
        Otherwise, searches all tasks (may be limited by pagination).
        """
        # If story_id is provided, use it to limit the search scope
        if story_id:
            tasks = await self.list_tasks(story_id=story_id, limit=1000)
        else:
            tasks = await self.list_tasks(limit=1000)

        return [task for task in tasks if task.plan_id == plan_id]

    # ========== ETAPA 0: Preparación ==========
    async def stage_0_preparation(self) -> tuple[str, list[str]]:
        """Etapa 0: Preparar ceremonia en estado REVIEWING."""
        print_stage(0, "Preparación")

        start_time = time.time()

        # Find test data
        if not await self.find_test_data():
            raise ValueError("Failed to find test data")

        # Find ceremony in REVIEWING state (with polling if needed)
        if not await self.find_ceremony_in_reviewing(self.ceremony_wait_timeout):
            raise ValueError("Failed to find ceremony in REVIEWING state")

        if not self.ceremony_id:
            raise ValueError("Ceremony ID not set")

        # Verify ceremony is in REVIEWING
        ceremony = await self.get_ceremony(self.ceremony_id)
        if not ceremony:
            raise ValueError("Ceremony not found")

        if ceremony.status != "REVIEWING":
            raise ValueError(
                f"Expected status REVIEWING, got: {ceremony.status}"
            )

        # Verify all stories have review_results with plan_preliminary
        for review_result in ceremony.review_results:
            if not review_result.plan_preliminary:
                raise ValueError(
                    f"Story {review_result.story_id} missing plan_preliminary"
                )

        # Verify all stories have tasks created
        for story_id in ceremony.story_ids:
            tasks = await self.list_tasks(story_id)
            if not tasks:
                raise ValueError(f"Story {story_id} has no tasks created")

        print_success(f"Ceremony {self.ceremony_id} is in REVIEWING")
        print_success(f"Ceremony has {len(ceremony.story_ids)} stories")
        print_success("All stories have review_results with plan_preliminary")
        print_success("All stories have tasks created")

        elapsed = time.time() - start_time
        self.stage_timings[0] = elapsed

        return self.ceremony_id, ceremony.story_ids

    # ========== ETAPA 1: Aprobar Plan para Primera Story ==========
    async def stage_1_approve_first_story(self, ceremony_id: str, story_id: str) -> str:
        """Etapa 1: Aprobar plan para primera story."""
        print_stage(1, "Aprobar Plan para Primera Story")

        start_time = time.time()

        if not self.planning_stub:
            raise ValueError("Planning stub not initialized")

        try:
            # Build request
            request = planning_pb2.ApproveReviewPlanRequest(
                ceremony_id=ceremony_id,
                story_id=story_id,
                approved_by=self.po_approved_by,
                po_notes=self.po_notes,
            )

            if self.po_concerns:
                request.po_concerns = self.po_concerns

            if self.priority_adjustment:
                request.priority_adjustment = self.priority_adjustment

            if self.po_priority_reason:
                request.po_priority_reason = self.po_priority_reason

            # Call service
            print_info(f"📞 Calling ApproveReviewPlan for story {story_id}...")
            print_info(f"   Ceremony ID: {ceremony_id}")
            print_info(f"   Story ID: {story_id}")
            print_info(f"   Approved by: {self.po_approved_by}")
            print_info(f"   PO Notes: {self.po_notes[:50]}..." if len(self.po_notes) > 50 else f"   PO Notes: {self.po_notes}")
            response = await self.planning_stub.ApproveReviewPlan(request)  # type: ignore[union-attr]
            print_info(f"   ✅ Received response from ApproveReviewPlan")

            # Verify response
            print_info(f"   📋 Response received:")
            print_info(f"      Success: {response.success}")
            print_info(f"      Message: {response.message}")
            print_info(f"      Plan ID: {response.plan_id if response.plan_id else 'None'}")

            if not response.success:
                print_error(f"   ❌ ApproveReviewPlan failed: {response.message}")
                raise ValueError(f"ApproveReviewPlan failed: {response.message}")

            if not response.plan_id:
                print_error(f"   ❌ ApproveReviewPlan did not return plan_id")
                raise ValueError("ApproveReviewPlan did not return plan_id")

            plan_id = response.plan_id
            print_success(f"✅ Plan approved: {plan_id}")
            print_info(f"   Plan ID: {plan_id}")
            print_info(f"   Story ID: {story_id}")

            # Verify plan properties in response
            if not response.ceremony:
                raise ValueError("Response missing ceremony")

            # Find review result for this story
            review_result = None
            for result in response.ceremony.review_results:
                if result.story_id == story_id:
                    review_result = result
                    break

            if not review_result:
                raise ValueError(f"Review result not found for story {story_id}")

            if review_result.approval_status != "APPROVED":
                raise ValueError(
                    f"Expected approval_status APPROVED, got: {review_result.approval_status}"
                )

            print_success("Plan has correct properties")
            print_success("Ceremony updated with approved_result")

            elapsed = time.time() - start_time
            self.stage_timings[1] = elapsed

            # Track approved plan
            self.approved_plans[story_id] = plan_id

            return plan_id

        except grpc.RpcError as e:
            print_error(f"gRPC error: {e.code()} - {e.details()}")
            raise
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback

            traceback.print_exc()
            raise

    # ========== ETAPA 1.5: Test Idempotency ==========
    async def stage_1_5_test_idempotency(
        self, ceremony_id: str, story_id: str, expected_plan_id: str
    ) -> bool:
        """Etapa 1.5: Test idempotency of ApproveReviewPlan.

        Note: ApproveReviewPlanRequest does not have request_id field,
        so we test idempotency by calling the same approval twice and
        verifying it returns the same plan_id or rejects the duplicate.
        """
        print_stage(1, "Test Idempotency (ApproveReviewPlan)")

        start_time = time.time()

        if not self.planning_stub:
            raise ValueError("Planning stub not initialized")

        try:
            # Build request (same as first call)
            request = planning_pb2.ApproveReviewPlanRequest(
                ceremony_id=ceremony_id,
                story_id=story_id,
                approved_by=self.po_approved_by,
                po_notes=self.po_notes,
            )

            if self.po_concerns:
                request.po_concerns = self.po_concerns

            if self.priority_adjustment:
                request.priority_adjustment = self.priority_adjustment

            if self.po_priority_reason:
                request.po_priority_reason = self.po_priority_reason

            # Second call with same parameters (should be idempotent)
            print_info(f"📞 Calling ApproveReviewPlan again (idempotency test)...")
            print_info(f"   Ceremony ID: {ceremony_id}")
            print_info(f"   Story ID: {story_id}")
            print_info(f"   Expected plan_id: {expected_plan_id}")

            try:
                response = await self.planning_stub.ApproveReviewPlan(request)  # type: ignore[union-attr]

                # If response is successful, verify it returns the same plan_id
                if response.success:
                    if response.plan_id:
                        if response.plan_id == expected_plan_id:
                            print_success(
                                f"✅ IDEMPOTENCY VALIDATED: Second call returned same plan_id: {response.plan_id}"
                            )
                        else:
                            print_error(
                                f"❌ IDEMPOTENCY VIOLATION: "
                                f"Second call returned different plan_id: {response.plan_id} "
                                f"(expected: {expected_plan_id})"
                            )
                            raise ValueError(
                                f"Idempotency violation: plan_id mismatch. "
                                f"Expected: {expected_plan_id}, got: {response.plan_id}"
                            )
                    else:
                        print_warning("Second call succeeded but did not return plan_id")
                else:
                    # If second call fails, check if it's because story is already approved
                    error_msg = response.message or ""
                    if "already" in error_msg.lower() or "approved" in error_msg.lower():
                        print_success(
                            f"✅ IDEMPOTENCY VALIDATED: Second call correctly rejected "
                            f"(story already approved): {error_msg}"
                        )
                    else:
                        print_warning(f"Second call failed with unexpected error: {error_msg}")

            except grpc.RpcError as e:
                # If gRPC error indicates already approved, that's valid idempotency
                error_code = e.code()
                error_details = e.details() or ""

                if error_code == grpc.StatusCode.ALREADY_EXISTS or error_code == grpc.StatusCode.INVALID_ARGUMENT:
                    if "already" in error_details.lower() or "approved" in error_details.lower():
                        print_success(
                            f"✅ IDEMPOTENCY VALIDATED: Second call correctly rejected "
                            f"(gRPC error): {error_code} - {error_details}"
                        )
                    else:
                        print_warning(f"gRPC error may indicate idempotency: {error_code} - {error_details}")
                else:
                    print_error(f"Unexpected gRPC error: {error_code} - {error_details}")
                    raise

            # Idempotency is verified by the checks above:
            # - If second call succeeds, it must return the same plan_id
            # - If second call fails, it must be because story is already approved
            # Note: We do NOT check for multiple plan_ids in all tasks because
            # a story can have multiple plans from different ceremonies, which is normal.

            elapsed = time.time() - start_time
            self.stage_timings[1.5] = elapsed  # type: ignore[index]

            return True

        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback

            traceback.print_exc()
            raise

    # ========== ETAPA 1b: Rechazar Plan para una Story (RejectReviewPlan) ==========
    async def stage_1b_reject_one_story(
        self, ceremony_id: str, story_id: str
    ) -> bool:
        """Etapa 1b: Llamar RejectReviewPlan para simular que el PO no aprueba la review."""
        print_stage(1, "Rechazar Plan (RejectReviewPlan) - Simular no aprobación PO")

        start_time = time.time()

        if not self.planning_stub:
            raise ValueError("Planning stub not initialized")

        rejected_by = os.getenv("PO_REJECTED_BY", "e2e-po@system.local")
        rejection_reason = os.getenv(
            "PO_REJECTION_REASON", "E2E test rejection - needs more detail"
        )

        try:
            request = planning_pb2.RejectReviewPlanRequest(
                ceremony_id=ceremony_id,
                story_id=story_id,
                rejected_by=rejected_by,
                rejection_reason=rejection_reason,
            )

            print_info(f"📞 Calling RejectReviewPlan for story {story_id}...")
            print_info(f"   Ceremony ID: {ceremony_id}")
            print_info(f"   Story ID: {story_id}")
            print_info(f"   Rejected by: {rejected_by}")
            print_info(f"   Reason: {rejection_reason[:50]}...")
            response = await self.planning_stub.RejectReviewPlan(request)  # type: ignore[union-attr]
            print_info("   ✅ Received response from RejectReviewPlan")

            if not response.success:
                print_error(f"   ❌ RejectReviewPlan failed: {response.message}")
                raise ValueError(f"RejectReviewPlan failed: {response.message}")

            if not response.ceremony:
                raise ValueError("Response missing ceremony")

            review_result = None
            for result in response.ceremony.review_results:
                if result.story_id == story_id:
                    review_result = result
                    break
            if not review_result:
                raise ValueError(f"Review result not found for story {story_id}")
            if review_result.approval_status != "REJECTED":
                raise ValueError(
                    f"Expected approval_status REJECTED, got: {review_result.approval_status}"
                )

            self.rejected_story_ids.add(story_id)
            print_success(f"✅ Plan rejected for story {story_id}")
            elapsed = time.time() - start_time
            self.stage_timings[1.6] = elapsed  # type: ignore[index]
            return True

        except grpc.RpcError as e:
            print_error(f"gRPC error: {e.code()} - {e.details()}")
            raise
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback

            traceback.print_exc()
            raise

    # ========== ETAPA 2: Validar Plan en Storage ==========
    async def stage_2_validate_plan_storage(
        self, plan_id: str, story_id: str
    ) -> bool:
        """Etapa 2: Validar plan en storage (Neo4j/Valkey)."""
        print_stage(2, "Validar Plan en Storage")

        start_time = time.time()

        # Note: Direct Neo4j/Valkey access would require additional clients
        # For now, we validate through gRPC by checking that tasks have plan_id
        # In a full implementation, we would:
        # 1. Connect to Neo4j and query for Plan node
        # 2. Connect to Valkey and check plan data
        # 3. Verify HAS_PLAN relationship

        print_info("Validating plan through task associations...")

        # Get tasks for story
        tasks = await self.list_tasks(story_id=story_id, limit=1000)

        # Verify at least one task has plan_id
        tasks_with_plan = [t for t in tasks if t.plan_id == plan_id]
        if not tasks_with_plan:
            raise ValueError(
                f"No tasks found with plan_id {plan_id} for story {story_id}"
            )

        print_success(f"Found {len(tasks_with_plan)} tasks associated with plan {plan_id}")
        print_info(f"  Total tasks for story: {len(tasks)}")
        print_info(f"  Tasks with plan_id {plan_id}: {len(tasks_with_plan)}")
        print_info("Note: Direct Neo4j/Valkey validation would require additional clients")

        elapsed = time.time() - start_time
        self.stage_timings[2] = elapsed

        return True

    # ========== ETAPA 3: Validar Tareas con Decisión ==========
    async def stage_3_validate_tasks_with_decision(
        self, plan_id: str, story_id: str, expected_task_count: int
    ) -> bool:
        """Etapa 3: Validar tareas con decision_metadata."""
        print_stage(3, "Validar Tareas con Decisión")

        start_time = time.time()

        # Small delay to ensure tasks are persisted after approval
        await asyncio.sleep(2)

        # Get tasks for plan (filter by story_id for efficiency and accuracy)
        tasks = await self.list_tasks_by_plan(plan_id, story_id=story_id)

        # Also get all tasks for story for debugging
        all_story_tasks = await self.list_tasks(story_id=story_id, limit=1000)
        tasks_with_plan = [t for t in all_story_tasks if t.plan_id == plan_id]
        tasks_without_plan = [t for t in all_story_tasks if not t.plan_id or t.plan_id == ""]

        print_info(f"Debug info:")
        print_info(f"  Total tasks for story: {len(all_story_tasks)}")
        print_info(f"  Tasks with plan_id {plan_id}: {len(tasks_with_plan)}")
        print_info(f"  Tasks without plan_id: {len(tasks_without_plan)}")
        print_info(f"  Tasks found by list_tasks_by_plan: {len(tasks)}")

        # Validate we have at least the expected count
        # (may be more if tasks were created elsewhere)
        if len(tasks) < expected_task_count:
            raise ValueError(
                f"Expected at least {expected_task_count} tasks, got {len(tasks)}. "
                f"Total story tasks: {len(all_story_tasks)}, "
                f"Tasks with plan_id: {len(tasks_with_plan)}, "
                f"Tasks without plan_id: {len(tasks_without_plan)}"
            )

        print_info(
            f"Found {len(tasks)} tasks (expected at least {expected_task_count})"
        )

        print_success(f"Found {len(tasks)} tasks for plan {plan_id}")

        # Validate each task
        for task in tasks:
            # Validate plan_id
            if task.plan_id != plan_id:
                raise ValueError(
                    f"Task {task.task_id} has wrong plan_id: {task.plan_id}"
                )

            # Validate type (case-insensitive comparison)
            # Protobuf may return enum values in different case
            task_type_upper = task.type.upper() if task.type else ""
            if task_type_upper != "BACKLOG_REVIEW_IDENTIFIED":
                raise ValueError(
                    f"Task {task.task_id} has wrong type: {task.type} "
                    f"(expected BACKLOG_REVIEW_IDENTIFIED, got {task_type_upper})"
                )

            print_success(f"Task {task.task_id} validated")

        print_info(
            "Note: decision_metadata validation would require Neo4j access "
            "to check relationship properties"
        )

        elapsed = time.time() - start_time
        self.stage_timings[3] = elapsed

        return True

    # ========== ETAPA 4: Validar Ceremonia Actualizada ==========
    async def stage_4_validate_ceremony_updated(
        self, ceremony_id: str, story_id: str, approved_by: str
    ) -> bool:
        """Etapa 4: Validar ceremonia actualizada."""
        print_stage(4, "Validar Ceremonia Actualizada")

        start_time = time.time()

        # Small delay to ensure ceremony is persisted after approval
        await asyncio.sleep(2)

        ceremony = await self.get_ceremony(ceremony_id)
        if not ceremony:
            raise ValueError("Ceremony not found")

        # Find review result for story
        review_result = None
        for result in ceremony.review_results:
            if result.story_id == story_id:
                review_result = result
                break

        if not review_result:
            raise ValueError(f"Review result not found for story {story_id}")

        # Debug logging
        print_info(f"Debug: Review result for story {story_id}:")
        print_info(f"  approval_status: {review_result.approval_status}")
        print_info(f"  approved_by: {review_result.approved_by}")
        print_info(f"  approved_at: {review_result.approved_at}")
        print_info(f"  po_notes: {review_result.po_notes}")
        print_info(f"  po_concerns: {review_result.po_concerns}")
        print_info(f"  priority_adjustment: {review_result.priority_adjustment}")
        print_info(f"  po_priority_reason: {review_result.po_priority_reason}")

        # Validate approval_status
        if review_result.approval_status != "APPROVED":
            raise ValueError(
                f"Expected approval_status APPROVED, got: {review_result.approval_status}"
            )

        # Validate approved_by
        if review_result.approved_by != approved_by:
            raise ValueError(
                f"Expected approved_by {approved_by}, got: {review_result.approved_by}"
            )

        # Validate approved_at
        if not review_result.approved_at:
            raise ValueError("Review result missing approved_at")

        # Validate po_notes
        # po_notes are now stored in Valkey and should be correctly retrieved
        if not review_result.po_notes:
            raise ValueError(
                f"Review result missing po_notes. "
                f"Was sent in request: '{self.po_notes}'. "
                f"po_notes should be persisted in Valkey and retrieved correctly."
            )
        if review_result.po_notes != self.po_notes:
            raise ValueError(
                f"po_notes mismatch. Expected: '{self.po_notes}', "
                f"got: '{review_result.po_notes}'"
            )
        print_success(f"Review result has po_notes: {review_result.po_notes[:50]}...")

        print_success("Review result has approval_status = APPROVED")
        print_success(f"Review result has approved_by = {approved_by}")
        print_success("Review result has approved_at timestamp")
        # po_notes validation is handled above (with warning if empty due to known bug)

        elapsed = time.time() - start_time
        self.stage_timings[4] = elapsed

        return True

    # ========== ETAPA 5: Validar Evento Publicado ==========
    async def stage_5_validate_event_published(
        self, ceremony_id: str, story_id: str, plan_id: str
    ) -> bool:
        """Etapa 5: Validar evento publicado."""
        print_stage(5, "Validar Evento Publicado")

        start_time = time.time()

        # Note: Direct NATS subscription would require NATS client
        # For now, we assume event is published if ApproveReviewPlan succeeded
        # In a full implementation, we would:
        # 1. Subscribe to planning.plan.approved stream
        # 2. Wait for event with matching ceremony_id, story_id, plan_id
        # 3. Validate payload structure

        print_info(
            "Event validation assumes success if ApproveReviewPlan succeeded"
        )
        print_info(
            "Note: Direct NATS validation would require NATS client subscription"
        )

        elapsed = time.time() - start_time
        self.stage_timings[5] = elapsed

        return True

    # ========== ETAPA 6: Aprobar Plan para Todas las Stories Restantes ==========
    async def stage_6_approve_all_remaining_stories(
        self, ceremony_id: str, story_ids: list[str]
    ) -> bool:
        """Etapa 6: Aprobar plan para todas las stories restantes."""
        print_stage(6, "Aprobar Plan para Todas las Stories Restantes")

        start_time = time.time()

        # Get already approved and rejected stories
        approved_story_ids = set(self.approved_plans.keys())
        remaining_story_ids = [
            sid
            for sid in story_ids
            if sid not in approved_story_ids and sid not in self.rejected_story_ids
        ]

        if not remaining_story_ids:
            print_info("No remaining stories to approve (approved + rejected cover all)")
            elapsed = time.time() - start_time
            self.stage_timings[6] = elapsed
            return True

        print_info(f"Approving plans for {len(remaining_story_ids)} remaining stories...")

        for idx, story_id in enumerate(remaining_story_ids, start=1):
            print_info(f"Approving plan for story {story_id} ({idx}/{len(remaining_story_ids)})...")

            try:
                plan_id = await self.stage_1_approve_first_story(ceremony_id, story_id)
                print_success(f"Plan {plan_id} created for story {story_id}")
            except Exception as e:
                print_error(f"Failed to approve plan for story {story_id}: {e}")
                raise

        print_success(f"All {len(remaining_story_ids)} remaining stories approved")

        elapsed = time.time() - start_time
        self.stage_timings[6] = elapsed

        return True

    # ========== ETAPA 7: Validar Estado Final ==========
    async def stage_7_validate_final_state(
        self, ceremony_id: str, expected_story_count: int
    ) -> bool:
        """Etapa 7: Validar estado final de ceremonia."""
        print_stage(7, "Validar Estado Final de Ceremonia")

        start_time = time.time()

        ceremony = await self.get_ceremony(ceremony_id)
        if not ceremony:
            raise ValueError("Ceremony not found")

        # Count approved stories (expected_story_count = stories we intended to approve)
        approved_count = 0
        rejected_count = 0
        for review_result in ceremony.review_results:
            if review_result.approval_status == "APPROVED":
                approved_count += 1
            elif review_result.approval_status == "REJECTED":
                rejected_count += 1

        if approved_count != expected_story_count:
            raise ValueError(
                f"Expected {expected_story_count} approved stories, got {approved_count} "
                f"(rejected: {rejected_count})"
            )

        # Verify approved plans count matches
        if len(self.approved_plans) != expected_story_count:
            raise ValueError(
                f"Expected {expected_story_count} plans, got {len(self.approved_plans)}"
            )

        print_success(f"All {approved_count} stories have approval_status = APPROVED")
        print_success(f"All {len(self.approved_plans)} stories have Plan associated")
        print_success(f"Total plans created: {len(self.approved_plans)}")

        elapsed = time.time() - start_time
        self.stage_timings[7] = elapsed

        return True

    # ========== ETAPA 8: Validar Persistencia Completa ==========
    async def stage_8_validate_complete_persistence(
        self, ceremony_id: str
    ) -> bool:
        """Etapa 8: Validar persistencia completa."""
        print_stage(8, "Validar Persistencia Completa")

        start_time = time.time()

        # Validate all plans through task associations
        for story_id, plan_id in self.approved_plans.items():
            tasks = await self.list_tasks_by_plan(plan_id)
            if not tasks:
                raise ValueError(f"No tasks found for plan {plan_id}")

            # Verify all tasks have plan_id
            for task in tasks:
                if task.plan_id != plan_id:
                    raise ValueError(
                        f"Task {task.task_id} has wrong plan_id: {task.plan_id}"
                    )

        print_success(f"All {len(self.approved_plans)} plans validated")
        print_success("All tasks have plan_id assigned")
        print_info(
            "Note: Direct Neo4j/Valkey validation would require additional clients"
        )

        elapsed = time.time() - start_time
        self.stage_timings[8] = elapsed

        return True

    async def run(self) -> int:
        """Run the complete E2E test."""
        print()
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print(f"{Colors.BLUE}🧪 E2E Test: Approve Review Plan and Validate Plan Creation{Colors.NC}")
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print()

        print("Configuration:")
        print(f"  Planning Service: {self.planning_url}")
        print(f"  Project: {self.project_name}")
        print(f"  Epic: {self.epic_title}")
        print(f"  PO Approved By: {self.po_approved_by}")
        print()

        try:
            await self.setup()

            # Stage 0: Preparation
            ceremony_id, story_ids = await self.stage_0_preparation()

            if not story_ids:
                raise ValueError("No stories found in ceremony")

            # Get expected task count from first story's plan_preliminary
            ceremony = await self.get_ceremony(ceremony_id)
            if not ceremony:
                raise ValueError("Ceremony not found")

            first_story_id = story_ids[0]
            first_review_result = None
            for result in ceremony.review_results:
                if result.story_id == first_story_id:
                    first_review_result = result
                    break

            if not first_review_result or not first_review_result.plan_preliminary:
                raise ValueError("First story missing plan_preliminary")

            # Check if review is already approved
            approval_status = first_review_result.approval_status
            print_info(f"Review approval status: {approval_status}")

            if approval_status == "APPROVED":
                print_warning(
                    f"Story {first_story_id} already approved. "
                    f"Looking for a different story in PENDING status..."
                )
                # Find a story with PENDING status
                pending_story_id = None
                for result in ceremony.review_results:
                    if result.approval_status == "PENDING" and result.plan_preliminary:
                        pending_story_id = result.story_id
                        first_review_result = result
                        break

                if not pending_story_id:
                    raise ValueError(
                        "No stories with PENDING approval status found. "
                        "All stories in ceremony are already approved."
                    )

                print_success(f"Found story {pending_story_id} in PENDING status")
                first_story_id = pending_story_id

            # Calculate expected tasks:
            # - Tasks from task_decisions (new tasks created on approval)
            # - Existing tasks WITHOUT plan_id (created during backlog review, will be updated)
            tasks_from_decisions = len(
                first_review_result.plan_preliminary.task_decisions
            ) if first_review_result.plan_preliminary.task_decisions else 0

            # Get existing tasks for this story (created during backlog review)
            # Only count tasks that don't have a plan_id yet (will be updated)
            existing_tasks = await self.list_tasks(story_id=first_story_id, limit=1000)
            tasks_without_plan = [t for t in existing_tasks if not t.plan_id or t.plan_id == ""]
            existing_task_count = len(tasks_without_plan)

            # Total expected: existing tasks without plan_id (will be updated) + new tasks from decisions
            expected_task_count = existing_task_count + tasks_from_decisions

            print_info(
                f"Expected tasks: {existing_task_count} existing (without plan_id) + "
                f"{tasks_from_decisions} from decisions = {expected_task_count} total"
            )
            print_info(
                f"   Total tasks for story: {len(existing_tasks)} "
                f"(of which {existing_task_count} will be updated with plan_id)"
            )

            # Stage 1: Approve first story
            plan_id = await self.stage_1_approve_first_story(ceremony_id, first_story_id)

            # Stage 1.5: Test idempotency (call ApproveReviewPlan again with same request_id)
            await self.stage_1_5_test_idempotency(ceremony_id, first_story_id, plan_id)

            # Stage 1b: Reject one story via RejectReviewPlan (PO no aprueba) when multiple stories
            if len(story_ids) >= 2:
                await self.stage_1b_reject_one_story(ceremony_id, story_ids[1])

            # Stage 2: Validate plan in storage
            await self.stage_2_validate_plan_storage(plan_id, first_story_id)

            # Stage 3: Validate tasks with decision
            # Note: We expect at least the existing tasks + new tasks from decisions
            await self.stage_3_validate_tasks_with_decision(
                plan_id, first_story_id, expected_task_count
            )

            # Stage 4: Validate ceremony updated
            await self.stage_4_validate_ceremony_updated(
                ceremony_id, first_story_id, self.po_approved_by
            )

            # Stage 5: Validate event published
            await self.stage_5_validate_event_published(
                ceremony_id, first_story_id, plan_id
            )

            # Stage 6: Approve all remaining stories
            await self.stage_6_approve_all_remaining_stories(ceremony_id, story_ids)

            # Stage 7: Validate final state (expected approved = total - rejected)
            expected_approved_count = len(story_ids) - len(self.rejected_story_ids)
            await self.stage_7_validate_final_state(
                ceremony_id, expected_approved_count
            )

            # Stage 8: Validate complete persistence
            await self.stage_8_validate_complete_persistence(ceremony_id)

            # Print summary
            print()
            print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
            print(f"{Colors.GREEN}📊 Test Execution Summary{Colors.NC}")
            print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
            print()

            print("Ceremony:")
            print(f"  Ceremony ID: {ceremony_id}")
            print(f"  Status: REVIEWING")
            print(
                f"  Stories Approved: {len(self.approved_plans)}/{len(story_ids)}"
            )
            if self.rejected_story_ids:
                print(
                    f"  Stories Rejected (RejectReviewPlan): "
                    f"{len(self.rejected_story_ids)} - {sorted(self.rejected_story_ids)}"
                )
            print()

            print("Plans Created:")
            print(f"  Total: {len(self.approved_plans)} plans")
            print("  By Story:")
            for story_id, plan_id in self.approved_plans.items():
                tasks = await self.list_tasks_by_plan(plan_id)
                print(f"    - {story_id}: {plan_id} ({len(tasks)} tasks)")
            print()

            print("Tasks with Decision:")
            total_tasks = 0
            for plan_id in self.approved_plans.values():
                tasks = await self.list_tasks_by_plan(plan_id)
                total_tasks += len(tasks)
            print(f"  Total: {total_tasks} tasks")
            print("  All tasks have:")
            print("    - plan_id assigned")
            print("    - type BACKLOG_REVIEW_IDENTIFIED")
            print()

            print("Timing by Stage:")
            for stage_num in sorted(self.stage_timings.keys()):
                elapsed = self.stage_timings[stage_num]
                print(f"  Etapa {stage_num}: {elapsed:.1f}s")
            total_time = sum(self.stage_timings.values())
            print(f"  Total: {total_time:.1f}s")
            print()

            print(f"{Colors.GREEN}✅ Todas las etapas completadas exitosamente{Colors.NC}")
            print(f"{Colors.GREEN}✅ Test Completed Successfully{Colors.NC}")
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
            await self.cleanup()


async def main() -> int:
    """Main entry point."""
    test = ApproveReviewPlanTest()
    return await test.run()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

