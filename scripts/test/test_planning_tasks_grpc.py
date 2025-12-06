#!/usr/bin/env python3
"""
Test Planning Service Task Endpoints via gRPC

Tests task creation, retrieval, and listing from the perspective of the UI
calling https://planning.underpassai.com
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


import grpc

# Import generated protobuf
# Add services/planning to path so we can import planning module
sys.path.insert(0, str(project_root / "services" / "planning"))
from planning.gen import planning_pb2, planning_pb2_grpc


def get_channel():
    """Get gRPC channel - tries multiple endpoints."""
    endpoints = [
        ("localhost:50054", False),  # Port-forward
        ("planning.underpassai.com:50054", False),  # Direct (if exposed)
        ("planning.underpassai.com:443", True),  # HTTPS
    ]

    for endpoint, use_ssl in endpoints:
        try:
            print(f"   Trying {endpoint} (SSL: {use_ssl})...")
            if use_ssl:
                credentials = grpc.ssl_channel_credentials()
                channel = grpc.secure_channel(endpoint, credentials)
            else:
                channel = grpc.insecure_channel(endpoint)

            # Test connection
            grpc.channel_ready_future(channel).result(timeout=5)
            print(f"   ✅ Connected to {endpoint}")
            return channel
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            if 'channel' in locals():
                channel.close()
            continue

    return None


def test_create_task_with_story_only(story_id: str = None):
    """Test creating a task with only story_id (no plan_id)."""
    print("\n" + "="*70)
    print("🧪 Test 1: Create Task with Story Only (no plan_id)")
    print("="*70)

    print("\n📡 Connecting to Planning Service...")
    channel = get_channel()

    if not channel:
        print("   ❌ Could not connect to any endpoint")
        print("   💡 Try: kubectl port-forward -n swe-ai-fleet svc/planning 50054:50054")
        return False, None

    stub = planning_pb2_grpc.PlanningServiceStub(channel)

    # Use provided story_id or default
    if not story_id:
        story_id = "STORY-TEST-001"

    request = planning_pb2.CreateTaskRequest(
        story_id=story_id,
        # plan_id is optional - not provided
        title="Test Task - Story Only",
        description="This task is created directly from a story without a plan",
        type="development",
        estimated_hours=4,
        priority=1,
    )

    print("\n📝 Creating task:")
    print(f"   Story ID: {story_id}")
    print("   Plan ID: <not provided>")
    print(f"   Title: {request.title}")

    try:
        response = stub.CreateTask(request, timeout=30)

        if response.success:
            print("\n   ✅ Task created successfully!")
            print(f"   Task ID: {response.task.task_id}")
            print(f"   Story ID: {response.task.story_id}")
            print(f"   Plan ID: {response.task.plan_id or '<none>'}")
            print(f"   Title: {response.task.title}")
            print(f"   Status: {response.task.status}")
            print(f"   Type: {response.task.type}")
            return True, response.task.task_id
        else:
            print(f"\n   ❌ Task creation failed: {response.message}")
            return False, None

    except grpc.RpcError as e:
        print(f"\n   ❌ gRPC error: {e.code()} - {e.details()}")
        return False, None
    except Exception as e:
        print(f"\n   ❌ Unexpected error: {e}")
        return False, None
    finally:
        channel.close()


def test_create_task_with_plan():
    """Test creating a task with both story_id and plan_id."""
    print("\n" + "="*70)
    print("🧪 Test 2: Create Task with Story and Plan")
    print("="*70)

    print("\n📡 Connecting to Planning Service...")
    channel = get_channel()

    if not channel:
        print("   ❌ Could not connect to any endpoint")
        return False, None

    stub = planning_pb2_grpc.PlanningServiceStub(channel)

    request = planning_pb2.CreateTaskRequest(
        story_id="STORY-TEST-001",
        plan_id="PLAN-TEST-001",  # With plan_id
        title="Test Task - With Plan",
        description="This task is created from a plan",
        type="development",
        estimated_hours=8,
        priority=2,
    )

    print("\n📝 Creating task:")
    print(f"   Story ID: {request.story_id}")
    print(f"   Plan ID: {request.plan_id}")
    print(f"   Title: {request.title}")

    try:
        response = stub.CreateTask(request, timeout=30)

        if response.success:
            print("\n   ✅ Task created successfully!")
            print(f"   Task ID: {response.task.task_id}")
            print(f"   Story ID: {response.task.story_id}")
            print(f"   Plan ID: {response.task.plan_id}")
            return True, response.task.task_id
        else:
            print(f"\n   ❌ Task creation failed: {response.message}")
            return False, None

    except grpc.RpcError as e:
        print(f"\n   ❌ gRPC error: {e.code()} - {e.details()}")
        return False, None
    except Exception as e:
        print(f"\n   ❌ Unexpected error: {e}")
        return False, None
    finally:
        channel.close()


def test_get_task(task_id: str):
    """Test retrieving a task by ID."""
    print("\n" + "="*70)
    print("🧪 Test 3: Get Task by ID")
    print("="*70)

    print("\n📡 Connecting to Planning Service...")
    channel = get_channel()

    if not channel:
        print("   ❌ Could not connect to any endpoint")
        return False

    stub = planning_pb2_grpc.PlanningServiceStub(channel)

    request = planning_pb2.GetTaskRequest(task_id=task_id)

    print(f"\n📖 Retrieving task: {task_id}")

    try:
        response = stub.GetTask(request, timeout=30)

        if response.success:
            print("\n   ✅ Task retrieved successfully!")
            print(f"   Task ID: {response.task.task_id}")
            print(f"   Story ID: {response.task.story_id}")
            print(f"   Plan ID: {response.task.plan_id or '<none>'}")
            print(f"   Title: {response.task.title}")
            print(f"   Description: {response.task.description}")
            print(f"   Status: {response.task.status}")
            print(f"   Type: {response.task.type}")
            return True
        else:
            print(f"\n   ❌ Task retrieval failed: {response.message}")
            return False

    except grpc.RpcError as e:
        print(f"\n   ❌ gRPC error: {e.code()} - {e.details()}")
        return False
    except Exception as e:
        print(f"\n   ❌ Unexpected error: {e}")
        return False
    finally:
        channel.close()


def test_list_tasks(story_id: str = None):
    """Test listing tasks, optionally filtered by story_id."""
    print("\n" + "="*70)
    print("🧪 Test 4: List Tasks" + (f" (filtered by story: {story_id})" if story_id else ""))
    print("="*70)

    print("\n📡 Connecting to Planning Service...")
    channel = get_channel()

    if not channel:
        print("   ❌ Could not connect to any endpoint")
        return False

    stub = planning_pb2_grpc.PlanningServiceStub(channel)

    request = planning_pb2.ListTasksRequest(
        story_id=story_id if story_id else None,
        limit=10,
        offset=0,
    )

    print("\n📋 Listing tasks...")
    if story_id:
        print(f"   Filter: story_id = {story_id}")

    try:
        response = stub.ListTasks(request, timeout=30)

        if response.success:
            print("\n   ✅ Tasks retrieved successfully!")
            print(f"   Total count: {response.total_count}")
            print(f"   Tasks returned: {len(response.tasks)}")

            for i, task in enumerate(response.tasks, 1):
                print(f"\n   Task {i}:")
                print(f"      ID: {task.task_id}")
                print(f"      Story: {task.story_id}")
                print(f"      Plan: {task.plan_id or '<none>'}")
                print(f"      Title: {task.title}")
                print(f"      Status: {task.status}")
            return True
        else:
            print(f"\n   ❌ Task listing failed: {response.message}")
            return False

    except grpc.RpcError as e:
        print(f"\n   ❌ gRPC error: {e.code()} - {e.details()}")
        return False
    except Exception as e:
        print(f"\n   ❌ Unexpected error: {e}")
        return False
    finally:
        channel.close()


def test_list_stories():
    """Helper: List stories to get a real story_id."""
    print("\n📋 Getting available stories...")
    channel = get_channel()
    if not channel:
        return None

    stub = planning_pb2_grpc.PlanningServiceStub(channel)
    request = planning_pb2.ListStoriesRequest(limit=5, offset=0)

    try:
        response = stub.ListStories(request, timeout=30)
        if response.success and response.stories:
            story_id = response.stories[0].story_id
            print(f"   ✅ Found story: {story_id}")
            channel.close()
            return story_id
        else:
            print("   ⚠️  No stories found")
            channel.close()
            return None
    except Exception as e:
        print(f"   ❌ Error listing stories: {e}")
        channel.close()
        return None


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("🚀 Planning Service Task Endpoints Test")
    print("="*70)
    print("\nTesting endpoints via: https://planning.underpassai.com")
    print("💡 Using port-forwarding: kubectl port-forward -n swe-ai-fleet svc/planning 50054:50054")

    # Get a real story_id first
    story_id = test_list_stories()
    if not story_id:
        print("\n⚠️  No stories found. Please create a story first or use an existing story_id.")
        print("   You can modify the script to use a specific story_id.")
        story_id = "STORY-TEST-001"  # Fallback

    results = []

    # Test 1: Create task with story only (use real story_id)
    success, task_id = test_create_task_with_story_only(story_id)
    results.append(("Create Task (Story Only)", success))

    if success and task_id:
        # Test 3: Get the created task
        results.append(("Get Task", test_get_task(task_id)))

        # Test 4: List tasks filtered by story
        results.append(("List Tasks (by story)", test_list_tasks(story_id)))

    # Test 2: Create task with plan (optional, may fail if plan doesn't exist)
    # success2, task_id2 = test_create_task_with_plan()
    # results.append(("Create Task (With Plan)", success2))

    # Test 4: List all tasks
    results.append(("List All Tasks", test_list_tasks()))

    # Summary
    print("\n" + "="*70)
    print("📊 Test Summary")
    print("="*70)

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status}: {test_name}")

    total = len(results)
    passed = sum(1 for _, success in results if success)
    print(f"\n   Total: {total}, Passed: {passed}, Failed: {total - passed}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())

