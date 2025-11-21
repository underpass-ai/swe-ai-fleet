"""
Simple Tests for Monitoring Sources - Correct Structure.

Tests based on actual class attributes and methods.
"""


from services.monitoring.sources.nats_source import NATSSource
from services.monitoring.sources.neo4j_source import Neo4jSource
from services.monitoring.sources.orchestrator_source import OrchestratorSource
from services.monitoring.sources.ray_source import RaySource
from services.monitoring.sources.valkey_source import ValKeySource


class TestMonitoringSourcesCorrect:
    """Test monitoring sources with correct structure."""

    def test_nats_source_initialization(self):
        """Test NATS source initialization with dependency injection."""
        from unittest.mock import Mock
        
        mock_connection = Mock()
        mock_stream = Mock()
        
        source = NATSSource(mock_connection, mock_stream)
        
        assert source.connection == mock_connection
        assert source.stream == mock_stream
        
    def test_nats_source_is_connected_with_exception(self):
        """Test is_connected property handles Exception correctly."""
        from unittest.mock import Mock
        
        mock_connection = Mock()
        mock_stream = Mock()
        source = NATSSource(mock_connection, mock_stream)
        
        # Mock asyncio.run to simulate exception handling
        async def mock_connected_error():
            await asyncio.sleep(0)  # Make function truly async
            raise ConnectionError("Connection error")
        
        async def mock_connected_success():
            await asyncio.sleep(0)  # Make function truly async
            return True
        
        # Test that Exception is caught and returns False
        mock_connection.is_connected.side_effect = mock_connected_error
        assert source.is_connected is False
        
        # Test that successful connection returns True
        mock_connection.is_connected.side_effect = mock_connected_success
        assert source.is_connected is True
        
    def test_nats_source_js_context(self):
        """Test js property returns context correctly."""
        from unittest.mock import Mock
        
        mock_connection = Mock()
        mock_stream = Mock()
        source = NATSSource(mock_connection, mock_stream)
        
        # Test that successful context returns the context
        mock_context = Mock()
        mock_connection.get_stream_context.return_value = mock_context
        result = source.js
        assert result is not None

    def test_nats_source_custom_url(self):
        """Test NATS source with dependency injection (no custom URL needed)."""
        from unittest.mock import Mock
        
        mock_connection = Mock()
        mock_stream = Mock()
        
        source = NATSSource(mock_connection, mock_stream)
        
        # With dependency injection, URL configuration is handled by the injected connection port
        assert source.connection == mock_connection
        assert source.stream == mock_stream

    def test_neo4j_source_initialization(self):
        """Test Neo4j source initialization."""
        source = Neo4jSource()
        
        assert source.driver is None
        assert source.uri == "bolt://neo4j.swe-ai-fleet.svc.cluster.local:7687"
        assert source.user == "neo4j"
        assert source.password == "devpassword123"

    def test_ray_source_initialization(self):
        """Test Ray source initialization."""
        source = RaySource()
        
        assert source.ray_executor_host == "ray_executor.swe-ai-fleet.svc.cluster.local"
        assert source.ray_executor_port == 50056
        assert source.channel is None
        assert source.stub is None

    def test_ray_source_custom_config(self):
        """Test Ray source with custom configuration."""
        custom_host = "custom-ray:50057"
        custom_port = 50057
        source = RaySource(ray_executor_host=custom_host, ray_executor_port=custom_port)
        
        assert source.ray_executor_host == custom_host
        assert source.ray_executor_port == custom_port

    def test_valkey_source_initialization(self):
        """Test ValKey source initialization."""
        source = ValKeySource()
        
        assert source.client is None
        assert "valkey.swe-ai-fleet.svc.cluster.local:6379" in source.url

    def test_orchestrator_source_initialization(self):
        """Test Orchestrator source initialization."""
        source = OrchestratorSource()
        
        assert source.channel is None
        assert source.stub is None
        assert "orchestrator.swe-ai-fleet.svc.cluster.local:50055" in source.address

    def test_all_sources_have_connect_method(self):
        """Test all sources have connect method."""
        from unittest.mock import Mock
        
        mock_connection = Mock()
        mock_stream = Mock()
        
        sources = [
            NATSSource(mock_connection, mock_stream),
            Neo4jSource(),
            RaySource(),
            ValKeySource(),
            OrchestratorSource()
        ]
        
        for source in sources:
            assert hasattr(source, 'connect'), f"{source.__class__.__name__} missing connect method"
            assert callable(source.connect), f"{source.__class__.__name__}.connect is not callable"

    def test_all_sources_initial_state(self):
        """Test all sources start in disconnected state."""
        from unittest.mock import Mock
        
        mock_connection = Mock()
        mock_stream = Mock()
        
        nats_source = NATSSource(mock_connection, mock_stream)
        assert nats_source.connection == mock_connection
        assert nats_source.stream == mock_stream
        
        neo4j_source = Neo4jSource()
        assert neo4j_source.driver is None
        
        ray_source = RaySource()
        assert ray_source.channel is None
        assert ray_source.stub is None
        
        valkey_source = ValKeySource()
        assert valkey_source.client is None
        
        orchestrator_source = OrchestratorSource()
        assert orchestrator_source.channel is None
        assert orchestrator_source.stub is None

    def test_nats_source_has_close_method(self):
        """Test NATS source has close method."""
        from unittest.mock import Mock
        
        mock_connection = Mock()
        mock_stream = Mock()
        
        source = NATSSource(mock_connection, mock_stream)
        assert hasattr(source, 'close')
        assert callable(source.close)

    def test_neo4j_source_has_close_method(self):
        """Test Neo4j source has close method."""
        source = Neo4jSource()
        assert hasattr(source, 'close')
        assert callable(source.close)

    def test_ray_source_has_close_method(self):
        """Test Ray source has close method."""
        source = RaySource()
        assert hasattr(source, 'close')
        assert callable(source.close)

    def test_valkey_source_has_close_method(self):
        """Test ValKey source has close method."""
        source = ValKeySource()
        assert hasattr(source, 'close')
        assert callable(source.close)

    def test_orchestrator_source_has_close_method(self):
        """Test Orchestrator source has close method."""
        source = OrchestratorSource()
        assert hasattr(source, 'close')
        assert callable(source.close)
