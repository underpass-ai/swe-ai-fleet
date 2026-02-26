package views

import (
	"fmt"
	"strings"
	"testing"

	tea "github.com/charmbracelet/bubbletea"
)

func TestDecisionsModel_SelectMode(t *testing.T) {
	client := &fakeFleetClient{}
	m := NewDecisionsModel(client, "story-1")
	m = m.SetDecisions([]DecisionItem{
		{ID: "dec-1", Type: "APPROVAL", Status: "PENDING"},
		{ID: "dec-2", Type: "REVIEW", Status: "PENDING"},
	})

	view := m.View()
	if !strings.Contains(view, "Pending Decisions") {
		t.Error("view should contain 'Pending Decisions' heading")
	}
	if !strings.Contains(view, "dec-1") || !strings.Contains(view, "dec-2") {
		t.Error("view should list both decisions")
	}
}

func TestDecisionsModel_NavigateDown(t *testing.T) {
	client := &fakeFleetClient{}
	m := NewDecisionsModel(client, "story-1")
	m = m.SetDecisions([]DecisionItem{
		{ID: "dec-1", Type: "APPROVAL", Status: "PENDING"},
		{ID: "dec-2", Type: "REVIEW", Status: "PENDING"},
	})

	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("j")})
	if m.selected != 1 {
		t.Errorf("after 'j', selected should be 1, got %d", m.selected)
	}
}

func TestDecisionsModel_ApproveFlow(t *testing.T) {
	client := &fakeFleetClient{}
	m := NewDecisionsModel(client, "story-1")
	m = m.SetDecisions([]DecisionItem{
		{ID: "dec-1", Type: "APPROVAL", Status: "PENDING"},
	})

	// Press 'a' to enter approve form
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("a")})
	if m.mode != decisionModeApproveForm {
		t.Errorf("mode should be approveForm, got %d", m.mode)
	}

	view := m.View()
	if !strings.Contains(view, "APPROVE") {
		t.Error("approve form should display APPROVE tag")
	}
}

func TestDecisionsModel_RejectFlow(t *testing.T) {
	client := &fakeFleetClient{}
	m := NewDecisionsModel(client, "story-1")
	m = m.SetDecisions([]DecisionItem{
		{ID: "dec-1", Type: "APPROVAL", Status: "PENDING"},
	})

	// Press 'x' to enter reject form
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("x")})
	if m.mode != decisionModeRejectForm {
		t.Errorf("mode should be rejectForm, got %d", m.mode)
	}

	view := m.View()
	if !strings.Contains(view, "REJECT") {
		t.Error("reject form should display REJECT tag")
	}
}

func TestDecisionsModel_RejectValidation(t *testing.T) {
	client := &fakeFleetClient{}
	m := NewDecisionsModel(client, "story-1")
	m = m.SetDecisions([]DecisionItem{
		{ID: "dec-1", Type: "APPROVAL", Status: "PENDING"},
	})

	// Enter reject mode and try to submit empty
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("x")})
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyCtrlD})
	if m.err == nil {
		t.Error("submitting empty reason should set error")
	}
}

func TestDecisionsModel_ApproveSuccess(t *testing.T) {
	client := &fakeFleetClient{}
	m := NewDecisionsModel(client, "story-1")
	m = m.SetDecisions([]DecisionItem{
		{ID: "dec-1", Type: "APPROVAL", Status: "PENDING"},
	})

	// Process approve result
	m, _ = m.Update(decisionApprovedMsg{})
	if m.mode != decisionModeResult {
		t.Errorf("mode should be result, got %d", m.mode)
	}
	if !m.resultOK {
		t.Error("resultOK should be true after approval")
	}
	view := m.View()
	if !strings.Contains(view, "approved") {
		t.Errorf("result should mention 'approved', got %q", view)
	}
}

func TestDecisionsModel_RejectSuccess(t *testing.T) {
	client := &fakeFleetClient{}
	m := NewDecisionsModel(client, "story-1")
	m = m.SetDecisions([]DecisionItem{
		{ID: "dec-1", Type: "APPROVAL", Status: "PENDING"},
	})

	m, _ = m.Update(decisionRejectedMsg{})
	if m.mode != decisionModeResult {
		t.Errorf("mode should be result, got %d", m.mode)
	}
	view := m.View()
	if !strings.Contains(view, "rejected") {
		t.Errorf("result should mention 'rejected', got %q", view)
	}
}

func TestDecisionsModel_Error(t *testing.T) {
	client := &fakeFleetClient{}
	m := NewDecisionsModel(client, "story-1")
	m = m.SetDecisions([]DecisionItem{
		{ID: "dec-1", Type: "APPROVAL", Status: "PENDING"},
	})

	m, _ = m.Update(decisionErrMsg{err: fmt.Errorf("server error")})
	if m.mode != decisionModeResult {
		t.Errorf("mode should be result, got %d", m.mode)
	}
	if m.resultOK {
		t.Error("resultOK should be false after error")
	}
}

func TestDecisionsModel_EmptyDecisions(t *testing.T) {
	client := &fakeFleetClient{}
	m := NewDecisionsModel(client, "story-1")
	m = m.SetDecisions(nil)

	view := m.View()
	if !strings.Contains(view, "No pending decisions") {
		t.Error("empty decisions should show empty message")
	}
}

func TestDecisionsModel_EscFromApprove(t *testing.T) {
	client := &fakeFleetClient{}
	m := NewDecisionsModel(client, "story-1")
	m = m.SetDecisions([]DecisionItem{
		{ID: "dec-1", Type: "APPROVAL", Status: "PENDING"},
	})

	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("a")})
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyEsc})
	if m.mode != decisionModeSelect {
		t.Error("esc should return to select mode")
	}
}

func TestDecisionsModel_ResultDone(t *testing.T) {
	client := &fakeFleetClient{}
	m := NewDecisionsModel(client, "story-1")
	m.mode = decisionModeResult

	m, _ = m.Update(decisionResultDoneMsg{})
	if m.mode != decisionModeSelect {
		t.Errorf("after result done, should return to select, got %d", m.mode)
	}
}
