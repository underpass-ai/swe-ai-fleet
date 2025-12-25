#!/usr/bin/env python3
"""Cleanup Storage - Clear Neo4j and Valkey before E2E tests.

This script clears all data from Neo4j and Valkey to ensure clean test state.
It should be run before executing E2E tests to avoid data corruption issues.

Usage:
    python cleanup_storage.py

Environment Variables:
    NEO4J_URI: Neo4j connection URI (default: bolt://neo4j.swe-ai-fleet.svc.cluster.local:7687)
    NEO4J_USER: Neo4j username (default: neo4j)
    NEO4J_PASSWORD: Neo4j password (required)
    VALKEY_HOST: Valkey host (default: valkey.swe-ai-fleet.svc.cluster.local)
    VALKEY_PORT: Valkey port (default: 6379)
    VALKEY_PASSWORD: Valkey password (optional)
"""

import os
import sys
from typing import Optional

try:
    from neo4j import GraphDatabase
except ImportError:
    print("ERROR: neo4j package not installed. Install with: pip install neo4j")
    sys.exit(1)

try:
    import redis
except ImportError:
    print("ERROR: redis package not installed. Install with: pip install redis")
    sys.exit(1)


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


def print_step(step: str) -> None:
    """Print step header."""
    print()
    print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
    print(f"{Colors.BLUE}{step}{Colors.NC}")
    print(f"{Colors.BLUE}{'=' * 80}{Colors.NC}")
    print()


class StorageCleaner:
    """Clean Neo4j and Valkey storage."""

    def __init__(self) -> None:
        """Initialize with connection details from environment."""
        # Neo4j configuration
        self.neo4j_uri = os.getenv(
            "NEO4J_URI", "bolt://neo4j.swe-ai-fleet.svc.cluster.local:7687"
        )
        self.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "")
        if not self.neo4j_password:
            print_error("NEO4J_PASSWORD environment variable is required")
            sys.exit(1)

        # Valkey configuration
        self.valkey_host = os.getenv(
            "VALKEY_HOST", "valkey.swe-ai-fleet.svc.cluster.local"
        )
        self.valkey_port = int(os.getenv("VALKEY_PORT", "6379"))
        self.valkey_password = os.getenv("VALKEY_PASSWORD") or None  # Empty string becomes None

    def cleanup_neo4j(self) -> bool:
        """Clean all data from Neo4j."""
        print_step("Cleaning Neo4j Database")
        print_info(f"Connecting to Neo4j: {self.neo4j_uri}")
        print_info(f"User: {self.neo4j_user}")

        try:
            driver = GraphDatabase.driver(
                self.neo4j_uri, auth=(self.neo4j_user, self.neo4j_password)
            )

            with driver.session() as session:
                # Get detailed counts before cleanup
                print_info("Counting nodes by type...")

                node_counts = {}
                for label in ["Project", "Epic", "Story", "Task", "BacklogReviewCeremony", "Plan", "PlanApproval"]:
                    result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
                    count = result.single()["count"] if result.peek() else 0
                    if count > 0:
                        node_counts[label] = count
                        print_info(f"  {label}: {count}")

                # Count all nodes
                result = session.run("MATCH (n) RETURN count(n) as count")
                node_count = result.single()["count"] if result.peek() else 0

                # Count all relationships
                result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
                rel_count = result.single()["count"] if result.peek() else 0

                # Count other node types
                other_count = node_count - sum(node_counts.values())
                if other_count > 0:
                    print_info(f"  Other nodes: {other_count}")

                print_info(f"Total: {node_count} nodes and {rel_count} relationships")

                if node_count == 0 and rel_count == 0:
                    print_success("Neo4j is already empty")
                    driver.close()
                    return True

                # Delete all nodes and relationships
                print_info("Deleting all nodes and relationships...")
                # Use execute_write to ensure commit (more reliable than write_transaction)
                def delete_all(tx):
                    result = tx.run("MATCH (n) DETACH DELETE n RETURN count(n) as deleted")
                    return result.single()["deleted"] if result.peek() else 0

                deleted_count = session.execute_write(delete_all)
                print_info(f"Deletion transaction committed: {deleted_count} nodes deleted")

                # Verify cleanup
                result = session.run("MATCH (n) RETURN count(n) as count")
                remaining_nodes = result.single()["count"] if result.peek() else 0

                result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
                remaining_rels = result.single()["count"] if result.peek() else 0

                if remaining_nodes == 0 and remaining_rels == 0:
                    print_success(f"✓ Neo4j cleaned successfully")
                    print_info(f"  Removed: {node_count} nodes and {rel_count} relationships")
                    if node_counts:
                        details = ", ".join([f"{label}: {count}" for label, count in node_counts.items()])
                        print_info(f"  Breakdown: {details}")
                else:
                    print_error(
                        f"Neo4j cleanup incomplete: {remaining_nodes} nodes and {remaining_rels} relationships remaining"
                    )
                    driver.close()
                    return False

            driver.close()
            return True

        except Exception as e:
            print_error(f"Failed to clean Neo4j: {e}")
            import traceback

            traceback.print_exc()
            return False

    def cleanup_valkey(self) -> bool:
        """Clean all data from Valkey."""
        print_step("Cleaning Valkey Database")
        print_info(f"Connecting to Valkey: {self.valkey_host}:{self.valkey_port}")

        try:
            # Connect to Valkey
            if self.valkey_password:
                r = redis.Redis(
                    host=self.valkey_host,
                    port=self.valkey_port,
                    password=self.valkey_password,
                    decode_responses=True,
                )
            else:
                r = redis.Redis(
                    host=self.valkey_host, port=self.valkey_port, decode_responses=True
                )

            # Test connection
            r.ping()
            print_success("Connected to Valkey")

            # Get key count and breakdown before cleanup
            key_count = r.dbsize()
            print_info(f"Found {key_count} keys")

            if key_count > 0:
                # Count keys by prefix
                key_prefixes = {}
                for key in r.scan_iter(match="*", count=1000):
                    prefix = key.split(":")[0] if ":" in key else "other"
                    key_prefixes[prefix] = key_prefixes.get(prefix, 0) + 1

                print_info("Key breakdown by prefix:")
                for prefix, count in sorted(key_prefixes.items(), key=lambda x: x[1], reverse=True):
                    print_info(f"  {prefix}: {count}")

            if key_count == 0:
                print_success("Valkey is already empty")
                return True

            # Delete all keys
            print_info("Deleting all keys...")
            r.flushdb()

            # Verify cleanup
            remaining_keys = r.dbsize()
            if remaining_keys == 0:
                print_success(f"✓ Valkey cleaned successfully")
                print_info(f"  Removed: {key_count} keys")
                if key_prefixes:
                    details = ", ".join([f"{prefix}: {count}" for prefix, count in sorted(key_prefixes.items(), key=lambda x: x[1], reverse=True)])
                    print_info(f"  Breakdown: {details}")
            else:
                print_error(f"Valkey cleanup incomplete: {remaining_keys} keys remaining")
                return False

            return True

        except Exception as e:
            print_error(f"Failed to clean Valkey: {e}")
            import traceback

            traceback.print_exc()
            return False

    def run(self) -> bool:
        """Run cleanup for both Neo4j and Valkey."""
        print()
        print("=" * 80)
        print("Storage Cleanup - Neo4j and Valkey")
        print("=" * 80)
        print()

        neo4j_success = self.cleanup_neo4j()
        valkey_success = self.cleanup_valkey()

        print()
        print("=" * 80)
        print("Cleanup Summary")
        print("=" * 80)
        print()

        if neo4j_success:
            print_success("Neo4j cleanup: SUCCESS")
        else:
            print_error("Neo4j cleanup: FAILED")

        if valkey_success:
            print_success("Valkey cleanup: SUCCESS")
        else:
            print_error("Valkey cleanup: FAILED")

        if neo4j_success and valkey_success:
            print()
            print_success("All storage cleanup completed successfully")
            return True
        else:
            print()
            print_error("Storage cleanup failed")
            return False


def main() -> int:
    """Main entry point."""
    cleaner = StorageCleaner()
    success = cleaner.run()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

