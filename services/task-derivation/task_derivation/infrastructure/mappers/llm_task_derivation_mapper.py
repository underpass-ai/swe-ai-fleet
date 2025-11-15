"""Mapper for LLM task derivation responses."""

from __future__ import annotations

import logging
import re
from typing import Any
from uuid import uuid4

from task_derivation.domain.value_objects.content.task_description import TaskDescription
from task_derivation.domain.value_objects.content.title import Title
from task_derivation.domain.value_objects.identifiers.task_id import TaskId
from task_derivation.domain.value_objects.task_attributes.duration import Duration
from task_derivation.domain.value_objects.task_attributes.priority import Priority
from task_derivation.domain.value_objects.task_derivation.dependency.keyword import (
    Keyword,
)
from task_derivation.domain.value_objects.task_derivation.dependency.task_node import (
    TaskNode,
)


class LLMTaskDerivationMapper:
    """Parse raw LLM output into TaskNode value objects."""

    @staticmethod
    def from_llm_text(text: str) -> tuple[TaskNode, ...]:
        """Parse LLM text response into TaskNode VOs."""
        raw_tasks = text.split("---")
        task_nodes: list[TaskNode] = []

        for raw_task in raw_tasks:
            raw_task = raw_task.strip()
            if not raw_task:
                continue

            try:
                task_nodes.append(LLMTaskDerivationMapper._parse_single_task(raw_task))
            except Exception as exc:  # pragma: no cover - logging branch
                logging.getLogger(__name__).warning("Failed to parse task: %s", exc)
                continue

        if not task_nodes:
            raise ValueError("No valid tasks parsed from LLM output")

        return tuple(task_nodes)

    @staticmethod
    def _parse_single_task(text: str) -> TaskNode:
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

        if not title_match:
            raise ValueError("Missing TITLE field")

        title_str = title_match.group(1).strip()
        description_str = (
            description_match.group(1).strip() if description_match else title_str
        )
        estimated_hours_str = (
            estimated_hours_match.group(1).strip() if estimated_hours_match else "0"
        )
        priority_str = priority_match.group(1).strip() if priority_match else "1"
        keywords_str = keywords_match.group(1).strip() if keywords_match else ""

        try:
            estimated_hours = Duration(int(estimated_hours_str))
        except ValueError:
            estimated_hours = Duration(0)

        try:
            priority = Priority(int(priority_str))
        except ValueError:
            priority = Priority(1)

        keywords = LLMTaskDerivationMapper._parse_keywords(keywords_str)

        return TaskNode(
            task_id=TaskId(f"TEMP-{uuid4()}"),
            title=Title(title_str),
            description=TaskDescription(description_str),
            keywords=keywords,
            estimated_hours=estimated_hours,
            priority=priority,
        )

    @staticmethod
    def _parse_keywords(keywords_str: str) -> tuple[Keyword, ...]:
        if not keywords_str:
            return ()

        keywords: list[Keyword] = []
        for raw_keyword in keywords_str.split(","):
            value = raw_keyword.strip().lower()
            if not value:
                continue
            try:
                keywords.append(Keyword(value))
            except ValueError:
                continue

        return tuple(keywords)

