# Orchestrator Integration Tests

Integration tests for the Orchestrator microservice using **Testcontainers** to run the actual service in Docker.

## 🎯 What These Tests Do

These tests:
- ✅ Spin up the **real Orchestrator service** in a Docker container
- ✅ Test actual gRPC communication over the network
- ✅ Verify all RPC methods work end-to-end
- ✅ Test concurrent requests and error scenarios
- ✅ Validate the complete service behavior

## 📋 Prerequisites

### Required
1. **Docker** - Must be installed and running
   ```bash
   docker --version
   docker info
   ```

2. **Python dependencies**
   ```bash
   pip install -e ".[grpc,integration]"
   ```

3. **Docker image** - Built Orchestrator service image
   ```bash
   docker build -t localhost:5000/swe-ai-fleet/orchestrator:latest \
     -f services/orchestrator/Dockerfile .
   ```

## 🚀 Running the Tests

### Option 1: Quick Run (Build + Test)
```bash
# Build image and run tests in one command
./scripts/run-integration-tests.sh
```

### Option 2: Manual Steps
```bash
# 1. Build the Docker image
docker build -t localhost:5000/swe-ai-fleet/orchestrator:latest \
  -f services/orchestrator/Dockerfile .

# 2. Run integration tests
pytest tests/integration/services/orchestrator/ -v -m integration

# 3. With coverage
pytest tests/integration/services/orchestrator/ \
  -v -m integration \
  --cov=services.orchestrator \
  --cov-report=html
```

### Option 3: Run specific test
```bash
pytest tests/integration/services/orchestrator/test_grpc_integration.py::TestDeliberateIntegration::test_deliberate_full_flow -v
```

## 📊 Test Structure

```
tests/integration/services/orchestrator/
├── conftest.py                    # Test configuration
├── test_grpc_integration.py       # Main integration tests
└── README.md                      # This file
```

### Test Classes

#### `TestDeliberateIntegration`
- `test_deliberate_full_flow` - Complete deliberation workflow
- `test_deliberate_multiple_roles` - Test different agent roles
- `test_deliberate_invalid_role` - Error handling for invalid roles
- `test_deliberate_with_custom_rounds` - Multi-round peer review

#### `TestOrchestrateIntegration`
- `test_orchestrate_full_flow` - End-to-end orchestration
- `test_orchestrate_with_options` - Custom orchestration options

#### `TestGetStatusIntegration`
- `test_get_status_basic` - Basic health check
- `test_get_status_with_stats` - Status with statistics
- `test_get_status_repeated_calls` - Multiple status calls

#### `TestConcurrentRequests`
- `test_concurrent_deliberations` - Parallel deliberation requests
- `test_mixed_concurrent_requests` - Mixed request types

#### `TestErrorHandling`
- `test_empty_task_description` - Edge case testing
- `test_large_task_description` - Stress testing
- `test_many_requirements` - Load testing

## 🔍 How Testcontainers Works

1. **Container Lifecycle**
   ```python
   @pytest.fixture(scope="module")
   def orchestrator_container():
       container = DockerContainer("localhost:5000/swe-ai-fleet/orchestrator:latest")
       container.start()  # Starts container
       yield container
       container.stop()   # Cleanup after tests
   ```

2. **Port Mapping**
   - Service runs on port `50055` inside container
   - Testcontainers maps it to a random host port
   - Tests connect via: `host:mapped_port`

3. **Waiting for Service**
   - Waits for log message: `"Orchestrator Service listening on port"`
   - Ensures service is fully started before testing
   - Timeout: 30 seconds

4. **gRPC Channel**
   - Creates real gRPC channel to containerized service
   - Waits for channel to be ready
   - Automatically cleans up after tests

## 🐛 Troubleshooting

### Docker Not Available
```
SKIPPED [1] Docker is not available
```
**Solution**: Start Docker daemon
```bash
sudo systemctl start docker
```

### Image Not Found
```
SKIPPED [1] Docker image 'localhost:5000/swe-ai-fleet/orchestrator:latest' not found
```
**Solution**: Build the image
```bash
docker build -t localhost:5000/swe-ai-fleet/orchestrator:latest \
  -f services/orchestrator/Dockerfile .
```

### Container Fails to Start
**Check logs:**
```bash
docker ps -a  # Find container ID
docker logs <container_id>
```

**Common issues:**
- Missing dependencies in `requirements.txt`
- Python path issues in Dockerfile
- Port already in use

### Tests Timeout
**Increase timeout in conftest.py:**
```python
wait_for_logs(container, "...", timeout=60)  # Increase from 30
```

### gRPC Connection Refused
**Check if container is running:**
```bash
docker ps | grep orchestrator
```

**Check container logs:**
```bash
docker logs <container_id>
```

## 📈 Performance

**Typical execution times:**
- Container startup: 5-10 seconds
- Per test: 100-500ms
- Full suite: 30-60 seconds

**Container resources:**
- Memory: ~512Mi
- CPU: 0.5-1.0 cores

## 🔐 Security

Integration tests use the same security settings as production:
- ✅ Non-root user (UID 1000)
- ✅ Read-only root filesystem (where possible)
- ✅ No privilege escalation
- ✅ Limited capabilities

## 📝 Adding New Tests

1. **Add test method** to appropriate test class
2. **Use fixtures**: `orchestrator_stub` for gRPC calls
3. **Mark as integration**: Automatically done via `pytestmark`
4. **Follow naming**: `test_<feature>_<scenario>`

Example:
```python
class TestNewFeature:
    """Test new feature."""
    
    def test_new_feature_success(self, orchestrator_stub):
        """Test successful execution of new feature."""
        from services.orchestrator.gen import orchestrator_pb2
        
        request = orchestrator_pb2.NewFeatureRequest(...)
        response = orchestrator_stub.NewFeature(request)
        
        assert response is not None
        assert response.status == "success"
```

## 🔗 Related Documentation

- [Orchestrator Service README](../../../../services/orchestrator/README.md)
- [Unit Tests](../../../unit/services/orchestrator/)
- [Testcontainers Python Docs](https://testcontainers-python.readthedocs.io/)

## 💡 Best Practices

1. **Scope fixtures at module level** - Reuse container across tests
2. **Wait for readiness** - Don't assume instant startup
3. **Test real scenarios** - Integration tests should be realistic
4. **Clean up resources** - Fixtures handle this automatically
5. **Use appropriate timeouts** - Network calls can be slow

