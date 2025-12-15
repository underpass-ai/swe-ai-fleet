package model

// BackendSelection is the resolved target for a single agent execution.
// It is intentionally transport-agnostic (no gRPC/protobuf coupling).
type BackendSelection struct {
	Tier     BackendTier
	GPUCount int
}
