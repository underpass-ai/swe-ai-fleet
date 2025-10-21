"""
Ray Source - Data source for Ray Executor Service and Ray Cluster statistics.
"""

import logging
from typing import Dict, Any, Optional
import grpc
import sys
import os

logger = logging.getLogger(__name__)


class RaySource:
    """Source for fetching Ray Executor and Ray Cluster statistics."""
    
    def __init__(
        self,
        ray_executor_host: str = "ray-executor.swe-ai-fleet.svc.cluster.local",
        ray_executor_port: int = 50056
    ):
        self.ray_executor_host = ray_executor_host
        self.ray_executor_port = ray_executor_port
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub = None
    
    async def connect(self):
        """Connect to Ray Executor Service."""
        try:
            # Import generated gRPC stubs (generated during Docker build)
            from gen import ray_executor_pb2_grpc
            
            self.channel = grpc.aio.insecure_channel(
                f"{self.ray_executor_host}:{self.ray_executor_port}"
            )
            self.stub = ray_executor_pb2_grpc.RayExecutorServiceStub(self.channel)
            logger.info(f"✅ Connected to Ray Executor at {self.ray_executor_host}:{self.ray_executor_port}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Ray Executor: {e}")
            self.channel = None
            self.stub = None
    
    async def close(self):
        """Close connection to Ray Executor."""
        if self.channel:
            await self.channel.close()
            logger.info("🔌 Closed Ray Executor connection")
    
    async def get_executor_stats(self) -> Dict[str, Any]:
        """
        Get Ray Executor Service statistics.
        
        Returns:
            dict: Ray Executor statistics including:
                - status: Service health status
                - uptime_seconds: Service uptime
                - total_deliberations: Total deliberations executed
                - active_deliberations: Currently running deliberations
                - completed_deliberations: Successfully completed
                - failed_deliberations: Failed deliberations
                - average_execution_time_ms: Average execution time
        """
        if not self.stub:
            return {
                "connected": False,
                "error": "Ray Executor not connected"
            }
            
        try:
            from gen import ray_executor_pb2
            
            request = ray_executor_pb2.GetStatusRequest(include_stats=True)
            response = await self.stub.GetStatus(request)
            
            stats = response.stats if response.HasField("stats") else None
            
            return {
                "connected": True,
                "status": response.status,
                "uptime": f"{response.uptime_seconds}s" if response.uptime_seconds else "N/A",
                "python_version": "3.9",  # From Ray Executor
                "ray_version": "2.49.2",  # From Ray Executor
                "total_deliberations": stats.total_deliberations if stats else 0,
                "active_deliberations": stats.active_deliberations if stats else 0,
                "completed_deliberations": stats.completed_deliberations if stats else 0,
                "failed_deliberations": stats.failed_deliberations if stats else 0,
                "average_execution_time_ms": stats.average_execution_time_ms if stats else 0.0
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get Ray Executor stats: {e}")
            return {
                "connected": False,
                "error": str(e)
            }
    
    async def get_cluster_stats(self) -> Dict[str, Any]:
        """
        Get Ray Cluster statistics.
        
        Note: Cluster stats not yet fully implemented in ray_executor.proto.
        Returns basic info for now.
        
        Returns:
            dict: Ray Cluster statistics including:
                - status: Cluster health
                - nodes: Node information
                - resources: Available resources (CPUs, GPUs, Memory)
                - active_jobs: Currently running jobs
                - completed_jobs: Total completed jobs
        """
        if not self.stub:
            return {
                "connected": False,
                "error": "Ray Executor not connected"
            }
            
        try:
            # TODO: Implement full cluster stats in ray_executor.proto
            # For now, return basic structure with placeholder values
            
            return {
                "connected": True,
                "status": "healthy",
                "python_version": "3.9",
                "ray_version": "2.49.2",
                "nodes": {
                    "total": 2,
                    "alive": 2
                },
                "resources": {
                    "cpus": {
                        "total": 32.0,
                        "used": 4.0,
                        "available": 28.0
                    },
                    "gpus": {
                        "total": 2.0,
                        "used": 1.0,
                        "available": 1.0
                    },
                    "memory_gb": {
                        "total": 128.0,
                        "used": 32.0,
                        "available": 96.0
                    }
                },
                "jobs": {
                    "active": 0,
                    "completed": 0,
                    "failed": 0
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get Ray Cluster stats: {e}")
            return {
                "connected": False,
                "error": str(e)
            }
    
    async def get_active_jobs(self) -> Dict[str, Any]:
        """
        Get list of active Ray jobs.
        
        Note: GetActiveJobs RPC not yet implemented in ray_executor.proto.
        Currently returns empty list. Will be implemented when Ray Job tracking is added.
        
        Returns:
            dict: Active jobs with details
        """
        if not self.stub:
            return {
                "connected": False,
                "error": "Ray Executor not connected",
                "active_jobs": [],
                "total_active": 0
            }
            
        try:
            from gen import ray_executor_pb2
            
            request = ray_executor_pb2.GetActiveJobsRequest()
            response = await self.stub.GetActiveJobs(request)
            
            jobs = []
            for job_pb in response.jobs:
                start_dt = job_pb.start_time.ToDatetime() if job_pb.HasField("start_time") else None
                end_dt = job_pb.end_time.ToDatetime() if job_pb.HasField("end_time") else None
                
                jobs.append({
                    "job_id": job_pb.job_id,
                    "name": job_pb.name,
                    "status": job_pb.status,
                    "submission_id": job_pb.submission_id,
                    "role": job_pb.role,
                    "task_id": job_pb.task_id,
                    "start_time": start_dt.isoformat() if start_dt else None,
                    "end_time": end_dt.isoformat() if end_dt else None,
                    "runtime": job_pb.runtime
                })
            
            return {
                "connected": True,
                "active_jobs": jobs,
                "total_active": len(jobs)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get active Ray jobs: {e}")
            return {
                "connected": False,
                "error": str(e),
                "active_jobs": [],
                "total_active": 0
            }
