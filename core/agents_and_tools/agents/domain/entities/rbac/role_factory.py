"""Factory for creating predefined roles with their allowed actions."""

from .action import ActionEnum, ScopeEnum
from .role import Role, RoleEnum


class RoleFactory:
    """Factory for creating predefined roles.

    This factory encapsulates the RBAC policy by defining which actions
    each role can perform. This is the single source of truth for role permissions.

    All roles are created as immutable Role value objects with their
    corresponding allowed actions and scope.

    Examples:
        >>> architect = RoleFactory.create_architect()
        >>> architect.get_name()
        'architect'
        >>> ActionEnum.APPROVE_DESIGN in architect.allowed_actions
        True
    """

    @staticmethod
    def create_architect() -> Role:
        """Create Architect role.

        Architect can:
        - Approve/reject architectural designs
        - Review architecture decisions
        - Make final technical decisions

        Tools: files (read/search), git (log/diff), db (query), http (get)
        Scope: Technical (read-only analysis)

        Returns:
            Role configured for Architect
        """
        return Role(
            value=RoleEnum.ARCHITECT,
            allowed_actions=frozenset([
                ActionEnum.APPROVE_DESIGN,
                ActionEnum.REJECT_DESIGN,
                ActionEnum.REVIEW_ARCHITECTURE,
            ]),
            allowed_tools=frozenset(["files", "git", "db", "http"]),
            scope=ScopeEnum.TECHNICAL,
        )

    @staticmethod
    def create_qa() -> Role:
        """Create QA role.

        QA can:
        - Approve/reject tests
        - Validate spec compliance
        - Validate acceptance criteria
        - NOT approve technical designs (out of scope)

        Tools: files (read/write tests), tests (pytest/go test), http (API testing)
        Scope: Quality

        Returns:
            Role configured for QA
        """
        return Role(
            value=RoleEnum.QA,
            allowed_actions=frozenset([
                ActionEnum.APPROVE_TESTS,
                ActionEnum.REJECT_TESTS,
                ActionEnum.VALIDATE_COMPLIANCE,
                ActionEnum.VALIDATE_SPEC,
            ]),
            allowed_tools=frozenset(["files", "tests", "http"]),
            scope=ScopeEnum.QUALITY,
        )

    @staticmethod
    def create_developer() -> Role:
        """Create Developer role.

        Developer can:
        - Execute tasks
        - Run tests
        - Commit code
        - NOT approve designs (Architect decides)

        Tools: files (read/write), git (add/commit/push), tests (pytest)
        Scope: Technical (full write access)

        Returns:
            Role configured for Developer
        """
        return Role(
            value=RoleEnum.DEVELOPER,
            allowed_actions=frozenset([
                ActionEnum.EXECUTE_TASK,
                ActionEnum.RUN_TESTS,
                ActionEnum.COMMIT_CODE,
            ]),
            allowed_tools=frozenset(["files", "git", "tests"]),
            scope=ScopeEnum.TECHNICAL,
        )

    @staticmethod
    def create_po() -> Role:
        """Create Product Owner role.

        PO can:
        - Approve/reject proposals
        - Request refinements
        - Approve scope
        - Modify constraints
        - Make final business decisions

        Tools: files (read-only for review), http (API testing)
        Scope: Business

        Returns:
            Role configured for Product Owner
        """
        return Role(
            value=RoleEnum.PO,
            allowed_actions=frozenset([
                ActionEnum.APPROVE_PROPOSAL,
                ActionEnum.REJECT_PROPOSAL,
                ActionEnum.REQUEST_REFINEMENT,
                ActionEnum.APPROVE_SCOPE,
                ActionEnum.MODIFY_CONSTRAINTS,
            ]),
            allowed_tools=frozenset(["files", "http"]),
            scope=ScopeEnum.BUSINESS,
        )

    @staticmethod
    def create_devops() -> Role:
        """Create DevOps role.

        DevOps can:
        - Deploy services
        - Configure infrastructure
        - Rollback deployments

        Tools: docker, files (Dockerfile/k8s), http (health checks), tests (e2e)
        Scope: Operations

        Returns:
            Role configured for DevOps
        """
        return Role(
            value=RoleEnum.DEVOPS,
            allowed_actions=frozenset([
                ActionEnum.DEPLOY_SERVICE,
                ActionEnum.CONFIGURE_INFRA,
                ActionEnum.ROLLBACK_DEPLOYMENT,
            ]),
            allowed_tools=frozenset(["docker", "files", "http", "tests"]),
            scope=ScopeEnum.OPERATIONS,
        )

    @staticmethod
    def create_data() -> Role:
        """Create Data role.

        Data can:
        - Execute database migrations
        - Validate schema changes

        Tools: db (postgres/neo4j/redis), files (migrations), tests (data validation)
        Scope: Data

        Returns:
            Role configured for Data
        """
        return Role(
            value=RoleEnum.DATA,
            allowed_actions=frozenset([
                ActionEnum.EXECUTE_MIGRATION,
                ActionEnum.VALIDATE_SCHEMA,
            ]),
            allowed_tools=frozenset(["db", "files", "tests"]),
            scope=ScopeEnum.DATA,
        )

    @staticmethod
    def create_role_by_name(name: str) -> Role:
        """Create role by name.

        Args:
            name: Role name (architect, qa, developer, po, devops, data)

        Returns:
            Role configured for the given name

        Raises:
            ValueError: If role name is not valid

        Examples:
            >>> role = RoleFactory.create_role_by_name("architect")
            >>> role.get_name()
            'architect'
        """
        role_creators = {
            "architect": RoleFactory.create_architect,
            "qa": RoleFactory.create_qa,
            "developer": RoleFactory.create_developer,
            "po": RoleFactory.create_po,
            "devops": RoleFactory.create_devops,
            "data": RoleFactory.create_data,
        }

        normalized_name = name.lower()
        if normalized_name not in role_creators:
            raise ValueError(
                f"Unknown role: {name}. Must be one of {sorted(role_creators.keys())}"
            )

        return role_creators[normalized_name]()

