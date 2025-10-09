# Running Integration Tests with Podman

This guide explains how to run integration tests using **Podman** instead of Docker on your local machine with CRI-O.

## 🎯 Prerequisites

### 1. Podman Installed
```bash
# Check if Podman is installed
podman --version

# If not, install it (Arch Linux)
sudo pacman -S podman

# For other distros:
# Fedora/RHEL: sudo dnf install podman
# Ubuntu: sudo apt install podman
```

### 2. Podman Socket Service
Testcontainers needs the Podman socket to communicate with Podman:

```bash
# Enable and start Podman socket (user mode)
systemctl --user enable --now podman.socket

# Verify it's running
systemctl --user status podman.socket

# Check socket location
ls -la /run/user/$(id -u)/podman/podman.sock
```

### 3. Python Dependencies
```bash
pip install -e ".[grpc,integration]"
```

## 🚀 Running Tests

### Option 1: Automatic (Recommended)
The script detects Podman automatically and configures everything:

```bash
./scripts/run-integration-tests.sh
```

The script will:
1. ✅ Detect Podman
2. ✅ Build the image with Podman
3. ✅ Start Podman socket if needed
4. ✅ Configure Testcontainers
5. ✅ Run integration tests

### Option 2: Manual Steps

#### Step 1: Build the Image
```bash
podman build -t localhost:5000/swe-ai-fleet/orchestrator:latest \
  -f services/orchestrator/Dockerfile .
```

#### Step 2: Verify Socket
```bash
# Make sure Podman socket is running
systemctl --user start podman.socket

# Verify
podman info
```

#### Step 3: Run Tests with Environment Variables
```bash
# Set environment variables for Testcontainers
export DOCKER_HOST="unix:///run/user/$(id -u)/podman/podman.sock"
export TESTCONTAINERS_RYUK_DISABLED="true"

# Run tests
pytest tests/integration/services/orchestrator/ -v -m integration
```

### Option 3: Run Specific Test
```bash
export DOCKER_HOST="unix:///run/user/$(id -u)/podman/podman.sock"
export TESTCONTAINERS_RYUK_DISABLED="true"

pytest tests/integration/services/orchestrator/test_grpc_integration.py::TestDeliberateIntegration::test_deliberate_full_flow -v
```

## 🔧 Configuration

### Environment Variables for Podman

The tests automatically configure these when Podman is detected:

```bash
# Point Testcontainers to Podman socket
DOCKER_HOST="unix:///run/user/$(id -u)/podman/podman.sock"

# Disable Ryuk (cleanup container that doesn't work well with Podman)
TESTCONTAINERS_RYUK_DISABLED="true"
```

### Podman Socket Location

Different locations depending on your setup:

- **User mode (rootless)**: `/run/user/$(id -u)/podman/podman.sock`
- **System mode (root)**: `/run/podman/podman.sock`

We use **user mode** (rootless) for better security.

## 🐛 Troubleshooting

### Issue: "No such file or directory: /run/user/.../podman.sock"

**Solution**: Start the Podman socket service
```bash
systemctl --user start podman.socket
systemctl --user enable podman.socket  # Start on boot
```

### Issue: "Permission denied" accessing socket

**Solution**: Check socket permissions
```bash
ls -la /run/user/$(id -u)/podman/podman.sock

# Should show something like:
# srw-rw----. 1 user user 0 ... podman.sock
```

If permissions are wrong:
```bash
systemctl --user restart podman.socket
```

### Issue: Tests hang or timeout

**Possible causes:**
1. Podman socket not responding
2. Image not built
3. Port conflicts

**Debug steps:**
```bash
# Check if Podman is working
podman ps

# Check socket
podman --remote info

# Check running containers
podman ps -a

# Check logs
journalctl --user -u podman.socket -n 50
```

### Issue: "Image not found"

**Solution**: Build the image first
```bash
podman build -t localhost:5000/swe-ai-fleet/orchestrator:latest \
  -f services/orchestrator/Dockerfile .

# Verify image exists
podman images | grep orchestrator
```

### Issue: Container fails to start

**Check container logs:**
```bash
# List all containers (including stopped)
podman ps -a

# Get logs from failed container
podman logs <container_id>
```

### Issue: Testcontainers can't find Podman

**Solution**: Set DOCKER_HOST manually before running tests
```bash
export DOCKER_HOST="unix:///run/user/$(id -u)/podman/podman.sock"
pytest tests/integration/services/orchestrator/ -v
```

## 📊 Podman vs Docker Differences

### What Works the Same
- ✅ Container images
- ✅ Building images
- ✅ Running containers
- ✅ Port mapping
- ✅ Environment variables
- ✅ Volume mounts

### Podman-Specific Features
- ✅ **Rootless by default** - Better security
- ✅ **No daemon** - Containers run as child processes
- ✅ **Systemd integration** - Can run as systemd services
- ✅ **CRI-O compatible** - Native Kubernetes support

### Known Limitations
- ⚠️ **Ryuk disabled** - Testcontainers' cleanup container doesn't work
  - Solution: Tests clean up containers manually in fixtures
- ⚠️ **Socket required** - Must have podman.socket running
  - Solution: Script auto-starts the socket

## 🔍 Verifying Setup

Run this checklist to verify everything is configured:

```bash
# 1. Check Podman is installed
podman --version
# Expected: podman version 4.x or higher

# 2. Check socket is running
systemctl --user is-active podman.socket
# Expected: active

# 3. Check socket location
ls -la /run/user/$(id -u)/podman/podman.sock
# Expected: srw-rw---- ... podman.sock

# 4. Check Podman API works
podman --remote info
# Expected: info output without errors

# 5. Check image exists
podman images | grep orchestrator
# Expected: localhost:5000/swe-ai-fleet/orchestrator

# 6. Try to run container
podman run --rm localhost:5000/swe-ai-fleet/orchestrator:latest echo "test"
# Expected: should fail (no echo command) but container should start
```

If all checks pass, you're ready to run tests!

## 🎓 Best Practices with Podman

### 1. Use Rootless Mode (Default)
```bash
# Always use user socket (more secure)
systemctl --user enable podman.socket
```

### 2. Clean Up Regularly
```bash
# Remove stopped containers
podman container prune -f

# Remove unused images
podman image prune -f

# Remove all (careful!)
podman system prune -a -f
```

### 3. Monitor Resources
```bash
# Check resource usage
podman stats --no-stream

# Check disk usage
podman system df
```

### 4. Enable Socket on Boot
```bash
# Make sure socket starts when you log in
systemctl --user enable podman.socket
loginctl enable-linger $(whoami)  # Keep user services running
```

## 📚 Additional Resources

- [Podman Documentation](https://docs.podman.io/)
- [Testcontainers with Podman](https://www.testcontainers.org/supported_docker_environment/podman/)
- [Podman vs Docker](https://podman.io/whatis.html)
- [Rootless Containers](https://rootlesscontaine.rs/)

## 💡 Quick Reference

```bash
# Build image
podman build -t localhost:5000/swe-ai-fleet/orchestrator:latest -f services/orchestrator/Dockerfile .

# Run tests (automatic)
./scripts/run-integration-tests.sh

# Run tests (manual)
export DOCKER_HOST="unix:///run/user/$(id -u)/podman/podman.sock"
export TESTCONTAINERS_RYUK_DISABLED="true"
pytest tests/integration/services/orchestrator/ -v -m integration

# Debug
podman ps -a                    # List containers
podman logs <container_id>      # View logs
podman inspect <container_id>   # Inspect container
systemctl --user status podman.socket  # Check socket status
```

