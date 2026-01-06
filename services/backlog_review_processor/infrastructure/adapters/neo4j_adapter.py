"""Neo4j adapter for Task Extraction Service.

Stores agent deliberations in Neo4j graph for observability.
"""

import asyncio
import json
import logging

from backlog_review_processor.application.ports.storage_port import StoragePort
from backlog_review_processor.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from backlog_review_processor.domain.value_objects.identifiers.story_id import StoryId
from backlog_review_processor.domain.value_objects.review.agent_deliberation import (
    AgentDeliberation,
)
from backlog_review_processor.infrastructure.adapters.neo4j_config import Neo4jConfig
from neo4j import Driver, GraphDatabase, Session

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
            single_result = result.single()
            ceremony_count = single_result["count"] if single_result else 0
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
            single_result = result.single()
            story_count = single_result["count"] if single_result else 0
            if story_count == 0:
                logger.debug(
                    f"Story {story_id.value} not found, "
                    f"skipping relationship creation"
                )

    async def get_agent_deliberations(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        story_id: StoryId,
    ) -> list[AgentDeliberation]:
        """Get all agent deliberations for a ceremony and story.

        Args:
            ceremony_id: Ceremony identifier
            story_id: Story identifier

        Returns:
            List of AgentDeliberation value objects

        Raises:
            RuntimeError: If query fails
        """
        try:
            deliberations = await asyncio.to_thread(
                self._get_agent_deliberations_sync,
                ceremony_id,
                story_id,
            )
            logger.debug(
                f"Retrieved {len(deliberations)} deliberations for "
                f"ceremony={ceremony_id.value}, story={story_id.value}"
            )
            return deliberations
        except Exception as e:
            error_msg = f"Failed to get agent deliberations: {e}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e

    def _get_agent_deliberations_sync(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        story_id: StoryId,
    ) -> list[AgentDeliberation]:
        """Synchronous retrieval of agent deliberations.

        Args:
            ceremony_id: Ceremony identifier
            story_id: Story identifier

        Returns:
            List of AgentDeliberation value objects
        """
        from datetime import datetime

        from backlog_review_processor.domain.value_objects.statuses.backlog_review_role import (
            BacklogReviewRole,
        )

        with self._session() as session:
            result = session.run(
                """
                MATCH (d:AgentDeliberation)
                WHERE d.ceremony_id = $ceremony_id AND d.story_id = $story_id
                RETURN d.agent_id as agent_id,
                       d.role as role,
                       d.proposal as proposal,
                       d.deliberated_at as deliberated_at
                ORDER BY d.deliberated_at ASC
                """,
                ceremony_id=ceremony_id.value,
                story_id=story_id.value,
            )

            deliberations = []
            for record in result:
                # Parse proposal (JSON string or plain string)
                proposal_raw = record["proposal"]
                if isinstance(proposal_raw, str):
                    try:
                        proposal = json.loads(proposal_raw)
                    except json.JSONDecodeError:
                        proposal = proposal_raw
                else:
                    proposal = proposal_raw

                # Parse role
                role_str = record["role"]
                role = BacklogReviewRole(role_str)

                # Parse deliberated_at
                deliberated_at_str = record["deliberated_at"]
                deliberated_at = datetime.fromisoformat(deliberated_at_str)

                deliberation = AgentDeliberation(
                    agent_id=record["agent_id"],
                    role=role,
                    proposal=proposal,
                    deliberated_at=deliberated_at,
                )
                deliberations.append(deliberation)

            return deliberations

    async def has_all_role_deliberations(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        story_id: StoryId,
    ) -> bool:
        """Check if all required roles (ARCHITECT, QA, DEVOPS) have deliberations.

        Args:
            ceremony_id: Ceremony identifier
            story_id: Story identifier

        Returns:
            True if all 3 roles have at least one deliberation, False otherwise

        Raises:
            RuntimeError: If query fails
        """
        try:
            has_all = await asyncio.to_thread(
                self._has_all_role_deliberations_sync,
                ceremony_id,
                story_id,
            )
            return has_all
        except Exception as e:
            error_msg = f"Failed to check role deliberations: {e}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e

    def _has_all_role_deliberations_sync(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        story_id: StoryId,
    ) -> bool:
        """Synchronous check for all role deliberations.

        Args:
            ceremony_id: Ceremony identifier
            story_id: Story identifier

        Returns:
            True if all 3 roles have at least one deliberation, False otherwise
        """
        from backlog_review_processor.domain.value_objects.statuses.backlog_review_role import (
            BacklogReviewRole,
        )

        required_roles = {
            BacklogReviewRole.ARCHITECT.value,
            BacklogReviewRole.QA.value,
            BacklogReviewRole.DEVOPS.value,
        }

        with self._session() as session:
            result = session.run(
                """
                MATCH (d:AgentDeliberation)
                WHERE d.ceremony_id = $ceremony_id AND d.story_id = $story_id
                RETURN DISTINCT d.role as role
                """,
                ceremony_id=ceremony_id.value,
                story_id=story_id.value,
            )

            roles_with_deliberations = {record["role"] for record in result}
            has_all = required_roles.issubset(roles_with_deliberations)

            logger.debug(
                f"Role check for ceremony={ceremony_id.value}, story={story_id.value}: "
                f"required={required_roles}, found={roles_with_deliberations}, "
                f"has_all={has_all}"
            )

            return has_all
