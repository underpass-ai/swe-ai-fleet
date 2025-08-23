"""Context utilities.

Small helper utilities for the `context` package.
"""

from __future__ import annotations

from typing import Any


class AttrUtils:
    """Attribute access helpers."""

    @staticmethod
    def pick_attr(
        primary: Any | None,
        fallback: Any | None,
        attr: str,
        default: Any,
    ) -> Any:
        """Return `attr` from `primary`, else from `fallback`, else `default`.

        This avoids repetitive conditional attribute access when combining
        data from multiple potential sources.
        """
        if primary is not None:
            return getattr(primary, attr)
        if fallback is not None:
            return getattr(fallback, attr)
        return default
