"""
Monitoring Data Source Ports.

Defines interfaces for monitoring data sources following hexagonal architecture.
Each port represents a contract for accessing external system metrics.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class MonitoringDataSourcePort(ABC):
    """Base port for monitoring data sources."""
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the data source."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the data source."""
        pass
    
    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if connected to the data source."""
        pass


class NATSMonitoringPort(MonitoringDataSourcePort):
    """Port for NATS JetStream monitoring data."""
    
    @abstractmethod
    async def get_stream_info(self, stream_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a NATS stream."""
        pass
    
    @abstractmethod
    async def get_stream_stats(self, stream_name: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a NATS stream."""
        pass
    
    @abstractmethod
    async def list_streams(self) -> List[Dict[str, Any]]:
        """List all available streams."""
        pass
    
    @abstractmethod
    async def get_consumer_info(self, stream_name: str, consumer_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a consumer."""
        pass


class Neo4jMonitoringPort(MonitoringDataSourcePort):
    """Port for Neo4j graph database monitoring data."""
    
    @abstractmethod
    async def get_graph_stats(self) -> Dict[str, Any]:
        """Get graph database statistics."""
        pass
    
    @abstractmethod
    async def get_node_count(self, label: Optional[str] = None) -> int:
        """Get count of nodes, optionally filtered by label."""
        pass
    
    @abstractmethod
    async def get_relationship_count(self, relationship_type: Optional[str] = None) -> int:
        """Get count of relationships, optionally filtered by type."""
        pass
    
    @abstractmethod
    async def get_recent_activity(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent graph activity."""
        pass


class RayMonitoringPort(MonitoringDataSourcePort):
    """Port for Ray cluster monitoring data."""
    
    @abstractmethod
    async def get_cluster_stats(self) -> Dict[str, Any]:
        """Get Ray cluster statistics."""
        pass
    
    @abstractmethod
    async def get_node_stats(self) -> List[Dict[str, Any]]:
        """Get statistics for Ray nodes."""
        pass
    
    @abstractmethod
    async def get_job_stats(self) -> List[Dict[str, Any]]:
        """Get statistics for Ray jobs."""
        pass
    
    @abstractmethod
    async def get_actor_stats(self) -> List[Dict[str, Any]]:
        """Get statistics for Ray actors."""
        pass


class ValkeyMonitoringPort(MonitoringDataSourcePort):
    """Port for Valkey/Redis monitoring data."""
    
    @abstractmethod
    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        pass
    
    @abstractmethod
    async def get_info(self) -> Dict[str, Any]:
        """Get general server information."""
        pass
    
    @abstractmethod
    async def get_keyspace_stats(self) -> Dict[str, Any]:
        """Get keyspace statistics."""
        pass
    
    @abstractmethod
    async def get_client_stats(self) -> Dict[str, Any]:
        """Get client connection statistics."""
        pass


class OrchestratorMonitoringPort(MonitoringDataSourcePort):
    """Port for Orchestrator service monitoring data."""
    
    @abstractmethod
    async def get_deliberation_stats(self) -> Dict[str, Any]:
        """Get deliberation statistics."""
        pass
    
    @abstractmethod
    async def get_council_stats(self) -> Dict[str, Any]:
        """Get council statistics."""
        pass
    
    @abstractmethod
    async def get_agent_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        pass
    
    @abstractmethod
    async def get_task_stats(self) -> Dict[str, Any]:
        """Get task execution statistics."""
        pass
