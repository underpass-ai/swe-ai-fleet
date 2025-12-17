package selector

import (
	"fmt"
	"strconv"
	"strings"

	"github.com/underpass-ai/swe-ai-fleet/services/agent_executor/internal/executor/model"
)

type Selector struct {
	MaxGPUCount int
}

func NewSelector(maxGPUCount int) (*Selector, error) {
	if maxGPUCount < 1 {
		return nil, fmt.Errorf("maxGPUCount must be >= 1")
	}
	return &Selector{MaxGPUCount: maxGPUCount}, nil
}

// Select resolves which vLLM backend pool should be used based on metadata.
//
// Rules:
// - gpu_count defaults to 1 if missing.
// - gpu_count must be an integer between 1 and MaxGPUCount.
// - backend_tier is optional; if missing it is inferred:
//   - tier=big when gpu_count >= 2
//   - tier=small otherwise
//
// - If backend_tier is provided, it must be "small" or "big".
func (s *Selector) Select(metadata map[string]string) (model.BackendSelection, error) {
	gpuCount, err := s.parseGPUCount(metadata)
	if err != nil {
		return model.BackendSelection{}, err
	}

	tier, err := s.parseTier(metadata, gpuCount)
	if err != nil {
		return model.BackendSelection{}, err
	}

	return model.BackendSelection{Tier: tier, GPUCount: gpuCount}, nil
}

func (s *Selector) parseGPUCount(metadata map[string]string) (int, error) {
	if metadata == nil {
		return 1, nil
	}

	raw, ok := metadata[MetadataKeyGPUCount]
	if !ok || strings.TrimSpace(raw) == "" {
		return 1, nil
	}

	value, err := strconv.Atoi(strings.TrimSpace(raw))
	if err != nil {
		return 0, fmt.Errorf("invalid %s: must be integer, got %q", MetadataKeyGPUCount, raw)
	}
	if value < 1 {
		return 0, fmt.Errorf("invalid %s: must be >= 1, got %d", MetadataKeyGPUCount, value)
	}
	if value > s.MaxGPUCount {
		return 0, fmt.Errorf("invalid %s: must be <= %d, got %d", MetadataKeyGPUCount, s.MaxGPUCount, value)
	}

	return value, nil
}

func (s *Selector) parseTier(metadata map[string]string, gpuCount int) (model.BackendTier, error) {
	if metadata == nil {
		return inferTier(gpuCount), nil
	}

	raw, ok := metadata[MetadataKeyBackendTier]
	if !ok || strings.TrimSpace(raw) == "" {
		return inferTier(gpuCount), nil
	}

	normalized := strings.ToLower(strings.TrimSpace(raw))
	switch normalized {
	case string(model.BackendTierSmall):
		return model.BackendTierSmall, nil
	case string(model.BackendTierBig):
		return model.BackendTierBig, nil
	default:
		return "", fmt.Errorf("invalid %s: must be %q or %q, got %q", MetadataKeyBackendTier, model.BackendTierSmall, model.BackendTierBig, raw)
	}
}

func inferTier(gpuCount int) model.BackendTier {
	if gpuCount >= 2 {
		return model.BackendTierBig
	}
	return model.BackendTierSmall
}
