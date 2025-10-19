"""gRPC adapter for Ray Executor communication."""

from __future__ import annotations

import logging
from typing import Any

import grpc
from services.orchestrator.domain.entities import (
    DeliberationStatus,
    DeliberationSubmission,
)
from services.orchestrator.domain.ports import RayExecutorPort

logger = logging.getLogger(__name__)


class GRPCRayExecutorAdapter(RayExecutorPort):
    """Adapter implementing Ray Executor communication via gRPC.
    
    This adapter implements the RayExecutorPort interface using gRPC,
    keeping infrastructure concerns separated from domain logic.
    
    Attributes:
        address: Ray Executor gRPC address
        channel: gRPC async channel
        stub: Ray Executor gRPC stub
    """
    
    def __init__(self, address: str):
        """Initialize gRPC Ray Executor adapter.
        
        Args:
            address: Ray Executor service address (e.g., "localhost:50056")
        """
        self.address = address
        self.channel = grpc.aio.insecure_channel(address)
        
        # Import protobuf stub
        try:
            from gen import ray_executor_pb2_grpc
        except ModuleNotFoundError:
            # Fallback for different import paths
            from services.orchestrator.gen import ray_executor_pb2_grpc
        
        self.stub = ray_executor_pb2_grpc.RayExecutorServiceStub(self.channel)
        
        logger.info(f"GRPCRayExecutorAdapter initialized: {address}")
    
    async def execute_deliberation(
        self,
        task_id: str,
        task_description: str,
        role: str,
        agents: list[dict[str, Any]],
        constraints: dict[str, Any],
        vllm_url: str,
        vllm_model: str,
    ) -> DeliberationSubmission:
        """Execute deliberation on Ray cluster via gRPC.
        
        Implements RayExecutorPort.execute_deliberation using gRPC.
        Returns DeliberationSubmission entity instead of dict.
        """
        try:
            # Import protobuf messages
            try:
                from gen import ray_executor_pb2
            except ModuleNotFoundError:
                from services.orchestrator.gen import ray_executor_pb2
            
            # Build agents list for proto
            proto_agents = []
            for agent in agents:
                proto_agent = ray_executor_pb2.Agent(
                    id=agent["id"],
                    role=agent["role"],
                    model=agent.get("model", vllm_model),
                    prompt_template=agent.get("prompt_template", "")
                )
                proto_agents.append(proto_agent)
            
            # Build constraints for proto
            task_constraints = ray_executor_pb2.TaskConstraints(
                story_id=constraints.get("story_id", ""),
                plan_id=constraints.get("plan_id", ""),
                timeout_seconds=constraints.get("timeout", 300),
                max_retries=constraints.get("max_retries", 3)
            )
            
            # Build request
            request = ray_executor_pb2.ExecuteDeliberationRequest(
                task_id=task_id,
                task_description=task_description,
                role=role,
                constraints=task_constraints,
                agents=proto_agents,
                vllm_url=vllm_url,
                vllm_model=vllm_model
            )
            
            # Execute gRPC call
            response = await self.stub.ExecuteDeliberation(request)
            
            logger.info(
                f"✅ Ray Executor accepted deliberation: {response.deliberation_id} "
                f"(status: {response.status})"
            )
            
            # Return domain entity instead of dict
            return DeliberationSubmission(
                deliberation_id=response.deliberation_id,
                status=response.status,
                message=response.message,
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to submit deliberation to Ray Executor: {e}")
            raise
    
    async def get_deliberation_status(
        self,
        deliberation_id: str,
    ) -> DeliberationStatus:
        """Get deliberation status via gRPC.
        
        Implements RayExecutorPort.get_deliberation_status using gRPC.
        Returns DeliberationStatus entity instead of dict.
        """
        try:
            # Import protobuf messages
            try:
                from gen import ray_executor_pb2
            except ModuleNotFoundError:
                from services.orchestrator.gen import ray_executor_pb2
            
            request = ray_executor_pb2.GetDeliberationStatusRequest(
                deliberation_id=deliberation_id
            )
            
            response = await self.stub.GetDeliberationStatus(request)
            
            # Extract result if present
            result_data = None
            if response.HasField("result"):
                result_data = response.result
            
            # Return domain entity instead of dict
            return DeliberationStatus(
                deliberation_id=deliberation_id,
                status=response.status,
                result=result_data,
                error_message=response.error_message if response.error_message else None
            )
            
        except Exception as e:
            logger.error(f"Failed to get deliberation status: {e}")
            raise
    
    async def close(self) -> None:
        """Close gRPC channel.
        
        Implements RayExecutorPort.close to release resources.
        """
        if self.channel:
            await self.channel.close()
            logger.info(f"Closed gRPC channel to Ray Executor: {self.address}")
    
    def __repr__(self) -> str:
        """String representation."""
        return f"GRPCRayExecutorAdapter(address={self.address})"

