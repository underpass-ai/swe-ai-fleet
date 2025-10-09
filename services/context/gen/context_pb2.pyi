from collections.abc import Iterable as _Iterable
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf.internal import containers as _containers

DESCRIPTOR: _descriptor.FileDescriptor

class GetContextRequest(_message.Message):
    __slots__ = ("story_id", "role", "phase", "subtask_id", "token_budget")
    STORY_ID_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    PHASE_FIELD_NUMBER: _ClassVar[int]
    SUBTASK_ID_FIELD_NUMBER: _ClassVar[int]
    TOKEN_BUDGET_FIELD_NUMBER: _ClassVar[int]
    story_id: str
    role: str
    phase: str
    subtask_id: str
    token_budget: int
    def __init__(self, story_id: str | None = ..., role: str | None = ..., phase: str | None = ..., subtask_id: str | None = ..., token_budget: int | None = ...) -> None: ...

class GetContextResponse(_message.Message):
    __slots__ = ("context", "token_count", "scopes", "version", "blocks")
    CONTEXT_FIELD_NUMBER: _ClassVar[int]
    TOKEN_COUNT_FIELD_NUMBER: _ClassVar[int]
    SCOPES_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    BLOCKS_FIELD_NUMBER: _ClassVar[int]
    context: str
    token_count: int
    scopes: _containers.RepeatedScalarFieldContainer[str]
    version: str
    blocks: PromptBlocks
    def __init__(self, context: str | None = ..., token_count: int | None = ..., scopes: _Iterable[str] | None = ..., version: str | None = ..., blocks: PromptBlocks | _Mapping | None = ...) -> None: ...

class PromptBlocks(_message.Message):
    __slots__ = ("system", "context", "tools")
    SYSTEM_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_FIELD_NUMBER: _ClassVar[int]
    TOOLS_FIELD_NUMBER: _ClassVar[int]
    system: str
    context: str
    tools: str
    def __init__(self, system: str | None = ..., context: str | None = ..., tools: str | None = ...) -> None: ...

class UpdateContextRequest(_message.Message):
    __slots__ = ("story_id", "task_id", "role", "changes", "timestamp")
    STORY_ID_FIELD_NUMBER: _ClassVar[int]
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    CHANGES_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    story_id: str
    task_id: str
    role: str
    changes: _containers.RepeatedCompositeFieldContainer[ContextChange]
    timestamp: str
    def __init__(self, story_id: str | None = ..., task_id: str | None = ..., role: str | None = ..., changes: _Iterable[ContextChange | _Mapping] | None = ..., timestamp: str | None = ...) -> None: ...

class ContextChange(_message.Message):
    __slots__ = ("operation", "entity_type", "entity_id", "payload", "reason")
    OPERATION_FIELD_NUMBER: _ClassVar[int]
    ENTITY_TYPE_FIELD_NUMBER: _ClassVar[int]
    ENTITY_ID_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    operation: str
    entity_type: str
    entity_id: str
    payload: str
    reason: str
    def __init__(self, operation: str | None = ..., entity_type: str | None = ..., entity_id: str | None = ..., payload: str | None = ..., reason: str | None = ...) -> None: ...

class UpdateContextResponse(_message.Message):
    __slots__ = ("version", "hash", "warnings")
    VERSION_FIELD_NUMBER: _ClassVar[int]
    HASH_FIELD_NUMBER: _ClassVar[int]
    WARNINGS_FIELD_NUMBER: _ClassVar[int]
    version: int
    hash: str
    warnings: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, version: int | None = ..., hash: str | None = ..., warnings: _Iterable[str] | None = ...) -> None: ...

class RehydrateSessionRequest(_message.Message):
    __slots__ = ("case_id", "roles", "include_timeline", "include_summaries", "timeline_events", "persist_bundle", "ttl_seconds")
    CASE_ID_FIELD_NUMBER: _ClassVar[int]
    ROLES_FIELD_NUMBER: _ClassVar[int]
    INCLUDE_TIMELINE_FIELD_NUMBER: _ClassVar[int]
    INCLUDE_SUMMARIES_FIELD_NUMBER: _ClassVar[int]
    TIMELINE_EVENTS_FIELD_NUMBER: _ClassVar[int]
    PERSIST_BUNDLE_FIELD_NUMBER: _ClassVar[int]
    TTL_SECONDS_FIELD_NUMBER: _ClassVar[int]
    case_id: str
    roles: _containers.RepeatedScalarFieldContainer[str]
    include_timeline: bool
    include_summaries: bool
    timeline_events: int
    persist_bundle: bool
    ttl_seconds: int
    def __init__(self, case_id: str | None = ..., roles: _Iterable[str] | None = ..., include_timeline: bool = ..., include_summaries: bool = ..., timeline_events: int | None = ..., persist_bundle: bool = ..., ttl_seconds: int | None = ...) -> None: ...

class RehydrateSessionResponse(_message.Message):
    __slots__ = ("case_id", "generated_at_ms", "packs", "stats")
    class PacksEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: RoleContextPack
        def __init__(self, key: str | None = ..., value: RoleContextPack | _Mapping | None = ...) -> None: ...
    CASE_ID_FIELD_NUMBER: _ClassVar[int]
    GENERATED_AT_MS_FIELD_NUMBER: _ClassVar[int]
    PACKS_FIELD_NUMBER: _ClassVar[int]
    STATS_FIELD_NUMBER: _ClassVar[int]
    case_id: str
    generated_at_ms: int
    packs: _containers.MessageMap[str, RoleContextPack]
    stats: RehydrationStats
    def __init__(self, case_id: str | None = ..., generated_at_ms: int | None = ..., packs: _Mapping[str, RoleContextPack] | None = ..., stats: RehydrationStats | _Mapping | None = ...) -> None: ...

class RoleContextPack(_message.Message):
    __slots__ = ("role", "case_header", "plan_header", "subtasks", "decisions", "decision_deps", "impacted", "milestones", "last_summary", "token_budget_hint")
    ROLE_FIELD_NUMBER: _ClassVar[int]
    CASE_HEADER_FIELD_NUMBER: _ClassVar[int]
    PLAN_HEADER_FIELD_NUMBER: _ClassVar[int]
    SUBTASKS_FIELD_NUMBER: _ClassVar[int]
    DECISIONS_FIELD_NUMBER: _ClassVar[int]
    DECISION_DEPS_FIELD_NUMBER: _ClassVar[int]
    IMPACTED_FIELD_NUMBER: _ClassVar[int]
    MILESTONES_FIELD_NUMBER: _ClassVar[int]
    LAST_SUMMARY_FIELD_NUMBER: _ClassVar[int]
    TOKEN_BUDGET_HINT_FIELD_NUMBER: _ClassVar[int]
    role: str
    case_header: CaseHeader
    plan_header: PlanHeader
    subtasks: _containers.RepeatedCompositeFieldContainer[Subtask]
    decisions: _containers.RepeatedCompositeFieldContainer[Decision]
    decision_deps: _containers.RepeatedCompositeFieldContainer[DecisionRelation]
    impacted: _containers.RepeatedCompositeFieldContainer[ImpactedSubtask]
    milestones: _containers.RepeatedCompositeFieldContainer[Milestone]
    last_summary: str
    token_budget_hint: int
    def __init__(self, role: str | None = ..., case_header: CaseHeader | _Mapping | None = ..., plan_header: PlanHeader | _Mapping | None = ..., subtasks: _Iterable[Subtask | _Mapping] | None = ..., decisions: _Iterable[Decision | _Mapping] | None = ..., decision_deps: _Iterable[DecisionRelation | _Mapping] | None = ..., impacted: _Iterable[ImpactedSubtask | _Mapping] | None = ..., milestones: _Iterable[Milestone | _Mapping] | None = ..., last_summary: str | None = ..., token_budget_hint: int | None = ...) -> None: ...

class CaseHeader(_message.Message):
    __slots__ = ("case_id", "title", "description", "status", "created_at", "created_by")
    CASE_ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    case_id: str
    title: str
    description: str
    status: str
    created_at: str
    created_by: str
    def __init__(self, case_id: str | None = ..., title: str | None = ..., description: str | None = ..., status: str | None = ..., created_at: str | None = ..., created_by: str | None = ...) -> None: ...

class PlanHeader(_message.Message):
    __slots__ = ("plan_id", "version", "status", "total_subtasks", "completed_subtasks")
    PLAN_ID_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_SUBTASKS_FIELD_NUMBER: _ClassVar[int]
    COMPLETED_SUBTASKS_FIELD_NUMBER: _ClassVar[int]
    plan_id: str
    version: int
    status: str
    total_subtasks: int
    completed_subtasks: int
    def __init__(self, plan_id: str | None = ..., version: int | None = ..., status: str | None = ..., total_subtasks: int | None = ..., completed_subtasks: int | None = ...) -> None: ...

class Subtask(_message.Message):
    __slots__ = ("subtask_id", "title", "description", "role", "status", "dependencies", "priority")
    SUBTASK_ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    DEPENDENCIES_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    subtask_id: str
    title: str
    description: str
    role: str
    status: str
    dependencies: _containers.RepeatedScalarFieldContainer[str]
    priority: int
    def __init__(self, subtask_id: str | None = ..., title: str | None = ..., description: str | None = ..., role: str | None = ..., status: str | None = ..., dependencies: _Iterable[str] | None = ..., priority: int | None = ...) -> None: ...

class Decision(_message.Message):
    __slots__ = ("id", "title", "rationale", "status", "decided_by", "decided_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    RATIONALE_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    DECIDED_BY_FIELD_NUMBER: _ClassVar[int]
    DECIDED_AT_FIELD_NUMBER: _ClassVar[int]
    id: str
    title: str
    rationale: str
    status: str
    decided_by: str
    decided_at: str
    def __init__(self, id: str | None = ..., title: str | None = ..., rationale: str | None = ..., status: str | None = ..., decided_by: str | None = ..., decided_at: str | None = ...) -> None: ...

class DecisionRelation(_message.Message):
    __slots__ = ("src_id", "dst_id", "relation_type")
    SRC_ID_FIELD_NUMBER: _ClassVar[int]
    DST_ID_FIELD_NUMBER: _ClassVar[int]
    RELATION_TYPE_FIELD_NUMBER: _ClassVar[int]
    src_id: str
    dst_id: str
    relation_type: str
    def __init__(self, src_id: str | None = ..., dst_id: str | None = ..., relation_type: str | None = ...) -> None: ...

class ImpactedSubtask(_message.Message):
    __slots__ = ("decision_id", "subtask_id", "title")
    DECISION_ID_FIELD_NUMBER: _ClassVar[int]
    SUBTASK_ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    decision_id: str
    subtask_id: str
    title: str
    def __init__(self, decision_id: str | None = ..., subtask_id: str | None = ..., title: str | None = ...) -> None: ...

class Milestone(_message.Message):
    __slots__ = ("event_type", "description", "ts_ms", "actor")
    EVENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    TS_MS_FIELD_NUMBER: _ClassVar[int]
    ACTOR_FIELD_NUMBER: _ClassVar[int]
    event_type: str
    description: str
    ts_ms: int
    actor: str
    def __init__(self, event_type: str | None = ..., description: str | None = ..., ts_ms: int | None = ..., actor: str | None = ...) -> None: ...

class RehydrationStats(_message.Message):
    __slots__ = ("decisions", "decision_edges", "impacts", "events", "roles")
    DECISIONS_FIELD_NUMBER: _ClassVar[int]
    DECISION_EDGES_FIELD_NUMBER: _ClassVar[int]
    IMPACTS_FIELD_NUMBER: _ClassVar[int]
    EVENTS_FIELD_NUMBER: _ClassVar[int]
    ROLES_FIELD_NUMBER: _ClassVar[int]
    decisions: int
    decision_edges: int
    impacts: int
    events: int
    roles: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, decisions: int | None = ..., decision_edges: int | None = ..., impacts: int | None = ..., events: int | None = ..., roles: _Iterable[str] | None = ...) -> None: ...

class ValidateScopeRequest(_message.Message):
    __slots__ = ("role", "phase", "provided_scopes")
    ROLE_FIELD_NUMBER: _ClassVar[int]
    PHASE_FIELD_NUMBER: _ClassVar[int]
    PROVIDED_SCOPES_FIELD_NUMBER: _ClassVar[int]
    role: str
    phase: str
    provided_scopes: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, role: str | None = ..., phase: str | None = ..., provided_scopes: _Iterable[str] | None = ...) -> None: ...

class ValidateScopeResponse(_message.Message):
    __slots__ = ("allowed", "missing", "extra", "reason")
    ALLOWED_FIELD_NUMBER: _ClassVar[int]
    MISSING_FIELD_NUMBER: _ClassVar[int]
    EXTRA_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    allowed: bool
    missing: _containers.RepeatedScalarFieldContainer[str]
    extra: _containers.RepeatedScalarFieldContainer[str]
    reason: str
    def __init__(self, allowed: bool = ..., missing: _Iterable[str] | None = ..., extra: _Iterable[str] | None = ..., reason: str | None = ...) -> None: ...
