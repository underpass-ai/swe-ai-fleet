package selector

import (
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/agent_executor/internal/executor/model"
)

func TestSelector_Select_DefaultsToSmallAnd1GPU(t *testing.T) {
	sel, err := NewSelector(4)
	if err != nil {
		t.Fatalf("NewSelector: %v", err)
	}

	got, err := sel.Select(nil)
	if err != nil {
		t.Fatalf("Select: %v", err)
	}

	if got.GPUCount != 1 {
		t.Fatalf("GPUCount: got %d, want 1", got.GPUCount)
	}
	if got.Tier != model.BackendTierSmall {
		t.Fatalf("Tier: got %q, want %q", got.Tier, model.BackendTierSmall)
	}
}

func TestSelector_Select_InfersBigWhenGPUCountAtLeast2(t *testing.T) {
	sel, err := NewSelector(4)
	if err != nil {
		t.Fatalf("NewSelector: %v", err)
	}

	got, err := sel.Select(map[string]string{MetadataKeyGPUCount: "2"})
	if err != nil {
		t.Fatalf("Select: %v", err)
	}

	if got.GPUCount != 2 {
		t.Fatalf("GPUCount: got %d, want 2", got.GPUCount)
	}
	if got.Tier != model.BackendTierBig {
		t.Fatalf("Tier: got %q, want %q", got.Tier, model.BackendTierBig)
	}
}

func TestSelector_Select_AllowsExplicitTierOverride(t *testing.T) {
	sel, err := NewSelector(4)
	if err != nil {
		t.Fatalf("NewSelector: %v", err)
	}

	got, err := sel.Select(map[string]string{MetadataKeyGPUCount: "2", MetadataKeyBackendTier: "small"})
	if err != nil {
		t.Fatalf("Select: %v", err)
	}

	if got.GPUCount != 2 {
		t.Fatalf("GPUCount: got %d, want 2", got.GPUCount)
	}
	if got.Tier != model.BackendTierSmall {
		t.Fatalf("Tier: got %q, want %q", got.Tier, model.BackendTierSmall)
	}
}

func TestSelector_Select_RejectsInvalidGPUCount(t *testing.T) {
	sel, err := NewSelector(4)
	if err != nil {
		t.Fatalf("NewSelector: %v", err)
	}

	_, err = sel.Select(map[string]string{MetadataKeyGPUCount: "nope"})
	if err == nil {
		t.Fatalf("expected error")
	}
}

func TestSelector_Select_RejectsGPUCountOutOfRange(t *testing.T) {
	sel, err := NewSelector(4)
	if err != nil {
		t.Fatalf("NewSelector: %v", err)
	}

	_, err = sel.Select(map[string]string{MetadataKeyGPUCount: "0"})
	if err == nil {
		t.Fatalf("expected error")
	}

	_, err = sel.Select(map[string]string{MetadataKeyGPUCount: "5"})
	if err == nil {
		t.Fatalf("expected error")
	}
}

func TestSelector_Select_RejectsInvalidTier(t *testing.T) {
	sel, err := NewSelector(4)
	if err != nil {
		t.Fatalf("NewSelector: %v", err)
	}

	_, err = sel.Select(map[string]string{MetadataKeyBackendTier: "medium"})
	if err == nil {
		t.Fatalf("expected error")
	}
}
