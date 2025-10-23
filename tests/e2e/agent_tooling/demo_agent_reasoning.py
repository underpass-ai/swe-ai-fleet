#!/usr/bin/env python3
"""
Demo script to show agent reasoning logs in action.

This script:
1. Creates a VLLMAgent with tools
2. Executes a simple task
3. Captures and displays reasoning logs
4. Shows how the agent thinks step-by-step

Can be run locally or in K8s cluster.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from core.agents import VLLMAgent


async def main():
    """Main demo function."""
    print("🚀 Creating DEV agent with tools...")
    print("")

    # Create agent
    agent = VLLMAgent(
        agent_id="agent-demo-001",
        role="DEV",
        workspace_path=Path.cwd(),  # Current directory
        enable_tools=True,
        vllm_url=None,  # Will use pattern matching (or set to "http://vllm-server-service:8000" for vLLM)
    )

    print(f"✓ Agent initialized: {agent.agent_id}")
    print(f"✓ Role: {agent.role}")
    print(f"✓ Mode: {'Full execution' if agent.enable_tools else 'Planning only'}")
    print(f"✓ Tools available: {len(agent.tools)}")
    print(f"✓ vLLM client: {'Enabled' if agent.vllm_client else 'Disabled (using pattern matching)'}")
    print("")

    # Simulate smart context from Context Service
    smart_context = """
Story: DEMO-001 - Demonstrate agent tooling
Phase: BUILD
Role: DEV

Task: Add a simple greeting function to demonstrate tool usage

Relevant Context:
- Python 3.13 project
- src/ directory contains source code
- tests/ directory for tests

Relevant Decisions:
- Use type hints (ARCHITECT)
- Maintain test coverage (QA)
"""

    print("📋 Task: Add hello_demo() function to core/__init__.py")
    print("")
    print("💭 Agent Reasoning (watch the agent think):")
    print("=" * 80)
    print("")

    # Execute task
    result = await agent.execute_task(
        task="Add hello_demo() function to core/__init__.py that returns 'Demo successful!'",
        context=smart_context,
        constraints={
            "max_operations": 10,
            "abort_on_error": False,  # Continue even if steps fail
        },
    )

    print("")
    print("=" * 80)
    print("")
    print("📊 Results:")
    print(f"  Success: {result.success}")
    print(f"  Operations: {len(result.operations)}")
    print(f"  Artifacts: {list(result.artifacts.keys())}")
    print("")

    print("🧠 Agent Reasoning Log:")
    print("-" * 80)
    for i, thought in enumerate(result.reasoning_log, 1):
        icon = {
            "analysis": "🔍",
            "decision": "🤔",
            "action": "⚡",
            "observation": "👁️",
            "conclusion": "✅",
            "error": "❌",
        }.get(thought["type"], "💭")

        conf = f" (confidence: {thought['confidence']})" if thought.get("confidence") else ""
        print(f"{i}. {icon} [{thought['type'].upper()}] {thought['content']}{conf}")

    print("")
    print("📝 Operations Executed:")
    print("-" * 80)
    for op in result.operations:
        status = "✅" if op["success"] else "❌"
        print(f"  {status} Step {op['step']}: {op['tool']}.{op['operation']}")

    print("")
    print("🎯 Artifacts:")
    print("-" * 80)
    for key, value in result.artifacts.items():
        print(f"  {key}: {value}")

    print("")

    # Verify file was modified (if applicable)
    target_file = Path("core/__init__.py")
    if target_file.exists():
        content = target_file.read_text()
        if "hello_demo" in content or "hello_world" in content:
            print("✅ SUCCESS: Function was added!")
            print("")
            print("Added code:")
            print("-" * 80)
            for line in content.split("\n"):
                if "hello" in line.lower() or "demo" in line.lower():
                    print(f"  {line}")
        else:
            print("⚠️  Function not found in file")

    print("")
    print("🎉 Demo Complete!")
    print("")

    # Export reasoning log as JSON
    log_file = Path("/tmp/reasoning_log.json")
    log_file.write_text(json.dumps(result.reasoning_log, indent=2))
    print(f"📄 Full reasoning log saved to: {log_file}")
    print(f"   ({len(result.reasoning_log)} thoughts captured)")
    print("")

    # Export summary
    summary = {
        "agent_id": agent.agent_id,
        "role": agent.role,
        "task": "Add hello_demo() function",
        "success": result.success,
        "total_operations": len(result.operations),
        "successful_operations": sum(1 for op in result.operations if op["success"]),
        "total_thoughts": len(result.reasoning_log),
        "artifacts": result.artifacts,
        "vllm_used": agent.vllm_client is not None,
    }

    summary_file = Path("/tmp/demo_summary.json")
    summary_file.write_text(json.dumps(summary, indent=2))
    print(f"📊 Summary saved to: {summary_file}")

    return result.success


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

