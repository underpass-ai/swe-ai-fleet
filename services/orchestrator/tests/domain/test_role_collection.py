"""Tests for RoleCollection entity."""

from services.orchestrator.domain.entities import RoleCollection, RoleConfig


class TestRoleCollection:
    """Test suite for RoleCollection entity."""
    
    def test_creation_empty(self):
        """Test creating empty collection."""
        collection = RoleCollection(roles=[])
        
        assert collection.count == 0
        assert collection.is_empty is True
    
    def test_creation_with_roles(self):
        """Test creating collection with roles."""
        roles = [
            RoleConfig(name="DEV", replicas=3),
            RoleConfig(name="QA", replicas=2)
        ]
        collection = RoleCollection(roles=roles)
        
        assert collection.count == 2
        assert collection.is_empty is False
    
    def test_create_default(self):
        """Test creating default role collection."""
        collection = RoleCollection.create_default()
        
        assert collection.count > 0
        role_names = [r.name for r in collection.roles]
        assert "DEV" in role_names  # Default roles use uppercase
    
    def test_get_role_names(self):
        """Test getting role names."""
        roles = [
            RoleConfig(name="DEV", replicas=3),
            RoleConfig(name="QA", replicas=2)
        ]
        collection = RoleCollection(roles=roles)
        
        names = collection.get_all_role_names()  # Fixed method name
        
        assert "DEV" in names
        assert "QA" in names
    
    def test_has_role(self):
        """Test checking if role exists."""
        roles = [RoleConfig(name="DEV", replicas=3)]
        collection = RoleCollection(roles=roles)
        
        assert collection.has_role("DEV") is True
        assert collection.has_role("NonExistent") is False

