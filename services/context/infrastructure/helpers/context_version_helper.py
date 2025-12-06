"""Context versioning helper - Infrastructure layer.

Static helper methods for version generation and hashing.
Pure infrastructure concern: technical versioning operations.
"""

import hashlib
import time


class ContextVersionHelper:
    """Helper class for context versioning and hashing operations.

    All methods are static - no state needed.
    Pure infrastructure logic (no business rules).
    """

    @staticmethod
    def generate_version_hash(content: str) -> str:
        """Generate a version hash for the context.

        Args:
            content: Content string to hash

        Returns:
            16-character SHA256 hash of the content
        """
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    @staticmethod
    def generate_new_version(story_id: str) -> int:
        """Generate new version number for context.

        Uses timestamp-based versioning until proper version tracking is implemented.
        This ensures monotonically increasing versions.

        Args:
            story_id: Story identifier (currently unused, for future implementation)

        Returns:
            Unix timestamp as version number
        """
        # Use timestamp-based versioning
        return int(time.time())

    @staticmethod
    def generate_context_hash(story_id: str, version: int) -> str:
        """Generate hash for context verification.

        Args:
            story_id: Story identifier
            version: Version number

        Returns:
            16-character SHA256 hash combining story_id and version
        """
        content = f"{story_id}:{version}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
