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
    __slots__ = ("task_id", "task_description", "role", "constraints", "options")
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    TASK_DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    CONSTRAINTS_FIELD_NUMBER: _ClassVar[int]
    OPTIONS_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    task_description: str
    role: str
    constraints: TaskConstraints
    options: OrchestratorOptions
    def __init__(self, task_id: _Optional[str] = ..., task_description: _Optional[str] = ..., role: _Optional[str] = ..., constraints: _Optional[_Union[TaskConstraints, _Mapping]] = ..., options: _Optional[_Union[OrchestratorOptions, _Mapping]] = ...) -> None: ...

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
