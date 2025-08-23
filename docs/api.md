# API Reference

This document provides a comprehensive reference for all public APIs in the SWE AI Fleet system. It covers classes, methods, configuration options, and usage examples.

## 📚 Table of Contents

- [Core Classes](#core-classes)
- [Agent System](#agent-system)
- [Orchestrator](#orchestrator)
- [Memory System](#memory-system)
- [Tool System](#tool-system)
- [CLI Interface](#cli-interface)
- [Configuration](#configuration)
- [Error Handling](#error-handling)

## 🏗️ Core Classes

### Base Classes

#### `BaseAgent`

The base class for all AI agents in the system.

```python
from swe_ai_fleet.agents.base import BaseAgent

class BaseAgent:
    """Base class for all AI agents in SWE AI Fleet."""
    
    def __init__(self, name: str, role: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize a new agent.
        
        Args:
            name: Unique identifier for the agent
            role: Role type (developer, devops, qa, architect)
            config: Optional configuration dictionary
        """
        pass
    
    async def execute_task(self, task: Task) -> TaskResult:
        """
        Execute a given task.
        
        Args:
            task: Task to execute
            
        Returns:
            TaskResult containing execution results
            
        Raises:
            TaskExecutionError: If task execution fails
        """
        pass
    
    async def get_status(self) -> AgentStatus:
        """Get current agent status."""
        pass
```

#### `Task`

Represents a task to be executed by an agent.

```python
from swe_ai_fleet.models.task import Task

@dataclass
class Task:
    """Represents a task to be executed by an agent."""
    
    id: str
    description: str
    agent_type: str
    priority: int = 3
    dependencies: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    deadline: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate task configuration."""
        if not 1 <= self.priority <= 5:
            raise ValueError("Priority must be between 1 and 5")
        if self.dependencies is None:
            self.dependencies = []
```

#### `TaskResult`

Result of task execution.

```python
from swe_ai_fleet.models.task import TaskResult

@dataclass
class TaskResult:
    """Result of task execution."""
    
    task_id: str
    success: bool
    output: Any
    error_message: Optional[str] = None
    execution_time: float = 0.0
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
```

## 🤖 Agent System

### Agent Types

#### `DeveloperAgent`

AI agent specialized in software development tasks.

```python
from swe_ai_fleet.agents.developer import DeveloperAgent

class DeveloperAgent(BaseAgent):
    """AI agent for software development tasks."""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(name, "developer", config)
        self.skills = ["python", "javascript", "git", "testing"]
    
    async def write_code(self, specification: str, language: str) -> str:
        """
        Generate code based on specification.
        
        Args:
            specification: Code requirements description
            language: Programming language to use
            
        Returns:
            Generated source code
        """
        pass
    
    async def review_code(self, code: str, language: str) -> CodeReview:
        """
        Review code for quality and issues.
        
        Args:
            code: Source code to review
            language: Programming language
            
        Returns:
            CodeReview with findings and suggestions
        """
        pass
    
    async def run_tests(self, test_path: str) -> TestResult:
        """
        Execute test suite.
        
        Args:
            test_path: Path to test files
            
        Returns:
            TestResult with execution results
        """
        pass
```

#### `DevOpsAgent`

AI agent specialized in DevOps and infrastructure tasks.

```python
from swe_ai_fleet.agents.devops import DevOpsAgent

class DevOpsAgent(BaseAgent):
    """AI agent for DevOps and infrastructure tasks."""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(name, "devops", config)
        self.skills = ["kubernetes", "docker", "helm", "terraform"]
    
    async def deploy_application(self, app_config: AppConfig) -> DeploymentResult:
        """
        Deploy application to infrastructure.
        
        Args:
            app_config: Application configuration
            
        Returns:
            DeploymentResult with deployment status
        """
        pass
    
    async def scale_infrastructure(self, scaling_config: ScalingConfig) -> ScalingResult:
        """
        Scale infrastructure resources.
        
        Args:
            scaling_config: Scaling configuration
            
        Returns:
            ScalingResult with scaling status
        """
        pass
    
    async def monitor_resources(self) -> ResourceMetrics:
        """Get current resource utilization metrics."""
        pass
```

#### `QAEngineerAgent`

AI agent specialized in quality assurance and testing.

```python
from swe_ai_fleet.agents.qa import QAEngineerAgent

class QAEngineerAgent(BaseAgent):
    """AI agent for quality assurance and testing."""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(name, "qa", config)
        self.skills = ["testing", "automation", "quality", "reporting"]
    
    async def create_test_plan(self, requirements: List[str]) -> TestPlan:
        """
        Create comprehensive test plan.
        
        Args:
            requirements: List of requirements to test
            
        Returns:
            TestPlan with test cases and strategy
        """
        pass
    
    async def execute_test_suite(self, test_plan: TestPlan) -> TestSuiteResult:
        """
        Execute complete test suite.
        
        Args:
            test_plan: Test plan to execute
            
        Returns:
            TestSuiteResult with execution results
        """
        pass
    
    async def generate_quality_report(self, test_results: List[TestResult]) -> QualityReport:
        """
        Generate quality assessment report.
        
        Args:
            test_results: List of test results
            
        Returns:
            QualityReport with quality metrics and recommendations
        """
        pass
```

#### `ArchitectAgent`

AI agent specialized in system architecture and design.

```python
from swe_ai_fleet.agents.architect import ArchitectAgent

class ArchitectAgent(BaseAgent):
    """AI agent for system architecture and design."""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(name, "architect", config)
        self.skills = ["design", "planning", "evaluation", "optimization"]
    
    async def design_system(self, requirements: SystemRequirements) -> SystemDesign:
        """
        Design system architecture.
        
        Args:
            requirements: System requirements specification
            
        Returns:
            SystemDesign with architecture components
        """
        pass
    
    async def evaluate_architecture(self, design: SystemDesign) -> ArchitectureEvaluation:
        """
        Evaluate architecture design.
        
        Args:
            design: System design to evaluate
            
        Returns:
            ArchitectureEvaluation with assessment results
        """
        pass
    
    async def optimize_system(self, current_design: SystemDesign, 
                            optimization_goals: List[str]) -> OptimizedDesign:
        """
        Optimize system design.
        
        Args:
            current_design: Current system design
            optimization_goals: List of optimization objectives
            
        Returns:
            OptimizedDesign with improvements
        """
        pass
```

### Agent Factory

#### `AgentFactory`

Factory for creating and configuring agents.

```python
from swe_ai_fleet.agents.factory import AgentFactory

class AgentFactory:
    """Factory for creating and configuring agents."""
    
    @classmethod
    def create_agent(cls, agent_type: str, name: str, 
                    config: Optional[Dict[str, Any]] = None) -> BaseAgent:
        """
        Create a new agent instance.
        
        Args:
            agent_type: Type of agent to create
            name: Agent name
            config: Agent configuration
            
        Returns:
            Configured agent instance
            
        Raises:
            InvalidAgentTypeError: If agent type is not supported
        """
        pass
    
    @classmethod
    def get_supported_agent_types(cls) -> List[str]:
        """Get list of supported agent types."""
        pass
    
    @classmethod
    def validate_config(cls, agent_type: str, config: Dict[str, Any]) -> bool:
        """
        Validate agent configuration.
        
        Args:
            agent_type: Type of agent
            config: Configuration to validate
            
        Returns:
            True if configuration is valid
        """
        pass
```

## 🎭 Orchestrator

### Task Scheduler

#### `TaskScheduler`

Manages task distribution and scheduling.

```python
from swe_ai_fleet.orchestrator.scheduler import TaskScheduler

class TaskScheduler:
    """Manages task distribution and scheduling."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.task_queue = asyncio.Queue()
        self.running_tasks = {}
    
    async def submit_task(self, task: Task) -> str:
        """
        Submit a task for execution.
        
        Args:
            task: Task to submit
            
        Returns:
            Task ID for tracking
        """
        pass
    
    async def get_task_status(self, task_id: str) -> TaskStatus:
        """
        Get status of a specific task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Current task status
        """
        pass
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            True if task was cancelled successfully
        """
        pass
    
    async def get_queue_status(self) -> QueueStatus:
        """Get current queue status and statistics."""
        pass
```

### Agent Manager

#### `AgentManager`

Manages agent lifecycle and coordination.

```python
from swe_ai_fleet.orchestrator.manager import AgentManager

class AgentManager:
    """Manages agent lifecycle and coordination."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.agents = {}
        self.agent_health = {}
    
    async def register_agent(self, agent: BaseAgent) -> bool:
        """
        Register a new agent.
        
        Args:
            agent: Agent to register
            
        Returns:
            True if registration was successful
        """
        pass
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent.
        
        Args:
            agent_id: ID of the agent to unregister
            
        Returns:
            True if unregistration was successful
        """
        pass
    
    async def get_available_agents(self, agent_type: Optional[str] = None) -> List[BaseAgent]:
        """
        Get list of available agents.
        
        Args:
            agent_type: Optional filter by agent type
            
        Returns:
            List of available agents
        """
        pass
    
    async def get_agent_health(self, agent_id: str) -> AgentHealth:
        """
        Get health status of an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Agent health information
        """
        pass
```

### Workflow Engine

#### `WorkflowEngine`

Coordinates complex multi-step workflows.

```python
from swe_ai_fleet.orchestrator.workflow import WorkflowEngine

class WorkflowEngine:
    """Coordinates complex multi-step workflows."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.workflows = {}
        self.workflow_templates = {}
    
    async def create_workflow(self, template_name: str, 
                             parameters: Dict[str, Any]) -> str:
        """
        Create a new workflow instance.
        
        Args:
            template_name: Name of workflow template
            parameters: Workflow parameters
            
        Returns:
            Workflow ID
        """
        pass
    
    async def execute_workflow(self, workflow_id: str) -> WorkflowResult:
        """
        Execute a workflow.
        
        Args:
            workflow_id: ID of the workflow to execute
            
        Returns:
            Workflow execution result
        """
        pass
    
    async def get_workflow_status(self, workflow_id: str) -> WorkflowStatus:
        """
        Get workflow execution status.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Current workflow status
        """
        pass
    
    async def pause_workflow(self, workflow_id: str) -> bool:
        """
        Pause workflow execution.
        
        Args:
            workflow_id: ID of the workflow to pause
            
        Returns:
            True if workflow was paused successfully
        """
        pass
```

## 🧠 Memory System

### Memory Interface

#### `MemoryInterface`

Abstract interface for memory operations.

```python
from swe_ai_fleet.memory.interface import MemoryInterface

class MemoryInterface(ABC):
    """Abstract interface for memory operations."""
    
    @abstractmethod
    async def store(self, key: str, value: Any, 
                   ttl: Optional[int] = None) -> bool:
        """
        Store a value in memory.
        
        Args:
            key: Memory key
            value: Value to store
            ttl: Time to live in seconds
            
        Returns:
            True if storage was successful
        """
        pass
    
    @abstractmethod
    async def retrieve(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from memory.
        
        Args:
            key: Memory key
            
        Returns:
            Stored value or None if not found
        """
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete a value from memory.
        
        Args:
            key: Memory key
            
        Returns:
            True if deletion was successful
        """
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in memory.
        
        Args:
            key: Memory key
            
        Returns:
            True if key exists
        """
        pass
```

### Redis Manager

#### `RedisManager`

Manages Redis-based short-term memory.

```python
from swe_ai_fleet.memory.redis_manager import RedisManager

class RedisManager(MemoryInterface):
    """Manages Redis-based short-term memory."""
    
    def __init__(self, host: str = "localhost", port: int = 6379, 
                 db: int = 0, password: Optional[str] = None):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.redis_client = None
    
    async def connect(self) -> bool:
        """Establish connection to Redis."""
        pass
    
    async def disconnect(self) -> bool:
        """Close connection to Redis."""
        pass
    
    async def store(self, key: str, value: Any, 
                   ttl: Optional[int] = None) -> bool:
        """Store value in Redis with optional TTL."""
        pass
    
    async def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve value from Redis."""
        pass
    
    async def delete(self, key: str) -> bool:
        """Delete value from Redis."""
        pass
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        pass
    
    async def get_keys(self, pattern: str = "*") -> List[str]:
        """
        Get keys matching pattern.
        
        Args:
            pattern: Redis key pattern
            
        Returns:
            List of matching keys
        """
        pass
```

### Neo4j Manager

#### `Neo4jManager`

Manages Neo4j-based long-term knowledge graph.

```python
from swe_ai_fleet.memory.neo4j_manager import Neo4jManager

class Neo4jManager:
    """Manages Neo4j-based long-term knowledge graph."""
    
    def __init__(self, uri: str, user: str, password: str):
        self.uri = uri
        self.user = user
        self.password = password
        self.driver = None
    
    async def connect(self) -> bool:
        """Establish connection to Neo4j."""
        pass
    
    async def disconnect(self) -> bool:
        """Close connection to Neo4j."""
        pass
    
    async def create_node(self, labels: List[str], 
                         properties: Dict[str, Any]) -> str:
        """
        Create a new node in the graph.
        
        Args:
            labels: Node labels
            properties: Node properties
            
        Returns:
            Node ID
        """
        pass
    
    async def create_relationship(self, from_node_id: str, to_node_id: str,
                                relationship_type: str, 
                                properties: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a relationship between nodes.
        
        Args:
            from_node_id: Source node ID
            to_node_id: Target node ID
            relationship_type: Type of relationship
            properties: Relationship properties
            
        Returns:
            Relationship ID
        """
        pass
    
    async def query(self, cypher_query: str, 
                   parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute Cypher query.
        
        Args:
            cypher_query: Cypher query string
            parameters: Query parameters
            
        Returns:
            Query results
        """
        pass
    
    async def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get node by ID.
        
        Args:
            node_id: Node ID
            
        Returns:
            Node data or None if not found
        """
        pass
```

## 🛠️ Tool System

### Tool Interface

#### `ToolInterface`

Abstract interface for tool operations.

```python
from swe_ai_fleet.tools.interface import ToolInterface

class ToolInterface(ABC):
    """Abstract interface for tool operations."""
    
    @abstractmethod
    async def execute(self, command: str, 
                     parameters: Optional[Dict[str, Any]] = None) -> ToolResult:
        """
        Execute tool command.
        
        Args:
            command: Command to execute
            parameters: Command parameters
            
        Returns:
            Tool execution result
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Get list of tool capabilities."""
        pass
    
    @abstractmethod
    def validate_command(self, command: str, 
                        parameters: Optional[Dict[str, Any]] = None) -> bool:
        """
        Validate tool command.
        
        Args:
            command: Command to validate
            parameters: Command parameters
            
        Returns:
            True if command is valid
        """
        pass
```

### Git Tools

#### `GitTool`

Safe wrapper for Git operations.

```python
from swe_ai_fleet.tools.git import GitTool

class GitTool(ToolInterface):
    """Safe wrapper for Git operations."""
    
    def __init__(self, repo_path: str, config: Optional[Dict[str, Any]] = None):
        self.repo_path = repo_path
        self.config = config or {}
    
    async def clone(self, repository_url: str, branch: Optional[str] = None) -> ToolResult:
        """
        Clone a repository.
        
        Args:
            repository_url: URL of repository to clone
            branch: Optional branch to checkout
            
        Returns:
            Clone operation result
        """
        pass
    
    async def commit(self, message: str, files: Optional[List[str]] = None) -> ToolResult:
        """
        Commit changes to repository.
        
        Args:
            message: Commit message
            files: Optional list of files to commit
            
        Returns:
            Commit operation result
        """
        pass
    
    async def push(self, remote: str = "origin", branch: Optional[str] = None) -> ToolResult:
        """
        Push changes to remote repository.
        
        Args:
            remote: Remote name
            branch: Optional branch to push
            
        Returns:
            Push operation result
        """
        pass
    
    async def pull(self, remote: str = "origin", branch: Optional[str] = None) -> ToolResult:
        """
        Pull changes from remote repository.
        
        Args:
            remote: Remote name
            branch: Optional branch to pull
            
        Returns:
            Pull operation result
        """
        pass
```

### Docker Tools

#### `DockerTool`

Safe wrapper for Docker operations.

```python
from swe_ai_fleet.tools.docker import DockerTool

class DockerTool(ToolInterface):
    """Safe wrapper for Docker operations."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
    
    async def build_image(self, dockerfile_path: str, tag: str, 
                         context: Optional[str] = None) -> ToolResult:
        """
        Build Docker image.
        
        Args:
            dockerfile_path: Path to Dockerfile
            tag: Image tag
            context: Build context directory
            
        Returns:
            Build operation result
        """
        pass
    
    async def run_container(self, image: str, command: Optional[str] = None,
                           ports: Optional[Dict[str, str]] = None,
                           environment: Optional[Dict[str, str]] = None) -> ToolResult:
        """
        Run Docker container.
        
        Args:
            image: Image to run
            command: Optional command to execute
            ports: Optional port mappings
            environment: Optional environment variables
            
        Returns:
            Container run result
        """
        pass
    
    async def stop_container(self, container_id: str) -> ToolResult:
        """
        Stop running container.
        
        Args:
            container_id: ID of container to stop
            
        Returns:
            Stop operation result
        """
        pass
    
    async def list_containers(self, all_containers: bool = False) -> ToolResult:
        """
        List Docker containers.
        
        Args:
            all_containers: Include stopped containers
            
        Returns:
            Container list result
        """
        pass
```

## 🖥️ CLI Interface

### Main CLI

#### `swe_ai_fleet`

Main command-line interface for SWE AI Fleet.

```bash
# Basic usage
swe_ai_fleet [OPTIONS] COMMAND [ARGS]...

# Available commands
swe_ai_fleet --help
swe_ai_fleet agents --help
swe_ai_fleet tasks --help
swe_ai_fleet workflows --help
swe_ai_fleet status --help
```

#### Agent Management Commands

```bash
# List all agents
swe_ai_fleet agents list

# Create new agent
swe_ai_fleet agents create --type developer --name dev-1

# Get agent status
swe_ai_fleet agents status dev-1

# Stop agent
swe_ai_fleet agents stop dev-1
```

#### Task Management Commands

```bash
# Submit new task
swe_ai_fleet tasks submit --description "Write unit tests" --agent-type developer

# List tasks
swe_ai_fleet tasks list

# Get task status
swe_ai_fleet tasks status <task-id>

# Cancel task
swe_ai_fleet tasks cancel <task-id>
```

#### Workflow Management Commands

```bash
# Create workflow
swe_ai_fleet workflows create --template ci-cd --parameters '{"app": "myapp"}'

# Execute workflow
swe_ai_fleet workflows execute <workflow-id>

# Get workflow status
swe_ai_fleet workflows status <workflow-id>

# List workflows
swe_ai_fleet workflows list
```

## ⚙️ Configuration

### Environment Variables

```bash
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Ray Configuration
RAY_HEAD_HOST=localhost
RAY_HEAD_PORT=10001

# Logging Configuration
SWE_AI_FLEET_LOG_LEVEL=INFO
SWE_AI_FLEET_LOG_FILE=/var/log/swe-ai-fleet.log

# Security Configuration
SWE_AI_FLEET_SECRET_KEY=your-secret-key
SWE_AI_FLEET_ALLOWED_HOSTS=localhost,127.0.0.1
```

### Configuration Files

#### YAML Configuration

```yaml
# config/swe_ai_fleet.yaml
agents:
  developer:
    max_instances: 5
    memory_limit: "4Gi"
    cpu_limit: "2"
  
  devops:
    max_instances: 3
    memory_limit: "8Gi"
    cpu_limit: "4"

memory:
  redis:
    host: localhost
    port: 6379
    db: 0
  
  neo4j:
    uri: bolt://localhost:7687
    user: neo4j
    password: password

orchestrator:
  max_concurrent_tasks: 100
  task_timeout: 300
  retry_attempts: 3

tools:
  git:
    allowed_operations: ["clone", "pull", "push"]
    max_repo_size: "1Gi"
  
  docker:
    allowed_operations: ["build", "run", "stop"]
    max_container_memory: "8Gi"
```

#### JSON Configuration

```json
{
  "agents": {
    "developer": {
      "max_instances": 5,
      "memory_limit": "4Gi",
      "cpu_limit": "2"
    },
    "devops": {
      "max_instances": 3,
      "memory_limit": "8Gi",
      "cpu_limit": "4"
    }
  },
  "memory": {
    "redis": {
      "host": "localhost",
      "port": 6379,
      "db": 0
    },
    "neo4j": {
      "uri": "bolt://localhost:7687",
      "user": "neo4j",
      "password": "password"
    }
  }
}
```

## ❌ Error Handling

### Exception Classes

#### `SWEAIFleetError`

Base exception class for all SWE AI Fleet errors.

```python
from swe_ai_fleet.exceptions import SWEAIFleetError

class SWEAIFleetError(Exception):
    """Base exception class for SWE AI Fleet."""
    
    def __init__(self, message: str, error_code: Optional[str] = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)
```

#### `AgentError`

Exception raised for agent-related errors.

```python
from swe_ai_fleet.exceptions import AgentError

class AgentError(SWEAIFleetError):
    """Exception raised for agent-related errors."""
    
    def __init__(self, message: str, agent_id: Optional[str] = None):
        self.agent_id = agent_id
        super().__init__(message, "AGENT_ERROR")
```

#### `TaskError`

Exception raised for task-related errors.

```python
from swe_ai_fleet.exceptions import TaskError

class TaskError(SWEAIFleetError):
    """Exception raised for task-related errors."""
    
    def __init__(self, message: str, task_id: Optional[str] = None):
        self.task_id = task_id
        super().__init__(message, "TASK_ERROR")
```

#### `MemoryError`

Exception raised for memory-related errors.

```python
from swe_ai_fleet.exceptions import MemoryError

class MemoryError(SWEAIFleetError):
    """Exception raised for memory-related errors."""
    
    def __init__(self, message: str, memory_type: Optional[str] = None):
        self.memory_type = memory_type
        super().__init__(message, "MEMORY_ERROR")
```

### Error Handling Examples

#### Basic Error Handling

```python
from swe_ai_fleet.exceptions import SWEAIFleetError, AgentError

try:
    agent = agent_factory.create_agent("developer", "dev-1")
    result = await agent.execute_task(task)
except AgentError as e:
    print(f"Agent error: {e.message}")
    print(f"Agent ID: {e.agent_id}")
except SWEAIFleetError as e:
    print(f"System error: {e.message}")
    print(f"Error code: {e.error_code}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

#### Error Recovery

```python
from swe_ai_fleet.exceptions import TaskError

async def execute_task_with_retry(task, max_retries=3):
    for attempt in range(max_retries):
        try:
            result = await agent.execute_task(task)
            return result
        except TaskError as e:
            if attempt == max_retries - 1:
                raise e
            print(f"Task failed, retrying... (attempt {attempt + 1})")
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

---

*This API reference provides comprehensive coverage of all public interfaces in SWE AI Fleet. For implementation details and examples, refer to the source code and other documentation sections.*