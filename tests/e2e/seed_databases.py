#!/usr/bin/env python3
"""
Seed Neo4j and ValKey with demo data for E2E testing

This script creates:
- Story US-DEMO-001 in Neo4j
- Phase transitions
- Project decisions
- Cache entries in ValKey
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from neo4j import GraphDatabase
import redis
from datetime import datetime, timezone
import json


class Colors:
    GREEN = '\033[92m'
    CYAN = '\033[96m'
    YELLOW = '\033[93m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{text.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}\n")


def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_info(text):
    print(f"   {text}")


def seed_neo4j():
    """Seed Neo4j with story, phases, and decisions"""
    print_header("SEEDING NEO4J")
    
    driver = GraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("neo4j", "testpassword")
    )
    
    with driver.session() as session:
        # Clear existing data (optional)
        print_info("Clearing existing data...")
        session.run("MATCH (n) DETACH DELETE n")
        print_success("Database cleared")
        
        # Create story node
        print_info("Creating story US-DEMO-001...")
        result = session.run("""
            CREATE (s:ProjectCase {
                story_id: $story_id,
                title: $title,
                description: $description,
                current_phase: $phase,
                created_at: $created_at,
                updated_at: $updated_at
            })
            RETURN s.story_id as story_id
        """, {
            "story_id": "US-DEMO-001",
            "title": "Implement Redis Caching for Context Service",
            "description": "Add Redis caching layer to improve Context Service read performance. Current Neo4j queries are slow for complex graph traversals.",
            "phase": "VALIDATE",  # Final phase after our demo
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        })
        print_success(f"Story created: {result.single()['story_id']}")
        
        # Create phase transitions
        print_info("Creating phase transitions...")
        
        phases = [
            ("INIT", "DESIGN", "Story initialized, ready for architectural design"),
            ("DESIGN", "BUILD", "Architecture approved by ARCHITECT council after 53.0s deliberation"),
            ("BUILD", "VALIDATE", "Implementation plan approved by DEV council after 53.8s deliberation")
        ]
        
        for from_phase, to_phase, rationale in phases:
            result = session.run("""
                MATCH (s:ProjectCase {story_id: $story_id})
                CREATE (p:PhaseTransition {
                    from_phase: $from_phase,
                    to_phase: $to_phase,
                    rationale: $rationale,
                    transitioned_at: $transitioned_at
                })
                CREATE (s)-[:HAS_PHASE]->(p)
                RETURN p.from_phase as from, p.to_phase as to
            """, {
                "story_id": "US-DEMO-001",
                "from_phase": from_phase,
                "to_phase": to_phase,
                "rationale": rationale,
                "transitioned_at": datetime.now(timezone.utc).isoformat()
            })
            record = result.single()
            print_success(f"  Transition: {record['from']} → {record['to']}")
        
        # Create project decisions
        print_info("Creating project decisions...")
        
        decisions = [
            {
                "id": "DEC-ARCH-001",
                "type": "ARCHITECTURE",
                "title": "Redis Caching Architecture",
                "rationale": "Proposed 3-node Redis cluster with master-slave replication for high availability. Analysis shows Neo4j query bottlenecks in complex graph traversals.",
                "role": "ARCHITECT",
                "author": "agent-architect-001",
                "content": "Redis cluster with 3 nodes (1 master, 2 replicas). Cache key strategy: story_id:phase:role. TTL: 3600s for context, 300s for decisions.",
                "alternatives": "3 proposals considered: single Redis, cluster, hybrid Neo4j+Redis. Cluster selected for scalability."
            },
            {
                "id": "DEC-DEV-001",
                "type": "IMPLEMENTATION",
                "title": "Redis Caching Implementation Plan",
                "rationale": "Python implementation with cache decorators and testcontainers for integration testing. Follows existing Context Service patterns.",
                "role": "DEV",
                "author": "agent-dev-001",
                "content": "RedisCache class with get/set/delete methods. Cache decorator for automatic caching. Integration with Context Service query methods.",
                "alternatives": "3 proposals: decorator pattern, AOP, manual caching. Decorator selected for clarity and testability."
            },
            {
                "id": "DEC-QA-001",
                "type": "TESTING",
                "title": "Redis Caching Testing Strategy",
                "rationale": "Comprehensive testing with unit, integration, and E2E tests. Performance benchmarks for cache hit rates.",
                "role": "QA",
                "author": "agent-qa-001",
                "content": "pytest for unit/integration. testcontainers for Redis. JMeter for performance. Target: >90% cache hit rate, <100ms p95 latency.",
                "alternatives": "3 proposals: pytest-only, mixed frameworks, E2E-first. pytest+testcontainers selected for consistency."
            }
        ]
        
        for dec in decisions:
            result = session.run("""
                MATCH (s:ProjectCase {story_id: $story_id})
                CREATE (d:ProjectDecision {
                    decision_id: $id,
                    decision_type: $type,
                    title: $title,
                    rationale: $rationale,
                    made_by_role: $role,
                    made_by_agent: $author,
                    content: $content,
                    alternatives_considered: $alternatives,
                    created_at: $created_at
                })
                CREATE (s)-[:MADE_DECISION]->(d)
                RETURN d.decision_id as id, d.title as title
            """, {
                "story_id": "US-DEMO-001",
                "id": dec["id"],
                "type": dec["type"],
                "title": dec["title"],
                "rationale": dec["rationale"],
                "role": dec["role"],
                "author": dec["author"],
                "content": dec["content"],
                "alternatives": dec["alternatives"],
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            record = result.single()
            print_success(f"  Decision: {record['title']} ({record['id']})")
        
        # Verify data
        print()
        print_info("Verifying seeded data...")
        
        result = session.run("MATCH (n) RETURN labels(n) as labels, count(n) as count")
        for record in result:
            print_info(f"  {record['labels']}: {record['count']} nodes")
        
        result = session.run("MATCH ()-[r]->() RETURN type(r) as rel, count(r) as count")
        for record in result:
            print_info(f"  {record['rel']}: {record['count']} relationships")
    
    driver.close()
    print_success("Neo4j seeding complete\n")


def seed_valkey():
    """Seed ValKey with context cache entries"""
    print_header("SEEDING VALKEY")
    
    r = redis.Redis(
        host='localhost',
        port=6379,
        decode_responses=True
    )
    
    # Test connection
    r.ping()
    print_success("Connected to ValKey")
    
    # Seed context cache entries
    print_info("Creating context cache entries...")
    
    # Cache for ARCHITECT in DESIGN phase
    architect_context = {
        "story_id": "US-DEMO-001",
        "role": "ARCHITECT",
        "phase": "DESIGN",
        "content": "Story: US-DEMO-001 - Implement Redis Caching\\n\\nCurrent State:\\n- Context Service reads from Neo4j\\n- Slow queries on complex graphs\\n- Need caching layer\\n\\nRelevant Decisions: (none yet)\\n\\nTask: Design Redis caching architecture",
        "token_count": 150,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
    key = "context:US-DEMO-001:DESIGN:ARCHITECT"
    r.setex(key, 3600, json.dumps(architect_context))
    print_success(f"  {key}")
    
    # Cache for DEV in BUILD phase
    dev_context = {
        "story_id": "US-DEMO-001",
        "role": "DEV",
        "phase": "BUILD",
        "content": "Story: US-DEMO-001 - Implement Redis Caching\\n\\nArchitecture Decision (DEC-ARCH-001):\\n- 3-node Redis cluster\\n- Master-slave replication\\n- Cache key: story_id:phase:role\\n- TTL: 3600s\\n\\nTask: Implement caching layer following approved architecture",
        "token_count": 200,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
    key = "context:US-DEMO-001:BUILD:DEV"
    r.setex(key, 3600, json.dumps(dev_context))
    print_success(f"  {key}")
    
    # Cache for QA in VALIDATE phase
    qa_context = {
        "story_id": "US-DEMO-001",
        "role": "QA",
        "phase": "VALIDATE",
        "content": "Story: US-DEMO-001 - Implement Redis Caching\\n\\nImplementation Decision (DEC-DEV-001):\\n- Python RedisCache class\\n- Cache decorators\\n- testcontainers for integration tests\\n\\nTask: Validate implementation with comprehensive testing",
        "token_count": 180,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
    key = "context:US-DEMO-001:VALIDATE:QA"
    r.setex(key, 3600, json.dumps(qa_context))
    print_success(f"  {key}")
    
    # Add some metadata keys
    metadata_keys = {
        "story:US-DEMO-001:metadata": json.dumps({
            "story_id": "US-DEMO-001",
            "title": "Implement Redis Caching",
            "phases_completed": ["DESIGN", "BUILD"],
            "current_phase": "VALIDATE",
            "agents_participated": 9,
            "total_duration_s": 162.3
        }),
        "agent:architect-001:last_active": datetime.now(timezone.utc).isoformat(),
        "agent:dev-001:last_active": datetime.now(timezone.utc).isoformat(),
        "agent:qa-001:last_active": datetime.now(timezone.utc).isoformat(),
    }
    
    for key, value in metadata_keys.items():
        r.setex(key, 7200, value)
        print_success(f"  {key}")
    
    # Verify
    print()
    print_info("Verifying seeded data...")
    dbsize = r.dbsize()
    print_info(f"  Total keys: {dbsize}")
    
    # Show keys by pattern
    patterns = ["context:*", "story:*", "agent:*"]
    for pattern in patterns:
        keys = r.keys(pattern)
        print_info(f"  {pattern} → {len(keys)} keys")
    
    print_success("ValKey seeding complete\n")


def verify_integration():
    """Verify Neo4j and ValKey integration"""
    print_header("VERIFICATION")
    
    # Neo4j
    print(f"{Colors.BOLD}Neo4j Graph Structure:{Colors.END}")
    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "testpassword"))
    
    with driver.session() as session:
        # Get graph overview
        result = session.run("""
            MATCH (s:ProjectCase {story_id: 'US-DEMO-001'})
            OPTIONAL MATCH (s)-[r1:HAS_PHASE]->(p:PhaseTransition)
            OPTIONAL MATCH (s)-[r2:MADE_DECISION]->(d:ProjectDecision)
            RETURN 
                s.story_id as story,
                count(DISTINCT p) as transitions,
                count(DISTINCT d) as decisions
        """)
        record = result.single()
        print_info(f"  Story: {record['story']}")
        print_info(f"  Phase transitions: {record['transitions']}")
        print_info(f"  Decisions: {record['decisions']}")
        
        # Get full story graph
        print()
        print(f"{Colors.BOLD}Complete Graph Path:{Colors.END}")
        result = session.run("""
            MATCH path = (s:ProjectCase {story_id: 'US-DEMO-001'})-[*]-(n)
            RETURN 
                labels(s)[0] as source,
                type(relationships(path)[0]) as relationship,
                labels(n)[0] as target
            LIMIT 20
        """)
        for record in result:
            print_info(f"  ({record['source']})-[{record['relationship']}]->({record['target']})")
    
    driver.close()
    
    # ValKey
    print()
    print(f"{Colors.BOLD}ValKey Cache Entries:{Colors.END}")
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    
    keys = r.keys("*")
    print_info(f"  Total keys: {len(keys)}")
    
    # Show sample keys
    for key in sorted(keys)[:10]:
        ttl = r.ttl(key)
        print_info(f"  {key} (TTL: {ttl}s)")
    
    print()
    print_success("Verification complete")


def main():
    print(f"\n{Colors.BOLD}Seeding Databases for E2E Demo{Colors.END}")
    print(f"{Colors.CYAN}Story: US-DEMO-001 - Implement Redis Caching{Colors.END}\n")
    
    try:
        # Seed both databases
        seed_neo4j()
        seed_valkey()
        
        # Verify
        verify_integration()
        
        print()
        print_success("✅ ALL DATABASES SEEDED SUCCESSFULLY!")
        print()
        print(f"{Colors.CYAN}You can now query:{Colors.END}")
        print(f"  • Neo4j: kubectl exec -n swe-ai-fleet neo4j-0 -- cypher-shell -u neo4j -p testpassword")
        print(f"  • ValKey: kubectl exec -n swe-ai-fleet valkey-0 -- redis-cli")
        print()
        
    except Exception as e:
        print(f"\n{Colors.YELLOW}❌ Error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

