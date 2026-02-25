#!/usr/bin/env python3
"""Cleanup Storage - Clear Neo4j and Valkey before E2E tests.

This script clears all data from Neo4j, Valkey and NATS JetStream to ensure clean test state.
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
    NATS_URL: NATS server URL (default: nats://nats.swe-ai-fleet.svc.cluster.local:4222)
"""

import asyncio
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

try:
    import nats
except ImportError:
    print("ERROR: nats-py package not installed. Install with: pip install nats-py")
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

        # NATS configuration
        self.nats_url = os.getenv(
            "NATS_URL", "nats://nats.swe-ai-fleet.svc.cluster.local:4222"
        )

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

    async def _cleanup_nats_streams(self) -> bool:
        """Purge all messages from all JetStream streams."""
        print_step("Cleaning NATS JetStream")
        print_info(f"Connecting to NATS: {self.nats_url}")

        nats_client = None
        try:
            nats_client = await nats.connect(
                servers=[self.nats_url],
                connect_timeout=10,
                max_reconnect_attempts=2,
                reconnect_time_wait=1,
            )
            jetstream = nats_client.jetstream()
            print_success("Connected to NATS JetStream")

            stream_infos = []
            offset = 0
            while True:
                batch = await jetstream.streams_info(offset=offset)
                if not batch:
                    break
                stream_infos.extend(batch)
                offset += len(batch)

            if not stream_infos:
                print_success("NATS JetStream has no streams configured")
                return True

            print_info(f"Found {len(stream_infos)} stream(s)")
            success = True
            total_messages_before = 0
            total_messages_after = 0

            for stream_info in stream_infos:
                stream_name = stream_info.config.name
                messages_before = stream_info.state.messages
                total_messages_before += messages_before

                print_info(
                    f"Purging stream '{stream_name}' "
                    f"(messages={messages_before}, bytes={stream_info.state.bytes})"
                )
                await jetstream.purge_stream(stream_name)

                refreshed = await jetstream.stream_info(stream_name)
                messages_after = refreshed.state.messages
                total_messages_after += messages_after

                if messages_after == 0:
                    print_success(
                        f"Stream '{stream_name}' purged successfully "
                        f"(messages_after={messages_after})"
                    )
                else:
                    print_error(
                        f"Stream '{stream_name}' purge incomplete "
                        f"(messages_after={messages_after})"
                    )
                    success = False

            if success:
                print_success(
                    "NATS JetStream cleanup successful: "
                    f"messages_before={total_messages_before}, messages_after={total_messages_after}"
                )
            return success

        except Exception as e:
            print_error(f"Failed to clean NATS JetStream: {e}")
            import traceback

            traceback.print_exc()
            return False
        finally:
            if nats_client:
                try:
                    await nats_client.drain()
                except Exception:
                    try:
                        await nats_client.close()
                    except Exception:
                        pass

    def cleanup_nats(self) -> bool:
        """Synchronous wrapper for async NATS cleanup."""
        try:
            return asyncio.run(self._cleanup_nats_streams())
        except Exception as e:
            print_error(f"Failed to execute NATS cleanup event loop: {e}")
            return False

    def verify_neo4j_empty(self) -> bool:
        """Verify Neo4j has zero nodes and relationships."""
        print_info("Verifying Neo4j final state...")
        try:
            driver = GraphDatabase.driver(
                self.neo4j_uri, auth=(self.neo4j_user, self.neo4j_password)
            )
            with driver.session() as session:
                nodes = session.run("MATCH (n) RETURN count(n) AS count").single()["count"]
                rels = session.run("MATCH ()-[r]->() RETURN count(r) AS count").single()["count"]
            driver.close()
            if nodes == 0 and rels == 0:
                print_success("Neo4j verification passed: nodes=0, relationships=0")
                return True
            print_error(
                f"Neo4j verification failed: nodes={nodes}, relationships={rels}"
            )
            return False
        except Exception as e:
            print_error(f"Neo4j verification error: {e}")
            return False

    def verify_valkey_empty(self) -> bool:
        """Verify Valkey database is empty."""
        print_info("Verifying Valkey final state...")
        try:
            if self.valkey_password:
                client = redis.Redis(
                    host=self.valkey_host,
                    port=self.valkey_port,
                    password=self.valkey_password,
                    decode_responses=True,
                )
            else:
                client = redis.Redis(
                    host=self.valkey_host,
                    port=self.valkey_port,
                    decode_responses=True,
                )
            size = client.dbsize()
            if size == 0:
                print_success("Valkey verification passed: dbsize=0")
                return True
            sample_keys = list(client.scan_iter(match="*", count=20))[:10]
            print_error(
                f"Valkey verification failed: dbsize={size}, sample_keys={sample_keys}"
            )
            return False
        except Exception as e:
            print_error(f"Valkey verification error: {e}")
            return False

    async def _verify_nats_empty(self) -> bool:
        """Verify all JetStream streams have zero messages."""
        print_info("Verifying NATS JetStream final state...")
        nats_client = None
        try:
            nats_client = await nats.connect(
                servers=[self.nats_url],
                connect_timeout=10,
                max_reconnect_attempts=2,
                reconnect_time_wait=1,
            )
            jetstream = nats_client.jetstream()

            stream_infos = []
            offset = 0
            while True:
                batch = await jetstream.streams_info(offset=offset)
                if not batch:
                    break
                stream_infos.extend(batch)
                offset += len(batch)

            if not stream_infos:
                print_success("NATS verification passed: no streams configured")
                return True

            non_empty_streams = []
            for stream_info in stream_infos:
                refreshed = await jetstream.stream_info(stream_info.config.name)
                if refreshed.state.messages > 0:
                    non_empty_streams.append(
                        (refreshed.config.name, refreshed.state.messages)
                    )

            if not non_empty_streams:
                print_success(
                    "NATS verification passed: all streams have 0 messages"
                )
                return True

            print_error(
                f"NATS verification failed: non-empty streams={non_empty_streams}"
            )
            return False
        except Exception as e:
            print_error(f"NATS verification error: {e}")
            return False
        finally:
            if nats_client:
                try:
                    await nats_client.drain()
                except Exception:
                    try:
                        await nats_client.close()
                    except Exception:
                        pass

    def verify_nats_empty(self) -> bool:
        """Synchronous wrapper for async NATS verification."""
        try:
            return asyncio.run(self._verify_nats_empty())
        except Exception as e:
            print_error(f"Failed to execute NATS verification event loop: {e}")
            return False

    def run(self) -> bool:
        """Run cleanup for Neo4j, Valkey and NATS."""
        print()
        print("=" * 80)
        print("Storage Cleanup - Neo4j, Valkey, and NATS")
        print("=" * 80)
        print()

        neo4j_success = self.cleanup_neo4j()
        valkey_success = self.cleanup_valkey()
        nats_success = self.cleanup_nats()
        print_step("Post-cleanup Verification")
        neo4j_verified = self.verify_neo4j_empty()
        valkey_verified = self.verify_valkey_empty()
        nats_verified = self.verify_nats_empty()

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

        if nats_success:
            print_success("NATS cleanup: SUCCESS")
        else:
            print_error("NATS cleanup: FAILED")

        if neo4j_verified:
            print_success("Neo4j verification: PASSED")
        else:
            print_error("Neo4j verification: FAILED")

        if valkey_verified:
            print_success("Valkey verification: PASSED")
        else:
            print_error("Valkey verification: FAILED")

        if nats_verified:
            print_success("NATS verification: PASSED")
        else:
            print_error("NATS verification: FAILED")

        if (
            neo4j_success
            and valkey_success
            and nats_success
            and neo4j_verified
            and valkey_verified
            and nats_verified
        ):
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
