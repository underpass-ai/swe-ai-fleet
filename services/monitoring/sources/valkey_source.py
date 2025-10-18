"""
ValKey (Redis) data source for monitoring.

Fetches cache statistics and recent operations.
"""
import asyncio
import logging
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ValKeySource:
    """Monitor ValKey cache."""
    
    def __init__(self):
        self.client = None
        self.url = os.getenv("VALKEY_URL", "redis://valkey.swe-ai-fleet.svc.cluster.local:6379")
    
    async def connect(self):
        """Connect to ValKey."""
        try:
            import redis.asyncio as redis
            
            self.client = await redis.from_url(self.url, decode_responses=True)
            
            # Test connection
            await self.client.ping()
            
            logger.info(f"✅ Connected to ValKey: {self.url}")
            
        except ImportError:
            logger.error("❌ redis package not installed")
            self.client = None
        except Exception as e:
            logger.error(f"❌ Failed to connect to ValKey: {e}")
            self.client = None
    
    async def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        if not self.client:
            return {
                "connected": False,
                "error": "ValKey not connected",
                "total_keys": 0,
                "memory_used_mb": 0.0,
                "hits": 0,
                "misses": 0,
                "recent_keys": []
            }
        
        try:
            # Get info
            info = await self.client.info('stats')
            memory_info = await self.client.info('memory')
            
            # Get all keys (be careful in production!)
            keys = await self.client.keys('*')
            
            # Sample recent keys
            recent_keys = []
            for key in keys[:10]:
                ttl = await self.client.ttl(key)
                key_type = await self.client.type(key)
                recent_keys.append({
                    "key": key,
                    "type": key_type,
                    "ttl": ttl
                })
            
            return {
                "total_keys": len(keys),
                "memory_used_mb": memory_info.get('used_memory', 0) / (1024 * 1024),
                "hits": info.get('keyspace_hits', 0),
                "misses": info.get('keyspace_misses', 0),
                "recent_keys": recent_keys,
                "connected": True
            }
        except Exception as e:
            logger.error(f"❌ Failed to get ValKey stats: {e}")
            return {
                "connected": False,
                "error": str(e),
                "total_keys": 0,
                "memory_used_mb": 0.0,
                "hits": 0,
                "misses": 0,
                "recent_keys": []
            }
    
    async def close(self):
        """Close ValKey connection."""
        if self.client:
            await self.client.close()

