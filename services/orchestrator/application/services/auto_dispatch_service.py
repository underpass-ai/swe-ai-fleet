"""Auto-dispatch service for triggering deliberations from planning events.

This service encapsulates the logic for automatically dispatching deliberations
when a plan is approved, following Hexagonal Architecture principles.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from core.orchestrator.domain.tasks.task_constraints import TaskConstraints
from services.orchestrator.application.usecases import DeliberateUseCase
from services.orchestrator.domain.entities import PlanApprovedEvent
from services.orchestrator.domain.ports import CouncilQueryPort, MessagingPort

logger = logging.getLogger(__name__)


class AutoDispatchService:
    """Service for auto-dispatching deliberations when plans are approved.
    
    This service acts as a facade between the planning consumer (infrastructure)
    and the deliberation use case (application), properly separating concerns
    and avoiding dynamic imports in handlers.
    
    Following Hexagonal Architecture:
    - Application Service (orchestrates use cases)
    - No infrastructure knowledge
    - Dependency Injection for all dependencies
    """
    
    def __init__(
        self,
        council_query: CouncilQueryPort,
        council_registry: Any,  # CouncilRegistry from domain
        stats: Any,  # OrchestratorStatistics from domain
        messaging: MessagingPort,
    ):
        """Initialize auto-dispatch service.
        
        Args:
            council_query: Port for querying council existence
            council_registry: Registry to get councils by role
            stats: Statistics entity for tracking
            messaging: Port for publishing events
        """
        self._council_query = council_query
        self._council_registry = council_registry
        self._stats = stats
        self._messaging = messaging
    
    async def dispatch_deliberations_for_plan(
        self,
        event: PlanApprovedEvent,
    ) -> dict[str, Any]:
        """Dispatch deliberations for all roles in an approved plan.
        
        Args:
            event: Plan approved event with roles to deliberate
            
        Returns:
            Dictionary with dispatch results:
            {
                "total_roles": int,
                "successful": int,
                "failed": int,
                "results": list[dict]
            }
            
        Raises:
            ValueError: If council for required role not found (fail-fast)
        """
        if not event.roles:
            logger.warning(f"No roles specified for plan {event.plan_id}, skipping auto-dispatch")
            return {
                "total_roles": 0,
                "successful": 0,
                "failed": 0,
                "results": []
            }
        
        logger.info(
            f"🚀 Auto-dispatching deliberations for {len(event.roles)} roles: {', '.join(event.roles)}"
        )
        
        results = []
        successful = 0
        failed = 0
        
        for role in event.roles:
            try:
                result = await self._dispatch_single_deliberation(
                    role=role,
                    plan_id=event.plan_id,
                    story_id=event.story_id,
                )
                results.append(result)
                successful += 1
                
            except Exception as e:
                logger.error(f"❌ Failed to execute deliberation for {role}: {e}", exc_info=True)
                results.append({
                    "role": role,
                    "success": False,
                    "error": str(e)
                })
                failed += 1
                # Continue with other roles even if one fails
                continue
        
        return {
            "total_roles": len(event.roles),
            "successful": successful,
            "failed": failed,
            "results": results
        }
    
    async def _dispatch_single_deliberation(
        self,
        role: str,
        plan_id: str,
        story_id: str,
    ) -> dict[str, Any]:
        """Dispatch a single deliberation for a specific role.
        
        Args:
            role: Role to deliberate (DEV, QA, etc.)
            plan_id: Plan identifier
            story_id: Story identifier
            
        Returns:
            Dictionary with deliberation result
            
        Raises:
            ValueError: If council not found
        """
        # Check if council exists (fail-fast)
        if not self._council_query.has_council(role, self._council_registry):
            raise ValueError(f"Council for role '{role}' not found. Cannot execute deliberation.")
        
        # Get council from registry
        council = self._council_registry.get_council(role)
        
        # Create deliberation use case
        deliberate_uc = DeliberateUseCase(
            stats=self._stats,
            messaging=self._messaging
        )
        
        # Build default constraints
        constraints = TaskConstraints(
            rubric={"quality": "high", "tests": "required", "documentation": "complete"},
            architect_rubric={"k": 3}
        )
        
        # Execute deliberation
        task_description = f"Implement plan {plan_id} for story {story_id}"
        
        logger.info(f"🎭 Starting deliberation for {role}: {task_description[:80]}...")
        
        result = await deliberate_uc.execute(
            council=council,
            role=role,
            task_description=task_description,
            constraints=constraints,
            story_id=story_id,
            task_id=plan_id
        )
        
        logger.info(
            f"✅ Deliberation completed for {role}: "
            f"{len(result.results)} proposals in {result.duration_ms}ms"
        )
        
        return {
            "role": role,
            "success": True,
            "num_proposals": len(result.results),
            "duration_ms": result.duration_ms
        }

