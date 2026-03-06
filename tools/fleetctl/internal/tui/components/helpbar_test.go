package components

import (
	"strings"
	"testing"
)

func TestHelpBar_EmptyBindings(t *testing.T) {
	h := NewHelpBar()
	if got := h.View(); got != "" {
		t.Errorf("empty HelpBar should render empty string, got %q", got)
	}
}

func TestHelpBar_RendersBindings(t *testing.T) {
	h := NewHelpBar(
		HelpBinding{Key: "q", Description: "quit"},
		HelpBinding{Key: "r", Description: "refresh"},
	)
	view := h.View()
	if !strings.Contains(view, "q") {
		t.Error("view should contain key 'q'")
	}
	if !strings.Contains(view, "quit") {
		t.Error("view should contain description 'quit'")
	}
	if !strings.Contains(view, "refresh") {
		t.Error("view should contain description 'refresh'")
	}
}

func TestHelpBar_SetWidth(t *testing.T) {
	h := NewHelpBar(HelpBinding{Key: "q", Description: "quit"})
	h2 := h.SetWidth(80)
	// SetWidth returns a copy; original unchanged.
	if h.width != 0 {
		t.Error("original should be unchanged")
	}
	if h2.width != 80 {
		t.Errorf("SetWidth should set to 80, got %d", h2.width)
	}
}

func TestHelpBar_SetBindings(t *testing.T) {
	h := NewHelpBar(HelpBinding{Key: "a", Description: "one"})
	h2 := h.SetBindings(HelpBinding{Key: "b", Description: "two"})
	if len(h.bindings) != 1 {
		t.Error("original bindings should be unchanged")
	}
	if len(h2.bindings) != 1 || h2.bindings[0].Key != "b" {
		t.Error("SetBindings should replace bindings")
	}
}
