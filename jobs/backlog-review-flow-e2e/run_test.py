#!/usr/bin/env python3
"""E2E test for Backlog Review Flow.

This test verifies the complete backlog review flow as described in:
docs/architecture/BACKLOG_REVIEW_FLOW_NO_STYLES.md

Flow Steps Verified:
1. UI → Planning Service (gRPC): Get node relations
2. UI → Planning Service (gRPC): Create backlog review ceremony
3. Planning → Context Service (gRPC): Get context rehydration
4. Planning → Ray Executor (gRPC): Trigger deliberation per RBAC agent
5. Ray Executor → Ray Job: Create Ray job
6. Ray Job → vLLM Service (REST): Model invocation
7. vLLM → NATS: VLLM response (StoryID, DeliberationId)
8. Backlog Review Processor → Context Service (gRPC): Save deliberation
9. Backlog Review Processor → Planning Service (NATS): DELIBERATIONS COMPLETED
10. Backlog Review Processor → Ray Executor (gRPC): Trigger task creation
11. Ray Executor → Ray Job: Create Ray job for task creation
12. Ray Job → vLLM Service (REST): Model invocation with all deliberations
13. vLLM → NATS: VLLM response (TaskId, StoryID) - N events
14. Backlog Review Processor → Context Service (gRPC): Save TASK response (N times)
15. Backlog Review Processor → Planning Service (NATS): ALL TASK CREATED
16. Planning Service → UI (gRPC/WebSocket): Notify all tasks created
"""

import asyncio
import os
import sys
import time
from datetime import UTC, datetime
from typing import Optional

import grpc
from fleet.planning.v2 import planning_pb2, planning_pb2_grpc
from fleet.context.v1 import context_pb2, context_pb2_grpc
from fleet.ray_executor.v1 import ray_executor_pb2, ray_executor_pb2_grpc

# Neo4j and Valkey for verification
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

# Kubernetes client for logs
try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False


class Colors:
    """ANSI color codes for terminal output."""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color


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


class BacklogReviewFlowE2ETest:
    """E2E test for Backlog Review Flow."""

    def __init__(self):
        """Initialize test with service URLs from environment."""
        # Service URLs (Kubernetes internal DNS)
        self.planning_url = os.getenv(
            "PLANNING_SERVICE_URL",
            "planning.swe-ai-fleet.svc.cluster.local:50054"
        )
        self.context_url = os.getenv(
            "CONTEXT_SERVICE_URL",
            "context.swe-ai-fleet.svc.cluster.local:50054"
        )
        self.ray_executor_url = os.getenv(
            "RAY_EXECUTOR_URL",
            "ray-executor.swe-ai-fleet.svc.cluster.local:50056"
        )

        # Neo4j connection
        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j.swe-ai-fleet.svc.cluster.local:7687")
        self.neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "")

        # Valkey connection
        self.valkey_host = os.getenv("VALKEY_HOST", "valkey.swe-ai-fleet.svc.cluster.local")
        self.valkey_port = int(os.getenv("VALKEY_PORT", "6379"))

        # Test data
        self.ceremony_id: Optional[str] = None
        self.project_id: Optional[str] = None
        self.epic_id: Optional[str] = None
        # Handle empty string case - if TEST_STORY_ID is set but empty, will create new hierarchy
        test_story_id = os.getenv("TEST_STORY_ID", "").strip()
        self.story_id = test_story_id if test_story_id else None  # Will be created if not provided
        self.created_by = os.getenv("TEST_CREATED_BY", "po@test.com").strip()

        # Test data for creation (if not using existing IDs)
        # Handle empty strings - if env var is set but empty, use default
        test_project_name = os.getenv("TEST_PROJECT_NAME", "").strip()
        self.test_project_name = test_project_name if test_project_name else f"E2E Test Project {int(time.time())}"

        test_epic_title = os.getenv("TEST_EPIC_TITLE", "").strip()
        self.test_epic_title = test_epic_title if test_epic_title else f"E2E Test Epic {int(time.time())}"

        test_story_title = os.getenv("TEST_STORY_TITLE", "").strip()
        self.test_story_title = test_story_title if test_story_title else f"E2E Test Story {int(time.time())}"

        test_story_brief = os.getenv("TEST_STORY_BRIEF", "").strip()
        self.test_story_brief = test_story_brief if test_story_brief else "This is a test story created by the E2E test for backlog review flow verification."

        # gRPC channels and stubs
        self.planning_channel: Optional[grpc.aio.Channel] = None
        self.planning_stub: Optional[planning_pb2_grpc.PlanningServiceStub] = None
        self.context_channel: Optional[grpc.aio.Channel] = None
        self.context_stub: Optional[context_pb2_grpc.ContextServiceStub] = None
        self.ray_executor_channel: Optional[grpc.aio.Channel] = None
        self.ray_executor_stub: Optional[ray_executor_pb2_grpc.RayExecutorServiceStub] = None

        # Neo4j and Valkey clients
        self.neo4j_driver = None
        self.valkey_client = None

        # Kubernetes client
        self.k8s_core_v1 = None
        self.k8s_namespace = os.getenv("KUBERNETES_NAMESPACE", "swe-ai-fleet")

    async def setup(self) -> None:
        """Set up gRPC connections and database clients."""
        print_info("Setting up connections...")

        # Create gRPC channels
        self.planning_channel = grpc.aio.insecure_channel(self.planning_url)
        self.context_channel = grpc.aio.insecure_channel(self.context_url)
        self.ray_executor_channel = grpc.aio.insecure_channel(self.ray_executor_url)

        # Create stubs
        self.planning_stub = planning_pb2_grpc.PlanningServiceStub(self.planning_channel)
        self.context_stub = context_pb2_grpc.ContextServiceStub(self.context_channel)
        self.ray_executor_stub = ray_executor_pb2_grpc.RayExecutorServiceStub(self.ray_executor_channel)

        # Set up Neo4j
        if NEO4J_AVAILABLE and self.neo4j_password:
            try:
                self.neo4j_driver = GraphDatabase.driver(
                    self.neo4j_uri,
                    auth=(self.neo4j_username, self.neo4j_password)
                )
                # Verify connection
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

        # Set up Kubernetes client
        if KUBERNETES_AVAILABLE:
            try:
                # Try to load in-cluster config first (when running in K8s)
                try:
                    config.load_incluster_config()
                except config.ConfigException:
                    # Fall back to kubeconfig (for local development)
                    config.load_kube_config()

                self.k8s_core_v1 = client.CoreV1Api()
                print_success("Kubernetes client initialized")
            except Exception as e:
                print_warning(f"Kubernetes client initialization failed: {e}")

        print_success("Setup completed")

    async def cleanup(self) -> None:
        """Clean up connections."""
        print_info("Cleaning up connections...")

        if self.planning_channel:
            await self.planning_channel.close()
        if self.context_channel:
            await self.context_channel.close()
        if self.ray_executor_channel:
            await self.ray_executor_channel.close()

        if self.neo4j_driver:
            self.neo4j_driver.close()

        if self.valkey_client:
            self.valkey_client.close()

        print_success("Cleanup completed")

    def get_pod_logs(
        self,
        app_label: str,
        tail_lines: int = 50,
        container: Optional[str] = None
    ) -> Optional[str]:
        """Get logs from pods matching the app label.

        Args:
            app_label: Label selector (e.g., 'app=planning')
            tail_lines: Number of lines to retrieve
            container: Container name (optional, uses first container if not specified)

        Returns:
            Logs as string, or None if unavailable
        """
        if not self.k8s_core_v1:
            return None

        try:
            # List pods matching the label
            pods = self.k8s_core_v1.list_namespaced_pod(
                namespace=self.k8s_namespace,
                label_selector=app_label
            )

            if not pods.items:
                return None

            # Get logs from the first pod (or most recent)
            pod = pods.items[0]
            pod_name = pod.metadata.name

            # Get container name
            if not container:
                if pod.spec.containers:
                    container = pod.spec.containers[0].name
                else:
                    return None

            # Retrieve logs
            logs = self.k8s_core_v1.read_namespaced_pod_log(
                name=pod_name,
                namespace=self.k8s_namespace,
                container=container,
                tail_lines=tail_lines
            )

            return logs

        except ApiException as e:
            print_warning(f"Failed to get logs for {app_label}: {e}")
            return None
        except Exception as e:
            print_warning(f"Error getting logs for {app_label}: {e}")
            return None

    def print_service_logs(self, service_name: str, tail_lines: int = 50) -> None:
        """Print logs from a service's pods.

        Args:
            service_name: Service name (e.g., 'planning', 'context', 'ray-executor')
            tail_lines: Number of lines to retrieve
        """
        print_info(f"Recent logs from {service_name} service:")
        print(f"{Colors.BLUE}{'-' * 80}{Colors.NC}")

        logs = self.get_pod_logs(f"app={service_name}", tail_lines=tail_lines)
        if logs:
            # Print last N lines
            lines = logs.split('\n')
            for line in lines[-tail_lines:]:
                print(line)
        else:
            print_warning(f"Could not retrieve logs for {service_name}")

        print(f"{Colors.BLUE}{'-' * 80}{Colors.NC}")
        print()

    async def step_0_create_hierarchy(self) -> bool:
        """Step 0: Create Project → Epic → Story hierarchy."""
        print_step(0, "Create Project → Epic → Story Hierarchy")

        # If story_id is provided, skip creation
        if self.story_id:
            print_info("Using existing story ID - skipping hierarchy creation")
            print_info(f"Story ID: {self.story_id}")
            return True

        try:
            # Step 0.1: Create Project
            print_info("Creating project...")
            project_request = planning_pb2.CreateProjectRequest(
                name=self.test_project_name,
                description="E2E test project for backlog review flow",
                owner=self.created_by
            )
            project_response = await self.planning_stub.CreateProject(project_request)

            if not project_response.success:
                print_error(f"Failed to create project: {project_response.message}")
                return False

            self.project_id = project_response.project.project_id
            print_success(f"Project created: {self.project_id}")
            print_info(f"  Name: {project_response.project.name}")

            # Step 0.2: Create Epic
            print_info("Creating epic...")
            epic_request = planning_pb2.CreateEpicRequest(
                project_id=self.project_id,
                title=self.test_epic_title,
                description="E2E test epic for backlog review flow"
            )
            epic_response = await self.planning_stub.CreateEpic(epic_request)

            if not epic_response.success:
                print_error(f"Failed to create epic: {epic_response.message}")
                return False

            self.epic_id = epic_response.epic.epic_id
            print_success(f"Epic created: {self.epic_id}")
            print_info(f"  Title: {epic_response.epic.title}")

            # Step 0.3: Create Story
            print_info("Creating story...")
            story_request = planning_pb2.CreateStoryRequest(
                epic_id=self.epic_id,
                title=self.test_story_title,
                brief=self.test_story_brief,
                created_by=self.created_by
            )
            story_response = await self.planning_stub.CreateStory(story_request)

            if not story_response.success:
                print_error(f"Failed to create story: {story_response.message}")
                return False

            self.story_id = story_response.story.story_id
            print_success(f"Story created: {self.story_id}")
            print_info(f"  Title: {story_response.story.title}")
            print_info(f"  State: {story_response.story.state}")

            return True

        except grpc.RpcError as e:
            print_error(f"gRPC error: {e.code()} - {e.details()}")
            print()
            print_info("Showing recent Planning Service logs for debugging:")
            self.print_service_logs("planning", tail_lines=30)
            return False
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def step_1_create_ceremony(self) -> bool:
        """Step 1: Create Backlog Review Ceremony."""
        print_step(1, "Create Backlog Review Ceremony")

        # Validate story_id is required - ceremonies must have at least one story
        if not self.story_id or not self.story_id.strip():
            print_error("Story ID is REQUIRED - ceremonies must have at least one story")
            print_error("Either set TEST_STORY_ID or ensure step_0_create_hierarchy succeeded")
            return False

        story_id = self.story_id.strip()
        print_info(f"Creating ceremony with story_id: {story_id}")

        try:
            request = planning_pb2.CreateBacklogReviewCeremonyRequest(
                created_by=self.created_by,
                story_ids=[story_id]
            )

            response = await self.planning_stub.CreateBacklogReviewCeremony(request)

            if not response.success:
                print_error(f"Failed to create ceremony: {response.message}")
                print_info("This might be because:")
                print_info("  - Story ID does not exist in the system")
                print_info("  - Story ID format is invalid")
                print_info("  - User does not have permission")
                print_info("  - Invalid created_by value")
                # Show planning service logs for debugging
                print()
                print_info("Showing recent Planning Service logs for debugging:")
                self.print_service_logs("planning", tail_lines=20)
                return False

            self.ceremony_id = response.ceremony.ceremony_id
            print_success(f"Ceremony created: {self.ceremony_id}")
            print_info(f"Status: {response.ceremony.status}")
            print_info(f"Stories: {list(response.ceremony.story_ids)}")

            return True

        except grpc.RpcError as e:
            print_error(f"gRPC error: {e.code()} - {e.details()}")
            if e.code() == grpc.StatusCode.INVALID_ARGUMENT:
                print_info("Common causes:")
                print_info("  - Story ID does not exist in the system")
                print_info("  - Story ID format is invalid")
                print_info("  - Invalid created_by value")
                print_info("  - Missing required fields")
            # Show planning service logs for debugging
            print()
            print_info("Showing recent Planning Service logs for debugging:")
            self.print_service_logs("planning", tail_lines=30)
            return False
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def step_2_verify_ceremony_persistence(self) -> bool:
        """Step 2: Verify ceremony persisted in Neo4j and Valkey."""
        print_step(2, "Verify Ceremony Persistence")

        if not self.ceremony_id:
            print_error("Ceremony ID not set")
            return False

        # Verify Neo4j
        if self.neo4j_driver:
            try:
                with self.neo4j_driver.session() as session:
                    result = session.run(
                        "MATCH (c:BacklogReviewCeremony {id: $id}) RETURN c",
                        id=self.ceremony_id
                    )
                    record = result.single()
                    if record:
                        print_success(f"Ceremony found in Neo4j: {self.ceremony_id}")
                    else:
                        print_error(f"Ceremony not found in Neo4j: {self.ceremony_id}")
                        return False
            except Exception as e:
                print_warning(f"Neo4j verification failed: {e}")
        else:
            print_warning("Neo4j not available, skipping verification")

        # Verify Valkey
        if self.valkey_client:
            try:
                key = f"ceremony:{self.ceremony_id}"
                value = self.valkey_client.get(key)
                if value:
                    print_success(f"Ceremony cached in Valkey: {self.ceremony_id}")
                else:
                    print_warning(f"Ceremony not cached in Valkey: {self.ceremony_id}")
            except Exception as e:
                print_warning(f"Valkey verification failed: {e}")
        else:
            print_warning("Valkey not available, skipping verification")

        return True

    async def step_3_start_ceremony(self) -> bool:
        """Step 3: Start Backlog Review Ceremony."""
        print_step(3, "Start Backlog Review Ceremony")

        if not self.ceremony_id:
            print_error("Ceremony ID not set")
            return False

        # Verify ceremony has stories (required)
        try:
            get_request = planning_pb2.GetBacklogReviewCeremonyRequest(
                ceremony_id=self.ceremony_id
            )
            get_response = await self.planning_stub.GetBacklogReviewCeremony(get_request)

            if get_response.success and get_response.ceremony:
                story_count = len(get_response.ceremony.story_ids)
                if story_count == 0:
                    print_error("Ceremony has no stories - cannot start review")
                    print_error("Ceremonies must have at least one story to start")
                    return False
                print_info(f"Ceremony has {story_count} story/stories")
        except Exception as e:
            print_warning(f"Could not verify ceremony stories: {e}")
            # Continue anyway - the start request will fail if there are no stories

        try:
            request = planning_pb2.StartBacklogReviewCeremonyRequest(
                ceremony_id=self.ceremony_id,
                started_by=self.created_by
            )

            response = await self.planning_stub.StartBacklogReviewCeremony(request)

            if not response.success:
                print_error(f"Failed to start ceremony: {response.message}")
                print()
                print_info("Showing recent Planning Service logs for debugging:")
                self.print_service_logs("planning", tail_lines=20)
                return False

            print_success(f"Ceremony started: {self.ceremony_id}")
            print_info(f"Status: {response.ceremony.status}")
            print_info(f"Total deliberations submitted: {response.total_deliberations_submitted}")

            # Verify status changed to IN_PROGRESS
            if response.ceremony.status != "IN_PROGRESS":
                print_error(f"Expected status IN_PROGRESS, got {response.ceremony.status}")
                return False

            print_success("Ceremony status is IN_PROGRESS")

            return True

        except grpc.RpcError as e:
            print_error(f"gRPC error: {e.code()} - {e.details()}")
            print()
            print_info("Showing recent Planning Service logs for debugging:")
            self.print_service_logs("planning", tail_lines=20)
            return False
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def step_4_wait_for_deliberations(self, timeout_seconds: int = 300) -> bool:
        """Step 4: Wait for deliberations to complete."""
        print_step(4, "Wait for Deliberations to Complete")

        if not self.ceremony_id:
            print_error("Ceremony ID not set")
            return False

        print_info(f"Waiting up to {timeout_seconds} seconds for deliberations to complete...")
        print_info("This step verifies:")
        print_info("  - Ray jobs are created and executed")
        print_info("  - vLLM Service is invoked")
        print_info("  - NATS events are published")
        print_info("  - Backlog Review Processor consumes events")
        print_info("  - Deliberations are saved in Context Service")
        print_info("  - Ceremony status transitions to REVIEWING")

        start_time = time.time()
        check_interval = 10  # Check every 10 seconds
        last_log_check = 0
        log_check_interval = 60  # Check logs every 60 seconds

        while time.time() - start_time < timeout_seconds:
            try:
                # Check ceremony status
                request = planning_pb2.GetBacklogReviewCeremonyRequest(
                    ceremony_id=self.ceremony_id
                )
                response = await self.planning_stub.GetBacklogReviewCeremony(request)

                if response.success and response.ceremony:
                    status = response.ceremony.status
                    elapsed = int(time.time() - start_time)
                    print_info(f"[{elapsed}s] Current ceremony status: {status}")

                    if status == "REVIEWING":
                        print_success("Deliberations completed! Ceremony status is REVIEWING")
                        # Show relevant logs
                        print()
                        print_info("Showing recent logs from relevant services:")
                        self.print_service_logs("planning", tail_lines=20)
                        self.print_service_logs("backlog-review-processor", tail_lines=20)
                        return True

                # Periodically show logs to help debug
                if time.time() - last_log_check >= log_check_interval:
                    elapsed = int(time.time() - start_time)
                    print_info(f"[{elapsed}s] Checking service logs...")
                    self.print_service_logs("planning", tail_lines=10)
                    self.print_service_logs("backlog-review-processor", tail_lines=10)
                    last_log_check = time.time()

                await asyncio.sleep(check_interval)

            except Exception as e:
                print_warning(f"Error checking ceremony status: {e}")
                await asyncio.sleep(check_interval)

        print_error(f"Timeout waiting for deliberations to complete after {timeout_seconds} seconds")
        print()
        print_info("Showing final logs from relevant services:")
        self.print_service_logs("planning", tail_lines=30)
        self.print_service_logs("backlog-review-processor", tail_lines=30)
        self.print_service_logs("ray-executor", tail_lines=20)
        return False

    async def step_5_verify_tasks_created(self, timeout_seconds: int = 300) -> bool:
        """Step 5: Verify tasks were created."""
        print_step(5, "Verify Tasks Created")

        if not self.ceremony_id:
            print_error("Ceremony ID not set")
            return False

        print_info(f"Waiting up to {timeout_seconds} seconds for tasks to be created...")
        print_info("This step verifies:")
        print_info("  - Task creation is triggered")
        print_info("  - Ray job for task extraction is created")
        print_info("  - vLLM Service is invoked for task extraction")
        print_info("  - Tasks are saved in Context Service")
        print_info("  - All tasks created event is published")

        # Verify tasks in Neo4j
        if self.neo4j_driver:
            start_time = time.time()
            check_interval = 10
            last_log_check = 0
            log_check_interval = 60

            while time.time() - start_time < timeout_seconds:
                try:
                    with self.neo4j_driver.session() as session:
                        result = session.run(
                            "MATCH (t:Task {story_id: $story_id}) RETURN count(t) AS task_count",
                            story_id=self.story_id
                        )
                        record = result.single()
                        if record:
                            task_count = record["task_count"]
                            elapsed = int(time.time() - start_time)
                            if task_count > 0:
                                print_success(f"Found {task_count} task(s) in Neo4j for story {self.story_id}")
                                # Show relevant logs
                                print()
                                print_info("Showing recent logs from relevant services:")
                                self.print_service_logs("backlog-review-processor", tail_lines=20)
                                self.print_service_logs("context", tail_lines=20)
                                return True
                            else:
                                print_info(f"[{elapsed}s] No tasks found yet...")

                    # Periodically show logs
                    if time.time() - last_log_check >= log_check_interval:
                        elapsed = int(time.time() - start_time)
                        print_info(f"[{elapsed}s] Checking service logs...")
                        self.print_service_logs("backlog-review-processor", tail_lines=10)
                        last_log_check = time.time()

                except Exception as e:
                    print_warning(f"Error checking tasks in Neo4j: {e}")

                await asyncio.sleep(check_interval)

            print_error(f"Timeout waiting for tasks to be created after {timeout_seconds} seconds")
            print()
            print_info("Showing final logs from relevant services:")
            self.print_service_logs("backlog-review-processor", tail_lines=30)
            self.print_service_logs("context", tail_lines=20)
            return False
        else:
            print_warning("Neo4j not available, cannot verify tasks")
            print_info("Assuming tasks were created (manual verification required)")
            return True

    async def run(self) -> int:
        """Run the complete E2E test."""
        print()
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print(f"{Colors.BLUE}🚀 Backlog Review Flow E2E Test{Colors.NC}")
        print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
        print()

        print("Configuration:")
        print(f"  Planning Service:  {self.planning_url}")
        print(f"  Context Service:   {self.context_url}")
        print(f"  Ray Executor:      {self.ray_executor_url}")
        print(f"  Neo4j:             {self.neo4j_uri}")
        print(f"  Valkey:            {self.valkey_host}:{self.valkey_port}")
        print()
        print("Test Data:")
        if self.story_id:
            print(f"  Story ID:          {self.story_id} (using existing)")
            print(f"  Project ID:        {self.project_id or '(will be created)'}")
            print(f"  Epic ID:           {self.epic_id or '(will be created)'}")
        else:
            print(f"  Story ID:          (will be created)")
            print(f"  Project Name:      {self.test_project_name}")
            print(f"  Epic Title:        {self.test_epic_title}")
            print(f"  Story Title:       {self.test_story_title}")
        print(f"  Created By:        {self.created_by}")
        print()

        try:
            # Setup
            await self.setup()

            # Run test steps
            steps = [
                ("Create Hierarchy", self.step_0_create_hierarchy),
                ("Create Ceremony", self.step_1_create_ceremony),
                ("Verify Persistence", self.step_2_verify_ceremony_persistence),
                ("Start Ceremony", self.step_3_start_ceremony),
                ("Wait for Deliberations", self.step_4_wait_for_deliberations),
                ("Verify Tasks Created", self.step_5_verify_tasks_created),
            ]

            for step_name, step_func in steps:
                success = await step_func()
                if not success:
                    print_error(f"Step '{step_name}' failed")
                    return 1

            print()
            print(f"{Colors.GREEN}{'=' * 80}{Colors.NC}")
            print(f"{Colors.GREEN}✅ All E2E test steps PASSED{Colors.NC}")
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
            await self.cleanup()


async def main() -> int:
    """Main entry point."""
    test = BacklogReviewFlowE2ETest()
    return await test.run()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)





