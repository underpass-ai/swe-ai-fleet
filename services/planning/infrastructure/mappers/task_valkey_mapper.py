"""Mapper: Domain Task ↔ Valkey dict format."""

from datetime import datetime

from planning.domain.entities.task import Task
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.statuses.task_status import TaskStatus
from planning.domain.value_objects.statuses.task_type import TaskType
from planning.infrastructure.mappers.task_valkey_fields import TaskValkeyFields


class TaskValkeyMapper:
    """
    Mapper: Convert domain Task to/from Valkey dict format.

    Infrastructure Layer Responsibility:
    - Domain entities should not know about Redis hash format
    - Conversions live in dedicated mappers (Hexagonal Architecture)
    """

    @staticmethod
    def _get_str_from_dict(
        data: dict[str, str] | dict[bytes, bytes],
        key: str,
        use_string_keys: bool,
    ) -> str:
        """
        Get string value from dict, handling both string and bytes keys.

        Args:
            data: Redis hash data (string or bytes keys/values).
            key: Field name to extract.
            use_string_keys: True if dict uses string keys, False for bytes keys.

        Returns:
            String value for the key.

        Raises:
            ValueError: If key is missing from dict.
        """
        if use_string_keys:
            # dict[str, str] - try string key
            # Mypy cannot narrow the union type after runtime check
            if key in data:
                value = data[key]  # type: ignore[index]
                return str(value)
            raise ValueError(f"Missing required field: {key}")

        # dict[bytes, bytes] - try bytes key
        # Mypy cannot narrow the union type after runtime check
        key_bytes = key.encode("utf-8")
        if key_bytes in data:
            value = data[key_bytes]  # type: ignore[index]
            if isinstance(value, bytes):
                return value.decode("utf-8")
            return str(value)
        raise ValueError(f"Missing required field: {key}")

    @staticmethod
    def _get_optional_str_from_dict(
        data: dict[str, str] | dict[bytes, bytes],
        key: str,
        use_string_keys: bool,
        default: str = "",
    ) -> str:
        """
        Get optional string value from dict, returning default if missing.

        Args:
            data: Redis hash data (string or bytes keys/values).
            key: Field name to extract.
            use_string_keys: True if dict uses string keys, False for bytes keys.
            default: Default value to return if key is missing.

        Returns:
            String value for the key, or default if missing.
        """
        if use_string_keys:
            # dict[str, str] - try string key
            # Mypy cannot narrow the union type after runtime check
            if key in data:
                value = data[key]  # type: ignore[index]
                return str(value)
            return default

        # dict[bytes, bytes] - try bytes key
        # Mypy cannot narrow the union type after runtime check
        key_bytes = key.encode("utf-8")
        if key_bytes in data:
            value = data[key_bytes]  # type: ignore[index]
            if isinstance(value, bytes):
                return value.decode("utf-8")
            return str(value)
        return default

    @staticmethod
    def to_dict(task: Task) -> dict[str, str]:
        """
        Convert domain Task to Valkey hash dict.

        Args:
            task: Domain Task entity.

        Returns:
            Dict suitable for Redis HSET (all values as strings).
        """
        data: dict[str, str] = {
            TaskValkeyFields.TASK_ID: task.task_id.value,
            TaskValkeyFields.STORY_ID: task.story_id.value,  # REQUIRED - domain invariant
            TaskValkeyFields.TITLE: task.title,
            TaskValkeyFields.TYPE: str(task.type),  # TaskType enum string value
            TaskValkeyFields.STATUS: str(task.status),  # TaskStatus enum string value
            TaskValkeyFields.ASSIGNED_TO: task.assigned_to,
            TaskValkeyFields.ESTIMATED_HOURS: str(task.estimated_hours),
            TaskValkeyFields.PRIORITY: str(task.priority),
            TaskValkeyFields.CREATED_AT: task.created_at.isoformat(),
            TaskValkeyFields.UPDATED_AT: task.updated_at.isoformat(),
        }

        # Optional fields (only include if not empty/None)
        if task.plan_id:
            data[TaskValkeyFields.PLAN_ID] = task.plan_id.value

        if task.description:
            data[TaskValkeyFields.DESCRIPTION] = task.description

        return data

    @staticmethod
    def from_dict(data: dict[str, str] | dict[bytes, bytes]) -> Task:
        """
        Convert Valkey hash dict to domain Task.

        Args:
            data: Redis hash data (string keys/values if decode_responses=True,
                  bytes keys/values if decode_responses=False).

        Returns:
            Domain Task entity.

        Raises:
            ValueError: If data is invalid or missing required fields.
        """
        if not data:
            raise ValueError("Cannot create Task from empty dict")

        # Determine key type once (string or bytes)
        # ValkeyConfig has decode_responses=True, so strings are expected
        # But we handle both for robustness
        sample_key = next(iter(data.keys()))
        use_string_keys = isinstance(sample_key, str)

        # Extract required fields
        task_id = TaskId(
            TaskValkeyMapper._get_str_from_dict(data, TaskValkeyFields.TASK_ID, use_string_keys)
        )
        story_id = StoryId(
            TaskValkeyMapper._get_str_from_dict(data, TaskValkeyFields.STORY_ID, use_string_keys)
        )  # REQUIRED - domain invariant
        title = TaskValkeyMapper._get_str_from_dict(data, TaskValkeyFields.TITLE, use_string_keys)
        task_type_str = TaskValkeyMapper._get_str_from_dict(
            data, TaskValkeyFields.TYPE, use_string_keys
        )
        status_str = TaskValkeyMapper._get_str_from_dict(
            data, TaskValkeyFields.STATUS, use_string_keys
        )
        created_at = datetime.fromisoformat(
            TaskValkeyMapper._get_str_from_dict(data, TaskValkeyFields.CREATED_AT, use_string_keys)
        )
        updated_at = datetime.fromisoformat(
            TaskValkeyMapper._get_str_from_dict(data, TaskValkeyFields.UPDATED_AT, use_string_keys)
        )

        # Extract optional fields
        plan_id_str = TaskValkeyMapper._get_optional_str_from_dict(
            data, TaskValkeyFields.PLAN_ID, use_string_keys
        )
        plan_id = PlanId(plan_id_str) if plan_id_str else None

        description = TaskValkeyMapper._get_optional_str_from_dict(
            data, TaskValkeyFields.DESCRIPTION, use_string_keys
        )
        assigned_to = TaskValkeyMapper._get_optional_str_from_dict(
            data, TaskValkeyFields.ASSIGNED_TO, use_string_keys
        )
        estimated_hours = int(
            TaskValkeyMapper._get_optional_str_from_dict(
                data, TaskValkeyFields.ESTIMATED_HOURS, use_string_keys, "0"
            )
        )
        priority = int(
            TaskValkeyMapper._get_optional_str_from_dict(
                data, TaskValkeyFields.PRIORITY, use_string_keys, "1"
            )
        )

        # Parse enums
        task_type = TaskType(task_type_str)
        status = TaskStatus(status_str)

        return Task(
            task_id=task_id,
            story_id=story_id,  # REQUIRED - domain invariant
            title=title,
            created_at=created_at,
            updated_at=updated_at,
            plan_id=plan_id,  # Optional
            description=description,
            assigned_to=assigned_to,
            estimated_hours=estimated_hours,
            type=task_type,
            status=status,
            priority=priority,
        )

