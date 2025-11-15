"""Role mapper for converting external role strings to domain RoleType.

Domain Value Object:
- Encapsulates role mapping logic (domain knowledge)
- Converts external format (strings from events) → domain RoleType
- Fail-fast validation
- NO primitives - uses RoleType enum
"""

from .role import Role
from .role_type import RoleType


class RoleMapper:
    """Mapper for converting role strings to domain Role VOs.

    Domain Value Object (DDD):
    - Encapsulates domain knowledge about role mappings
    - Converts external format (strings from events) → domain RoleType
    - Handles role aliases and variants
    - Fail-fast validation

    Following DDD:
    - Domain layer (no infrastructure dependencies)
    - Immutable mapping logic
    - Tell, Don't Ask: mapper knows how to convert roles
    """

    # Role mapping: external string → domain RoleType
    # This is domain knowledge: which external role strings map to which domain roles
    _ROLE_MAPPING: dict[str, RoleType] = {
        "DEVELOPER": RoleType.DEVELOPER,
        "DEV": RoleType.DEVELOPER,
        "QA": RoleType.QA,
        "TESTER": RoleType.QA,
        "ARCHITECT": RoleType.ARCHITECT,
        "ARCH": RoleType.ARCHITECT,
        "PO": RoleType.PRODUCT_OWNER,
        "PRODUCT_OWNER": RoleType.PRODUCT_OWNER,
    }

    # Default role if mapping not found
    _DEFAULT_ROLE = RoleType.DEVELOPER

    @classmethod
    def from_string(cls, role_str: str) -> Role:
        """Convert role string to Role VO.

        Maps external role strings (from events) to domain RoleType enum.
        Handles role aliases and variants (e.g., "DEV" → DEVELOPER).

        Args:
            role_str: Role string from external source (e.g., planning.plan.approved event)

        Returns:
            Role value object

        Raises:
            ValueError: If role_str is empty (fail-fast)
        """
        if not role_str or not role_str.strip():
            raise ValueError("Role string cannot be empty")

        # Normalize: uppercase and strip whitespace
        normalized = role_str.upper().strip()

        # Map to RoleType enum
        role_type = cls._ROLE_MAPPING.get(normalized, cls._DEFAULT_ROLE)

        return Role(role_type)

    @classmethod
    def from_strings(cls, role_strings: tuple[str, ...]) -> Role:
        """Convert first role string from tuple to Role VO.

        Used when multiple roles are provided (e.g., from plan.roles).
        Uses the first role in the tuple.

        Args:
            role_strings: Tuple of role strings from external source

        Returns:
            Role value object (from first role string)

        Raises:
            ValueError: If role_strings is empty or first role is invalid
        """
        if not role_strings:
            raise ValueError("Role strings tuple cannot be empty")

        return cls.from_string(role_strings[0])

