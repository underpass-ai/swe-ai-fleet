"""
Workspace Runner: Consumes agent.requests and creates Kubernetes Jobs
for containerized workspace execution.
"""

import asyncio
import json
import logging
import os
from typing import Any

from kubernetes import client, config
from kubernetes.client.rest import ApiException
from natsx import NatsX

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WorkspaceRunner:
    """Manages workspace job lifecycle."""

    def __init__(self, nats_url: str = "nats://nats:4222", namespace: str = "swe"):
        self.nats_url = nats_url
        self.namespace = namespace
        self.nats: NatsX = NatsX(url=nats_url)

        # Load Kubernetes config (in-cluster or local kubeconfig)
        try:
            config.load_incluster_config()
            logger.info("Loaded in-cluster Kubernetes config")
        except config.ConfigException:
            config.load_kube_config()
            logger.info("Loaded local kubeconfig")

        self.batch_v1 = client.BatchV1Api()
        self.core_v1 = client.CoreV1Api()

    async def start(self):
        """Connect to NATS and start consuming."""
        await self.nats.connect()
        logger.info(f"Connected to NATS at {self.nats_url}")

        # Ensure streams
        await self.nats.ensure_stream("AGENT_WORK", ["agent.requests"], work_queue=True)
        await self.nats.ensure_stream("AGENT_RESP", ["agent.responses"])
        logger.info("Ensured NATS streams")

        # Create durable consumer
        subscriber = await self.nats.create_pull_consumer("AGENT_WORK", "workspace_runner")
        logger.info("Created pull consumer: workspace_runner")

        # Consume loop
        while True:
            try:
                msgs = await subscriber.fetch(batch=1, timeout=10.0)
                for msg in msgs:
                    await self.handle_request(msg)
                    await msg.ack()
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await asyncio.sleep(1)

    async def handle_request(self, msg):
        """Handle an agent request by creating a K8s Job."""
        try:
            payload = json.loads(msg.data)
            logger.info(f"Processing task: {payload.get('task_id')}")

            workspace_spec = payload.get("input", {}).get("workspace_spec")
            if not workspace_spec:
                logger.warning(f"No workspace_spec in task {payload.get('task_id')}")
                return

            # Create Kubernetes Job
            job_id = self.create_job(payload, workspace_spec)
            logger.info(f"Created Job: {job_id}")

            # Wait for job completion (in production, poll async)
            result = await self.wait_for_job(job_id)

            # Publish response
            await self.publish_response(payload, result)

        except Exception as e:
            logger.error(f"Failed to handle request: {e}")

    def create_job(self, request: dict[str, Any], spec: dict[str, Any]) -> str:
        """Create a Kubernetes Job for the workspace."""
        task_id = request.get("task_id", "unknown")
        job_id = f"ws-{task_id}"

        # Build Job manifest
        job = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(
                name=job_id,
                namespace=self.namespace,
                labels={"app": "workspace", "task_id": task_id},
            ),
            spec=client.V1JobSpec(
                ttl_seconds_after_finished=600,  # Auto-cleanup
                backoff_limit=2,
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(labels={"app": "workspace"}),
                    spec=client.V1PodSpec(
                        restart_policy="Never",
                        service_account_name="workspace-runner",
                        containers=[
                            client.V1Container(
                                name="agent",
                                image=spec.get(
                                    "image",
                                    "ghcr.io/underpass-ai/agent-workspace:tooling-2025.10",
                                ),
                                env=[
                                    client.V1EnvVar(name="TASK_ID", value=task_id),
                                    client.V1EnvVar(
                                        name="REPO_URL",
                                        value=spec.get("repo", {}).get("name", ""),
                                    ),
                                ],
                                command=["/bin/sh", "-c"],
                                args=[self.build_script(spec)],
                            )
                        ],
                    ),
                ),
            ),
        )

        try:
            self.batch_v1.create_namespaced_job(namespace=self.namespace, body=job)
            return job_id
        except ApiException as e:
            logger.error(f"Failed to create Job: {e}")
            raise

    def build_script(self, spec: dict[str, Any]) -> str:
        """Build shell script from workspace steps."""
        steps = spec.get("steps", [])
        script_lines = ["set -e"]  # Exit on error

        for step in steps:
            script_lines.append(f"echo '=== {step['name']} ==='")
            script_lines.append(step["run"])

        return " && ".join(script_lines)

    async def wait_for_job(self, job_id: str, timeout: int = 3600) -> dict[str, Any]:
        """Wait for Job to complete (simplified polling)."""
        import time

        start = time.time()
        while time.time() - start < timeout:
            try:
                job = self.batch_v1.read_namespaced_job(name=job_id, namespace=self.namespace)
                if job.status.succeeded:
                    return {"status": "ok", "job_id": job_id}
                elif job.status.failed:
                    return {"status": "error", "job_id": job_id, "reason": "Job failed"}

                await asyncio.sleep(5)
            except ApiException as e:
                logger.error(f"Failed to read Job status: {e}")
                return {"status": "error", "job_id": job_id, "reason": str(e)}

        return {"status": "error", "job_id": job_id, "reason": "Timeout"}

    async def publish_response(self, request: dict[str, Any], result: dict[str, Any]):
        """Publish agent.responses."""
        response = {
            "event_id": request.get("event_id"),
            "case_id": request.get("case_id"),
            "task_id": request.get("task_id"),
            "status": result.get("status"),
            "summary": f"Workspace job {result.get('job_id')} completed",
            "ts": "2025-10-07T12:00:00Z",  # TODO: use actual timestamp
            "workspace_report": {},  # TODO: parse artifacts
        }

        await self.nats.publish("agent.responses", response)
        logger.info(f"Published response for task {request.get('task_id')}")


async def main():
    """Main entry point."""
    nats_url = os.getenv("NATS_URL", "nats://nats:4222")
    namespace = os.getenv("K8S_NAMESPACE", "swe")

    runner = WorkspaceRunner(nats_url=nats_url, namespace=namespace)
    await runner.start()


if __name__ == "__main__":
    asyncio.run(main())



