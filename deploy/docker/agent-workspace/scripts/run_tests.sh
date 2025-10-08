#!/bin/bash
# Helper script to run tests in agent workspace

set -e

echo "=== Running Tests ==="

# Detect project type and run appropriate tests
if [ -f "go.mod" ]; then
    echo "Go project detected"
    go test -v -coverprofile=coverage.out ./...
    go tool cover -func=coverage.out
elif [ -f "package.json" ]; then
    echo "Node.js project detected"
    npm test -- --coverage
elif [ -f "pyproject.toml" ] || [ -f "setup.py" ]; then
    echo "Python project detected"
    pytest --cov --cov-report=xml --cov-report=term
elif [ -f "Cargo.toml" ]; then
    echo "Rust project detected"
    cargo test
else
    echo "Unknown project type"
    exit 1
fi

echo "=== Tests Complete ==="



