"""Environment configuration adapter for Backlog Review Processor Service."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class EnvironmentConfig:
    """Environment configuration for Backlog Review Processor Service."""

    nats_url: str
    planning_service_url: str
    ray_executor_url: str
    vllm_url: str
    vllm_model: str
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    neo4j_database: str

    @classmethod
    def from_env(cls) -> "EnvironmentConfig":
        """Create config from environment variables.

        Returns:
            EnvironmentConfig instance

        Raises:
            ValueError: If required env vars are missing
        """
        return cls(
            nats_url=os.getenv("NATS_URL", "nats://nats:4222"),
            planning_service_url=os.getenv(
                "PLANNING_SERVICE_URL", "planning:50054"
            ),
            ray_executor_url=os.getenv("RAY_EXECUTOR_URL", "ray-executor:50056"),
            vllm_url=os.getenv("VLLM_URL", "http://vllm-server:8000/v1"),
            vllm_model=os.getenv(
                "VLLM_MODEL", "meta-llama/Llama-3.1-8B-Instruct"
            ),
            neo4j_uri=os.getenv("NEO4J_URI", "bolt://neo4j:7687"),
            neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
            neo4j_password=os.getenv("NEO4J_PASSWORD", ""),
            neo4j_database=os.getenv("NEO4J_DATABASE", "neo4j"),
        )

    def get_neo4j_config(self) -> "Neo4jConfig":
        """Get Neo4j configuration.

        Returns:
            Neo4jConfig instance
        """
        from backlog_review_processor.infrastructure.adapters.neo4j_config import Neo4jConfig

        return Neo4jConfig(
            uri=self.neo4j_uri,
            user=self.neo4j_user,
            password=self.neo4j_password,
            database=self.neo4j_database,
        )
