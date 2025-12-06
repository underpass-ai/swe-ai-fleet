"""Scope detection helper - Infrastructure layer.

Static helper methods for detecting scopes in prompt blocks.
Pure infrastructure concern: technical scope detection.
"""

from services.context.utils import detect_scopes


class ScopeDetectionHelper:
    """Helper class for scope detection operations.

    All methods are static - no state needed.
    Delegates to domain service for actual detection logic.
    """

    @staticmethod
    def detect_scopes(prompt_blocks) -> list[str]:
        """Detect which scopes are present in the prompt blocks based on content sections.

        Args:
            prompt_blocks: PromptBlocks domain object

        Returns:
            List of detected scope identifiers

        Note:
            Delegates to domain service detect_scopes() for the actual detection logic.
            This helper exists to maintain consistency with other static helpers.
        """
        return detect_scopes(prompt_blocks)
