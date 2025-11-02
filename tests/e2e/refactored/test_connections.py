#!/usr/bin/env python3
"""
Connection Test Script for E2E Tests
Validates Neo4j and Valkey connectivity before running full test suite.
"""

import asyncio
import os
import sys

from neo4j import AsyncDriver, AsyncGraphDatabase
from redis.asyncio import Redis


async def test_neo4j_connection() -> bool:
    """Test Neo4j connection and basic operations."""
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j.swe-ai-fleet.svc.cluster.local:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "test")
    
    print("\n🔍 Testing Neo4j connection...")
    print(f"   URI: {neo4j_uri}")
    print(f"   User: {neo4j_user}")
    
    driver: AsyncDriver | None = None
    
    try:
        # Create driver
        driver = AsyncGraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )
        
        # Verify connectivity
        await driver.verify_connectivity()
        print("✅ Neo4j driver connected successfully")
        
        # Test basic query
        async with driver.session() as session:
            result = await session.run("RETURN 1 AS num")
            record = await result.single()
            
            if record and record["num"] == 1:
                print("✅ Neo4j query test passed")
            else:
                print("❌ Neo4j query test failed")
                return False
        
        # Test write operation (create and delete test node)
        async with driver.session() as session:
            # Create test node
            await session.run(
                "CREATE (n:TestNode {id: 'connection-test', created_at: datetime()}) RETURN n"
            )
            print("✅ Neo4j write test passed (test node created)")
            
            # Verify node exists
            result = await session.run(
                "MATCH (n:TestNode {id: 'connection-test'}) RETURN n"
            )
            record = await result.single()
            
            if record:
                print("✅ Neo4j read test passed (test node found)")
            else:
                print("❌ Neo4j read test failed (test node not found)")
                return False
            
            # Clean up test node
            await session.run(
                "MATCH (n:TestNode {id: 'connection-test'}) DELETE n"
            )
            print("✅ Neo4j cleanup test passed (test node deleted)")
        
        print("✅ All Neo4j connection tests passed\n")
        return True
        
    except Exception as e:
        print(f"❌ Neo4j connection failed: {e}")
        return False
        
    finally:
        if driver:
            await driver.close()


async def test_valkey_connection() -> bool:
    """Test Valkey/Redis connection and basic operations."""
    valkey_host = os.getenv("VALKEY_HOST", "valkey.swe-ai-fleet.svc.cluster.local")
    valkey_port = int(os.getenv("VALKEY_PORT", "6379"))
    
    print("\n🔍 Testing Valkey connection...")
    print(f"   Host: {valkey_host}")
    print(f"   Port: {valkey_port}")
    
    redis_client: Redis | None = None
    
    try:
        # Create client
        redis_client = Redis(
            host=valkey_host,
            port=valkey_port,
            decode_responses=True
        )
        
        # Test PING
        pong = await redis_client.ping()
        if pong:
            print("✅ Valkey PING successful")
        else:
            print("❌ Valkey PING failed")
            return False
        
        # Test SET/GET
        test_key = "connection:test"
        test_value = "hello-from-e2e-tests"
        
        await redis_client.set(test_key, test_value, ex=60)
        print("✅ Valkey SET test passed")
        
        retrieved_value = await redis_client.get(test_key)
        if retrieved_value == test_value:
            print("✅ Valkey GET test passed")
        else:
            print(f"❌ Valkey GET test failed: expected '{test_value}', got '{retrieved_value}'")
            return False
        
        # Test HSET/HGET (hash operations - used by tests)
        test_hash = "connection:test:hash"
        test_data = {
            "field1": "value1",
            "field2": "value2",
            "timestamp": "2025-11-02T00:00:00Z"
        }
        
        await redis_client.hset(test_hash, mapping=test_data)
        print("✅ Valkey HSET test passed")
        
        retrieved_hash = await redis_client.hgetall(test_hash)
        if retrieved_hash == test_data:
            print("✅ Valkey HGETALL test passed")
        else:
            print("❌ Valkey HGETALL test failed")
            return False
        
        # Test key existence
        exists = await redis_client.exists(test_hash)
        if exists:
            print("✅ Valkey EXISTS test passed")
        else:
            print("❌ Valkey EXISTS test failed")
            return False
        
        # Clean up test data
        await redis_client.delete(test_key, test_hash)
        print("✅ Valkey cleanup test passed")
        
        print("✅ All Valkey connection tests passed\n")
        return True
        
    except Exception as e:
        print(f"❌ Valkey connection failed: {e}")
        return False
        
    finally:
        if redis_client:
            await redis_client.close()


async def main() -> int:
    """Run all connection tests."""
    print("=" * 60)
    print("E2E Connection Tests")
    print("=" * 60)
    
    neo4j_ok = await test_neo4j_connection()
    valkey_ok = await test_valkey_connection()
    
    print("=" * 60)
    print("Summary:")
    print("=" * 60)
    print(f"Neo4j:  {'✅ PASS' if neo4j_ok else '❌ FAIL'}")
    print(f"Valkey: {'✅ PASS' if valkey_ok else '❌ FAIL'}")
    print("=" * 60)
    
    if neo4j_ok and valkey_ok:
        print("\n✅ All connection tests passed! Ready to run e2e tests.\n")
        return 0
    else:
        print("\n❌ Some connection tests failed. Fix connectivity before running e2e tests.\n")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

