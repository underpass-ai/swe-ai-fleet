"""
HTTP client tool for REST API interactions from agent workspace.

Supports GET, POST, PUT, PATCH, DELETE with authentication and validation.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    requests = None  # Will be handled in __init__


HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"]


@dataclass
class HttpResult:
    """Result of an HTTP request."""

    success: bool
    method: HttpMethod
    url: str
    status_code: int | None
    headers: dict[str, str] | None
    body: str | dict | None
    metadata: dict[str, Any]
    error: str | None = None


class HttpTool:
    """
    HTTP client tool for REST API interactions.

    Security:
    - URL validation (no localhost unless explicitly allowed)
    - Request size limits
    - Timeout protection
    - No credential logging
    - Audit trail of all requests
    """

    MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
    DEFAULT_TIMEOUT = 30  # seconds

    @staticmethod
    def create(audit_callback: Callable | None = None) -> "HttpTool":
        """Factory method to create HttpTool instance."""
        return HttpTool(audit_callback)

    def __init__(
        self,
        audit_callback: Callable | None = None,
        allow_localhost: bool = False,
    ):
        """
        Initialize HTTP tool.

        Args:
            audit_callback: Optional callback for audit logging
            allow_localhost: Allow requests to localhost/127.0.0.1
        """
        if requests is None:
            raise ImportError(
                "requests library not installed. Install with: pip install requests"
            )

        self.audit_callback = audit_callback
        self.allow_localhost = allow_localhost
        self.session = requests.Session()

    def _audit(self, method: str, url: str, result: HttpResult) -> None:
        """Log HTTP request to audit trail."""
        if self.audit_callback:
            self.audit_callback(
                {
                    "tool": "http",
                    "operation": method,
                    "params": {"url": url},
                    "success": result.success,
                    "metadata": {"status_code": result.status_code, "method": method},
                }
            )

    def _validate_url(self, url: str) -> bool:
        """
        Validate URL for security.

        Args:
            url: URL to validate

        Returns:
            True if valid

        Raises:
            ValueError: If URL is invalid or forbidden
        """
        parsed = urlparse(url)

        # Must have scheme
        if not parsed.scheme:
            raise ValueError("URL must have scheme (http:// or https://)")

        # Only http/https allowed
        if parsed.scheme not in ["http", "https"]:
            raise ValueError(f"Only http:// and https:// schemes allowed, got: {parsed.scheme}")

        # Check localhost restrictions
        if not self.allow_localhost:
            forbidden_hosts = ["localhost", "127.0.0.1", "0.0.0.0", "::1"]
            if parsed.hostname in forbidden_hosts:
                raise ValueError(
                    f"Requests to {parsed.hostname} are not allowed. "
                    "Set allow_localhost=True if needed."
                )

        return True

    def request(
        self,
        method: HttpMethod,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        json_data: dict | None = None,
        data: str | None = None,
        auth: tuple[str, str] | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> HttpResult:
        """
        Make HTTP request.

        Args:
            method: HTTP method
            url: Target URL
            headers: Request headers
            params: URL query parameters
            json_data: JSON request body (dict)
            data: Raw request body (string)
            auth: Basic auth tuple (username, password)
            timeout: Timeout in seconds

        Returns:
            HttpResult with response data
        """
        try:
            # Validate URL
            self._validate_url(url)

            # Validate request size
            if json_data and len(json.dumps(json_data)) > self.MAX_REQUEST_SIZE:
                return HttpResult(
                    success=False,
                    method=method,
                    url=url,
                    status_code=None,
                    headers=None,
                    body=None,
                    metadata={},
                    error=f"Request body too large (max: {self.MAX_REQUEST_SIZE} bytes)",
                )

            # Make request
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                data=data,
                auth=auth,
                timeout=timeout,
            )

            # Try to parse JSON response
            try:
                body = response.json()
            except json.JSONDecodeError:
                body = response.text

            http_result = HttpResult(
                success=response.status_code < 400,
                method=method,
                url=url,
                status_code=response.status_code,
                headers=dict(response.headers),
                body=body,
                metadata={
                    "method": method,
                    "status_code": response.status_code,
                    "content_type": response.headers.get("Content-Type"),
                    "size": len(response.content),
                },
            )

            self._audit(method, url, http_result)
            return http_result

        except requests.exceptions.Timeout:
            return HttpResult(
                success=False,
                method=method,
                url=url,
                status_code=None,
                headers=None,
                body=None,
                metadata={"timeout": timeout},
                error=f"Request timed out after {timeout} seconds",
            )
        except requests.exceptions.RequestException as e:
            return HttpResult(
                success=False,
                method=method,
                url=url,
                status_code=None,
                headers=None,
                body=None,
                metadata={},
                error=f"Request failed: {e}",
            )
        except Exception as e:
            return HttpResult(
                success=False,
                method=method,
                url=url,
                status_code=None,
                headers=None,
                body=None,
                metadata={},
                error=f"Error making request: {e}",
            )

    def get(self, url: str, **kwargs: Any) -> HttpResult:
        """GET request."""
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> HttpResult:
        """POST request."""
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> HttpResult:
        """PUT request."""
        return self.request("PUT", url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> HttpResult:
        """PATCH request."""
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> HttpResult:
        """DELETE request."""
        return self.request("DELETE", url, **kwargs)

    def head(self, url: str, **kwargs: Any) -> HttpResult:
        """HEAD request."""
        return self.request("HEAD", url, **kwargs)

    def get_operations(self) -> dict[str, Any]:
        """Return dictionary mapping operation names to method callables."""
        return {
            "get": self.get,
            "post": self.post,
            "put": self.put,
            "patch": self.patch,
            "delete": self.delete,
            "head": self.head,
        }

    def execute(self, operation: str, **params: Any) -> HttpResult:
        """
        Execute an HTTP operation by name.

        Args:
            operation: Name of the operation
            **params: Operation parameters

        Returns:
            HttpResult

        Raises:
            ValueError: If operation is not supported
        """
        operations = self.get_operations()
        method = operations.get(operation)
        if not method:
            raise ValueError(f"Unknown HTTP operation: {operation}")
        return method(**params)

    def _get_mapper(self):
        """Return the mapper for HttpTool results."""
        from core.agents_and_tools.agents.infrastructure.mappers.http_result_mapper import HttpResultMapper
        return HttpResultMapper()


# Convenience function for use in agent tasks
def execute_http_request(
    method: HttpMethod,
    url: str,
    allow_localhost: bool = False,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Execute HTTP request from agent workspace.

    Args:
        method: HTTP method
        url: Target URL
        allow_localhost: Allow requests to localhost
        **kwargs: Request parameters (headers, json_data, etc.)

    Returns:
        Dictionary with request result

    Examples:
        # GET request
        result = execute_http_request("GET", "https://api.example.com/users")

        # POST request with JSON
        result = execute_http_request(
            "POST",
            "https://api.example.com/users",
            json_data={"name": "John", "email": "john@example.com"},
            headers={"Authorization": "Bearer token123"}
        )
    """
    tool = HttpTool(allow_localhost=allow_localhost)
    result = tool.request(method, url, **kwargs)

    return {
        "success": result.success,
        "method": result.method,
        "url": result.url,
        "status_code": result.status_code,
        "headers": result.headers,
        "body": result.body,
        "metadata": result.metadata,
        "error": result.error,
    }

