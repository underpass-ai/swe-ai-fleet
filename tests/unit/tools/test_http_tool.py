"""Unit tests for http_tool.py coverage - HTTP client operations."""

import json
from unittest.mock import Mock, patch

import pytest
from core.agents_and_tools.tools.http_tool import HttpTool

# =============================================================================
# URL Validation Tests
# =============================================================================

class TestHttpToolUrlValidation:
    """Test URL validation logic."""

    def test_rejects_url_without_scheme(self):
        """Should reject URLs without scheme."""
        tool = HttpTool.create()
        
        with pytest.raises(ValueError, match="URL must have scheme"):
            tool._validate_url("example.com/api")

    def test_rejects_invalid_scheme(self):
        """Should reject non-http/https schemes."""
        tool = HttpTool.create()
        
        with pytest.raises(ValueError, match="Only http:// and https:// schemes allowed"):
            tool._validate_url("ftp://example.com")

    def test_rejects_localhost_by_default(self):
        """Should reject localhost URLs by default."""
        tool = HttpTool.create()
        
        with pytest.raises(ValueError, match="Requests to localhost are not allowed"):
            tool._validate_url("http://localhost:8080/api")

    def test_rejects_127_0_0_1_by_default(self):
        """Should reject 127.0.0.1 URLs by default."""
        tool = HttpTool.create()
        
        with pytest.raises(ValueError, match="Requests to 127.0.0.1 are not allowed"):
            tool._validate_url("http://127.0.0.1:8000")

    def test_allows_localhost_when_enabled(self):
        """Should allow localhost when allow_localhost=True."""
        tool = HttpTool(allow_localhost=True)
        
        # Should not raise
        assert tool._validate_url("http://localhost:8080/api") is True

    def test_allows_valid_http_url(self):
        """Should allow valid HTTP URLs."""
        tool = HttpTool.create()
        
        assert tool._validate_url("http://api.example.com/v1/users") is True

    def test_allows_valid_https_url(self):
        """Should allow valid HTTPS URLs."""
        tool = HttpTool.create()
        
        assert tool._validate_url("https://secure.example.com") is True


# =============================================================================
# HTTP Request Tests
# =============================================================================

class TestHttpToolRequest:
    """Test HTTP request method."""

    @patch('core.agents_and_tools.tools.http_tool.requests')
    def test_makes_successful_get_request(self, mock_requests_module):
        """Should make successful GET request."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.content = b'{"key": "value"}'
        mock_response.json.return_value = {"key": "value"}
        mock_session.request.return_value = mock_response
        mock_requests_module.Session.return_value = mock_session

        tool = HttpTool.create()
        result = tool.request("GET", "https://api.example.com/data")

        assert result.success is True
        assert result.status_code == 200
        assert result.body == {"key": "value"}
        assert result.method == "GET"

    @patch('core.agents_and_tools.tools.http_tool.requests')
    def test_makes_post_request_with_json(self, mock_requests_module):
        """Should make POST request with JSON data."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {}
        mock_response.content = b'created'
        mock_response.json.side_effect = json.JSONDecodeError("", "", 0)
        mock_response.text = "created"
        mock_session.request.return_value = mock_response
        mock_requests_module.Session.return_value = mock_session

        tool = HttpTool.create()
        result = tool.request(
            "POST",
            "https://api.example.com/users",
            json_data={"name": "Alice"},
        )

        assert result.success is True
        assert result.status_code == 201
        assert result.body == "created"  # Falls back to text

        # Verify JSON was passed
        call_kwargs = mock_session.request.call_args[1]
        assert call_kwargs["json"] == {"name": "Alice"}

    @patch('core.agents_and_tools.tools.http_tool.requests')
    def test_makes_request_with_headers(self, mock_requests_module):
        """Should include custom headers in request."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b''
        mock_response.json.side_effect = json.JSONDecodeError("", "", 0)
        mock_response.text = ""
        mock_session.request.return_value = mock_response
        mock_requests_module.Session.return_value = mock_session

        tool = HttpTool.create()
        tool.request(
            "GET",
            "https://api.example.com",
            headers={"Authorization": "Bearer token123"},
        )

        call_kwargs = mock_session.request.call_args[1]
        assert call_kwargs["headers"] == {"Authorization": "Bearer token123"}

    @patch('core.agents_and_tools.tools.http_tool.requests')
    def test_makes_request_with_basic_auth(self, mock_requests_module):
        """Should include basic auth in request."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b''
        mock_response.json.side_effect = json.JSONDecodeError("", "", 0)
        mock_response.text = ""
        mock_session.request.return_value = mock_response
        mock_requests_module.Session.return_value = mock_session

        tool = HttpTool.create()
        tool.request(
            "GET",
            "https://api.example.com",
            auth=("user", "pass"),
        )

        call_kwargs = mock_session.request.call_args[1]
        assert call_kwargs["auth"] == ("user", "pass")

    @patch('core.agents_and_tools.tools.http_tool.requests')
    def test_handles_4xx_errors(self, mock_requests_module):
        """Should mark 4xx responses as unsuccessful."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.headers = {}
        mock_response.content = b'Not Found'
        mock_response.json.side_effect = json.JSONDecodeError("", "", 0)
        mock_response.text = "Not Found"
        mock_session.request.return_value = mock_response
        mock_requests_module.Session.return_value = mock_session

        tool = HttpTool.create()
        result = tool.request("GET", "https://api.example.com/missing")

        assert result.success is False
        assert result.status_code == 404

    @patch('core.agents_and_tools.tools.http_tool.requests')
    def test_handles_timeout_error(self, mock_requests_module):
        """Should handle request timeouts."""
        # Create real exception classes
        class MockTimeout(Exception):
            pass
        
        mock_exceptions = Mock()
        mock_exceptions.Timeout = MockTimeout
        mock_exceptions.RequestException = Exception
        mock_requests_module.exceptions = mock_exceptions
        
        mock_session = Mock()
        mock_session.request.side_effect = MockTimeout("Timeout")
        mock_requests_module.Session.return_value = mock_session

        tool = HttpTool.create()
        result = tool.request("GET", "https://slow.example.com", timeout=5)

        assert result.success is False
        assert "timed out after 5 seconds" in result.error

    @patch('core.agents_and_tools.tools.http_tool.requests')
    def test_handles_connection_error(self, mock_requests_module):
        """Should handle connection errors."""
        # Create real exception classes that don't inherit from each other
        class MockTimeout(Exception):
            pass
        
        class MockRequestException(Exception):
            pass
        
        mock_exceptions = Mock()
        mock_exceptions.Timeout = MockTimeout
        mock_exceptions.RequestException = MockRequestException
        mock_requests_module.exceptions = mock_exceptions
        
        mock_session = Mock()
        mock_session.request.side_effect = MockRequestException("Failed")
        mock_requests_module.Session.return_value = mock_session

        tool = HttpTool.create()
        result = tool.request("GET", "https://down.example.com")

        assert result.success is False
        assert "Request failed" in result.error

    @patch('core.agents_and_tools.tools.http_tool.requests')
    def test_rejects_oversized_request(self, mock_requests_module):
        """Should reject requests larger than MAX_REQUEST_SIZE."""
        mock_session = Mock()
        mock_requests_module.Session.return_value = mock_session

        tool = HttpTool.create()
        
        # Create a large JSON payload
        large_data = {"data": "x" * (tool.MAX_REQUEST_SIZE + 1)}
        
        result = tool.request("POST", "https://api.example.com", json_data=large_data)

        assert result.success is False
        assert "Request body too large" in result.error


# =============================================================================
# HTTP Method Shortcuts Tests
# =============================================================================

class TestHttpToolMethodShortcuts:
    """Test HTTP method shortcut methods."""

    @patch('core.agents_and_tools.tools.http_tool.requests')
    def test_get_shortcut(self, mock_requests_module):
        """Should call request() with GET method."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b''
        mock_response.json.side_effect = json.JSONDecodeError("", "", 0)
        mock_response.text = ""
        mock_session.request.return_value = mock_response
        mock_requests_module.Session.return_value = mock_session

        tool = HttpTool.create()
        result = tool.get("https://api.example.com")

        assert result.method == "GET"
        assert mock_session.request.call_args[1]["method"] == "GET"

    @patch('core.agents_and_tools.tools.http_tool.requests')
    def test_post_shortcut(self, mock_requests_module):
        """Should call request() with POST method."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {}
        mock_response.content = b''
        mock_response.json.side_effect = json.JSONDecodeError("", "", 0)
        mock_response.text = ""
        mock_session.request.return_value = mock_response
        mock_requests_module.Session.return_value = mock_session

        tool = HttpTool.create()
        result = tool.post("https://api.example.com", json_data={"test": 1})

        assert result.method == "POST"

    @patch('core.agents_and_tools.tools.http_tool.requests')
    def test_put_shortcut(self, mock_requests_module):
        """Should call request() with PUT method."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b''
        mock_response.json.side_effect = json.JSONDecodeError("", "", 0)
        mock_response.text = ""
        mock_session.request.return_value = mock_response
        mock_requests_module.Session.return_value = mock_session

        tool = HttpTool.create()
        result = tool.put("https://api.example.com/resource")

        assert result.method == "PUT"

    @patch('core.agents_and_tools.tools.http_tool.requests')
    def test_delete_shortcut(self, mock_requests_module):
        """Should call request() with DELETE method."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.headers = {}
        mock_response.content = b''
        mock_response.json.side_effect = json.JSONDecodeError("", "", 0)
        mock_response.text = ""
        mock_session.request.return_value = mock_response
        mock_requests_module.Session.return_value = mock_session

        tool = HttpTool.create()
        result = tool.delete("https://api.example.com/resource/123")

        assert result.method == "DELETE"


# =============================================================================
# Audit Callback Tests
# =============================================================================

class TestHttpToolAuditCallback:
    """Test audit callback functionality."""

    @patch('core.agents_and_tools.tools.http_tool.requests')
    def test_calls_audit_callback_on_success(self, mock_requests_module):
        """Should call audit callback with request details."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b''
        mock_response.json.side_effect = json.JSONDecodeError("", "", 0)
        mock_response.text = ""
        mock_session.request.return_value = mock_response
        mock_requests_module.Session.return_value = mock_session

        audit_callback = Mock()
        tool = HttpTool.create(audit_callback=audit_callback)
        
        tool.get("https://api.example.com/test")

        audit_callback.assert_called_once()
        call_args = audit_callback.call_args[0][0]
        
        assert call_args["tool"] == "http"
        assert call_args["operation"] == "GET"
        assert call_args["params"]["url"] == "https://api.example.com/test"
        assert call_args["success"] is True
        assert call_args["metadata"]["status_code"] == 200


# =============================================================================
# Execute Method Tests
# =============================================================================

class TestHttpToolExecute:
    """Test execute() method."""

    @patch('core.agents_and_tools.tools.http_tool.requests')
    def test_executes_get_by_name(self, mock_requests_module):
        """Should execute GET via execute() method."""
        mock_session = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.content = b''
        mock_response.json.side_effect = json.JSONDecodeError("", "", 0)
        mock_response.text = ""
        mock_session.request.return_value = mock_response
        mock_requests_module.Session.return_value = mock_session

        tool = HttpTool.create()
        result = tool.execute(operation="get", url="https://api.example.com")

        assert result.success is True
        assert result.method == "GET"

    def test_execute_raises_on_invalid_operation(self):
        """Should raise ValueError for unsupported operation."""
        tool = HttpTool.create()
        
        with pytest.raises(ValueError, match="Unknown HTTP operation"):
            tool.execute(operation="invalid")


# =============================================================================
# Summarize and Collect Artifacts Tests
# =============================================================================

class TestHttpToolSummarizeAndCollect:
    """Test summarize_result and collect_artifacts methods."""

    def test_summarize_result_with_status_code(self):
        """Should summarize result with status code."""
        tool = HttpTool.create()
        
        # Create a mock result with metadata
        mock_result = Mock()
        mock_result.metadata = {"status_code": 200}
        
        summary = tool.summarize_result("get", mock_result, {})
        
        assert "HTTP 200" in summary

    def test_summarize_result_without_metadata(self):
        """Should handle result without metadata."""
        tool = HttpTool.create()
        
        # Create a mock result without metadata
        mock_result = Mock()
        mock_result.metadata = None
        
        summary = tool.summarize_result("get", mock_result, {})
        
        assert "HTTP request completed" in summary

    def test_collect_artifacts_with_metadata(self):
        """Should collect artifacts with metadata."""
        tool = HttpTool.create()
        
        # Create a mock result with metadata
        mock_result = Mock()
        mock_result.metadata = {
            "status_code": 200,
            "url": "https://api.example.com"
        }
        
        artifacts = tool.collect_artifacts("get", mock_result, {})
        
        assert isinstance(artifacts, dict)
        assert artifacts["http_status"] == 200
        assert artifacts["http_url"] == "https://api.example.com"

    def test_collect_artifacts_without_metadata(self):
        """Should handle result without metadata."""
        tool = HttpTool.create()
        
        # Create a mock result without metadata
        mock_result = Mock()
        mock_result.metadata = None
        
        artifacts = tool.collect_artifacts("get", mock_result, {})
        
        assert isinstance(artifacts, dict)
        assert artifacts == {}

