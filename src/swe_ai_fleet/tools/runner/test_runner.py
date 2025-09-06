#!/usr/bin/env python3
"""
Test script for SWE AI Fleet Runner Tool

This script demonstrates the TaskSpec/TaskResult contract implementation
and tests the runner tool functionality.
"""

import asyncio
import json
import tempfile
from pathlib import Path
from runner_tool import RunnerTool, TaskSpec, TaskStatus


async def test_basic_task():
    """Test basic task execution"""
    print("🧪 Testing basic task execution...")
    
    # Create temporary workspace
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir) / "workspace"
        workspace_path.mkdir()
        
        # Create a simple test script
        test_script = workspace_path / "test.py"
        test_script.write_text("""
import sys
print("Hello from Python!")
print("Python version:", sys.version)
print("Working directory:", sys.path[0])
""")
        
        # Create TaskSpec
        spec = TaskSpec(
            image="localhost/swe-ai-fleet-runner:latest",
            cmd=["/bin/bash", "-lc", "agent-task"],
            env={
                "TASK": "unit",
                "LANG": "python",
                "TEST_CMD": f"python3 {test_script.name}"
            },
            mounts=[
                {"type": "bind", "source": str(workspace_path), "target": "/workspace"}
            ],
            timeouts={"overallSec": 60},
            resources={"cpu": "1", "memory": "1Gi"},
            artifacts={"paths": ["/workspace/test-reports"]},
            context={
                "case_id": "test-case-001",
                "task_id": "test-python-unit",
                "role": "developer"
            }
        )
        
        # Run task
        runner = RunnerTool()
        task_id = await runner.run_task(spec)
        print(f"✅ Started task: {task_id}")
        
        # Stream logs
        print("📋 Streaming logs...")
        logs = await runner.stream_logs(task_id)
        for log in logs:
            print(f"   {log}")
        
        # Wait for result
        print("⏳ Waiting for result...")
        result = await runner.await_result(task_id, timeout_sec=30)
        
        print(f"📊 Task Result:")
        print(f"   Status: {result.status.value}")
        print(f"   Exit Code: {result.exitCode}")
        print(f"   Duration: {result.metadata.get('duration', 'unknown')}s")
        print(f"   Case ID: {result.metadata.get('case_id')}")
        
        return result.status == TaskStatus.PASSED


async def test_go_task():
    """Test Go task execution"""
    print("\n🧪 Testing Go task execution...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir) / "workspace"
        workspace_path.mkdir()
        
        # Create a simple Go test
        go_file = workspace_path / "main.go"
        go_file.write_text("""
package main

import "fmt"

func main() {
    fmt.Println("Hello from Go!")
    fmt.Println("This is a test program")
}
""")
        
        spec = TaskSpec(
            image="localhost/swe-ai-fleet-runner:latest",
            cmd=["/bin/bash", "-lc", "agent-task"],
            env={
                "TASK": "unit",
                "LANG": "go",
                "GO_TEST_CMD": f"go run {go_file.name}"
            },
            mounts=[
                {"type": "bind", "source": str(workspace_path), "target": "/workspace"}
            ],
            timeouts={"overallSec": 60},
            resources={"cpu": "1", "memory": "1Gi"},
            artifacts={"paths": ["/workspace/test-reports"]}
        )
        
        runner = RunnerTool()
        task_id = await runner.run_task(spec)
        print(f"✅ Started Go task: {task_id}")
        
        result = await runner.await_result(task_id, timeout_sec=30)
        print(f"📊 Go Task Result: {result.status.value}")
        
        return result.status == TaskStatus.PASSED


async def test_health_check():
    """Test health check functionality"""
    print("\n🧪 Testing health check...")
    
    runner = RunnerTool()
    health_info = await runner.health()
    
    print(f"📊 Health Status:")
    print(f"   Status: {health_info['status']}")
    print(f"   Runtime: {health_info['runtime']}")
    print(f"   Registry: {health_info['registry']}")
    print(f"   Active Tasks: {health_info['active_tasks']}")
    
    return health_info['status'] == 'healthy'


async def test_task_cancellation():
    """Test task cancellation"""
    print("\n🧪 Testing task cancellation...")
    
    spec = TaskSpec(
        image="localhost/swe-ai-fleet-runner:latest",
        cmd=["/bin/bash", "-lc", "sleep 10"],
        env={"TASK": "unit", "LANG": "python"},
        mounts=[],
        timeouts={"overallSec": 5},
        resources={"cpu": "1", "memory": "1Gi"},
        artifacts={"paths": []}
    )
    
    runner = RunnerTool()
    task_id = await runner.run_task(spec)
    print(f"✅ Started long-running task: {task_id}")
    
    # Cancel after a short delay
    await asyncio.sleep(0.5)
    cancelled = await runner.cancel(task_id)
    print(f"🛑 Cancelled task: {cancelled}")
    
    result = await runner.await_result(task_id, timeout_sec=5)
    print(f"📊 Cancelled Task Result: {result.status.value}")
    
    return result.status == TaskStatus.ERROR


async def main():
    """Run all tests"""
    print("🚀 Starting SWE AI Fleet Runner Tool Tests\n")
    
    tests = [
        ("Basic Python Task", test_basic_task),
        ("Go Task", test_go_task),
        ("Health Check", test_health_check),
        ("Task Cancellation", test_task_cancellation),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
            print(f"{'✅' if result else '❌'} {test_name}: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
            results.append((test_name, False))
    
    print(f"\n📊 Test Summary:")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"   Passed: {passed}/{total}")
    print(f"   Success Rate: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed")


if __name__ == "__main__":
    asyncio.run(main())

