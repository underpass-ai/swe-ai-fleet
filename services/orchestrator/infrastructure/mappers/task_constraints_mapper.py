"""Mapper for TaskConstraintsVO."""

from __future__ import annotations

from typing import Any

from services.orchestrator.domain.value_objects.task_constraints import TaskConstraintsVO


class TaskConstraintsMapper:
    """Maps TaskConstraintsVO to/from Protobuf DTOs."""
    
    @staticmethod
    def from_proto(proto_constraints: Any) -> TaskConstraintsVO:
        """Convert protobuf TaskConstraints to TaskConstraintsVO.
        
        Args:
            proto_constraints: orchestrator_pb2.TaskConstraints instance
            
        Returns:
            TaskConstraintsVO domain value object
        """
        # Build rubric dict from proto
        rubric_dict = {
            "description": proto_constraints.rubric,
            "requirements": list(proto_constraints.requirements),
        }
        
        # Build architect rubric dict
        architect_rubric_dict = {
            "k": 3,  # Top-k selection (default)
            "criteria": proto_constraints.rubric
        }
        
        # Extract metadata if present
        metadata = None
        if proto_constraints.metadata:
            metadata = dict(proto_constraints.metadata)
        
        return TaskConstraintsVO(
            rubric=rubric_dict,
            architect_rubric=architect_rubric_dict,
            max_iterations=proto_constraints.max_iterations if proto_constraints.max_iterations else 10,
            timeout_seconds=proto_constraints.timeout_seconds if proto_constraints.timeout_seconds else 300,
            metadata=metadata,
        )
    
    @staticmethod
    def to_proto(vo: TaskConstraintsVO, orchestrator_pb2: Any) -> Any:
        """Convert TaskConstraintsVO to protobuf TaskConstraints.
        
        Args:
            vo: TaskConstraintsVO domain value object
            orchestrator_pb2: Protobuf module
            
        Returns:
            orchestrator_pb2.TaskConstraints instance
        """
        # Extract requirements from rubric
        requirements = vo.rubric.get("requirements", [])
        rubric_description = vo.rubric.get("description", "")
        
        # Build metadata dict
        metadata = vo.metadata if vo.metadata else {}
        
        return orchestrator_pb2.TaskConstraints(
            rubric=rubric_description,
            requirements=requirements,
            max_iterations=vo.max_iterations,
            timeout_seconds=vo.timeout_seconds,
            metadata=metadata,
        )
    
    @staticmethod
    def create_default() -> TaskConstraintsVO:
        """Create default task constraints.
        
        Returns:
            TaskConstraintsVO with default values
        """
        return TaskConstraintsVO(
            rubric={
                "description": "Standard task execution rubric",
                "requirements": [
                    "Clear and complete implementation",
                    "Proper error handling",
                    "Tests included",
                    "Documentation provided",
                ],
            },
            architect_rubric={
                "k": 3,
                "criteria": "Select top 3 proposals based on quality score"
            },
            max_iterations=10,
            timeout_seconds=300,
            metadata=None,
        )

