#!/usr/bin/env python3
"""
Ray Executor Service

Microservicio dedicado a ejecutar deliberaciones en Ray cluster.
Responsabilidad única: ejecutar VLLMAgentJob en Ray workers.
"""

import asyncio
import json
import logging
import os
import sys
import time
from typing import Dict, Optional

# Add /app/src to path for imports
sys.path.insert(0, '/app/src')

import grpc
from grpc import aio as grpc_aio
import nats
from nats.js import JetStreamContext

# Import generated gRPC code
from gen import ray_executor_pb2
from gen import ray_executor_pb2_grpc

# Import Ray and VLLM components
import ray

# Import VLLMAgentJob from swe_ai_fleet
from swe_ai_fleet.ray_jobs.vllm_agent_job import VLLMAgentJob

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

class RayExecutorServiceServicer(ray_executor_pb2_grpc.RayExecutorServiceServicer):
    """gRPC servicer for Ray Executor Service."""
    
    def __init__(self):
        self.start_time = time.time()
        self.deliberations: Dict[str, Dict] = {}  # deliberation_id -> info
        self.stats = {
            'total_deliberations': 0,
            'active_deliberations': 0,
            'completed_deliberations': 0,
            'failed_deliberations': 0,
            'execution_times': []
        }
        
        # NATS connection for streaming events
        self.nats_client = None
        self.js: JetStreamContext = None
        
        # Initialize Ray connection
        ray_address = os.getenv('RAY_ADDRESS', 'ray://ray-gpu-head-svc.ray.svc.cluster.local:10001')
        logger.info(f"🔗 Connecting to Ray cluster at: {ray_address}")
        
        try:
            ray.init(address=ray_address, ignore_reinit_error=True)
            logger.info("✅ Ray connection established")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Ray: {e}")
            raise
    
    async def init_nats(self):
        """Initialize NATS connection for streaming events."""
        nats_url = os.getenv('NATS_URL', 'nats://nats.swe-ai-fleet.svc.cluster.local:4222')
        try:
            self.nats_client = await nats.connect(nats_url)
            self.js = self.nats_client.jetstream()
            logger.info("✅ NATS connection established for streaming")
        except Exception as e:
            logger.error(f"❌ Failed to connect to NATS: {e}")
            # Don't raise - streaming is optional
    
    async def publish_stream_event(self, event_type: str, agent_id: str, data: Dict):
        """Publish streaming event to NATS."""
        if not self.js:
            return
            
        try:
            event = {
                "type": event_type,
                "agent_id": agent_id,
                "timestamp": time.time(),
                **data
            }
            
            subject = f"vllm.streaming.{agent_id}"
            await self.js.publish(subject, json.dumps(event).encode())
            
        except Exception as e:
            logger.warning(f"Failed to publish stream event: {e}")

    async def ExecuteDeliberation(self, request, context):
        """Execute deliberation on Ray cluster."""
        deliberation_id = f"deliberation-{request.task_id}-{int(time.time())}"
        
        logger.info(f"🚀 Executing deliberation: {deliberation_id}")
        logger.info(f"   Task: {request.task_description}")
        logger.info(f"   Role: {request.role}")
        logger.info(f"   Agents: {len(request.agents)}")
        
        try:
            # Create VLLMAgentJob as Ray actor for each agent in the request
            # For now, we'll create one job per role (simplified)
            # TODO: Handle multiple agents properly
            agent = request.agents[0] if request.agents else None
            if not agent:
                raise ValueError("At least one agent required")
            
            agent_job = VLLMAgentJob.remote(
                agent_id=agent.id,
                role=agent.role,
                vllm_url=request.vllm_url,
                model=request.vllm_model,
                nats_url=os.getenv('NATS_URL', 'nats://nats.swe-ai-fleet.svc.cluster.local:4222'),
                workspace_path=None,  # No workspace path for now (text-only mode)
                enable_tools=False,   # Disabled for now (requires workspace in Ray worker)
            )
            
            # Submit to Ray
            logger.info("📤 Submitting to Ray cluster...")
            future = agent_job.run.remote(
                task_id=request.task_id,
                task_description=request.task_description,
                constraints={
                    'story_id': request.constraints.story_id,
                    'plan_id': request.constraints.plan_id,
                    'timeout': request.constraints.timeout_seconds
                }
            )
            
            # Store deliberation info
            self.deliberations[deliberation_id] = {
                'future': future,
                'task_id': request.task_id,
                'role': request.role,
                'status': 'running',
                'start_time': time.time(),
                'agents': [agent.id for agent in request.agents]
            }
            
            self.stats['total_deliberations'] += 1
            self.stats['active_deliberations'] += 1
            
            # Publish stream start event
            await self.publish_stream_event(
                "vllm_stream_start",
                deliberation_id,
                {
                    "task_description": request.task_description,
                    "role": request.role,
                    "status": "streaming",
                    "model": request.vllm_model,
                    "deliberation_id": deliberation_id
                }
            )
            
            logger.info(f"✅ Deliberation submitted to Ray: {deliberation_id}")
            
            return ray_executor_pb2.ExecuteDeliberationResponse(
                deliberation_id=deliberation_id,
                status="submitted",
                message=f"Deliberation submitted to Ray cluster"
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to execute deliberation: {e}")
            self.stats['failed_deliberations'] += 1
            
            return ray_executor_pb2.ExecuteDeliberationResponse(
                deliberation_id=deliberation_id,
                status="failed",
                message=f"Failed to execute deliberation: {str(e)}"
            )

    async def GetDeliberationStatus(self, request, context):
        """Get status of a running deliberation."""
        deliberation_id = request.deliberation_id
        
        if deliberation_id not in self.deliberations:
            return ray_executor_pb2.GetDeliberationStatusResponse(
                status="not_found",
                error_message=f"Deliberation {deliberation_id} not found"
            )
        
        deliberation = self.deliberations[deliberation_id]
        
        try:
            # Check if Ray job is ready
            if ray.wait([deliberation['future']], timeout=0.1)[0]:
                # Job completed
                result = ray.get(deliberation['future'])
                
                deliberation['status'] = 'completed'
                deliberation['result'] = result
                deliberation['end_time'] = time.time()
                
                execution_time = deliberation['end_time'] - deliberation['start_time']
                self.stats['execution_times'].append(execution_time)
                self.stats['active_deliberations'] -= 1
                self.stats['completed_deliberations'] += 1
                
                logger.info(f"✅ Deliberation completed: {deliberation_id} (took {execution_time:.2f}s)")
                
                # Convert result to protobuf
                deliberation_result = ray_executor_pb2.DeliberationResult(
                    agent_id=result.get('agent_id', 'unknown'),
                    proposal=result.get('proposal', ''),
                    reasoning=result.get('reasoning', ''),
                    score=result.get('score', 0.0),
                    metadata=result.get('metadata', {})
                )
                
                return ray_executor_pb2.GetDeliberationStatusResponse(
                    status="completed",
                    result=deliberation_result
                )
            
            else:
                # Job still running
                return ray_executor_pb2.GetDeliberationStatusResponse(
                    status="running"
                )
                
        except Exception as e:
            logger.error(f"❌ Error checking deliberation status: {e}")
            deliberation['status'] = 'failed'
            deliberation['error'] = str(e)
            self.stats['active_deliberations'] -= 1
            self.stats['failed_deliberations'] += 1
            
            return ray_executor_pb2.GetDeliberationStatusResponse(
                status="failed",
                error_message=str(e)
            )

    async def GetStatus(self, request, context):
        """Get service health and statistics."""
        uptime = time.time() - self.start_time
        
        # Calculate average execution time
        avg_time = 0.0
        if self.stats['execution_times']:
            avg_time = sum(self.stats['execution_times']) / len(self.stats['execution_times'])
            avg_time *= 1000  # Convert to milliseconds
        
        stats = ray_executor_pb2.RayExecutorStats(
            total_deliberations=self.stats['total_deliberations'],
            active_deliberations=self.stats['active_deliberations'],
            completed_deliberations=self.stats['completed_deliberations'],
            failed_deliberations=self.stats['failed_deliberations'],
            average_execution_time_ms=avg_time
        )
        
        return ray_executor_pb2.GetStatusResponse(
            status="healthy",
            uptime_seconds=int(uptime),
            stats=stats
        )
    
    async def GetActiveJobs(self, request, context):
        """Get list of active Ray jobs."""
        try:
            from google.protobuf.timestamp_pb2 import Timestamp
            
            jobs = []
            current_time = time.time()
            
            for deliberation_id, delib_info in self.deliberations.items():
                # Only include running jobs
                if delib_info.get('status') != 'running':
                    continue
                
                # Calculate runtime
                start_time = delib_info.get('start_time', current_time)
                runtime_seconds = int(current_time - start_time)
                minutes = runtime_seconds // 60
                seconds = runtime_seconds % 60
                runtime_str = f"{minutes}m {seconds}s"
                
                # Create start_time timestamp
                start_timestamp = Timestamp()
                start_timestamp.FromSeconds(int(start_time))
                
                # Create JobInfo message
                job_info = ray_executor_pb2.JobInfo(
                    job_id=deliberation_id,
                    name=f"vllm-agent-job-{deliberation_id}",
                    status="RUNNING",
                    submission_id=deliberation_id,
                    role=delib_info.get('role', 'UNKNOWN'),
                    task_id=delib_info.get('task_id', 'unknown'),
                    start_time=start_timestamp,
                    runtime=runtime_str
                )
                
                jobs.append(job_info)
            
            logger.info(f"📊 Returning {len(jobs)} active jobs")
            return ray_executor_pb2.GetActiveJobsResponse(jobs=jobs)
            
        except Exception as e:
            logger.error(f"❌ Error getting active jobs: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return ray_executor_pb2.GetActiveJobsResponse()

async def serve():
    """Start the gRPC server."""
    port = int(os.getenv('GRPC_PORT', '50056'))
    
    logger.info(f"🚀 Starting Ray Executor Service on port {port}")
    
    server = grpc_aio.server()
    
    # Add servicer
    servicer = RayExecutorServiceServicer()
    ray_executor_pb2_grpc.add_RayExecutorServiceServicer_to_server(servicer, server)
    
    # Initialize NATS for streaming
    await servicer.init_nats()
    
    # Start server
    listen_addr = f'[::]:{port}'
    server.add_insecure_port(listen_addr)
    
    logger.info(f"✅ Ray Executor Service listening on {listen_addr}")
    await server.start()
    
    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down Ray Executor Service...")
        await server.stop(grace=5.0)
        ray.shutdown()

if __name__ == '__main__':
    asyncio.run(serve())
