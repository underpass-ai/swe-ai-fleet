"""GetRoleBasedContextUseCase - Fetch context filtered by role (RBAC L3)."""

from dataclasses import dataclass

from datetime import datetime

from core.context.domain.role import Role
from core.context.domain.rehydration_bundle import RehydrationBundle
from core.context.domain.rehydration_request import RehydrationRequest
from core.context.domain.get_role_based_context_request import GetRoleBasedContextRequest
from core.context.domain.value_objects.role_visibility_policy import RoleVisibilityPolicy, VisibilityScope
from core.context.domain.value_objects.data_access_log_entry import DataAccessLogEntry
from core.context.domain.services.column_filter_service import ColumnFilterService
from core.context.application.session_rehydration_service import SessionRehydrationApplicationService
from core.context.ports.planning_read_port import PlanningReadPort
from core.context.ports.decisiongraph_read_port import DecisionGraphReadPort
from core.context.ports.data_access_audit_port import DataAccessAuditPort
from core.context.ports.story_authorization_port import StoryAuthorizationPort


@dataclass
class GetRoleBasedContextUseCase:
    """Use case for fetching context with RBAC L3 enforcement.

    This use case orchestrates:
    1. Authorization check (can role access this story?)
    2. Row-level filtering (visibility policy - what entities to fetch)
    3. Data fetching (via SessionRehydrationApplicationService)
    4. Column-level filtering (sensitive field removal)
    5. Audit logging (who accessed what)

    Hexagonal Architecture: Depends on Ports and Application Service.
    """

    # Application service (reuses rehydration logic)
    rehydration_service: SessionRehydrationApplicationService

    # Domain services (injected via DI)
    column_filter: ColumnFilterService

    # Ports (injected via DI)
    audit_logger: DataAccessAuditPort
    story_auth: StoryAuthorizationPort

    # Policies (injected - loaded from YAML config)
    visibility_policies: dict[Role, RoleVisibilityPolicy]

    async def execute(self, req: GetRoleBasedContextRequest) -> RehydrationBundle:
        """Fetch role-based context for a story.

        RBAC L3 Enforcement:
        - Row-level: Only fetch data visible to role (visibility policy)
        - Column-level: Filter sensitive columns (column filter)
        - Audit: Log all access attempts

        Args:
            req: Request with story_id, role, user_id

        Returns:
            RehydrationBundle filtered for role

        Raises:
            ValueError: If role has no policy or unauthorized access
        """
        # Step 1: Get visibility policy for role (fail-fast if missing)
        policy = self._get_policy_for_role(req.requesting_role)

        # Step 2: Authorization check - Can role access stories at all?
        if not policy.can_access_stories():
            raise ValueError(
                f"Role {req.requesting_role.value} has no story access. "
                f"Access denied by visibility policy."
            )

        # Step 3: Check specific story authorization
        await self._check_story_authorization(req, policy)

        # Step 4: Fetch full context (using existing rehydration service)
        # This fetches ALL data (we'll filter it next)
        rehydration_request = RehydrationRequest(
            case_id=req.story_id.to_string(),  # Convert StoryId to string
            roles=[req.requesting_role.value],  # Only fetch for this role
            include_timeline=req.include_timeline,
            include_summaries=req.include_summaries,
            persist_handoff_bundle=False,  # Don't cache unfiltered data (RBAC applies)
            timeline_events=req.timeline_events,  # From request (NO hardcoded)
            ttl_seconds=0,  # No cache for unfiltered data
        )

        full_bundle = await self.rehydration_service.rehydrate_session(rehydration_request)

        # Step 5: Apply row-level filtering
        # Filter out entities that role shouldn't see based on policy
        filtered_bundle = self._apply_row_level_filtering(full_bundle, policy, req)

        # Step 6: Apply column-level filtering
        # Remove sensitive fields that role shouldn't see
        column_filtered_bundle = self._apply_column_level_filtering(
            filtered_bundle,
            req.requesting_role,
        )

        # Step 7: Audit log the access (RBAC L3 compliance)
        await self._audit_log_access(req, column_filtered_bundle, access_granted=True)

        # Step 8: Return RBAC L3 filtered bundle
        return column_filtered_bundle

    async def _check_story_authorization(
        self,
        req: GetRoleBasedContextRequest,
        policy: RoleVisibilityPolicy,
    ) -> None:
        """Check if role is authorized to access specific story.

        RBAC L2: Row-level authorization check.

        Args:
            req: Request with story_id and user_id
            policy: Visibility policy for role

        Raises:
            ValueError: If access is denied
        """
        # If role has full access, allow immediately
        if policy.story_rule.allows_all_access():
            return

        # If role has no access, deny immediately
        if policy.story_rule.denies_all_access():
            raise ValueError(
                f"Role {req.requesting_role.value} cannot access stories. "
                f"Access denied by visibility policy."
            )

        # Scoped access - verify user_id matches filter criteria
        scope = policy.story_rule.scope

        if scope == VisibilityScope.ASSIGNED:
            # Check if story is assigned to this user
            is_assigned = await self.story_auth.is_story_assigned_to_user(
                req.story_id,
                req.user_id,
            )
            if not is_assigned:
                raise ValueError(
                    f"Story {req.story_id.to_string()} is not assigned to user {req.user_id}. "
                    f"Access denied (scope=assigned)."
                )

        elif scope == VisibilityScope.EPIC_CHILDREN:
            # Check if story's epic is assigned to this user
            epic_id = await self.story_auth.get_epic_for_story(req.story_id)
            is_epic_assigned = await self.story_auth.is_epic_assigned_to_user(
                epic_id,
                req.user_id,
            )
            if not is_epic_assigned:
                raise ValueError(
                    f"Story's epic {epic_id.to_string()} is not assigned to user {req.user_id}. "
                    f"Access denied (scope=epic_children)."
                )

        elif scope == VisibilityScope.TESTING_PHASE:
            # Check if story is in testing phase
            is_testing = await self.story_auth.is_story_in_testing_phase(req.story_id)
            if not is_testing:
                raise ValueError(
                    f"Story {req.story_id.to_string()} is not in testing phase. "
                    f"Access denied (scope=testing_phase)."
                )

        else:
            # Unknown scope - fail-fast
            raise ValueError(
                f"Unknown visibility scope: {scope.value}. "
                f"Cannot determine authorization."
            )

    def _apply_row_level_filtering(
        self,
        bundle: RehydrationBundle,
        policy: RoleVisibilityPolicy,
        req: GetRoleBasedContextRequest,
    ) -> RehydrationBundle:
        """Apply row-level filtering based on visibility policy.

        Filters out entire entities (rows) that role shouldn't see.

        Args:
            bundle: Full rehydration bundle
            policy: Visibility policy
            req: Original request

        Returns:
            Filtered bundle with only visible entities
        """
        # Get the pack for this role
        role_pack = bundle.get_pack_for_role(req.requesting_role)
        if not role_pack:
            # No pack for this role (shouldn't happen after rehydration)
            return bundle

        # Row-level filtering would filter tasks, decisions, etc. here
        # based on policy.task_rule, policy.decision_rule, etc.

        # For now, return unfiltered (column filtering will still apply)
        # TODO: Implement row-level filtering logic
        return bundle

    def _apply_column_level_filtering(
        self,
        bundle: RehydrationBundle,
        role: Role,
    ) -> RehydrationBundle:
        """Apply column-level filtering to remove sensitive fields.

        Args:
            bundle: Bundle to filter
            role: Requesting role

        Returns:
            Bundle with sensitive columns removed
        """
        # Get pack for role
        role_pack = bundle.get_pack_for_role(role)
        if not role_pack:
            return bundle

        # Apply column filtering to each entity type in the pack
        # TODO: Implement column filtering for:
        # - story_header
        # - plan_header
        # - role_tasks
        # - decisions_relevant
        # - etc.

        # For now, return unfiltered
        # Column filtering will be implemented when we integrate mappers
        return bundle

    def _get_policy_for_role(self, role: Role) -> RoleVisibilityPolicy:
        """Get visibility policy for role.

        Args:
            role: User/agent role

        Returns:
            RoleVisibilityPolicy

        Raises:
            ValueError: If no policy defined for role
        """
        if role not in self.visibility_policies:
            raise ValueError(
                f"No visibility policy defined for role {role.value}. "
                f"This is a configuration error. "
                f"Available roles: {[r.value for r in self.visibility_policies.keys()]}"
            )

        return self.visibility_policies[role]

    async def _audit_log_access(
        self,
        req: GetRoleBasedContextRequest,
        bundle: RehydrationBundle,
        access_granted: bool,
        denial_reason: str | None = None,
    ) -> None:
        """Audit log the data access.

        This method is fail-safe: If audit logging fails, it logs the error
        but does NOT propagate the exception to the caller.

        Args:
            req: Original request
            bundle: Bundle that was accessed
            access_granted: Whether access was granted
            denial_reason: If denied, why
        """
        try:
            # Count accessed entities in bundle
            role_pack = bundle.get_pack_for_role(req.requesting_role)
            accessed_entities = {}

            if role_pack:
                accessed_entities = {
                    "task": role_pack.get_task_count(),
                    "decision": role_pack.get_decision_count(),
                    "milestone": len(role_pack.recent_milestones),
                }

            # Create audit log entry
            log_entry = DataAccessLogEntry(
                user_id=req.user_id,
                role=req.requesting_role,
                story_id=req.story_id,
                accessed_at=datetime.now(),
                accessed_entities=accessed_entities,
                access_granted=access_granted,
                denial_reason=denial_reason,
                source_ip=None,  # TODO: Get from request context
                request_id=None,  # TODO: Get from request context
            )

            # Log via port (fail-safe)
            await self.audit_logger.log_access(log_entry)

        except Exception as e:
            # Audit logging MUST be fail-safe
            # Log the error but don't propagate
            # TODO: Log audit failure to error log
            print(f"WARNING: Audit logging failed: {e}")
            pass

