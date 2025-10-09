from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class DeliberateRequest(_message.Message):
    __slots__ = ("task_description", "role", "constraints", "rounds", "num_agents")
    TASK_DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    CONSTRAINTS_FIELD_NUMBER: _ClassVar[int]
    ROUNDS_FIELD_NUMBER: _ClassVar[int]
    NUM_AGENTS_FIELD_NUMBER: _ClassVar[int]
    task_description: str
    role: str
    constraints: TaskConstraints
    rounds: int
    num_agents: int
    def __init__(self, task_description: _Optional[str] = ..., role: _Optional[str] = ..., constraints: _Optional[_Union[TaskConstraints, _Mapping]] = ..., rounds: _Optional[int] = ..., num_agents: _Optional[int] = ...) -> None: ...

class DeliberateResponse(_message.Message):
    __slots__ = ("results", "winner_id", "duration_ms", "metadata")
    RESULTS_FIELD_NUMBER: _ClassVar[int]
    WINNER_ID_FIELD_NUMBER: _ClassVar[int]
    DURATION_MS_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    results: _containers.RepeatedCompositeFieldContainer[DeliberationResult]
    winner_id: str
    duration_ms: int
    metadata: OrchestratorMetadata
    def __init__(self, results: _Optional[_Iterable[_Union[DeliberationResult, _Mapping]]] = ..., winner_id: _Optional[str] = ..., duration_ms: _Optional[int] = ..., metadata: _Optional[_Union[OrchestratorMetadata, _Mapping]] = ...) -> None: ...

class OrchestrateRequest(_message.Message):
    __slots__ = ("task_id", "task_description", "role", "constraints", "options", "case_id", "story_id", "plan_id", "context_options")
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    TASK_DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    CONSTRAINTS_FIELD_NUMBER: _ClassVar[int]
    OPTIONS_FIELD_NUMBER: _ClassVar[int]
    CASE_ID_FIELD_NUMBER: _ClassVar[int]
    STORY_ID_FIELD_NUMBER: _ClassVar[int]
    PLAN_ID_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_OPTIONS_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    task_description: str
    role: str
    constraints: TaskConstraints
    options: OrchestratorOptions
    case_id: str
    story_id: str
    plan_id: str
    context_options: ContextOptions
    def __init__(self, task_id: _Optional[str] = ..., task_description: _Optional[str] = ..., role: _Optional[str] = ..., constraints: _Optional[_Union[TaskConstraints, _Mapping]] = ..., options: _Optional[_Union[OrchestratorOptions, _Mapping]] = ..., case_id: _Optional[str] = ..., story_id: _Optional[str] = ..., plan_id: _Optional[str] = ..., context_options: _Optional[_Union[ContextOptions, _Mapping]] = ...) -> None: ...

class OrchestrateResponse(_message.Message):
    __slots__ = ("winner", "candidates", "execution_id", "duration_ms", "metadata")
    WINNER_FIELD_NUMBER: _ClassVar[int]
    CANDIDATES_FIELD_NUMBER: _ClassVar[int]
    EXECUTION_ID_FIELD_NUMBER: _ClassVar[int]
    DURATION_MS_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    winner: DeliberationResult
    candidates: _containers.RepeatedCompositeFieldContainer[DeliberationResult]
    execution_id: str
    duration_ms: int
    metadata: OrchestratorMetadata
    def __init__(self, winner: _Optional[_Union[DeliberationResult, _Mapping]] = ..., candidates: _Optional[_Iterable[_Union[DeliberationResult, _Mapping]]] = ..., execution_id: _Optional[str] = ..., duration_ms: _Optional[int] = ..., metadata: _Optional[_Union[OrchestratorMetadata, _Mapping]] = ...) -> None: ...

class GetStatusRequest(_message.Message):
    __slots__ = ("include_stats",)
    INCLUDE_STATS_FIELD_NUMBER: _ClassVar[int]
    include_stats: bool
    def __init__(self, include_stats: bool = ...) -> None: ...

class GetStatusResponse(_message.Message):
    __slots__ = ("status", "uptime_seconds", "stats")
    STATUS_FIELD_NUMBER: _ClassVar[int]
    UPTIME_SECONDS_FIELD_NUMBER: _ClassVar[int]
    STATS_FIELD_NUMBER: _ClassVar[int]
    status: str
    uptime_seconds: int
    stats: OrchestratorStats
    def __init__(self, status: _Optional[str] = ..., uptime_seconds: _Optional[int] = ..., stats: _Optional[_Union[OrchestratorStats, _Mapping]] = ...) -> None: ...

class TaskConstraints(_message.Message):
    __slots__ = ("rubric", "requirements", "metadata", "max_iterations", "timeout_seconds")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    RUBRIC_FIELD_NUMBER: _ClassVar[int]
    REQUIREMENTS_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    MAX_ITERATIONS_FIELD_NUMBER: _ClassVar[int]
    TIMEOUT_SECONDS_FIELD_NUMBER: _ClassVar[int]
    rubric: str
    requirements: _containers.RepeatedScalarFieldContainer[str]
    metadata: _containers.ScalarMap[str, str]
    max_iterations: int
    timeout_seconds: int
    def __init__(self, rubric: _Optional[str] = ..., requirements: _Optional[_Iterable[str]] = ..., metadata: _Optional[_Mapping[str, str]] = ..., max_iterations: _Optional[int] = ..., timeout_seconds: _Optional[int] = ...) -> None: ...

class OrchestratorOptions(_message.Message):
    __slots__ = ("enable_peer_review", "deliberation_rounds", "enable_architect_selection", "custom_params")
    class CustomParamsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    ENABLE_PEER_REVIEW_FIELD_NUMBER: _ClassVar[int]
    DELIBERATION_ROUNDS_FIELD_NUMBER: _ClassVar[int]
    ENABLE_ARCHITECT_SELECTION_FIELD_NUMBER: _ClassVar[int]
    CUSTOM_PARAMS_FIELD_NUMBER: _ClassVar[int]
    enable_peer_review: bool
    deliberation_rounds: int
    enable_architect_selection: bool
    custom_params: _containers.ScalarMap[str, str]
    def __init__(self, enable_peer_review: bool = ..., deliberation_rounds: _Optional[int] = ..., enable_architect_selection: bool = ..., custom_params: _Optional[_Mapping[str, str]] = ...) -> None: ...

class DeliberationResult(_message.Message):
    __slots__ = ("proposal", "checks", "score", "rank")
    PROPOSAL_FIELD_NUMBER: _ClassVar[int]
    CHECKS_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    RANK_FIELD_NUMBER: _ClassVar[int]
    proposal: Proposal
    checks: CheckSuite
    score: float
    rank: int
    def __init__(self, proposal: _Optional[_Union[Proposal, _Mapping]] = ..., checks: _Optional[_Union[CheckSuite, _Mapping]] = ..., score: _Optional[float] = ..., rank: _Optional[int] = ...) -> None: ...

class Proposal(_message.Message):
    __slots__ = ("author_id", "author_role", "content", "created_at_ms", "revisions")
    AUTHOR_ID_FIELD_NUMBER: _ClassVar[int]
    AUTHOR_ROLE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_MS_FIELD_NUMBER: _ClassVar[int]
    REVISIONS_FIELD_NUMBER: _ClassVar[int]
    author_id: str
    author_role: str
    content: str
    created_at_ms: int
    revisions: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, author_id: _Optional[str] = ..., author_role: _Optional[str] = ..., content: _Optional[str] = ..., created_at_ms: _Optional[int] = ..., revisions: _Optional[_Iterable[str]] = ...) -> None: ...

class CheckSuite(_message.Message):
    __slots__ = ("policy", "lint", "dryrun", "additional_checks", "all_passed")
    POLICY_FIELD_NUMBER: _ClassVar[int]
    LINT_FIELD_NUMBER: _ClassVar[int]
    DRYRUN_FIELD_NUMBER: _ClassVar[int]
    ADDITIONAL_CHECKS_FIELD_NUMBER: _ClassVar[int]
    ALL_PASSED_FIELD_NUMBER: _ClassVar[int]
    policy: PolicyResult
    lint: LintResult
    dryrun: DryRunResult
    additional_checks: _containers.RepeatedCompositeFieldContainer[CheckResult]
    all_passed: bool
    def __init__(self, policy: _Optional[_Union[PolicyResult, _Mapping]] = ..., lint: _Optional[_Union[LintResult, _Mapping]] = ..., dryrun: _Optional[_Union[DryRunResult, _Mapping]] = ..., additional_checks: _Optional[_Iterable[_Union[CheckResult, _Mapping]]] = ..., all_passed: bool = ...) -> None: ...

class PolicyResult(_message.Message):
    __slots__ = ("passed", "violations", "message")
    PASSED_FIELD_NUMBER: _ClassVar[int]
    VIOLATIONS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    passed: bool
    violations: _containers.RepeatedScalarFieldContainer[str]
    message: str
    def __init__(self, passed: bool = ..., violations: _Optional[_Iterable[str]] = ..., message: _Optional[str] = ...) -> None: ...

class LintResult(_message.Message):
    __slots__ = ("passed", "error_count", "warning_count", "errors")
    PASSED_FIELD_NUMBER: _ClassVar[int]
    ERROR_COUNT_FIELD_NUMBER: _ClassVar[int]
    WARNING_COUNT_FIELD_NUMBER: _ClassVar[int]
    ERRORS_FIELD_NUMBER: _ClassVar[int]
    passed: bool
    error_count: int
    warning_count: int
    errors: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, passed: bool = ..., error_count: _Optional[int] = ..., warning_count: _Optional[int] = ..., errors: _Optional[_Iterable[str]] = ...) -> None: ...

class DryRunResult(_message.Message):
    __slots__ = ("passed", "output", "exit_code", "message")
    PASSED_FIELD_NUMBER: _ClassVar[int]
    OUTPUT_FIELD_NUMBER: _ClassVar[int]
    EXIT_CODE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    passed: bool
    output: str
    exit_code: int
    message: str
    def __init__(self, passed: bool = ..., output: _Optional[str] = ..., exit_code: _Optional[int] = ..., message: _Optional[str] = ...) -> None: ...

class CheckResult(_message.Message):
    __slots__ = ("check_type", "passed", "score", "message", "details")
    class DetailsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    CHECK_TYPE_FIELD_NUMBER: _ClassVar[int]
    PASSED_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    DETAILS_FIELD_NUMBER: _ClassVar[int]
    check_type: str
    passed: bool
    score: float
    message: str
    details: _containers.ScalarMap[str, str]
    def __init__(self, check_type: _Optional[str] = ..., passed: bool = ..., score: _Optional[float] = ..., message: _Optional[str] = ..., details: _Optional[_Mapping[str, str]] = ...) -> None: ...

class OrchestratorMetadata(_message.Message):
    __slots__ = ("orchestrator_version", "timestamp_ms", "execution_id", "tags")
    class TagsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    ORCHESTRATOR_VERSION_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_MS_FIELD_NUMBER: _ClassVar[int]
    EXECUTION_ID_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    orchestrator_version: str
    timestamp_ms: int
    execution_id: str
    tags: _containers.ScalarMap[str, str]
    def __init__(self, orchestrator_version: _Optional[str] = ..., timestamp_ms: _Optional[int] = ..., execution_id: _Optional[str] = ..., tags: _Optional[_Mapping[str, str]] = ...) -> None: ...

class OrchestratorStats(_message.Message):
    __slots__ = ("total_deliberations", "total_orchestrations", "avg_deliberation_time_ms", "active_councils", "role_counts")
    class RoleCountsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: int
        def __init__(self, key: _Optional[str] = ..., value: _Optional[int] = ...) -> None: ...
    TOTAL_DELIBERATIONS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_ORCHESTRATIONS_FIELD_NUMBER: _ClassVar[int]
    AVG_DELIBERATION_TIME_MS_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_COUNCILS_FIELD_NUMBER: _ClassVar[int]
    ROLE_COUNTS_FIELD_NUMBER: _ClassVar[int]
    total_deliberations: int
    total_orchestrations: int
    avg_deliberation_time_ms: float
    active_councils: int
    role_counts: _containers.ScalarMap[str, int]
    def __init__(self, total_deliberations: _Optional[int] = ..., total_orchestrations: _Optional[int] = ..., avg_deliberation_time_ms: _Optional[float] = ..., active_councils: _Optional[int] = ..., role_counts: _Optional[_Mapping[str, int]] = ...) -> None: ...

class ContextOptions(_message.Message):
    __slots__ = ("include_timeline", "include_decisions", "include_summaries", "max_events", "scopes")
    INCLUDE_TIMELINE_FIELD_NUMBER: _ClassVar[int]
    INCLUDE_DECISIONS_FIELD_NUMBER: _ClassVar[int]
    INCLUDE_SUMMARIES_FIELD_NUMBER: _ClassVar[int]
    MAX_EVENTS_FIELD_NUMBER: _ClassVar[int]
    SCOPES_FIELD_NUMBER: _ClassVar[int]
    include_timeline: bool
    include_decisions: bool
    include_summaries: bool
    max_events: int
    scopes: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, include_timeline: bool = ..., include_decisions: bool = ..., include_summaries: bool = ..., max_events: _Optional[int] = ..., scopes: _Optional[_Iterable[str]] = ...) -> None: ...

class DeliberationUpdate(_message.Message):
    __slots__ = ("status", "progress_percent", "current_step", "current_agent", "partial_result")
    STATUS_FIELD_NUMBER: _ClassVar[int]
    PROGRESS_PERCENT_FIELD_NUMBER: _ClassVar[int]
    CURRENT_STEP_FIELD_NUMBER: _ClassVar[int]
    CURRENT_AGENT_FIELD_NUMBER: _ClassVar[int]
    PARTIAL_RESULT_FIELD_NUMBER: _ClassVar[int]
    status: str
    progress_percent: int
    current_step: str
    current_agent: str
    partial_result: DeliberationResult
    def __init__(self, status: _Optional[str] = ..., progress_percent: _Optional[int] = ..., current_step: _Optional[str] = ..., current_agent: _Optional[str] = ..., partial_result: _Optional[_Union[DeliberationResult, _Mapping]] = ...) -> None: ...

class RegisterAgentRequest(_message.Message):
    __slots__ = ("agent_id", "role", "capabilities", "endpoint", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    AGENT_ID_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    ENDPOINT_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    agent_id: str
    role: str
    capabilities: AgentCapabilities
    endpoint: str
    metadata: _containers.ScalarMap[str, str]
    def __init__(self, agent_id: _Optional[str] = ..., role: _Optional[str] = ..., capabilities: _Optional[_Union[AgentCapabilities, _Mapping]] = ..., endpoint: _Optional[str] = ..., metadata: _Optional[_Mapping[str, str]] = ...) -> None: ...

class RegisterAgentResponse(_message.Message):
    __slots__ = ("success", "message", "council_id")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    COUNCIL_ID_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    council_id: str
    def __init__(self, success: bool = ..., message: _Optional[str] = ..., council_id: _Optional[str] = ...) -> None: ...

class AgentCapabilities(_message.Message):
    __slots__ = ("supported_tasks", "model_profile", "max_concurrent_tasks", "languages")
    SUPPORTED_TASKS_FIELD_NUMBER: _ClassVar[int]
    MODEL_PROFILE_FIELD_NUMBER: _ClassVar[int]
    MAX_CONCURRENT_TASKS_FIELD_NUMBER: _ClassVar[int]
    LANGUAGES_FIELD_NUMBER: _ClassVar[int]
    supported_tasks: _containers.RepeatedScalarFieldContainer[str]
    model_profile: str
    max_concurrent_tasks: int
    languages: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, supported_tasks: _Optional[_Iterable[str]] = ..., model_profile: _Optional[str] = ..., max_concurrent_tasks: _Optional[int] = ..., languages: _Optional[_Iterable[str]] = ...) -> None: ...

class CreateCouncilRequest(_message.Message):
    __slots__ = ("role", "num_agents", "config")
    ROLE_FIELD_NUMBER: _ClassVar[int]
    NUM_AGENTS_FIELD_NUMBER: _ClassVar[int]
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    role: str
    num_agents: int
    config: CouncilConfig
    def __init__(self, role: _Optional[str] = ..., num_agents: _Optional[int] = ..., config: _Optional[_Union[CouncilConfig, _Mapping]] = ...) -> None: ...

class CreateCouncilResponse(_message.Message):
    __slots__ = ("council_id", "agents_created", "agent_ids")
    COUNCIL_ID_FIELD_NUMBER: _ClassVar[int]
    AGENTS_CREATED_FIELD_NUMBER: _ClassVar[int]
    AGENT_IDS_FIELD_NUMBER: _ClassVar[int]
    council_id: str
    agents_created: int
    agent_ids: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, council_id: _Optional[str] = ..., agents_created: _Optional[int] = ..., agent_ids: _Optional[_Iterable[str]] = ...) -> None: ...

class CouncilConfig(_message.Message):
    __slots__ = ("deliberation_rounds", "enable_peer_review", "model_profile", "custom_params")
    class CustomParamsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    DELIBERATION_ROUNDS_FIELD_NUMBER: _ClassVar[int]
    ENABLE_PEER_REVIEW_FIELD_NUMBER: _ClassVar[int]
    MODEL_PROFILE_FIELD_NUMBER: _ClassVar[int]
    CUSTOM_PARAMS_FIELD_NUMBER: _ClassVar[int]
    deliberation_rounds: int
    enable_peer_review: bool
    model_profile: str
    custom_params: _containers.ScalarMap[str, str]
    def __init__(self, deliberation_rounds: _Optional[int] = ..., enable_peer_review: bool = ..., model_profile: _Optional[str] = ..., custom_params: _Optional[_Mapping[str, str]] = ...) -> None: ...

class ListCouncilsRequest(_message.Message):
    __slots__ = ("role_filter", "include_agents")
    ROLE_FILTER_FIELD_NUMBER: _ClassVar[int]
    INCLUDE_AGENTS_FIELD_NUMBER: _ClassVar[int]
    role_filter: str
    include_agents: bool
    def __init__(self, role_filter: _Optional[str] = ..., include_agents: bool = ...) -> None: ...

class ListCouncilsResponse(_message.Message):
    __slots__ = ("councils",)
    COUNCILS_FIELD_NUMBER: _ClassVar[int]
    councils: _containers.RepeatedCompositeFieldContainer[CouncilInfo]
    def __init__(self, councils: _Optional[_Iterable[_Union[CouncilInfo, _Mapping]]] = ...) -> None: ...

class CouncilInfo(_message.Message):
    __slots__ = ("council_id", "role", "num_agents", "agents", "status")
    COUNCIL_ID_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    NUM_AGENTS_FIELD_NUMBER: _ClassVar[int]
    AGENTS_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    council_id: str
    role: str
    num_agents: int
    agents: _containers.RepeatedCompositeFieldContainer[AgentInfo]
    status: str
    def __init__(self, council_id: _Optional[str] = ..., role: _Optional[str] = ..., num_agents: _Optional[int] = ..., agents: _Optional[_Iterable[_Union[AgentInfo, _Mapping]]] = ..., status: _Optional[str] = ...) -> None: ...

class AgentInfo(_message.Message):
    __slots__ = ("agent_id", "role", "status", "capabilities")
    AGENT_ID_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    agent_id: str
    role: str
    status: str
    capabilities: AgentCapabilities
    def __init__(self, agent_id: _Optional[str] = ..., role: _Optional[str] = ..., status: _Optional[str] = ..., capabilities: _Optional[_Union[AgentCapabilities, _Mapping]] = ...) -> None: ...

class UnregisterAgentRequest(_message.Message):
    __slots__ = ("agent_id", "role")
    AGENT_ID_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    agent_id: str
    role: str
    def __init__(self, agent_id: _Optional[str] = ..., role: _Optional[str] = ...) -> None: ...

class UnregisterAgentResponse(_message.Message):
    __slots__ = ("success", "message")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    def __init__(self, success: bool = ..., message: _Optional[str] = ...) -> None: ...

class PlanningEventRequest(_message.Message):
    __slots__ = ("event_type", "case_id", "plan_id", "from_state", "to_state", "timestamp_ms", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    EVENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    CASE_ID_FIELD_NUMBER: _ClassVar[int]
    PLAN_ID_FIELD_NUMBER: _ClassVar[int]
    FROM_STATE_FIELD_NUMBER: _ClassVar[int]
    TO_STATE_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_MS_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    event_type: str
    case_id: str
    plan_id: str
    from_state: str
    to_state: str
    timestamp_ms: int
    metadata: _containers.ScalarMap[str, str]
    def __init__(self, event_type: _Optional[str] = ..., case_id: _Optional[str] = ..., plan_id: _Optional[str] = ..., from_state: _Optional[str] = ..., to_state: _Optional[str] = ..., timestamp_ms: _Optional[int] = ..., metadata: _Optional[_Mapping[str, str]] = ...) -> None: ...

class PlanningEventResponse(_message.Message):
    __slots__ = ("processed", "message", "derived_task_ids")
    PROCESSED_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    DERIVED_TASK_IDS_FIELD_NUMBER: _ClassVar[int]
    processed: bool
    message: str
    derived_task_ids: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, processed: bool = ..., message: _Optional[str] = ..., derived_task_ids: _Optional[_Iterable[str]] = ...) -> None: ...

class DeriveSubtasksRequest(_message.Message):
    __slots__ = ("case_id", "plan_id", "roles", "strategy")
    CASE_ID_FIELD_NUMBER: _ClassVar[int]
    PLAN_ID_FIELD_NUMBER: _ClassVar[int]
    ROLES_FIELD_NUMBER: _ClassVar[int]
    STRATEGY_FIELD_NUMBER: _ClassVar[int]
    case_id: str
    plan_id: str
    roles: _containers.RepeatedScalarFieldContainer[str]
    strategy: DerivationStrategy
    def __init__(self, case_id: _Optional[str] = ..., plan_id: _Optional[str] = ..., roles: _Optional[_Iterable[str]] = ..., strategy: _Optional[_Union[DerivationStrategy, _Mapping]] = ...) -> None: ...

class DeriveSubtasksResponse(_message.Message):
    __slots__ = ("tasks", "derivation_id", "total_tasks")
    TASKS_FIELD_NUMBER: _ClassVar[int]
    DERIVATION_ID_FIELD_NUMBER: _ClassVar[int]
    TOTAL_TASKS_FIELD_NUMBER: _ClassVar[int]
    tasks: _containers.RepeatedCompositeFieldContainer[AtomicTask]
    derivation_id: str
    total_tasks: int
    def __init__(self, tasks: _Optional[_Iterable[_Union[AtomicTask, _Mapping]]] = ..., derivation_id: _Optional[str] = ..., total_tasks: _Optional[int] = ...) -> None: ...

class DerivationStrategy(_message.Message):
    __slots__ = ("parallel_execution", "dependency_order", "max_tasks_per_role", "auto_publish_to_nats")
    PARALLEL_EXECUTION_FIELD_NUMBER: _ClassVar[int]
    DEPENDENCY_ORDER_FIELD_NUMBER: _ClassVar[int]
    MAX_TASKS_PER_ROLE_FIELD_NUMBER: _ClassVar[int]
    AUTO_PUBLISH_TO_NATS_FIELD_NUMBER: _ClassVar[int]
    parallel_execution: bool
    dependency_order: _containers.RepeatedScalarFieldContainer[str]
    max_tasks_per_role: int
    auto_publish_to_nats: bool
    def __init__(self, parallel_execution: bool = ..., dependency_order: _Optional[_Iterable[str]] = ..., max_tasks_per_role: _Optional[int] = ..., auto_publish_to_nats: bool = ...) -> None: ...

class AtomicTask(_message.Message):
    __slots__ = ("task_id", "role", "description", "dependencies", "constraints", "case_id", "plan_id", "priority")
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    DEPENDENCIES_FIELD_NUMBER: _ClassVar[int]
    CONSTRAINTS_FIELD_NUMBER: _ClassVar[int]
    CASE_ID_FIELD_NUMBER: _ClassVar[int]
    PLAN_ID_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    role: str
    description: str
    dependencies: _containers.RepeatedScalarFieldContainer[str]
    constraints: TaskConstraints
    case_id: str
    plan_id: str
    priority: int
    def __init__(self, task_id: _Optional[str] = ..., role: _Optional[str] = ..., description: _Optional[str] = ..., dependencies: _Optional[_Iterable[str]] = ..., constraints: _Optional[_Union[TaskConstraints, _Mapping]] = ..., case_id: _Optional[str] = ..., plan_id: _Optional[str] = ..., priority: _Optional[int] = ...) -> None: ...

class GetTaskContextRequest(_message.Message):
    __slots__ = ("task_id", "case_id", "story_id", "role", "phase", "options")
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    CASE_ID_FIELD_NUMBER: _ClassVar[int]
    STORY_ID_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    PHASE_FIELD_NUMBER: _ClassVar[int]
    OPTIONS_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    case_id: str
    story_id: str
    role: str
    phase: str
    options: ContextOptions
    def __init__(self, task_id: _Optional[str] = ..., case_id: _Optional[str] = ..., story_id: _Optional[str] = ..., role: _Optional[str] = ..., phase: _Optional[str] = ..., options: _Optional[_Union[ContextOptions, _Mapping]] = ...) -> None: ...

class GetTaskContextResponse(_message.Message):
    __slots__ = ("context_text", "blocks", "token_count", "version_hash")
    CONTEXT_TEXT_FIELD_NUMBER: _ClassVar[int]
    BLOCKS_FIELD_NUMBER: _ClassVar[int]
    TOKEN_COUNT_FIELD_NUMBER: _ClassVar[int]
    VERSION_HASH_FIELD_NUMBER: _ClassVar[int]
    context_text: str
    blocks: ContextBlocks
    token_count: int
    version_hash: str
    def __init__(self, context_text: _Optional[str] = ..., blocks: _Optional[_Union[ContextBlocks, _Mapping]] = ..., token_count: _Optional[int] = ..., version_hash: _Optional[str] = ...) -> None: ...

class ContextBlocks(_message.Message):
    __slots__ = ("system", "context", "tools", "history")
    SYSTEM_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_FIELD_NUMBER: _ClassVar[int]
    TOOLS_FIELD_NUMBER: _ClassVar[int]
    HISTORY_FIELD_NUMBER: _ClassVar[int]
    system: str
    context: str
    tools: str
    history: str
    def __init__(self, system: _Optional[str] = ..., context: _Optional[str] = ..., tools: _Optional[str] = ..., history: _Optional[str] = ...) -> None: ...

class GetMetricsRequest(_message.Message):
    __slots__ = ("metric_type", "time_range_ms")
    METRIC_TYPE_FIELD_NUMBER: _ClassVar[int]
    TIME_RANGE_MS_FIELD_NUMBER: _ClassVar[int]
    metric_type: str
    time_range_ms: int
    def __init__(self, metric_type: _Optional[str] = ..., time_range_ms: _Optional[int] = ...) -> None: ...

class GetMetricsResponse(_message.Message):
    __slots__ = ("performance", "agents", "councils")
    PERFORMANCE_FIELD_NUMBER: _ClassVar[int]
    AGENTS_FIELD_NUMBER: _ClassVar[int]
    COUNCILS_FIELD_NUMBER: _ClassVar[int]
    performance: PerformanceMetrics
    agents: AgentMetrics
    councils: CouncilMetrics
    def __init__(self, performance: _Optional[_Union[PerformanceMetrics, _Mapping]] = ..., agents: _Optional[_Union[AgentMetrics, _Mapping]] = ..., councils: _Optional[_Union[CouncilMetrics, _Mapping]] = ...) -> None: ...

class PerformanceMetrics(_message.Message):
    __slots__ = ("avg_deliberation_ms", "avg_orchestration_ms", "p50_latency_ms", "p95_latency_ms", "p99_latency_ms")
    AVG_DELIBERATION_MS_FIELD_NUMBER: _ClassVar[int]
    AVG_ORCHESTRATION_MS_FIELD_NUMBER: _ClassVar[int]
    P50_LATENCY_MS_FIELD_NUMBER: _ClassVar[int]
    P95_LATENCY_MS_FIELD_NUMBER: _ClassVar[int]
    P99_LATENCY_MS_FIELD_NUMBER: _ClassVar[int]
    avg_deliberation_ms: float
    avg_orchestration_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    def __init__(self, avg_deliberation_ms: _Optional[float] = ..., avg_orchestration_ms: _Optional[float] = ..., p50_latency_ms: _Optional[float] = ..., p95_latency_ms: _Optional[float] = ..., p99_latency_ms: _Optional[float] = ...) -> None: ...

class AgentMetrics(_message.Message):
    __slots__ = ("total_agents", "active_agents", "agents_per_role", "avg_agent_response_time_ms")
    class AgentsPerRoleEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: int
        def __init__(self, key: _Optional[str] = ..., value: _Optional[int] = ...) -> None: ...
    TOTAL_AGENTS_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_AGENTS_FIELD_NUMBER: _ClassVar[int]
    AGENTS_PER_ROLE_FIELD_NUMBER: _ClassVar[int]
    AVG_AGENT_RESPONSE_TIME_MS_FIELD_NUMBER: _ClassVar[int]
    total_agents: int
    active_agents: int
    agents_per_role: _containers.ScalarMap[str, int]
    avg_agent_response_time_ms: float
    def __init__(self, total_agents: _Optional[int] = ..., active_agents: _Optional[int] = ..., agents_per_role: _Optional[_Mapping[str, int]] = ..., avg_agent_response_time_ms: _Optional[float] = ...) -> None: ...

class CouncilMetrics(_message.Message):
    __slots__ = ("total_councils", "active_councils", "health_per_council")
    class HealthPerCouncilEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: CouncilHealth
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[CouncilHealth, _Mapping]] = ...) -> None: ...
    TOTAL_COUNCILS_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_COUNCILS_FIELD_NUMBER: _ClassVar[int]
    HEALTH_PER_COUNCIL_FIELD_NUMBER: _ClassVar[int]
    total_councils: int
    active_councils: int
    health_per_council: _containers.MessageMap[str, CouncilHealth]
    def __init__(self, total_councils: _Optional[int] = ..., active_councils: _Optional[int] = ..., health_per_council: _Optional[_Mapping[str, CouncilHealth]] = ...) -> None: ...

class CouncilHealth(_message.Message):
    __slots__ = ("status", "available_agents", "busy_agents", "success_rate")
    STATUS_FIELD_NUMBER: _ClassVar[int]
    AVAILABLE_AGENTS_FIELD_NUMBER: _ClassVar[int]
    BUSY_AGENTS_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_RATE_FIELD_NUMBER: _ClassVar[int]
    status: str
    available_agents: int
    busy_agents: int
    success_rate: float
    def __init__(self, status: _Optional[str] = ..., available_agents: _Optional[int] = ..., busy_agents: _Optional[int] = ..., success_rate: _Optional[float] = ...) -> None: ...
