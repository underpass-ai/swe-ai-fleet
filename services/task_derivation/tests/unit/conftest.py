"""Pytest configuration for unit tests - runs BEFORE any test imports."""

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

# Add services/task_derivation to Python path FIRST (before any other service paths)
# This ensures 'server' resolves to services/task_derivation/server.py, not services/planning/server.py
_task_derivation_dir = Path(__file__).parent.parent.parent
_task_derivation_path = str(_task_derivation_dir)
# Remove if already present (to avoid duplicates)
if _task_derivation_path in sys.path:
    sys.path.remove(_task_derivation_path)
# Insert at the beginning to ensure it's checked first
sys.path.insert(0, _task_derivation_path)

# Mock task_derivation.gen modules BEFORE any imports
# These modules are generated during Docker build or by _generate_protos.sh
# Only mock if not already present (e.g., if _generate_protos.sh has run)
if "task_derivation.gen" not in sys.modules:
    fake_gen = ModuleType("task_derivation.gen")

    # Mock context_pb2
    fake_context_pb2 = ModuleType("task_derivation.gen.context_pb2")
    fake_context_pb2.GetContextRequest = MagicMock
    fake_context_pb2.GetContextResponse = MagicMock
    fake_gen.context_pb2 = fake_context_pb2

    fake_context_pb2_grpc = ModuleType("task_derivation.gen.context_pb2_grpc")
    # Add ContextServiceStub class to the mock module
    fake_context_pb2_grpc.ContextServiceStub = MagicMock
    fake_gen.context_pb2_grpc = fake_context_pb2_grpc

    # Mock task_derivation_pb2
    fake_task_derivation_pb2 = ModuleType("task_derivation.gen.task_derivation_pb2")
    fake_task_derivation_pb2.GetPlanRequest = MagicMock
    fake_task_derivation_pb2.PlanContext = MagicMock
    fake_task_derivation_pb2.TaskCreationCommand = MagicMock
    fake_task_derivation_pb2.DependencyEdge = MagicMock
    fake_gen.task_derivation_pb2 = fake_task_derivation_pb2

    fake_task_derivation_pb2_grpc = ModuleType("task_derivation.gen.task_derivation_pb2_grpc")
    fake_task_derivation_pb2_grpc.TaskDerivationPlanningServiceStub = MagicMock
    fake_gen.task_derivation_pb2_grpc = fake_task_derivation_pb2_grpc

    # Mock ray_executor_pb2
    fake_ray_executor_pb2 = ModuleType("task_derivation.gen.ray_executor_pb2")
    fake_ray_executor_pb2.ExecuteDeliberationRequest = MagicMock
    fake_ray_executor_pb2.ExecuteDeliberationResponse = MagicMock
    fake_ray_executor_pb2.Agent = MagicMock
    fake_ray_executor_pb2.TaskConstraints = MagicMock
    fake_gen.ray_executor_pb2 = fake_ray_executor_pb2

    fake_ray_executor_pb2_grpc = ModuleType("task_derivation.gen.ray_executor_pb2_grpc")
    fake_ray_executor_pb2_grpc.RayExecutorServiceStub = MagicMock
    fake_gen.ray_executor_pb2_grpc = fake_ray_executor_pb2_grpc

    # Register in sys.modules
    sys.modules["task_derivation.gen"] = fake_gen
    sys.modules["task_derivation.gen.context_pb2"] = fake_context_pb2
    sys.modules["task_derivation.gen.context_pb2_grpc"] = fake_context_pb2_grpc
    sys.modules["task_derivation.gen.task_derivation_pb2"] = fake_task_derivation_pb2
    sys.modules["task_derivation.gen.task_derivation_pb2_grpc"] = fake_task_derivation_pb2_grpc
    sys.modules["task_derivation.gen.ray_executor_pb2"] = fake_ray_executor_pb2
    sys.modules["task_derivation.gen.ray_executor_pb2_grpc"] = fake_ray_executor_pb2_grpc

