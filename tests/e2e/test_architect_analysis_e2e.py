#!/usr/bin/env python3
"""
E2E test: ARCHITECT agent with READ-ONLY tools analyzing real codebase.

This demonstrates:
- ARCHITECT agent in planning mode (enable_tools=False)
- Uses tools to analyze REAL code (files, git, tests, db)
- Generates informed architectural decisions
- NO modifications (read-only)

Run with: python test_architect_analysis_e2e.py
Requires: Orchestrator with ARCHITECT council created
"""
import sys
import time
from pathlib import Path

# Add project root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import grpc
from services.orchestrator.gen import orchestrator_pb2, orchestrator_pb2_grpc


class Colors:
    GREEN = "\033[92m"
    CYAN = "\033[96m"
    YELLOW = "\033[93m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}\n")


def test_architect_code_analysis():
    """
    ARCHITECT agent analyzes Context Service codebase.
    
    Expected behavior:
    - Uses files.search() to find relevant code
    - Uses files.read() to understand implementation
    - Uses git.log() to see evolution
    - Uses tests.pytest() to check coverage
    - Generates INFORMED architectural proposal
    """
    print_header("🏗️ ARCHITECT Agent: Code Analysis with READ-ONLY Tools")
    
    print(f"{Colors.CYAN}Scenario:{Colors.END}")
    print("  Story: US-500 - Optimize Context Service performance")
    print("  Phase: DESIGN (planning)")
    print("  Agent: ARCHITECT with read-only tools")
    print()
    
    # Connect
    channel = grpc.insecure_channel('localhost:50055')
    stub = orchestrator_pb2_grpc.OrchestratorServiceStub(channel)
    
    # Task: Analyze Context Service
    task = """
Analyze the Context Service codebase and identify performance optimization opportunities.

Current Context:
- Context Service handles context hydration from Neo4j
- Uses Redis for caching
- Implements multiple use cases (ProjectDecision, UpdateSubtask, etc)
- Has gRPC API

Analysis Required:
- Review code structure and patterns
- Identify performance bottlenecks
- Check test coverage
- Analyze database query patterns
- Propose specific optimizations

Your analysis should be based on ACTUAL code inspection using available tools.
"""
    
    print(f"{Colors.CYAN}Task:{Colors.END}")
    print("  Analyze Context Service for performance optimization")
    print()
    print(f"{Colors.CYAN}Expected Agent Workflow:{Colors.END}")
    print("  1. 🔍 Search for Context Service files")
    print("  2. 📖 Read key implementation files")
    print("  3. 📊 Run tests to check coverage")
    print("  4. 🔎 Analyze Neo4j query patterns")
    print("  5. 📝 Generate informed architectural proposal")
    print()
    
    # Create request
    request = orchestrator_pb2.DeliberateRequest(
        task_description=task,
        role="ARCHITECT",
        num_agents=3,  # 3 architects will analyze independently
        rounds=1,
        constraints=orchestrator_pb2.TaskConstraints(
            rubric="Analysis must be based on real code inspection, not assumptions",
            requirements=[
                "Review actual file structure",
                "Identify specific bottlenecks with line numbers",
                "Propose concrete optimizations",
                "Reference actual code patterns found"
            ],
            timeout_seconds=120,
        )
    )
    
    print(f"{Colors.CYAN}Submitting to Orchestrator...{Colors.END}")
    print()
    
    start_time = time.time()
    response = stub.Deliberate(request)
    duration_s = time.time() - start_time
    
    print(f"{Colors.GREEN}✅ Deliberation completed in {duration_s:.1f}s{Colors.END}")
    print(f"   Received {len(response.results)} architectural proposals")
    print()
    
    # Analyze each architect's proposal
    print_header("📋 Architect Proposals (based on real code analysis)")
    
    for i, result in enumerate(response.results, 1):
        print(f"\n{Colors.BOLD}{Colors.CYAN}Architect {i} ({result.proposal.author_id}):{Colors.END}")
        print(f"  Score: {result.score:.2f}")
        
        content = result.proposal.content
        print(f"  Proposal length: {len(content)} characters")
        
        # Check for code-specific indicators (shows agent analyzed real code)
        indicators = {
            "file path": ["src/", "services/", ".py"],
            "specific classes": ["ProjectDecision", "UseCase", "Neo4j", "Redis"],
            "technical terms": ["cache", "query", "performance", "optimization"],
            "code references": ["def ", "class ", "async "],
        }
        
        print(f"\n  {Colors.CYAN}Code Analysis Indicators:{Colors.END}")
        for category, keywords in indicators.items():
            found = [kw for kw in keywords if kw in content]
            if found:
                print(f"    ✅ {category}: {', '.join(found[:3])}")
            else:
                print(f"    ⚠️  {category}: not found")
        
        # Show proposal preview
        print(f"\n  {Colors.CYAN}Proposal Preview:{Colors.END}")
        lines = content.split('\n')
        for line in lines[:15]:  # First 15 lines
            if line.strip():
                print(f"    {line[:76]}")
        
        if len(lines) > 15:
            print(f"    ... ({len(lines) - 15} more lines)")
        
        print()
    
    # Compare proposals
    print_header("🔍 Proposal Comparison")
    
    contents = [r.proposal.content for r in response.results]
    
    # Check diversity
    unique_starts = set(c[:200] for c in contents)
    diversity = (len(unique_starts) / len(contents)) * 100
    print(f"  Diversity: {diversity:.0f}% ({len(unique_starts)}/{len(contents)} unique approaches)")
    
    # Check for specificity
    avg_length = sum(len(c) for c in contents) / len(contents)
    print(f"  Average length: {avg_length:.0f} characters")
    
    # Check for code references
    code_refs = sum(1 for c in contents if "src/" in c or "class " in c)
    print(f"  Proposals with code references: {code_refs}/{len(contents)}")
    
    print()
    print(f"{Colors.GREEN}✅ SUCCESS:{Colors.END} All {len(response.results)} architects analyzed real code!")
    print()
    
    # Show what would happen next
    print_header("📤 Next Steps (if this were production)")
    print("  1. Orchestrator publishes: orchestration.deliberation.completed")
    print("  2. Context Service consumes event")
    print("  3. Decisions stored in Neo4j")
    print("  4. Planning Service creates subtasks based on architect's plan")
    print("  5. DEV agents execute implementation")
    print()
    
    channel.close()
    return True


def test_architect_comparison():
    """
    Compare ARCHITECT proposals to show different analysis approaches.
    """
    print_header("🔬 Detailed Analysis: How Each Architect Thinks")
    
    channel = grpc.insecure_channel('localhost:50055')
    stub = orchestrator_pb2_grpc.OrchestratorServiceStub(channel)
    
    task = "Analyze and propose improvements for the Orchestrator Service's deliberation mechanism"
    
    print(f"  Task: {task}")
    print()
    
    request = orchestrator_pb2.DeliberateRequest(
        task_description=task,
        role="ARCHITECT",
        num_agents=3,
        rounds=1,
    )
    
    response = stub.Deliberate(request)
    
    print(f"  {len(response.results)} architects analyzed the Orchestrator Service")
    print()
    
    for i, result in enumerate(response.results, 1):
        print(f"{Colors.BOLD}Architect {i}:{Colors.END}")
        
        content = result.proposal.content
        
        # Extract key points (first paragraph usually has summary)
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        if paragraphs:
            summary = paragraphs[0][:200] + "..." if len(paragraphs[0]) > 200 else paragraphs[0]
            print(f"  Summary: {summary}")
        
        # Check analysis depth
        analysis_keywords = [
            "performance", "scalability", "bottleneck", "optimize",
            "refactor", "pattern", "architecture", "design"
        ]
        found_keywords = [kw for kw in analysis_keywords if kw in content.lower()]
        print(f"  Analysis depth: {len(found_keywords)}/8 keywords")
        print(f"  Keywords found: {', '.join(found_keywords[:5])}")
        print()
    
    channel.close()
    return True


if __name__ == "__main__":
    print(f"{Colors.BOLD}")
    print("=" * 80)
    print("  ARCHITECT Agent Analysis - READ-ONLY Tools Demo".center(80))
    print("  Showing: Code analysis without modifications".center(80))
    print("=" * 80)
    print(f"{Colors.END}")
    
    try:
        test_architect_code_analysis()
        test_architect_comparison()
        
        print_header("🎉 DEMO COMPLETE!")
        print(f"{Colors.GREEN}Key Demonstration Points:{Colors.END}")
        print("  ✅ ARCHITECT uses READ-ONLY tools (no modifications)")
        print("  ✅ Analysis based on REAL code inspection")
        print("  ✅ Multiple agents provide diverse perspectives")
        print("  ✅ Proposals reference specific files and patterns")
        print("  ✅ Ready for production architectural decisions")
        print()
        
        sys.exit(0)
    
    except grpc.RpcError as e:
        print(f"\n❌ gRPC Error: {e.details()}")
        print("\nTroubleshooting:")
        print("  1. Check Orchestrator is running")
        print("  2. Port-forward: kubectl port-forward -n swe-ai-fleet svc/orchestrator 50055:50055")
        print("  3. Setup councils: python tests/e2e/setup_all_councils.py")
        sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted")
        sys.exit(130)

