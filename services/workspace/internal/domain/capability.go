package domain

import "encoding/json"

type Scope string

const (
	ScopeRepo      Scope = "repo"
	ScopeWorkspace Scope = "workspace"
	ScopeCluster   Scope = "cluster"
	ScopeExternal  Scope = "external"
)

type SideEffects string

const (
	SideEffectsNone         SideEffects = "none"
	SideEffectsReversible   SideEffects = "reversible"
	SideEffectsIrreversible SideEffects = "irreversible"
)

type RiskLevel string

const (
	RiskLow    RiskLevel = "low"
	RiskMedium RiskLevel = "medium"
	RiskHigh   RiskLevel = "high"
)

type Idempotency string

const (
	IdempotencyGuaranteed Idempotency = "guaranteed"
	IdempotencyBestEffort Idempotency = "best-effort"
	IdempotencyNone       Idempotency = "none"
)

type Observability struct {
	TraceName string `json:"trace_name"`
	SpanName  string `json:"span_name"`
}

type Constraints struct {
	TimeoutSeconds int      `json:"timeout_seconds"`
	MaxRetries     int      `json:"max_retries"`
	AllowedPaths   []string `json:"allowed_paths,omitempty"`
	OutputLimitKB  int      `json:"output_limit_kb,omitempty"`
}

type Capability struct {
	Name             string            `json:"name"`
	Description      string            `json:"description"`
	InputSchema      json.RawMessage   `json:"input_schema"`
	OutputSchema     json.RawMessage   `json:"output_schema"`
	Scope            Scope             `json:"scope"`
	SideEffects      SideEffects       `json:"side_effects"`
	RiskLevel        RiskLevel         `json:"risk_level"`
	RequiresApproval bool              `json:"requires_approval"`
	Idempotency      Idempotency       `json:"idempotency"`
	Constraints      Constraints       `json:"constraints"`
	Preconditions    []string          `json:"preconditions,omitempty"`
	Postconditions   []string          `json:"postconditions,omitempty"`
	CostHint         string            `json:"cost_hint,omitempty"`
	Observability    Observability     `json:"observability"`
	Examples         []json.RawMessage `json:"examples,omitempty"`
}
