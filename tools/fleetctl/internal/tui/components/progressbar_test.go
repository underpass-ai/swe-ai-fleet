package components

import (
	"strings"
	"testing"
)

func TestProgressBar_Defaults(t *testing.T) {
	p := NewProgressBar(5)
	view := p.View()
	if !strings.Contains(view, "0/5") {
		t.Errorf("initial bar should show 0/5, got %q", view)
	}
	if !strings.Contains(view, "steps") {
		t.Error("view should contain 'steps' label")
	}
}

func TestProgressBar_SetCurrent(t *testing.T) {
	p := NewProgressBar(4).SetCurrent(3)
	view := p.View()
	if !strings.Contains(view, "3/4") {
		t.Errorf("bar should show 3/4, got %q", view)
	}
}

func TestProgressBar_ClampsCurrent(t *testing.T) {
	p := NewProgressBar(3).SetCurrent(10)
	view := p.View()
	if !strings.Contains(view, "3/3") {
		t.Errorf("current should be clamped to total, got %q", view)
	}

	p = NewProgressBar(3).SetCurrent(-1)
	view = p.View()
	if !strings.Contains(view, "0/3") {
		t.Errorf("negative current should be clamped to 0, got %q", view)
	}
}

func TestProgressBar_ZeroTotal(t *testing.T) {
	p := NewProgressBar(0)
	view := p.View()
	if !strings.Contains(view, "No steps") {
		t.Errorf("zero total should show 'No steps', got %q", view)
	}
}

func TestProgressBar_SetWidth(t *testing.T) {
	p := NewProgressBar(5).SetWidth(40)
	if p.width != 40 {
		t.Errorf("SetWidth(40) should set width to 40, got %d", p.width)
	}
}

func TestProgressBar_FullCompletion(t *testing.T) {
	p := NewProgressBar(3).SetCurrent(3).SetWidth(12)
	view := p.View()
	// Should be fully filled (12 block chars)
	if strings.Count(view, "█") != 12 {
		t.Errorf("fully complete bar should have 12 filled blocks, got %d in %q",
			strings.Count(view, "█"), view)
	}
}
