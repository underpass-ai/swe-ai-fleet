"""Mapper for LLM task derivation responses.

Infrastructure Mapper:
- Parses LLM text output → TaskNode VOs
- Anti-corruption layer (external format → domain)
- Handles LLM format variations
"""

import re
from uuid import uuid4

# Role removed - Planning Service assigns roles based on RBAC and event context, NOT from LLM
from planning.domain.value_objects.content.task_description import TaskDescription
from planning.domain.value_objects.content.title import Title
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.task_attributes.duration import Duration
from planning.domain.value_objects.task_attributes.priority import Priority
from planning.domain.value_objects.task_derivation.keyword import Keyword
from planning.domain.value_objects.task_derivation.task_node import TaskNode


class LLMTaskDerivationMapper:
    """Mapper for parsing LLM task derivation output.

    Following Hexagonal Architecture:
    - Infrastructure layer (mapper)
    - Converts external format (LLM text) → domain VOs
    - Handles parsing errors gracefully

    Expected LLM format (strict, enforced by prompt template):
    ```
    TITLE: Setup project structure
    DESCRIPTION: Create initial project folders and files
    ESTIMATED_HOURS: 8
    PRIORITY: 1
    KEYWORDS: setup, project, structure
    ---
    TITLE: Create database schema
    DESCRIPTION: Design and implement database tables
    ESTIMATED_HOURS: 16
    PRIORITY: 2
    KEYWORDS: database, schema, tables
    ```

    Format rules (enforced by prompt template):
    - Fields in exact order: TITLE, DESCRIPTION, ESTIMATED_HOURS, PRIORITY, KEYWORDS
    - Each field on single line (no multiline values)
    - Field names uppercase with underscore
    - Tasks separated by "---" on its own line
    - No markdown formatting or code blocks
    - Do NOT include TASK_ID - Planning Service generates task IDs automatically
    - Do NOT include ROLE - Planning Service assigns roles based on RBAC and event context

    Important:
    - Planning Service generates TaskId when creating tasks (e.g., "T-{uuid}")
    - Planning Service assigns roles based on RBAC and event context (NOT from LLM)
    - Dependencies are inferred from keyword matching in the graph context (Neo4j relationships)
    - ESTIMATED_HOURS is optional. If missing, defaults to 0 (not estimated).
    - PRIORITY is optional. If missing, defaults to 1 (highest priority).
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
        # Extract fields using regex with proper boundaries
        # LLM is not idempotent - capture until next field or end of text
        # Use non-greedy match (.+?) and lookahead for next field or end
        # Pattern: FIELD_NAME: value (capture until \nFIELD_NAME: or end)
        field_boundary = r"(?=\n[A-Z_]+:|$)"

        title_match = re.search(
            r"TITLE:\s*(.+?)" + field_boundary,
            text,
            re.IGNORECASE | re.MULTILINE | re.DOTALL,
        )
        description_match = re.search(
            r"DESCRIPTION:\s*(.+?)" + field_boundary,
            text,
            re.IGNORECASE | re.MULTILINE | re.DOTALL,
        )
        estimated_hours_match = re.search(
            r"ESTIMATED_HOURS:\s*(\d+)" + field_boundary,
            text,
            re.IGNORECASE | re.MULTILINE,
        )
        priority_match = re.search(
            r"PRIORITY:\s*(\d+)" + field_boundary,
            text,
            re.IGNORECASE | re.MULTILINE,
        )
        keywords_match = re.search(
            r"KEYWORDS:\s*(.+?)" + field_boundary,
            text,
            re.IGNORECASE | re.MULTILINE | re.DOTALL,
        )

        # Validate required fields
        if not title_match:
            raise ValueError("Missing TITLE field")

        # Extract values
        title_str = title_match.group(1).strip()
        description_str = description_match.group(1).strip() if description_match else title_str
        estimated_hours_str = estimated_hours_match.group(1).strip() if estimated_hours_match else "0"
        priority_str = priority_match.group(1).strip() if priority_match else "1"  # Default to 1 if missing
        keywords_str = keywords_match.group(1).strip() if keywords_match else ""

        # Convert to VOs (string → domain objects)
        title = Title(title_str)
        description = TaskDescription(description_str)

        # Role is NOT parsed from LLM - Planning Service assigns roles based on RBAC and event context

        # Parse estimated hours (default to 0 if missing)
        try:
            estimated_hours_int = int(estimated_hours_str)
        except ValueError:
            estimated_hours_int = 0

        estimated_hours = Duration(estimated_hours_int)

        # Parse priority (default to 1 if missing)
        try:
            priority_int = int(priority_str)
        except ValueError:
            priority_int = 1

        priority = Priority(priority_int)

        # Parse keywords (comma-separated)
        keywords = LLMTaskDerivationMapper._parse_keywords(keywords_str)

        # Generate temporary TaskId for TaskNode (Planning Service generates real TaskId later)
        # TaskNode needs task_id for dependency graph, but LLM doesn't generate it
        temp_task_id = TaskId(f"TEMP-{uuid4()}")

        # Build TaskNode (immutable VO)
        # Note: role is optional - Planning Service assigns roles based on RBAC and event context
        return TaskNode(
            task_id=temp_task_id,  # Temporary ID for graph - Planning Service generates real ID
            title=title,
            description=description,
            keywords=keywords,
            estimated_hours=estimated_hours,
            priority=priority,
        )

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

