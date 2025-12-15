package selector

import "testing"

func TestNewSelector_RejectsInvalidMaxGPUCount(t *testing.T) {
	_, err := NewSelector(0)
	if err == nil {
		t.Fatalf("expected error")
	}
}
