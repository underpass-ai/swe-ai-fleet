# Development Guide

This guide provides comprehensive information for developers who want to contribute to SWE AI Fleet. It covers setting up the development environment, understanding the codebase, and contributing to the project.

## 🚀 Development Environment Setup

### Prerequisites

- **Python 3.13+** - The project requires Python 3.13 or higher
- **Git** - For version control
- **Docker** - For containerized services
- **Make** - For build automation (optional but recommended)

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/tgarciai/swe-ai-fleet.git
cd swe-ai-fleet

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e .
pip install -r requirements-dev.txt
```

### 2. Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality:

```bash
# Install pre-commit hooks
pre-commit install

# Run pre-commit on all files
pre-commit run --all-files
```

### 3. Development Tools

Install additional development tools:

```bash
# Install development tools
pip install black isort mypy pytest pytest-cov pytest-mock

# Install linting tools
pip install ruff flake8 bandit
```

## 🏗️ Project Structure

### Directory Layout

```
swe_ai_fleet/
├── src/swe_ai_fleet/           # Main source code
│   ├── __init__.py             # Package initialization
│   ├── agents/                 # AI agent implementations
│   ├── cli/                    # Command-line interface
│   ├── context/                # Context management
│   ├── evaluators/             # Agent evaluation
│   ├── memory/                 # Memory management
│   ├── models/                 # Data models
│   ├── orchestrator/           # Multi-agent orchestration
│   ├── reports/                # Reporting and analytics
│   └── tools/                  # Tool wrappers
├── tests/                      # Test suite
├── examples/                   # Example configurations
├── docs/                       # Documentation
├── deploy/                     # Deployment manifests
├── scripts/                    # Utility scripts
├── config/                     # Configuration files
└── .github/                    # GitHub workflows
```

### Key Components

#### 1. Agents (`src/swe_ai_fleet/agents/`)

The agents directory contains role-based AI agent implementations:

- **Base Agent**: Abstract base class for all agents
- **Role-specific Agents**: Developer, DevOps, QA, Architect agents
- **Agent Factory**: Creates and configures agents

#### 2. Orchestrator (`src/swe_ai_fleet/orchestrator/`)

Manages multi-agent coordination:

- **Task Scheduler**: Assigns tasks to appropriate agents
- **Agent Manager**: Handles agent lifecycle
- **Workflow Engine**: Coordinates complex workflows

#### 3. Tools (`src/swe_ai_fleet/tools/`)

Safe wrappers for external tools:

- **Git Tools**: Version control operations
- **Docker Tools**: Container management
- **Kubernetes Tools**: Cluster operations
- **Database Tools**: Database interactions

#### 4. Memory (`src/swe_ai_fleet/memory/`)

Knowledge management system:

- **Redis Manager**: Short-term memory
- **Neo4j Manager**: Long-term knowledge graph
- **Memory Interface**: Abstract memory operations

## 🔧 Development Workflow

### 1. Code Style and Standards

The project follows strict coding standards:

#### Python Style Guide

- **PEP 8**: Python style guide compliance
- **Type Hints**: Full type annotation support
- **Docstrings**: Google-style docstrings
- **Line Length**: 110 characters maximum

#### Code Quality Tools

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint code
ruff check src/ tests/
flake8 src/ tests/

# Type checking
mypy src/

# Security scanning
bandit -r src/
```

### 2. Testing Strategy

#### Test Structure

```
tests/
├── unit/                    # Unit tests
├── integration/            # Integration tests
├── e2e/                    # End-to-end tests
├── fixtures/               # Test fixtures
└── conftest.py             # Pytest configuration
```

#### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Run with coverage
pytest --cov=swe_ai_fleet --cov-report=html

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_agents.py
```

#### Test Writing Guidelines

- **Test Naming**: Use descriptive test names
- **Test Isolation**: Each test should be independent
- **Mocking**: Use mocks for external dependencies
- **Fixtures**: Use pytest fixtures for common setup

Example test:

```python
import pytest
from unittest.mock import Mock, patch
from swe_ai_fleet.agents import DeveloperAgent

class TestDeveloperAgent:
    @pytest.fixture
    def agent(self):
        return DeveloperAgent(name="test-dev", role="developer")
    
    def test_agent_initialization(self, agent):
        assert agent.name == "test-dev"
        assert agent.role == "developer"
    
    @patch('swe_ai_fleet.tools.git.GitTool')
    def test_git_operations(self, mock_git_tool, agent):
        mock_git_tool.return_value.clone.return_value = True
        result = agent.clone_repository("https://github.com/test/repo")
        assert result is True
```

### 3. Documentation Standards

#### Code Documentation

- **Docstrings**: Every public function/class must have docstrings
- **Type Hints**: Use type hints for all function parameters and return values
- **Examples**: Include usage examples in docstrings

Example:

```python
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class Task:
    """Represents a task to be executed by an agent.
    
    Attributes:
        id: Unique task identifier
        description: Human-readable task description
        agent_type: Type of agent required for this task
        priority: Task priority (1=highest, 5=lowest)
        dependencies: List of task IDs this task depends on
    """
    id: str
    description: str
    agent_type: str
    priority: int = 3
    dependencies: Optional[List[str]] = None
    
    def __post_init__(self):
        """Validate task configuration after initialization."""
        if not 1 <= self.priority <= 5:
            raise ValueError("Priority must be between 1 and 5")
        if self.dependencies is None:
            self.dependencies = []
```

#### API Documentation

- **OpenAPI/Swagger**: API endpoints should be documented
- **Examples**: Include request/response examples
- **Error Codes**: Document all possible error responses

## 🚀 Development Commands

### Makefile Commands

The project includes a Makefile for common development tasks:

```bash
# Install dependencies
make install

# Run tests
make test

# Run linting
make lint

# Format code
make format

# Build package
make build

# Clean build artifacts
make clean

# Start development services
make dev-start

# Stop development services
make dev-stop
```

### Manual Commands

```bash
# Install in development mode
pip install -e .

# Run specific test with coverage
pytest tests/unit/test_agents.py --cov=swe_ai_fleet.agents --cov-report=term-missing

# Check code quality
ruff check src/ --output-format=text

# Format specific files
black src/swe_ai_fleet/agents/
isort src/swe_ai_fleet/agents/

# Type checking with specific config
mypy src/ --config-file=mypy.ini
```

## 🔍 Debugging and Troubleshooting

### 1. Development Mode

Enable development mode for better debugging:

```bash
# Set development environment
export SWE_AI_FLEET_ENV=development
export SWE_AI_FLEET_DEBUG=true

# Run with debug logging
python -m swe_ai_fleet.cli.main --debug
```

### 2. Logging Configuration

Configure logging for development:

```python
import logging

# Set up development logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable specific module logging
logging.getLogger('swe_ai_fleet.agents').setLevel(logging.DEBUG)
logging.getLogger('swe_ai_fleet.orchestrator').setLevel(logging.DEBUG)
```

### 3. Common Issues

#### Import Errors

```bash
# Ensure you're in the right directory
cd /path/to/swe-ai-fleet

# Activate virtual environment
source venv/bin/activate

# Install in development mode
pip install -e .
```

#### Test Failures

```bash
# Check test dependencies
pip install -r requirements-dev.txt

# Run tests with verbose output
pytest -v --tb=short

# Check specific test
pytest tests/unit/test_specific.py -v -s
```

#### Linting Issues

```bash
# Auto-fix some issues
ruff check src/ --fix

# Check specific rules
ruff check src/ --select=E,W

# Ignore specific rules for a line
# ruff: noqa: E501
```

## 📝 Contributing Guidelines

### 1. Issue Reporting

Before contributing, check existing issues and create new ones with:

- **Clear description** of the problem or feature
- **Reproduction steps** for bugs
- **Expected vs actual behavior**
- **Environment information** (OS, Python version, etc.)

### 2. Pull Request Process

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** following the coding standards
4. **Add tests** for new functionality
5. **Update documentation** as needed
6. **Run the test suite**: `make test`
7. **Submit a pull request** with a clear description

### 3. Commit Message Format

Use conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Examples:

```
feat(agents): add new developer agent type
fix(orchestrator): resolve task scheduling deadlock
docs(api): update endpoint documentation
test(memory): add Redis connection tests
```

### 4. Code Review Process

- **Self-review**: Review your own code before submitting
- **Peer review**: At least one maintainer must approve
- **CI checks**: All automated tests must pass
- **Documentation**: Ensure documentation is updated

## 🔧 Development Tools

### 1. IDE Configuration

#### VS Code

Install recommended extensions:

```json
{
    "recommendations": [
        "ms-python.python",
        "ms-python.black-formatter",
        "ms-python.isort",
        "ms-python.mypy-type-checker",
        "ms-python.pylint"
    ]
}
```

#### PyCharm

Configure code style:
- **File → Settings → Editor → Code Style → Python**
- Set line length to 110
- Enable type checking
- Configure formatter to use Black

### 2. Git Hooks

The project includes Git hooks for code quality:

```bash
# Install Git hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

### 3. Continuous Integration

GitHub Actions automatically run:

- **Code formatting** (Black, isort)
- **Linting** (Ruff, Flake8)
- **Type checking** (MyPy)
- **Testing** (pytest)
- **Security scanning** (Bandit)

## 📚 Additional Resources

### 1. Project Documentation

- **[Architecture Guide](architecture.md)** - System design and components
- **[API Reference](api.md)** - Complete API documentation
- **[CLI Reference](cli.md)** - Command-line interface guide

### 2. External Resources

- **[Python Documentation](https://docs.python.org/3/)** - Python language reference
- **[Pytest Documentation](https://docs.pytest.org/)** - Testing framework
- **[Ray Documentation](https://docs.ray.io/)** - Distributed computing
- **[Neo4j Documentation](https://neo4j.com/docs/)** - Graph database

### 3. Community

- **GitHub Issues**: [Report bugs and request features](https://github.com/tgarciai/swe-ai-fleet/issues)
- **Discussions**: [Ask questions and share ideas](https://github.com/tgarciai/swe-ai-fleet/discussions)
- **Contributing Guidelines**: [How to contribute](../CONTRIBUTING.md)

## 🎯 Next Steps

Now that you're set up for development:

1. **Explore the codebase** - Start with the main modules
2. **Run the test suite** - Ensure everything works
3. **Try the examples** - See the system in action
4. **Pick an issue** - Start with "good first issue" labels
5. **Join discussions** - Connect with other contributors

---

*Happy coding! If you have questions or need help, don't hesitate to reach out to the community.*