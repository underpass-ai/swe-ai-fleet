"""
Tests for Neo4j Source monitoring module.

Tests with proper mocking to avoid external dependencies and ensure fast execution.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock

from services.monitoring.sources.neo4j_source import Neo4jSource


class TestNeo4jSource:
    """Test Neo4j monitoring source with mocks."""

    def test_initialization(self):
        """Test Neo4j source initialization."""
        source = Neo4jSource()
        
        assert source.driver is None
        assert source.uri == "bolt://neo4j.swe-ai-fleet.svc.cluster.local:7687"
        assert source.user == "neo4j"
        assert source.password == "devpassword123"

    def test_initialization_with_env_vars(self):
        """Test Neo4j source initialization with environment variables."""
        with patch.dict('os.environ', {
            'NEO4J_URI': 'bolt://custom:7687',
            'NEO4J_USER': 'custom_user',
            'NEO4J_PASSWORD': 'custom_pass'
        }):
            source = Neo4jSource()
            
            assert source.uri == "bolt://custom:7687"
            assert source.user == "custom_user"
            assert source.password == "custom_pass"

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful connection to Neo4j."""
        source = Neo4jSource()
        
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = {"test": 1}
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        with patch('neo4j.GraphDatabase') as mock_graph_db:
            mock_graph_db.driver.return_value = mock_driver
            
            await source.connect()
            
            assert source.driver == mock_driver
            mock_graph_db.driver.assert_called_once_with(
                source.uri,
                auth=(source.user, source.password)
            )

    @pytest.mark.asyncio
    async def test_connect_import_error(self):
        """Test connection when neo4j package is not available."""
        source = Neo4jSource()
        
        with patch('services.monitoring.sources.neo4j_source.GraphDatabase', side_effect=ImportError("No module named 'neo4j'")):
            await source.connect()
            
            assert source.driver is None

    @pytest.mark.asyncio
    async def test_connect_exception(self):
        """Test connection failure due to exception."""
        source = Neo4jSource()
        
        with patch('neo4j.GraphDatabase') as mock_graph_db:
            mock_graph_db.driver.side_effect = Exception("Connection failed")
            
            await source.connect()
            
            assert source.driver is None

    @pytest.mark.asyncio
    async def test_get_graph_stats_no_driver(self):
        """Test get_graph_stats when driver is not initialized."""
        source = Neo4jSource()
        source.driver = None
        
        result = await source.get_graph_stats()
        
        assert result["connected"] is False
        assert "error" in result
        assert result["error"] == "Neo4j driver not initialized"

    @pytest.mark.asyncio
    async def test_get_graph_stats_success(self):
        """Test successful get_graph_stats."""
        source = Neo4jSource()
        
        # Mock driver and session
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        
        # Mock query results
        mock_node_counts = [
            {"labels": ["Agent"], "count": 5},
            {"labels": ["Task"], "count": 10}
        ]
        mock_rel_counts = [
            {"type": "ASSIGNED_TO", "count": 8},
            {"type": "DEPENDS_ON", "count": 3}
        ]
        mock_recent_nodes = [
            {"labels": ["Agent"], "timestamp": "2024-01-01T10:00:00Z"}
        ]
        
        # Configure session.run to return different results based on query
        def mock_run(query):
            mock_result = MagicMock()
            if "labels(n) as labels, count(n) as count" in query:
                mock_result.__iter__.return_value = iter(mock_node_counts)
            elif "type(r) as type, count(r) as count" in query:
                mock_result.__iter__.return_value = iter(mock_rel_counts)
            elif "ORDER BY n.timestamp DESC" in query:
                mock_result.__iter__.return_value = iter(mock_recent_nodes)
            return mock_result
        
        mock_session.run.side_effect = mock_run
        source.driver = mock_driver
        
        result = await source.get_graph_stats()
        
        assert result["connected"] is True
        assert result["total_nodes"] == 15  # 5 + 10
        assert result["total_relationships"] == 11  # 8 + 3
        assert len(result["nodes_by_label"]) == 2
        assert len(result["relationships_by_type"]) == 2
        assert len(result["recent_nodes"]) == 1

    @pytest.mark.asyncio
    async def test_get_graph_stats_exception(self):
        """Test get_graph_stats when exception occurs."""
        source = Neo4jSource()
        
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__.return_value = mock_session
        mock_session.run.side_effect = Exception("Query failed")
        
        source.driver = mock_driver
        
        result = await source.get_graph_stats()
        
        assert result["connected"] is False
        assert "error" in result
        assert result["error"] == "Query failed"

    @pytest.mark.asyncio
    async def test_close_with_driver(self):
        """Test close when driver exists."""
        source = Neo4jSource()
        mock_driver = MagicMock()
        source.driver = mock_driver
        
        await source.close()
        
        mock_driver.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_without_driver(self):
        """Test close when driver is None."""
        source = Neo4jSource()
        source.driver = None
        
        # Should not raise exception
        await source.close()

    def test_has_required_methods(self):
        """Test that Neo4jSource has all required methods."""
        source = Neo4jSource()
        
        required_methods = ['connect', 'get_graph_stats', 'close']
        for method in required_methods:
            assert hasattr(source, method), f"Missing method: {method}"
            assert callable(getattr(source, method)), f"Method {method} is not callable"