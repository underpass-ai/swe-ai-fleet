package views

import (
	"fmt"
	"strings"
	"testing"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

func TestCeremoniesModel_ListMode(t *testing.T) {
	client := &fakeFleetClient{
		ceremonies: []domain.CeremonyStatus{
			{
				InstanceID:     "inst-0001-abcdef",
				CeremonyID:     "cer-001",
				StoryID:        "story-001",
				DefinitionName: "backlog_review",
				Status:         "RUNNING",
				StepStatuses:   map[string]string{"step-1": "COMPLETED", "step-2": "RUNNING"},
				UpdatedAt:      "2026-01-15T10:00:00Z",
			},
		},
	}
	m := NewCeremoniesModel(client)
	m = m.SetSize(120, 40)

	// Simulate data loaded
	m, _ = m.Update(ceremoniesLoadedMsg{
		ceremonies: client.ceremonies,
		total:      1,
	})

	view := m.View()
	if !strings.Contains(view, "backlog_review") {
		t.Error("list view should show definition name")
	}
	if !strings.Contains(view, "RUNNING") {
		t.Error("list view should show status")
	}
	if m.mode != ceremonyModeList {
		t.Error("initial mode should be list")
	}
}

func TestCeremoniesModel_EnterDetail(t *testing.T) {
	client := &fakeFleetClient{
		ceremonies: []domain.CeremonyStatus{
			{
				InstanceID:     "inst-0001",
				DefinitionName: "planning",
				Status:         "COMPLETED",
				StepStatuses:   map[string]string{"analyze": "COMPLETED", "plan": "COMPLETED"},
				StepOutputs:    map[string]string{"analyze": "Found 3 stories", "plan": "Created 5 tasks"},
			},
		},
	}
	m := NewCeremoniesModel(client)
	m = m.SetSize(120, 40)

	m, _ = m.Update(ceremoniesLoadedMsg{ceremonies: client.ceremonies, total: 1})
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})

	if m.mode != ceremonyModeDetail {
		t.Errorf("after enter, mode should be detail, got %d", m.mode)
	}

	view := m.View()
	if !strings.Contains(view, "Ceremony Detail") {
		t.Error("detail view should show heading")
	}
}

func TestCeremoniesModel_WatchMode(t *testing.T) {
	client := &fakeFleetClient{
		ceremonies: []domain.CeremonyStatus{
			{
				InstanceID:   "inst-0001",
				Status:       "RUNNING",
				StepStatuses: map[string]string{"step-1": "RUNNING"},
				StepOutputs:  map[string]string{"step-1": "processing..."},
			},
		},
	}
	m := NewCeremoniesModel(client)
	m = m.SetSize(120, 40)

	m, _ = m.Update(ceremoniesLoadedMsg{ceremonies: client.ceremonies, total: 1})
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter}) // enter detail
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("w")}) // enter watch

	if m.mode != ceremonyModeWatch {
		t.Errorf("after 'w', mode should be watch, got %d", m.mode)
	}
	if !m.watchActive {
		t.Error("watchActive should be true")
	}

	view := m.View()
	if !strings.Contains(view, "LIVE") {
		t.Error("watch view should show LIVE indicator")
	}
}

func TestCeremoniesModel_EscFromWatch(t *testing.T) {
	client := &fakeFleetClient{
		ceremonies: []domain.CeremonyStatus{
			{InstanceID: "inst-0001", StepStatuses: map[string]string{}},
		},
	}
	m := NewCeremoniesModel(client)
	m = m.SetSize(120, 40)

	m, _ = m.Update(ceremoniesLoadedMsg{ceremonies: client.ceremonies, total: 1})
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("w")})
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyEsc})

	if m.mode != ceremonyModeDetail {
		t.Errorf("esc from watch should go to detail, got %d", m.mode)
	}
}

func TestCeremoniesModel_EscFromDetail(t *testing.T) {
	client := &fakeFleetClient{
		ceremonies: []domain.CeremonyStatus{
			{InstanceID: "inst-0001", StepStatuses: map[string]string{}},
		},
	}
	m := NewCeremoniesModel(client)
	m = m.SetSize(120, 40)

	m, _ = m.Update(ceremoniesLoadedMsg{ceremonies: client.ceremonies, total: 1})
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyEsc})

	if m.mode != ceremonyModeList {
		t.Errorf("esc from detail should go to list, got %d", m.mode)
	}
}

func TestCeremoniesModel_FilterCycle(t *testing.T) {
	client := &fakeFleetClient{}
	m := NewCeremoniesModel(client)

	if m.statusFilter != 0 {
		t.Error("initial filter should be 0 (ALL)")
	}

	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("f")})
	if m.statusFilter != 1 {
		t.Errorf("after 'f', filter should be 1, got %d", m.statusFilter)
	}
}

func TestCeremoniesModel_Error(t *testing.T) {
	client := &fakeFleetClient{}
	m := NewCeremoniesModel(client)
	m = m.SetSize(120, 40)

	m, _ = m.Update(ceremoniesErrMsg{err: fmt.Errorf("test error")})
	if m.err == nil {
		t.Error("error message should set err")
	}
	if m.loading {
		t.Error("loading should be false after error")
	}
}


func TestCeremoniesModel_NavigateList(t *testing.T) {
	client := &fakeFleetClient{}
	m := NewCeremoniesModel(client)
	m, _ = m.Update(ceremoniesLoadedMsg{
		ceremonies: []domain.CeremonyStatus{
			{InstanceID: "a", Status: "RUNNING"},
			{InstanceID: "b", Status: "COMPLETED"},
		},
		total: 2,
	})

	if m.selected != 0 {
		t.Error("initial selection should be 0")
	}
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("j")})
	if m.selected != 1 {
		t.Errorf("after 'j', selected should be 1, got %d", m.selected)
	}
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("k")})
	if m.selected != 0 {
		t.Errorf("after 'k', selected should be 0, got %d", m.selected)
	}
}

func TestCeremoniesModel_WatchTick(t *testing.T) {
	client := &fakeFleetClient{
		ceremonies: []domain.CeremonyStatus{
			{InstanceID: "inst-0001", StepStatuses: map[string]string{"s1": "RUNNING"}},
		},
	}
	m := NewCeremoniesModel(client)
	m = m.SetSize(120, 40)
	m, _ = m.Update(ceremoniesLoadedMsg{ceremonies: client.ceremonies, total: 1})
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("w")})

	// Process watch tick
	m, cmd := m.Update(ceremonyWatchTickMsg{})
	if cmd == nil {
		t.Error("watch tick should produce a cmd for refresh + next tick")
	}
	_ = m // avoid unused
}

func TestStepStatusDot(t *testing.T) {
	tests := []struct {
		status string
		want   string
	}{
		{"COMPLETED", stepDone},
		{"DONE", stepDone},
		{"RUNNING", stepRunning},
		{"IN_PROGRESS", stepRunning},
		{"FAILED", stepFailed},
		{"ERROR", stepFailed},
		{"PENDING", stepPending},
		{"unknown", stepPending},
	}
	for _, tt := range tests {
		t.Run(tt.status, func(t *testing.T) {
			if got := stepStatusDot(tt.status); got != tt.want {
				t.Errorf("stepStatusDot(%q) = %q, want %q", tt.status, got, tt.want)
			}
		})
	}
}

func TestTruncID(t *testing.T) {
	if got := truncID("abcdefghij"); got != "abcdefgh" {
		t.Errorf("truncID should truncate to 8, got %q", got)
	}
	if got := truncID("short"); got != "short" {
		t.Errorf("truncID should not truncate short ids, got %q", got)
	}
}
