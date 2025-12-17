"""Neo4j adapter for Task Extraction Service.

Stores agent deliberations in Neo4j graph for observability.
"""

import asyncio
import json
import logging

from neo4j import Driver, GraphDatabase, Session
from backlog_review_processor.application.ports.storage_port import StoragePort
from backlog_review_processor.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from backlog_review_processor.domain.value_objects.identifiers.story_id import StoryId
from backlog_review_processor.domain.value_objects.review.agent_deliberation import (
    AgentDeliberation,
)
from backlog_review_processor.infrastructure.adapters.neo4j_config import Neo4jConfig

logger = logging.getLogger(__name__)


class Neo4jStorageAdapter(StoragePort):
    """Neo4j adapter for storing agent deliberations.

    Responsibilities:
    - Store agent deliberations as nodes in Neo4j
    - Link deliberations to ceremony and story
    - Enable querying of deliberations for observability

    Following Hexagonal Architecture:
    - Implements StoragePort (application layer interface)
    - Uses Neo4j driver (infrastructure detail)
    """

    def __init__(self, config: Neo4jConfig | None = None):
        """Initialize Neo4j adapter.

        Args:
            config: Neo4j configuration (defaults to from_env)
        """
        self.config = config or Neo4jConfig.from_env()
        self.driver: Driver = GraphDatabase.driver(
            self.config.uri,
            auth=(self.config.user, self.config.password),
        )
        self._init_constraints()
        logger.info(f"Neo4j adapter initialized: {self.config.uri}")

    def _init_constraints(self) -> None:
        """Initialize Neo4j constraints."""
        try:
            with self._session() as session:
                # Create unique constraint on AgentDeliberation node
                session.run(
                    """
                    CREATE CONSTRAINT agent_deliberation_id_unique IF NOT EXISTS
                    FOR (d:AgentDeliberation)
                    REQUIRE d.id IS UNIQUE
                    """
                )
                logger.info("✓ Neo4j constraints initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Neo4j constraints: {e}")

    def close(self) -> None:
        """Close Neo4j driver."""
        self.driver.close()
        logger.info("Neo4j driver closed")

    def _session(self) -> Session:
        """Get Neo4j session."""
        return self.driver.session(database=self.config.database)

    async def save_agent_deliberation(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        story_id: StoryId,
        deliberation: AgentDeliberation,
    ) -> None:
        """Save an agent deliberation to Neo4j.

        Creates:
        - AgentDeliberation node with deliberation details
        - Links to BacklogReviewCeremony node (if exists)
        - Links to Story node (if exists)

        Args:
            ceremony_id: Ceremony identifier
            story_id: Story identifier
            deliberation: Agent deliberation to save

        Raises:
            RuntimeError: If save fails
        """
        try:
            # Run in thread pool to avoid blocking
            await asyncio.to_thread(
                self._save_agent_deliberation_sync,
                ceremony_id,
                story_id,
                deliberation,
            )
            logger.info(
                f"Agent deliberation saved: ceremony={ceremony_id.value}, "
                f"story={story_id.value}, agent={deliberation.agent_id}, "
                f"role={deliberation.role.value}"
            )
        except Exception as e:
            error_msg = f"Failed to save agent deliberation: {e}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e

    def _save_agent_deliberation_sync(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        story_id: StoryId,
        deliberation: AgentDeliberation,
    ) -> None:
        """Synchronous save of agent deliberation.

        Args:
            ceremony_id: Ceremony identifier
            story_id: Story identifier
            deliberation: Agent deliberation to save
        """
        # Generate unique ID for deliberation
        import uuid

        deliberation_id = f"deliberation-{uuid.uuid4().hex[:12]}"

        # Serialize proposal
        if isinstance(deliberation.proposal, dict):
            proposal_json = json.dumps(deliberation.proposal)
        else:
            proposal_json = str(deliberation.proposal)

        with self._session() as session:
            # Create or update AgentDeliberation node
            session.run(
                """
                MERGE (d:AgentDeliberation {id: $deliberation_id})
                SET d.agent_id = $agent_id,
                    d.role = $role,
                    d.proposal = $proposal,
                    d.deliberated_at = $deliberated_at,
                    d.ceremony_id = $ceremony_id,
                    d.story_id = $story_id
                """,
                deliberation_id=deliberation_id,
                agent_id=deliberation.agent_id,
                role=deliberation.role.value,
                proposal=proposal_json,
                deliberated_at=deliberation.deliberated_at.isoformat(),
                ceremony_id=ceremony_id.value,
                story_id=story_id.value,
            )

            # Link to BacklogReviewCeremony if it exists (optional - ceremony may not exist yet)
            result = session.run(
                """
                MATCH (c:BacklogReviewCeremony {id: $ceremony_id})
                MATCH (d:AgentDeliberation {id: $deliberation_id})
                MERGE (d)-[:BELONGS_TO_CEREMONY]->(c)
                RETURN count(c) as count
                """,
                deliberation_id=deliberation_id,
                ceremony_id=ceremony_id.value,
            )
            ceremony_count = result.single()["count"] if result.peek() else 0
            if ceremony_count == 0:
                logger.debug(
                    f"BacklogReviewCeremony {ceremony_id.value} not found, "
                    f"skipping relationship creation"
                )

            # Link to Story if it exists (optional - story may not exist yet)
            result = session.run(
                """
                MATCH (s:Story {id: $story_id})
                MATCH (d:AgentDeliberation {id: $deliberation_id})
                MERGE (d)-[:FOR_STORY]->(s)
                RETURN count(s) as count
                """,
                deliberation_id=deliberation_id,
                story_id=story_id.value,
            )
            story_count = result.single()["count"] if result.peek() else 0
            if story_count == 0:
                logger.debug(
                    f"Story {story_id.value} not found, "
                    f"skipping relationship creation"
                )
