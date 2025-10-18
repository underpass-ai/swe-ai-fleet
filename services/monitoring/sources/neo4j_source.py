"""
Neo4j data source for monitoring.

Fetches graph statistics and recent nodes/relationships.
"""
import asyncio
import logging
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class Neo4jSource:
    """Monitor Neo4j graph database."""
    
    def __init__(self):
        self.driver = None
        self.uri = os.getenv("NEO4J_URI", "bolt://neo4j.swe-ai-fleet.svc.cluster.local:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "devpassword123")
    
    async def connect(self):
        """Connect to Neo4j."""
        try:
            # Import neo4j driver (requires neo4j package)
            from neo4j import GraphDatabase
            
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            
            # Test connection
            with self.driver.session() as session:
                result = session.run("RETURN 1 AS test")
                result.single()
            
            logger.info(f"✅ Connected to Neo4j: {self.uri}")
            
        except ImportError:
            logger.warning("⚠️  neo4j package not installed, using mock data")
            self.driver = None
        except Exception as e:
            logger.error(f"❌ Failed to connect to Neo4j: {e}")
            self.driver = None
    
    async def get_graph_stats(self) -> Dict:
        """Get graph statistics."""
        if not self.driver:
            return {
                "connected": False,
                "error": "Neo4j driver not initialized"
            }
        
        try:
            with self.driver.session() as session:
                # Count nodes by label
                node_counts = session.run("""
                    MATCH (n)
                    RETURN labels(n) as labels, count(n) as count
                """)
                
                # Count relationships by type
                rel_counts = session.run("""
                    MATCH ()-[r]->()
                    RETURN type(r) as type, count(r) as count
                """)
                
                # Recent nodes
                recent_nodes = session.run("""
                    MATCH (n)
                    WHERE n.timestamp IS NOT NULL
                    RETURN labels(n) as labels, n.timestamp as timestamp
                    ORDER BY n.timestamp DESC
                    LIMIT 10
                """)
                
                nodes = [{"labels": record["labels"], "count": record["count"]} 
                        for record in node_counts]
                
                relationships = [{"type": record["type"], "count": record["count"]} 
                               for record in rel_counts]
                
                recent = [{"labels": record["labels"], "timestamp": record["timestamp"]} 
                         for record in recent_nodes]
                
                total_nodes = sum(n["count"] for n in nodes)
                total_relationships = sum(r["count"] for r in relationships)
                
                return {
                    "connected": True,
                    "total_nodes": total_nodes,
                    "total_relationships": total_relationships,
                    "nodes_by_label": nodes,
                    "relationships_by_type": relationships,
                    "recent_nodes": recent
                }
        except Exception as e:
            logger.error(f"❌ Failed to get Neo4j stats: {e}")
            return {
                "connected": False,
                "error": str(e)
            }
    
    async def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()

