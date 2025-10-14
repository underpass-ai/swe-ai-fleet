#!/usr/bin/env python3
"""
Complete End-to-End System Demonstration

This script demonstrates a full user story refinement iteration with:
- Real vLLM agents (ARCHITECT, DEV, QA)
- Context Service storing decisions in Neo4j
- ValKey caching
- Complete logging and observability

Story: US-DEMO-001 - Implement Redis Caching for Context Service
"""
import sys
import time
import json
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import grpc
from services.orchestrator.gen import orchestrator_pb2, orchestrator_pb2_grpc
from services.context.gen import context_pb2, context_pb2_grpc


class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")


def print_step(step_num, title):
    print(f"\n{Colors.BOLD}{Colors.GREEN}{'▶'*3} STEP {step_num}: {title}{Colors.END}")
    print(f"{Colors.BLUE}{'-'*80}{Colors.END}")


def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_info(text):
    print(f"{Colors.CYAN}ℹ️  {text}{Colors.END}")


def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")


def main():
    print_header("FULL SYSTEM E2E DEMONSTRATION")
    print_info("Story: US-DEMO-001 - Implement Redis Caching for Context Service")
    print_info("Participants: ARCHITECT (design) → DEV (implement) → QA (validate)")
    print_info("All agents using REAL vLLM (Qwen/Qwen3-0.6B)")
    print()

    # Connect to services
    orchestrator_channel = grpc.insecure_channel('localhost:50055')
    orchestrator_stub = orchestrator_pb2_grpc.OrchestratorServiceStub(orchestrator_channel)
    
    context_channel = grpc.insecure_channel('localhost:50054')
    context_stub = context_pb2_grpc.ContextServiceStub(context_channel)

    story_id = "US-DEMO-001"
    
    # ============================================================================
    # STEP 1: Create Project Case in Context Service
    # ============================================================================
    print_step(1, "Initialize Story in Context Service")
    
    try:
        init_response = context_stub.InitializeProjectContext(context_pb2.InitializeProjectContextRequest(
            story_id=story_id,
            title="Implement Redis Caching for Context Service",
            description="Add Redis caching layer to improve Context Service read performance. Current Neo4j queries are slow.",
            initial_phase="DESIGN"
        ))
        print_success(f"Story created: {story_id}")
        print_info(f"  Initial phase: DESIGN")
        print_info(f"  Context ID: {init_response.context_id if hasattr(init_response, 'context_id') else 'N/A'}")
    except Exception as e:
        print_warning(f"Story may already exist: {e}")
    
    time.sleep(2)
    
    # ============================================================================
    # STEP 2: ARCHITECT Council - Design Phase
    # ============================================================================
    print_step(2, "ARCHITECT Council - Design & Analysis")
    
    print_info("Task: Analyze and propose Redis caching architecture")
    print_info("Agents: 3 ARCHITECT agents with vLLM")
    print()
    
    start_time = time.time()
    architect_response = orchestrator_stub.Deliberate(orchestrator_pb2.DeliberateRequest(
        task_description=f"Story {story_id}: Design a Redis caching architecture for the Context Service. Analyze current Neo4j bottlenecks and propose optimal caching strategy.",
        role="ARCHITECT",
        num_agents=3,
        rounds=1,
        constraints=orchestrator_pb2.TaskConstraints(
            rubric="Design must be scalable, maintainable, and production-ready.",
            requirements=["Redis cluster design", "Cache key strategy", "Consistency model"]
        )
    ))
    architect_duration = time.time() - start_time
    
    print_success(f"Deliberation completed in {architect_duration:.1f}s")
    print_info(f"Winner: {architect_response.winner_id}")
    print_info(f"Proposals: {len(architect_response.results)}")
    print()
    
    for i, result in enumerate(architect_response.results, 1):
        print(f"  {Colors.BOLD}Architect {i}{Colors.END} ({result.proposal.author_id}):")
        print(f"    Score: {result.score:.2f}")
        print(f"    Length: {len(result.proposal.content)} chars")
        preview = result.proposal.content[:150].replace('\n', ' ')
        print(f"    Preview: {preview}...")
    
    # Store architect decision in Context Service
    print()
    print_info("Storing ARCHITECT decision in Context Service...")
    
    try:
        decision_response = context_stub.AddProjectDecision(context_pb2.AddProjectDecisionRequest(
            story_id=story_id,
            decision_type="ARCHITECTURE",
            title="Redis Caching Architecture",
            rationale=f"Design proposed by {architect_response.winner_id} after {architect_duration:.1f}s deliberation",
            alternatives_considered=f"{len(architect_response.results)} alternatives from ARCHITECT council",
            metadata={
                "deliberation_duration": str(architect_duration),
                "num_proposals": str(len(architect_response.results)),
                "winner": architect_response.winner_id
            }
        ))
        print_success(f"Decision stored: {decision_response.decision_id if hasattr(decision_response, 'decision_id') else 'OK'}")
    except Exception as e:
        print_warning(f"Error storing decision: {e}")
    
    time.sleep(2)
    
    # ============================================================================
    # STEP 3: Transition to BUILD Phase
    # ============================================================================
    print_step(3, "Transition Story to BUILD Phase")
    
    try:
        transition_response = context_stub.TransitionPhase(context_pb2.TransitionPhaseRequest(
            story_id=story_id,
            from_phase="DESIGN",
            to_phase="BUILD",
            rationale="Architecture approved, ready for implementation"
        ))
        print_success(f"Phase transition: DESIGN → BUILD")
    except Exception as e:
        print_warning(f"Phase transition: {e}")
    
    time.sleep(2)
    
    # ============================================================================
    # STEP 4: DEV Council - Implementation Phase
    # ============================================================================
    print_step(4, "DEV Council - Implementation Planning")
    
    print_info("Task: Plan Redis caching implementation")
    print_info("Agents: 3 DEV agents with vLLM")
    print()
    
    start_time = time.time()
    dev_response = orchestrator_stub.Deliberate(orchestrator_pb2.DeliberateRequest(
        task_description=f"Story {story_id}: Implement the Redis caching layer based on approved architecture. Create implementation plan with code structure, tests, and deployment.",
        role="DEV",
        num_agents=3,
        rounds=1,
        constraints=orchestrator_pb2.TaskConstraints(
            rubric="Implementation must follow architecture, be well-tested, and production-ready.",
            requirements=["Python implementation", "Unit tests", "Integration tests", "Documentation"]
        )
    ))
    dev_duration = time.time() - start_time
    
    print_success(f"Deliberation completed in {dev_duration:.1f}s")
    print_info(f"Winner: {dev_response.winner_id}")
    print_info(f"Proposals: {len(dev_response.results)}")
    print()
    
    for i, result in enumerate(dev_response.results, 1):
        print(f"  {Colors.BOLD}DEV {i}{Colors.END} ({result.proposal.author_id}):")
        print(f"    Score: {result.score:.2f}")
        print(f"    Length: {len(result.proposal.content)} chars")
        preview = result.proposal.content[:150].replace('\n', ' ')
        print(f"    Preview: {preview}...")
    
    # Store dev decision
    print()
    print_info("Storing DEV implementation plan in Context Service...")
    
    try:
        decision_response = context_stub.AddProjectDecision(context_pb2.AddProjectDecisionRequest(
            story_id=story_id,
            decision_type="IMPLEMENTATION",
            title="Redis Caching Implementation Plan",
            rationale=f"Implementation plan by {dev_response.winner_id} after {dev_duration:.1f}s deliberation",
            alternatives_considered=f"{len(dev_response.results)} alternatives from DEV council",
            metadata={
                "deliberation_duration": str(dev_duration),
                "num_proposals": str(len(dev_response.results)),
                "winner": dev_response.winner_id
            }
        ))
        print_success(f"Decision stored: {decision_response.decision_id if hasattr(decision_response, 'decision_id') else 'OK'}")
    except Exception as e:
        print_warning(f"Error storing decision: {e}")
    
    time.sleep(2)
    
    # ============================================================================
    # STEP 5: Transition to VALIDATE Phase
    # ============================================================================
    print_step(5, "Transition Story to VALIDATE Phase")
    
    try:
        transition_response = context_stub.TransitionPhase(context_pb2.TransitionPhaseRequest(
            story_id=story_id,
            from_phase="BUILD",
            to_phase="VALIDATE",
            rationale="Implementation complete, ready for QA validation"
        ))
        print_success(f"Phase transition: BUILD → VALIDATE")
    except Exception as e:
        print_warning(f"Phase transition: {e}")
    
    time.sleep(2)
    
    # ============================================================================
    # STEP 6: QA Council - Validation Phase
    # ============================================================================
    print_step(6, "QA Council - Testing & Validation")
    
    print_info("Task: Design testing strategy for Redis caching")
    print_info("Agents: 3 QA agents with vLLM")
    print()
    
    start_time = time.time()
    qa_response = orchestrator_stub.Deliberate(orchestrator_pb2.DeliberateRequest(
        task_description=f"Story {story_id}: Design comprehensive testing strategy for the Redis caching implementation. Include unit, integration, and E2E tests.",
        role="QA",
        num_agents=3,
        rounds=1,
        constraints=orchestrator_pb2.TaskConstraints(
            rubric="Testing must be thorough, automated, and cover edge cases.",
            requirements=["Unit tests", "Integration tests", "E2E tests", "Performance benchmarks"]
        )
    ))
    qa_duration = time.time() - start_time
    
    print_success(f"Deliberation completed in {qa_duration:.1f}s")
    print_info(f"Winner: {qa_response.winner_id}")
    print_info(f"Proposals: {len(qa_response.results)}")
    print()
    
    for i, result in enumerate(qa_response.results, 1):
        print(f"  {Colors.BOLD}QA {i}{Colors.END} ({result.proposal.author_id}):")
        print(f"    Score: {result.score:.2f}")
        print(f"    Length: {len(result.proposal.content)} chars")
        preview = result.proposal.content[:150].replace('\n', ' ')
        print(f"    Preview: {preview}...")
    
    # Store QA decision
    print()
    print_info("Storing QA testing strategy in Context Service...")
    
    try:
        decision_response = context_stub.AddProjectDecision(context_pb2.AddProjectDecisionRequest(
            story_id=story_id,
            decision_type="TESTING",
            title="Redis Caching Testing Strategy",
            rationale=f"Testing strategy by {qa_response.winner_id} after {qa_duration:.1f}s deliberation",
            alternatives_considered=f"{len(qa_response.results)} alternatives from QA council",
            metadata={
                "deliberation_duration": str(qa_duration),
                "num_proposals": str(len(qa_response.results)),
                "winner": qa_response.winner_id
            }
        ))
        print_success(f"Decision stored: {decision_response.decision_id if hasattr(decision_response, 'decision_id') else 'OK'}")
    except Exception as e:
        print_warning(f"Error storing decision: {e}")
    
    time.sleep(2)
    
    # ============================================================================
    # STEP 7: Summary
    # ============================================================================
    print_step(7, "Story Completion Summary")
    
    total_duration = architect_duration + dev_duration + qa_duration
    
    print()
    print(f"{Colors.BOLD}Story: {story_id}{Colors.END}")
    print(f"  Title: Implement Redis Caching for Context Service")
    print()
    print(f"{Colors.BOLD}Phases Completed:{Colors.END}")
    print(f"  1. DESIGN    → {architect_duration:.1f}s (ARCHITECT × 3)")
    print(f"  2. BUILD     → {dev_duration:.1f}s (DEV × 3)")
    print(f"  3. VALIDATE  → {qa_duration:.1f}s (QA × 3)")
    print(f"  {Colors.BOLD}Total: {total_duration:.1f}s{Colors.END}")
    print()
    print(f"{Colors.BOLD}Agents Participated:{Colors.END}")
    print(f"  • {architect_response.results[0].proposal.author_id}")
    print(f"  • {architect_response.results[1].proposal.author_id}")
    print(f"  • {architect_response.results[2].proposal.author_id}")
    print(f"  • {dev_response.results[0].proposal.author_id}")
    print(f"  • {dev_response.results[1].proposal.author_id}")
    print(f"  • {dev_response.results[2].proposal.author_id}")
    print(f"  • {qa_response.results[0].proposal.author_id}")
    print(f"  • {qa_response.results[1].proposal.author_id}")
    print(f"  • {qa_response.results[2].proposal.author_id}")
    print(f"  {Colors.BOLD}Total: 9 agents (all using vLLM real){Colors.END}")
    print()
    print(f"{Colors.BOLD}Decisions Stored:{Colors.END}")
    print(f"  1. Architecture Design")
    print(f"  2. Implementation Plan")
    print(f"  3. Testing Strategy")
    print()
    print(f"{Colors.BOLD}Data Stored:{Colors.END}")
    print(f"  • Neo4j: Story, Phases, Decisions, Relationships")
    print(f"  • ValKey: Context cache")
    print()
    print_success("✅ FULL E2E DEMONSTRATION COMPLETE!")
    print()
    print_info("Next: Query Neo4j and ValKey to see stored data...")
    
    orchestrator_channel.close()
    context_channel.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}❌ Error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

