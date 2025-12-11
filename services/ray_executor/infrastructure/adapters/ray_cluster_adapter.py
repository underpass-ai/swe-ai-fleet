"""Ray cluster adapter implementation."""

import asyncio
import logging
import os
import time
from typing import Any

import ray
from core.ray_jobs import RayAgentExecutor, RayAgentFactory

from services.ray_executor.domain.entities import (
    DeliberationResult,
    MultiAgentDeliberationResult,
)

logger = logging.getLogger(__name__)

# Create Ray remote actor from RayAgentExecutor
# NOTE: runtime_env is configured at ray.init() level in server.py
# This ensures that the 'core' module is available in Ray workers
RayAgentJob = ray.remote(RayAgentExecutor)


class RayClusterAdapter:
    """Adapter for Ray cluster interaction.

    This adapter implements RayClusterPort using Ray client API.

    Following Hexagonal Architecture:
    - Implements port (interface) defined in domain
    - Translates domain entities to Ray-specific data structures
    - Handles Ray-specific errors and retries
    """

    def __init__(self, deliberations_registry: dict):
        """Initialize Ray cluster adapter.

        Args:
            deliberations_registry: Shared registry for tracking deliberations
        """
        self._deliberations = deliberations_registry

    async def submit_deliberation(
        self,
        deliberation_id: str,
        task_id: str,
        task_description: str,
        role: str,
        agents: list[dict[str, Any]],
        constraints: dict[str, Any],
        vllm_url: str,
        vllm_model: str,
    ) -> str:
        """Submit deliberation to Ray cluster.

        Creates one Ray job per agent and executes them in parallel.
        All agents deliberate on the same task independently.

        Implements RayClusterPort.submit_deliberation()
        """
        await asyncio.sleep(0)  # Make function truly async

        if not agents:
            raise ValueError("At least one agent required")

        logger.info(
            f"📤 Submitting {len(agents)} agent(s) to Ray cluster for deliberation {deliberation_id}"
        )

        # Create one Ray job per agent
        agent_futures: list[ray.ObjectRef] = []
        agent_ids: list[str] = []

        for agent_config in agents:
            agent_id = agent_config["agent_id"]
            agent_ids.append(agent_id)

            # Read NATS URL from environment (same as server.py)
            nats_url = os.getenv('NATS_URL', 'nats://nats.swe-ai-fleet.svc.cluster.local:4222')

            # Use Factory to create executor with all dependencies injected
            executor = RayAgentFactory.create(
                agent_id=agent_id,
                role=agent_config["role"],
                vllm_url=vllm_url,
                model=vllm_model,
                nats_url=nats_url,
                workspace_path=None,
                enable_tools=False,
            )

            # Create Ray remote actor from the configured executor
            # Pass only config to avoid serialization issues with dependencies
            # Dependencies will be recreated in the worker
            logger.info(f"Creating Ray remote actor for agent {agent_id}...")
            logger.debug(f"  Config: {executor.config.agent_id}, {executor.config.role}")
            logger.debug(f"  Passing: publisher=None, vllm_client=None, async_executor=None, vllm_agent={executor.vllm_agent is not None}")

            try:
                agent_job = RayAgentJob.remote(
                    config=executor.config,
                    publisher=None,  # Will be recreated in worker
                    vllm_client=None,  # Will be recreated in worker
                    async_executor=None,  # Will be recreated in worker
                    vllm_agent=executor.vllm_agent,  # None when enable_tools=False, so safe
                )
                logger.info(f"✅ Ray remote actor created for agent {agent_id}")
            except Exception as e:
                logger.error(f"❌ Failed to create Ray remote actor for agent {agent_id}: {e}", exc_info=True)
                raise

            # Submit to Ray
            logger.info(f"📤 Invoking agent_job.run.remote() for agent {agent_id}, task {task_id}")
            logger.debug(f"   Task description: {task_description[:100]}...")
            logger.debug(f"   Constraints: {constraints}")

            # Add num_agents to constraints metadata so agents can include it in NATS payload
            # Preserve existing metadata (e.g., original task_id from planning)
            # TaskConstraints is immutable, so we create a new dict (not mutating the value object)
            constraints_with_metadata = dict(constraints)
            if "metadata" not in constraints_with_metadata:
                constraints_with_metadata["metadata"] = {}
            elif not isinstance(constraints_with_metadata.get("metadata"), dict):
                # If metadata exists but is not a dict, preserve it and create new dict
                old_metadata = constraints_with_metadata["metadata"]
                constraints_with_metadata["metadata"] = {"original": old_metadata}

            # Preserve existing task_id if present (from planning mapper)
            existing_task_id = constraints_with_metadata["metadata"].get("task_id")
            constraints_with_metadata["metadata"]["num_agents"] = len(agents)
            if existing_task_id:
                # Ensure task_id is preserved (it should already be there, but double-check)
                constraints_with_metadata["metadata"]["task_id"] = existing_task_id
                logger.info(f"✅ Preserved original task_id in constraints metadata: {existing_task_id}")
            else:
                logger.warning(f"⚠️ No original task_id found in constraints metadata. Keys: {list(constraints_with_metadata.get('metadata', {}).keys())}")

            # Ensure story_id is in metadata (required for TaskExtractionResultConsumer)
            # Use story_id from constraints if not already in metadata
            if "story_id" not in constraints_with_metadata["metadata"] and constraints_with_metadata.get("story_id"):
                constraints_with_metadata["metadata"]["story_id"] = constraints_with_metadata["story_id"]
                logger.info(f"✅ Added story_id to constraints metadata: {constraints_with_metadata['story_id']}")

            future = agent_job.run.remote(
                task_id=task_id,
                task_description=task_description,
                constraints=constraints_with_metadata,
            )

            logger.info(f"✅ Ray future created for agent {agent_id}: {future}")

            agent_futures.append(future)

            logger.debug(f"   Created Ray job for agent {agent_id}")

        # Store deliberation info in registry with all futures
        self._deliberations[deliberation_id] = {
            'futures': agent_futures,  # List of futures (one per agent)
            'task_id': task_id,
            'role': role,
            'status': 'running',
            'start_time': time.time(),
            'agents': agent_ids,
            'total_agents': len(agents),
        }

        logger.info(
            f"✅ Submitted {len(agents)} agent(s) to Ray cluster for deliberation {deliberation_id}"
        )

        return deliberation_id

    async def check_deliberation_status(
        self,
        deliberation_id: str,
    ) -> tuple[str, DeliberationResult | MultiAgentDeliberationResult | None, str | None]:
        """Check deliberation status on Ray cluster.

        Implements RayClusterPort.check_deliberation_status()

        For single-agent deliberations, returns DeliberationResult.
        For multi-agent deliberations, returns MultiAgentDeliberationResult with all results.

        Returns:
            Tuple of (status, result, error_message)
        """
        await asyncio.sleep(0)  # Make function truly async
        if deliberation_id not in self._deliberations:
            return ("not_found", None, f"Deliberation {deliberation_id} not found")

        deliberation = self._deliberations[deliberation_id]

        try:
            # Support both old format (single future) and new format (list of futures)
            futures = deliberation.get('futures', [deliberation.get('future')])
            futures = [f for f in futures if f is not None]  # Filter None values

            if not futures:
                return ("failed", None, "No futures found in deliberation registry")

            total_agents = deliberation.get('total_agents', len(futures))

            # Check if all Ray jobs are ready (non-blocking check with short timeout)
            # NOTE: ray.wait() is synchronous but with minimal timeout (0.1s) to avoid blocking event loop
            ready, not_ready = ray.wait(futures, num_returns=len(futures), timeout=0.1)

            if len(ready) == len(futures):
                # All jobs completed - aggregate results
                agent_results: list[DeliberationResult] = []
                failed_count = 0

                for future in ready:
                    try:
                        # NOTE: ray.get() blocks but only called when we know result is ready
                        result_data = ray.get(future)

                        logger.debug(f"Raw result_data keys: {list(result_data.keys()) if isinstance(result_data, dict) else type(result_data)}")

                        # Log LLM response if available
                        agent_id = result_data.get('agent_id', 'unknown')
                        proposal_data = result_data.get('proposal', {})

                        logger.debug(f"Proposal data type: {type(proposal_data)}, value: {str(proposal_data)[:200] if proposal_data else 'None'}")

                        # Extract LLM content from proposal
                        llm_content = None
                        if isinstance(proposal_data, dict):
                            llm_content = proposal_data.get('content', '')
                            if not llm_content:
                                # Try to find content in nested structure
                                logger.debug(f"Proposal dict keys: {list(proposal_data.keys())}")
                        elif isinstance(proposal_data, str):
                            # Legacy format: proposal is a string
                            llm_content = proposal_data

                        if llm_content:
                            logger.info(
                                f"\n{'='*80}\n"
                                f"💡 LLM RESPONSE - Agent: {agent_id}\n"
                                f"{'='*80}\n"
                                f"{llm_content}\n"
                                f"{'='*80}\n"
                            )
                        else:
                            logger.warning(f"⚠️ No LLM content found for agent {agent_id}. Proposal type: {type(proposal_data)}")

                        # Build DeliberationResult entity
                        agent_result = DeliberationResult(
                            agent_id=agent_id,
                            proposal=proposal_data if isinstance(proposal_data, str) else proposal_data.get('content', ''),
                            reasoning=result_data.get('reasoning', ''),
                            score=result_data.get('score', 0.0),
                            metadata=result_data.get('metadata', {}),
                        )

                        agent_results.append(agent_result)

                    except Exception as e:
                        logger.warning(f"Failed to get result from future: {e}")
                        failed_count += 1

                # Determine return type based on number of agents
                if total_agents == 1 and len(agent_results) == 1:
                    # Single agent - return single DeliberationResult for backward compatibility
                    return ("completed", agent_results[0], None)
                else:
                    # Multiple agents - return MultiAgentDeliberationResult
                    multi_result = MultiAgentDeliberationResult(
                        agent_results=agent_results,
                        total_agents=total_agents,
                        completed_agents=len(agent_results),
                        failed_agents=failed_count,
                    )

                    return ("completed", multi_result, None)

            elif len(ready) > 0:
                # Some jobs completed but not all - still running
                logger.debug(
                    f"Deliberation {deliberation_id}: {len(ready)}/{len(futures)} agents completed"
                )
                return ("running", None, None)
            else:
                # No jobs completed yet - still running
                return ("running", None, None)

        except Exception as e:
            logger.error(f"❌ Error checking deliberation status: {e}", exc_info=True)
            return ("failed", None, str(e))

    async def get_active_jobs(self) -> list[dict[str, Any]]:
        """Get list of active Ray jobs.

        Implements RayClusterPort.get_active_jobs()
        """
        await asyncio.sleep(0)  # Make function truly async
        # Return deliberations from registry
        # The use case will filter for running jobs
        return list(self._deliberations.items())

