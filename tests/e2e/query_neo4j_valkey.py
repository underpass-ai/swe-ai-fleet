#!/usr/bin/env python3
"""
Query Neo4j and ValKey to show stored data from E2E demo
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Try to import Neo4j driver
try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    print("⚠️  neo4j driver not installed. Install with: pip install neo4j")
    NEO4J_AVAILABLE = False

# Try to import Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    print("⚠️  redis not installed. Install with: pip install redis")
    REDIS_AVAILABLE = False


class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")


def print_section(text):
    print(f"\n{Colors.BOLD}{Colors.GREEN}{text}{Colors.END}")
    print(f"{Colors.BLUE}{'-'*80}{Colors.END}")


def query_neo4j():
    """Query Neo4j for story data"""
    if not NEO4J_AVAILABLE:
        print("Neo4j driver not available, skipping...")
        return
    
    print_header("NEO4J DATABASE - Story US-DEMO-001")
    
    try:
        driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "password")  # Default password, adjust if needed
        )
        
        with driver.session() as session:
            # Query 1: All nodes
            print_section("1. ALL NODES IN DATABASE")
            result = session.run("MATCH (n) RETURN labels(n) as labels, count(n) as count")
            for record in result:
                print(f"  {Colors.CYAN}{record['labels']}{Colors.END}: {record['count']} nodes")
            
            # Query 2: Story nodes
            print_section("2. STORY NODES (ProjectCase)")
            result = session.run("""
                MATCH (s:ProjectCase)
                RETURN s.story_id as story_id, s.title as title, 
                       s.description as description, s.current_phase as phase,
                       s.created_at as created_at
                ORDER BY s.created_at DESC
                LIMIT 10
            """)
            for record in result:
                print(f"\n  Story ID: {Colors.BOLD}{record['story_id']}{Colors.END}")
                print(f"  Title: {record['title']}")
                print(f"  Description: {record['description'][:100]}...")
                print(f"  Current Phase: {Colors.GREEN}{record['phase']}{Colors.END}")
                print(f"  Created: {record['created_at']}")
            
            # Query 3: Phase transitions
            print_section("3. PHASE TRANSITIONS")
            result = session.run("""
                MATCH (s:ProjectCase {story_id: 'US-DEMO-001'})-[r:HAS_PHASE]->(p:PhaseTransition)
                RETURN p.from_phase as from_phase, p.to_phase as to_phase,
                       p.rationale as rationale, p.transitioned_at as when
                ORDER BY p.transitioned_at
            """)
            count = 0
            for record in result:
                count += 1
                print(f"\n  Transition {count}:")
                print(f"    {record['from_phase']} → {Colors.GREEN}{record['to_phase']}{Colors.END}")
                print(f"    Rationale: {record['rationale']}")
                print(f"    When: {record['when']}")
            if count == 0:
                print(f"  {Colors.YELLOW}No phase transitions found{Colors.END}")
            
            # Query 4: Decisions
            print_section("4. PROJECT DECISIONS")
            result = session.run("""
                MATCH (s:ProjectCase {story_id: 'US-DEMO-001'})-[r:MADE_DECISION]->(d:ProjectDecision)
                RETURN d.decision_id as id, d.decision_type as type, d.title as title,
                       d.rationale as rationale, d.made_by_role as role,
                       d.created_at as when
                ORDER BY d.created_at
            """)
            count = 0
            for record in result:
                count += 1
                print(f"\n  Decision {count}: {Colors.BOLD}{record['title']}{Colors.END}")
                print(f"    ID: {record['id']}")
                print(f"    Type: {Colors.CYAN}{record['type']}{Colors.END}")
                print(f"    Made by: {record['role']}")
                print(f"    Rationale: {record['rationale'][:100]}...")
                print(f"    When: {record['when']}")
            if count == 0:
                print(f"  {Colors.YELLOW}No decisions found{Colors.END}")
            
            # Query 5: Full graph for story
            print_section("5. COMPLETE GRAPH STRUCTURE FOR US-DEMO-001")
            result = session.run("""
                MATCH path = (s:ProjectCase {story_id: 'US-DEMO-001'})-[*]-(n)
                RETURN 
                    labels(s) as source_labels,
                    type(relationships(path)[0]) as rel_type,
                    labels(n) as target_labels,
                    count(*) as count
            """)
            print(f"\n  {Colors.BOLD}Relationships:{Colors.END}")
            for record in result:
                source = record['source_labels'][0] if record['source_labels'] else 'Unknown'
                target = record['target_labels'][0] if record['target_labels'] else 'Unknown'
                rel = record['rel_type']
                count = record['count']
                print(f"    ({Colors.CYAN}{source}{Colors.END})-[{Colors.GREEN}{rel}{Colors.END}]->({Colors.CYAN}{target}{Colors.END}): {count}")
            
            # Query 6: Cypher visualization query
            print_section("6. CYPHER QUERY FOR VISUALIZATION")
            print(f"""
  Copy this query into Neo4j Browser (http://localhost:7474):
  
  {Colors.CYAN}MATCH path = (s:ProjectCase {{story_id: 'US-DEMO-001'}})-[*]-(n)
  RETURN path{Colors.END}
  
  This will show the complete graph for the story.
""")
        
        driver.close()
        print(f"\n{Colors.GREEN}✅ Neo4j query complete{Colors.END}\n")
        
    except Exception as e:
        print(f"\n{Colors.RED}❌ Error connecting to Neo4j: {e}{Colors.END}")
        print(f"{Colors.YELLOW}Make sure Neo4j is running and port-forwarded{Colors.END}\n")


def query_valkey():
    """Query ValKey (Redis) for cached data"""
    if not REDIS_AVAILABLE:
        print("Redis client not available, skipping...")
        return
    
    print_header("VALKEY (REDIS) CACHE - Context Data")
    
    try:
        # Try multiple possible ValKey/Redis locations
        redis_clients = [
            {"host": "localhost", "port": 6379, "name": "ValKey (localhost)"},
        ]
        
        connected = False
        r = None
        
        for config in redis_clients:
            try:
                r = redis.Redis(
                    host=config["host"],
                    port=config["port"],
                    decode_responses=True,
                    socket_timeout=2
                )
                r.ping()
                print(f"{Colors.GREEN}✅ Connected to {config['name']}{Colors.END}\n")
                connected = True
                break
            except Exception as e:
                continue
        
        if not connected:
            print(f"{Colors.YELLOW}⚠️  ValKey/Redis not accessible at localhost:6379{Colors.END}")
            print(f"{Colors.YELLOW}   Run: kubectl port-forward -n default svc/valkey 6379:6379{Colors.END}\n")
            return
        
        # Query 1: All keys
        print_section("1. ALL KEYS IN VALKEY")
        keys = r.keys("*")
        print(f"  Total keys: {Colors.BOLD}{len(keys)}{Colors.END}")
        if keys:
            print(f"\n  {Colors.CYAN}Key patterns:{Colors.END}")
            # Group by prefix
            prefixes = {}
            for key in keys:
                prefix = key.split(':')[0] if ':' in key else 'other'
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
            for prefix, count in sorted(prefixes.items()):
                print(f"    {prefix}:* → {count} keys")
        
        # Query 2: Context keys
        print_section("2. CONTEXT CACHE KEYS")
        context_keys = r.keys("context:*")
        print(f"  Found: {len(context_keys)} context keys")
        for key in context_keys[:10]:  # Show first 10
            ttl = r.ttl(key)
            print(f"\n  Key: {Colors.CYAN}{key}{Colors.END}")
            print(f"    TTL: {ttl}s" if ttl > 0 else "    TTL: No expiration")
            
            # Try to get value (might be JSON)
            value = r.get(key)
            if value:
                if len(value) > 200:
                    print(f"    Value: {value[:200]}... ({len(value)} chars)")
                else:
                    print(f"    Value: {value}")
        
        # Query 3: Story-specific keys
        print_section("3. STORY-SPECIFIC CACHE (US-DEMO-001)")
        story_keys = r.keys("*US-DEMO-001*") + r.keys("*demo*")
        if story_keys:
            print(f"  Found: {len(story_keys)} keys")
            for key in story_keys:
                value = r.get(key)
                ttl = r.ttl(key)
                print(f"\n  Key: {Colors.CYAN}{key}{Colors.END}")
                print(f"    TTL: {ttl}s" if ttl > 0 else "    TTL: No expiration")
                if value:
                    if len(value) > 150:
                        print(f"    Value: {value[:150]}...")
                    else:
                        print(f"    Value: {value}")
        else:
            print(f"  {Colors.YELLOW}No story-specific keys found{Colors.END}")
        
        # Query 4: Cache statistics
        print_section("4. CACHE STATISTICS")
        info = r.info("stats")
        print(f"  Total connections: {info.get('total_connections_received', 'N/A')}")
        print(f"  Total commands: {info.get('total_commands_processed', 'N/A')}")
        print(f"  Keyspace hits: {info.get('keyspace_hits', 'N/A')}")
        print(f"  Keyspace misses: {info.get('keyspace_misses', 'N/A')}")
        
        hit_rate = 0
        if info.get('keyspace_hits') and info.get('keyspace_misses'):
            total = info['keyspace_hits'] + info['keyspace_misses']
            if total > 0:
                hit_rate = (info['keyspace_hits'] / total) * 100
                print(f"  {Colors.BOLD}Hit rate: {hit_rate:.1f}%{Colors.END}")
        
        # Query 5: Memory usage
        print_section("5. MEMORY USAGE")
        memory_info = r.info("memory")
        used_memory = memory_info.get('used_memory_human', 'N/A')
        max_memory = memory_info.get('maxmemory_human', 'N/A')
        print(f"  Used memory: {Colors.BOLD}{used_memory}{Colors.END}")
        print(f"  Max memory: {max_memory}")
        
        print(f"\n{Colors.GREEN}✅ ValKey query complete{Colors.END}\n")
        
    except Exception as e:
        print(f"\n{Colors.RED}❌ Error connecting to ValKey: {e}{Colors.END}\n")


def main():
    print(f"{Colors.BOLD}Querying Neo4j and ValKey for E2E Demo Data{Colors.END}")
    print(f"{Colors.CYAN}Story: US-DEMO-001 - Implement Redis Caching{Colors.END}\n")
    
    # Query both databases
    query_neo4j()
    query_valkey()
    
    print_header("SUMMARY")
    print(f"{Colors.GREEN}✅ Database queries complete{Colors.END}")
    print(f"\n{Colors.CYAN}What we showed:{Colors.END}")
    print(f"  • Neo4j: Story structure, phase transitions, decisions, relationships")
    print(f"  • ValKey: Cached context, keys, statistics, memory usage")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)

