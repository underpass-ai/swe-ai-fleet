"""RbacContextApplicationService - RBAC L3 enforcement for context retrieval.

This is an Application Service (NOT a Use Case) that orchestrates:
- Authorization checks (RBAC L1, L2, L3)
- Data fetching (via SessionRehydrationApplicationService)
- Row-level and column-level filtering
- Audit logging

It coordinates multiple domain services and ports to enforce role-based access control.
"""

from dataclasses import dataclass
from datetime import datetime

from core.context.domain.role import Role
from core.context.domain.entity_type import EntityType
from core.context.domain.rehydration_bundle import RehydrationBundle
from core.context.domain.rehydration_request import RehydrationRequest
from core.context.domain.get_role_based_context_request import GetRoleBasedContextRequest
from core.context.domain.value_objects.role_visibility_policy import RoleVisibilityPolicy, VisibilityScope
from core.context.domain.value_objects.data_access_log_entry import DataAccessLogEntry
from core.context.domain.value_objects.authorization_result import AuthorizationResult
from core.context.domain.services.column_filter_service import ColumnFilterService
from core.context.domain.services.authorization_checker import AuthorizationChecker
from core.context.application.session_rehydration_service import SessionRehydrationApplicationService
from core.context.ports.planning_read_port import PlanningReadPort
from core.context.ports.decisiongraph_read_port import DecisionGraphReadPort
from core.context.ports.data_access_audit_port import DataAccessAuditPort
from core.context.ports.story_authorization_port import StoryAuthorizationPort


@dataclass
class RbacContextApplicationService:
    """Application Service for fetching context with RBAC L3 enforcement.

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
    authorization_checker: AuthorizationChecker

    # Ports (injected via DI)
    audit_logger: DataAccessAuditPort

    # Policies (injected - loaded from YAML config)
    visibility_policies: dict[Role, RoleVisibilityPolicy]

    async def get_filtered_context(self, req: GetRoleBasedContextRequest) -> RehydrationBundle:
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
        Delegates to AuthorizationChecker domain service.

        Args:
            req: Request with story_id and user_id
            policy: Visibility policy for role

        Raises:
            ValueError: If access is denied
        """
        # Delegate to domain service (eliminates if/elif ladder)
        auth_result = await self.authorization_checker.check_story_access(
            story_id=req.story_id,
            user_id=req.user_id,
            rule=policy.story_rule,
        )

        # Fail-fast if denied
        if auth_result.was_denied():
            raise ValueError(
                f"Access denied for user {req.user_id} (role={req.requesting_role.value}) "
                f"to story {req.story_id.to_string()}: {auth_result.get_denial_reason()}"
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

        RBAC L3: Column-level security.
        Uses ColumnFilterService to remove sensitive fields based on role.

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

        # Apply column filtering to story_header
        filtered_story_header = self.column_filter.filter_entity(
            entity=role_pack.story_header,
            entity_type=EntityType.STORY,
            role=role,
        )

        # Apply column filtering to plan_header (if exists)
        filtered_plan_header = None
        if role_pack.plan_header:
            filtered_plan_header = self.column_filter.filter_entity(
                entity=role_pack.plan_header,
                entity_type=EntityType.PLAN,
                role=role,
            )

        # Apply column filtering to each task
        filtered_tasks = tuple(
            self.column_filter.filter_entity(
                entity=task,
                entity_type=EntityType.TASK,
                role=role,
            )
            for task in role_pack.role_tasks
        )

        # Apply column filtering to each decision
        filtered_decisions = tuple(
            self.column_filter.filter_entity(
                entity=decision,
                entity_type=EntityType.DECISION,
                role=role,
            )
            for decision in role_pack.decisions_relevant
        )

        # Apply column filtering to each milestone
        filtered_milestones = tuple(
            self.column_filter.filter_entity(
                entity=milestone,
                entity_type=EntityType.MILESTONE,
                role=role,
            )
            for milestone in role_pack.milestones
        )

        # Apply column filtering to each decision relation
        filtered_decision_deps = tuple(
            self.column_filter.filter_entity(
                entity=dep,
                entity_type=EntityType.DECISION_RELATION,
                role=role,
            )
            for dep in role_pack.decision_dependencies
        )

        # Apply column filtering to each impacted task
        filtered_impacted = tuple(
            self.column_filter.filter_entity(
                entity=impact,
                entity_type=EntityType.IMPACTED_TASK,
                role=role,
            )
            for impact in role_pack.impacted_tasks
        )

        # Reconstruct filtered pack
        from core.context.domain.role_context_fields import RoleContextFields

        filtered_pack = RoleContextFields(
            story_header=filtered_story_header,
            plan_header=filtered_plan_header,
            role_tasks=filtered_tasks,
            decisions_relevant=filtered_decisions,
            milestones=filtered_milestones,
            decision_dependencies=filtered_decision_deps,
            impacted_tasks=filtered_impacted,
            last_summary=role_pack.last_summary,  # Summary is text, no filtering needed
        )

        # Reconstruct bundle with filtered pack
        filtered_packs = {role: filtered_pack}

        from core.context.domain.rehydration_bundle import RehydrationBundle

        return RehydrationBundle(
            session_id=bundle.session_id,
            packs=filtered_packs,
        )

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
            import logging
            logger = logging.getLogger(__name__)
            logger.error(
                f"Audit logging failed for user {req.user_id} accessing story {req.story_id.to_string()}: {e}",
                exc_info=True,
            )

