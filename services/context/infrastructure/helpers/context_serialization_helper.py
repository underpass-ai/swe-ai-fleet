"""Context serialization helper - Infrastructure layer.

Static helper methods for serializing and formatting context-related data.
Pure infrastructure concern: formatting for output/display.
"""


class ContextSerializationHelper:
    """Helper class for context serialization and formatting operations.

    All methods are static - no state needed.
    Pure infrastructure logic (no business rules).
    """

    @staticmethod
    def serialize_prompt_blocks(prompt_blocks) -> str:
        """Serialize PromptBlocks to a single context string.

        Args:
            prompt_blocks: PromptBlocks domain object

        Returns:
            Serialized string with sections separated by ---
        """
        sections = []

        if prompt_blocks.system:
            sections.append(f"# System\n\n{prompt_blocks.system}")

        if prompt_blocks.context:
            sections.append(f"# Context\n\n{prompt_blocks.context}")

        if prompt_blocks.tools:
            sections.append(f"# Tools\n\n{prompt_blocks.tools}")

        return "\n\n---\n\n".join(sections)

    @staticmethod
    def format_scope_reason(scope_check) -> str:
        """Format scope check result into human-readable reason.

        Args:
            scope_check: ScopeCheckResult domain object

        Returns:
            Human-readable formatted reason string
        """
        if scope_check.allowed:
            return "All scopes are allowed"

        parts = []
        if scope_check.missing:
            parts.append(f"Missing required scopes: {', '.join(scope_check.missing)}")
        if scope_check.extra:
            parts.append(f"Extra scopes not allowed: {', '.join(scope_check.extra)}")

        return "; ".join(parts)
