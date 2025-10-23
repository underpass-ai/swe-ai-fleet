"""Use case: Execute agent task (with or without tools)."""

import logging
import time
from typing import Any

from ..domain import (
    ExecutionRequest,
    AgentConfig,
    AgentResult,
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
            
            # Publicar resultado
            if result_obj.is_success:
                await self.publisher.publish_success(result_obj)
            else:
                await self.publisher.publish_failure(result_obj)
            
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
            # Delegar a GenerateProposal use case
            generate_proposal = GenerateProposal(
                config=self.config,
                llm_client=self.vllm_client,
            )
            
            proposal = await generate_proposal.execute(
                task=request.task_description,
                constraints=request.constraints,
                diversity=request.diversity,
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

