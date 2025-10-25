"""Agent role enumeration."""

from enum import Enum


class AgentRole(Enum):
    """Enumeration of valid agent roles.
    
    This enumeration centralizes all valid agent roles in the system,
    ensuring consistency across all entities and preventing magic strings.
    """
    
    DEV = "DEV"
    QA = "QA"
    ARCHITECT = "ARCHITECT"
    DEVOPS = "DEVOPS"
    DATA = "DATA"
    
    @classmethod
    def validate_role(cls, role: str) -> None:
        """Validate a role string and raise exception if invalid.
        
        Args:
            role: Role string to validate.
            
        Raises:
            ValueError: If role is not valid.
        """
        valid_roles = {role.value for role in cls}
        if role not in valid_roles:
            raise ValueError(f"Invalid agent role '{role}'. Must be one of: {', '.join(sorted(valid_roles))}")
    
    @classmethod
    def get_role_emoji(cls, role: str) -> str:
        """Get emoji for a specific role.
        
        Args:
            role: Role string.
            
        Returns:
            Emoji string for the role, or default emoji if not found.
        """
        role_emojis = {
            cls.DEV.value: "🧑‍💻",
            cls.QA.value: "🧪",
            cls.ARCHITECT.value: "🏗️",
            cls.DEVOPS.value: "⚙️",
            cls.DATA.value: "📊"
        }
        return role_emojis.get(role, "🤖")
    
    @classmethod
    def get_all_role_emojis(cls) -> dict[str, str]:
        """Get mapping of all roles to their emojis.
        
        Returns:
            Dictionary mapping role strings to emoji strings.
        """
        return {
            cls.DEV.value: "🧑‍💻",
            cls.QA.value: "🧪",
            cls.ARCHITECT.value: "🏗️",
            cls.DEVOPS.value: "⚙️",
            cls.DATA.value: "📊"
        }
