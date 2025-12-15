from core.orchestrator.domain.agents.role import Role


class TestRole:
    def test_str_returns_name(self) -> None:
        role = Role(name="DEV")

        assert str(role) == "DEV"

    def test_is_devops_recognizes_variants(self) -> None:
        assert Role(name="devops").is_devops is True
        assert Role(name="DEV-OPS").is_devops is True
        assert Role(name="dev_ops").is_devops is True
        assert Role(name="DEV").is_devops is False

    def test_is_developer_recognizes_variants(self) -> None:
        assert Role(name="developer").is_developer is True
        assert Role(name="DEV").is_developer is True
        assert Role(name="programmer").is_developer is True
        assert Role(name="engineer").is_developer is True
        assert Role(name="QA").is_developer is False

    def test_is_architect_recognizes_variants(self) -> None:
        assert Role(name="architect").is_architect is True
        assert Role(name="ARCHITECTURE").is_architect is True
        assert Role(name="solution_architect").is_architect is True
        assert Role(name="DEV").is_architect is False

    def test_has_capability_returns_true_when_present(self) -> None:
        role = Role(name="DEV", capabilities=["coding", "testing"])

        assert role.has_capability("coding") is True
        assert role.has_capability("CODING") is True
        assert role.has_capability("testing") is True

    def test_has_capability_returns_false_when_absent(self) -> None:
        role = Role(name="DEV", capabilities=["coding"])

        assert role.has_capability("design") is False

    def test_has_capability_returns_false_when_capabilities_none(self) -> None:
        role = Role(name="DEV", capabilities=None)

        assert role.has_capability("coding") is False

    def test_from_string_creates_role_with_name(self) -> None:
        role = Role.from_string("DEV")

        assert role.name == "DEV"
        assert role.capabilities is None

    def test_from_string_creates_role_with_capabilities(self) -> None:
        role = Role.from_string("DEV", capabilities=["coding", "testing"])

        assert role.name == "DEV"
        assert role.capabilities == ["coding", "testing"]
