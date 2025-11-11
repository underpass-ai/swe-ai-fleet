"""Mapper for LLM task derivation responses.

Infrastructure Mapper:
- Parses LLM text output → TaskNode VOs
- Anti-corruption layer (external format → domain)
- Handles LLM format variations
"""

import re
from typing import Any

from planning.domain.value_objects.actors.role import Role, RoleType
from planning.domain.value_objects.content.brief import Brief
from planning.domain.value_objects.content.title import Title
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.task_derivation.keyword import Keyword
from planning.domain.value_objects.task_derivation.task_node import TaskNode


class LLMTaskDerivationMapper:
    """Mapper for parsing LLM task derivation output.

    Following Hexagonal Architecture:
    - Infrastructure layer (mapper)
    - Converts external format (LLM text) → domain VOs
    - Handles parsing errors gracefully

    Expected LLM format:
    ```
    TASK_ID: TASK-001
    TITLE: Setup project structure
    DESCRIPTION: Create initial project folders and files
    ROLE: DEVELOPER
    KEYWORDS: setup, project, structure
    ---
    TASK_ID: TASK-002
    ...
    ```
    """

    @staticmethod
    def from_llm_text(text: str) -> tuple[TaskNode, ...]:
        """Parse LLM text response into TaskNode VOs.

        Args:
            text: LLM generated text with structured tasks

        Returns:
            Tuple of TaskNode value objects

        Raises:
            ValueError: If text format is invalid
        """
        # Split tasks by separator (---)
        raw_tasks = text.split("---")

        task_nodes = []

        for raw_task in raw_tasks:
            raw_task = raw_task.strip()

            if not raw_task:
                continue

            try:
                task_node = LLMTaskDerivationMapper._parse_single_task(raw_task)
                task_nodes.append(task_node)

            except Exception as e:
                # Log but continue - partial success better than total failure
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to parse task: {e}")
                continue

        if not task_nodes:
            raise ValueError("No valid tasks parsed from LLM output")

        return tuple(task_nodes)

    @staticmethod
    def _parse_single_task(text: str) -> TaskNode:
        """Parse a single task block.

        Args:
            text: Single task text block

        Returns:
            TaskNode value object

        Raises:
            ValueError: If required fields are missing
        """
        # Extract fields using regex
        task_id_match = re.search(r"TASK_ID:\s*(.+)", text, re.IGNORECASE)
        title_match = re.search(r"TITLE:\s*(.+)", text, re.IGNORECASE)
        description_match = re.search(r"DESCRIPTION:\s*(.+)", text, re.IGNORECASE)
        role_match = re.search(r"ROLE:\s*(.+)", text, re.IGNORECASE)
        keywords_match = re.search(r"KEYWORDS:\s*(.+)", text, re.IGNORECASE)

        # Validate required fields
        if not task_id_match:
            raise ValueError("Missing TASK_ID field")
        if not title_match:
            raise ValueError("Missing TITLE field")
        if not role_match:
            raise ValueError("Missing ROLE field")

        # Extract values
        task_id_str = task_id_match.group(1).strip()
        title_str = title_match.group(1).strip()
        description_str = description_match.group(1).strip() if description_match else title_str
        role_str = role_match.group(1).strip().upper()
        keywords_str = keywords_match.group(1).strip() if keywords_match else ""

        # Convert to VOs (string → domain objects)
        task_id = TaskId(task_id_str)
        title = Title(title_str)
        description = Brief(description_str)

        # Map role string to RoleType enum
        role = LLMTaskDerivationMapper._map_role(role_str)

        # Parse keywords (comma-separated)
        keywords = LLMTaskDerivationMapper._parse_keywords(keywords_str)

        # Build TaskNode (immutable VO)
        return TaskNode(
            task_id=task_id,
            title=title,
            description=description,
            role=role,
            keywords=keywords,
        )

    @staticmethod
    def _map_role(role_str: str) -> Role:
        """Map LLM role string to Role VO.

        Args:
            role_str: Role string from LLM (e.g. "DEVELOPER", "QA")

        Returns:
            Role value object
        """
        # Normalize
        role_str = role_str.upper().strip()

        # Map to RoleType enum
        role_mapping = {
            "DEVELOPER": RoleType.DEVELOPER,
            "DEV": RoleType.DEVELOPER,
            "QA": RoleType.QA,
            "TESTER": RoleType.QA,
            "ARCHITECT": RoleType.ARCHITECT,
            "ARCH": RoleType.ARCHITECT,
            "PO": RoleType.PO,
            "PRODUCT_OWNER": RoleType.PO,
        }

        role_type = role_mapping.get(role_str, RoleType.DEVELOPER)  # Default: DEVELOPER

        return Role(role_type)

    @staticmethod
    def _parse_keywords(keywords_str: str) -> tuple[Keyword, ...]:
        """Parse comma-separated keywords into Keyword VOs.

        Args:
            keywords_str: Comma-separated keywords

        Returns:
            Tuple of Keyword value objects
        """
        if not keywords_str:
            return ()

        # Split by comma and clean
        raw_keywords = keywords_str.split(",")
        keywords = []

        for raw_keyword in raw_keywords:
            keyword_str = raw_keyword.strip().lower()

            if keyword_str:
                try:
                    keywords.append(Keyword(keyword_str))
                except ValueError:
                    # Skip invalid keywords
                    continue

        return tuple(keywords)

