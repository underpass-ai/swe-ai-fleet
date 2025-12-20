"""Use case: Execute agent task (with or without tools)."""

import logging
import time
from typing import Any

from ..domain import (
    AgentConfig,
    AgentResult,
    ExecutionRequest,
)
from ..domain.ports import IResultPublisher, IVLLMClient
from .generate_proposal import GenerateProposal

logger = logging.getLogger(__name__)


class ExecuteAgentTask:
    """
    Caso de uso: Ejecutar tarea de agente.

    Orquesta la ejecución de una tarea, decidiendo entre:
    - Ejecución con herramientas (VLLMAgent)
    - Generación de texto (vLLM API)

    Responsabilidades:
    - Timing y métricas
    - Decisión de estrategia (tools vs text-only)
    - Conversión de resultados a domain models
    - Publicación de resultados
    """

    def __init__(
        self,
        config: AgentConfig,
        publisher: IResultPublisher,
        vllm_client: IVLLMClient,
        vllm_agent: Any | None = None,  # core.agents.VLLMAgent
    ):
        """
        Initialize use case.

        Args:
            config: Configuración del agente
            publisher: Puerto para publicar resultados (NATS, etc.)
            vllm_client: Puerto para cliente vLLM (text generation)
            vllm_agent: VLLMAgent instance (optional, for tool execution)
        """
        self.config = config
        self.publisher = publisher
        self.vllm_client = vllm_client
        self.vllm_agent = vllm_agent

    async def execute(self, request: ExecutionRequest) -> dict[str, Any]:
        """
        Ejecutar tarea de agente.

        Args:
            request: Request con task_id, description, constraints

        Returns:
            Result dictionary con proposal/operations y metadata
        """
        start_time = time.time()
        result_obj: AgentResult

        try:
            # Conectar a NATS
            await self.publisher.connect()

            # Decidir estrategia: tools enabled?
            if self.config.enable_tools:
                # Estrategia 1: Ejecutar con herramientas (VLLMAgent)
                result_obj = await self._execute_with_tools(request, start_time)
            else:
                # Estrategia 2: Generar texto (vLLM API)
                result_obj = await self._execute_text_only(request, start_time)

            # Log LLM response before publishing
            if result_obj.is_success and result_obj.proposal:
                proposal_data = result_obj.proposal
                llm_content = None
                if isinstance(proposal_data, dict):
                    llm_content = proposal_data.get('content', '')
                elif isinstance(proposal_data, str):
                    llm_content = proposal_data

                if llm_content:
                    logger.info(
                        f"\n{'='*80}\n"
                        f"💡 LLM RESPONSE - Agent: {result_obj.agent_id} ({result_obj.role})\n"
                        f"{'='*80}\n"
                        f"{llm_content}\n"
                        f"{'='*80}\n"
                    )

            # Extract num_agents and original_task_id from request metadata
            num_agents = None
            original_task_id = None
            if request.constraints and isinstance(request.constraints, dict):
                metadata = request.constraints.get("metadata", {})
                num_agents = metadata.get("num_agents")
                # Original task_id from planning (in metadata) or use request.task_id if it contains :task-extraction
                original_task_id = metadata.get("task_id")
                # Fallback: if task_id itself contains :task-extraction, use it as original_task_id
                if not original_task_id and ":task-extraction" in request.task_id:
                    original_task_id = request.task_id

            # Log before publishing
            logger.info(
                f"🔍 [ExecuteAgentTask] About to publish result: "
                f"task_id={result_obj.task_id}, "
                f"agent_id={result_obj.agent_id}, "
                f"role={result_obj.role}, "
                f"is_success={result_obj.is_success}, "
                f"num_agents={num_agents}, "
                f"original_task_id={original_task_id}, "
                f"has_constraints={request.constraints is not None}, "
                f"constraints_keys={list(request.constraints.keys()) if request.constraints else []}"
            )

            # Publicar resultado (publisher will add num_agents, original_task_id, and constraints to payload)
            if result_obj.is_success:
                logger.info(
                    f"📤 [ExecuteAgentTask] Calling publish_success for task_id={result_obj.task_id}, "
                    f"original_task_id={original_task_id}"
                )
                await self.publisher.publish_success(
                    result_obj,
                    num_agents=num_agents,
                    original_task_id=original_task_id,
                    constraints=request.constraints  # Preserve constraints for metadata (story_id, ceremony_id, etc.)
                )
                logger.info(
                    f"✅ [ExecuteAgentTask] publish_success completed for task_id={result_obj.task_id}"
                )
            else:
                await self.publisher.publish_failure(result_obj, num_agents=num_agents, original_task_id=original_task_id)

            return result_obj.to_dict()

        except Exception as e:
            # Error no capturado: crear failure result
            duration_ms = int((time.time() - start_time) * 1000)
            result_obj = AgentResult.failure_result(
                task_id=request.task_id,
                agent_id=self.config.agent_id,
                role=str(self.config.role),
                duration_ms=duration_ms,
                error=e,
                model=self.config.model,
            )

            await self.publisher.publish_failure(result_obj)
            return result_obj.to_dict()

        finally:
            # Cerrar conexión NATS
            await self.publisher.close()

    async def _execute_with_tools(
        self,
        request: ExecutionRequest,
        start_time: float,
    ) -> AgentResult:
        """
        Ejecutar con herramientas usando VLLMAgent.

        Args:
            request: Execution request
            start_time: Timestamp de inicio

        Returns:
            AgentResult con operations, artifacts, audit_trail
        """
        mode = "with tools" if self.config.enable_tools else "planning only"
        logger.info(
            f"[{self.config.agent_id}] Executing task {request.task_id} {mode} "
            f"(workspace={self.config.workspace_path})"
        )

        # Ejecutar usando VLLMAgent (componente externo)
        # VLLMAgent ya maneja: workspace, git, files, tests, etc.
        agent_result = await self.vllm_agent.execute_task(
            task=request.task_description,
            context=request.get_context(),
            constraints=request.constraints,
        )

        duration_ms = int((time.time() - start_time) * 1000)

        # Convertir resultado de VLLMAgent a domain model
        if agent_result.success:
            return AgentResult.success_result(
                task_id=request.task_id,
                agent_id=self.config.agent_id,
                role=str(self.config.role),
                duration_ms=duration_ms,
                proposal=None,  # VLLMAgent no retorna proposal dict
                operations=agent_result.operations,
                artifacts=agent_result.artifacts,
                audit_trail=agent_result.audit_trail,
                model=self.config.model,
                enable_tools=self.config.enable_tools,
            )
        else:
            # Error desde VLLMAgent
            error = Exception(agent_result.error or "Unknown error")
            return AgentResult.failure_result(
                task_id=request.task_id,
                agent_id=self.config.agent_id,
                role=str(self.config.role),
                duration_ms=duration_ms,
                error=error,
                model=self.config.model,
            )

    async def _execute_text_only(
        self,
        request: ExecutionRequest,
        start_time: float,
    ) -> AgentResult:
        """
        Generar texto usando vLLM API (sin herramientas).

        Args:
            request: Execution request
            start_time: Timestamp de inicio

        Returns:
            AgentResult con proposal generado
        """
        logger.info(
            f"[{self.config.agent_id}] Generating text-only proposal for task {request.task_id}"
        )

        try:
            # Detect if this is task extraction
            is_task_extraction = self._is_task_extraction(request)
            
            # Delegar a GenerateProposal use case
            generate_proposal = GenerateProposal(
                config=self.config,
                llm_client=self.vllm_client,
            )

            proposal = await generate_proposal.execute(
                task=request.task_description,
                constraints=request.constraints,
                diversity=request.diversity,
                use_structured_outputs=is_task_extraction,
                task_type="TASK_EXTRACTION" if is_task_extraction else None,
            )

            duration_ms = int((time.time() - start_time) * 1000)

            return AgentResult.success_result(
                task_id=request.task_id,
                agent_id=self.config.agent_id,
                role=str(self.config.role),
                duration_ms=duration_ms,
                proposal=proposal,
                operations=[],
                artifacts={},
                audit_trail=[],
                model=self.config.model,
                enable_tools=False,
            )

        except Exception as e:
            # Error durante generación de texto
            duration_ms = int((time.time() - start_time) * 1000)
            return AgentResult.failure_result(
                task_id=request.task_id,
                agent_id=self.config.agent_id,
                role=str(self.config.role),
                duration_ms=duration_ms,
                error=e,
                model=self.config.model,
            )
    
    def _is_task_extraction(self, request: ExecutionRequest) -> bool:
        """Detectar si es task extraction por task_id o metadata.
        
        Args:
            request: Execution request
            
        Returns:
            True si es task extraction, False en caso contrario
        """
        # Detect by task_id
        if request.task_id and ":task-extraction" in request.task_id:
            return True
        
        # Detect by metadata
        if request.constraints and isinstance(request.constraints, dict):
            metadata = request.constraints.get("metadata", {})
            task_type = metadata.get("task_type")
            if task_type == "TASK_EXTRACTION":
                return True
        
        return False

