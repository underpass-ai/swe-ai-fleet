package views

import (
	"fmt"
	"strings"
	"testing"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

func testEpics() []domain.EpicSummary {
	return []domain.EpicSummary{
		{ID: "epic-001-abcdef", Title: "User Auth", Status: "ACTIVE", CreatedAt: "2026-01-10"},
		{ID: "epic-002-abcdef", Title: "Dashboard", Status: "ARCHIVED", CreatedAt: "2026-01-11"},
		{ID: "epic-003-abcdef", Title: "Settings", Status: "DRAFT", CreatedAt: "2026-01-12"},
	}
}

var testProject = domain.ProjectSummary{
	ID: "proj-001", Name: "TestProject", Status: "ACTIVE", Owner: "alice",
}

func TestProjectDetailModel_LoadedMsg(t *testing.T) {
	t.Parallel()
	m := NewProjectDetailModel(&fakeFleetClient{}, testProject)
	m = m.SetSize(120, 40)

	epics := testEpics()
	m, _ = m.Update(epicsLoadedMsg{epics: epics, total: 3})

	if m.loading {
		t.Error("loading should be false after data load")
	}
	if len(m.epics) != 3 {
		t.Errorf("epics count = %d, want 3", len(m.epics))
	}
	view := m.View()
	if !strings.Contains(view, "User Auth") {
		t.Error("view should show epic title")
	}
	if !strings.Contains(view, "TestProject") {
		t.Error("view should show project name in card")
	}
}

func TestProjectDetailModel_ErrMsg(t *testing.T) {
	t.Parallel()
	m := NewProjectDetailModel(&fakeFleetClient{}, testProject)
	m = m.SetSize(120, 40)

	m, _ = m.Update(epicsErrMsg{err: fmt.Errorf("rpc timeout")})

	if m.err == nil {
		t.Fatal("err should be set")
	}
	view := m.View()
	if !strings.Contains(view, "rpc timeout") {
		t.Error("view should show error message")
	}
}

func TestProjectDetailModel_StatusFilter(t *testing.T) {
	t.Parallel()
	m := NewProjectDetailModel(&fakeFleetClient{epics: testEpics()}, testProject)
	m = m.SetSize(120, 40)
	m, _ = m.Update(epicsLoadedMsg{epics: testEpics(), total: 3})

	// Cycle to ACTIVE — triggers server reload
	m, cmd := m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("f")})
	if m.statusFilter != 1 {
		t.Errorf("after f, filter = %d, want 1", m.statusFilter)
	}
	if !m.loading {
		t.Error("filter change should set loading")
	}
	if cmd == nil {
		t.Error("filter change should return load command")
	}
	if got := m.serverStatusFilter(); got != "ACTIVE" {
		t.Errorf("filter 1 should send ACTIVE, got %q", got)
	}

	// Simulate server response for ACTIVE
	m, _ = m.Update(epicsLoadedMsg{
		epics: []domain.EpicSummary{{ID: "epic-001-abcdef", Title: "User Auth", Status: "ACTIVE"}},
		total: 1,
	})
	if len(m.epics) != 1 || m.epics[0].Title != "User Auth" {
		t.Errorf("after ACTIVE load, should have 1 epic, got %d", len(m.epics))
	}

	// Cycle to ARCHIVED
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("f")})
	if got := m.serverStatusFilter(); got != "ARCHIVED" {
		t.Errorf("filter 2 should send ARCHIVED, got %q", got)
	}

	// Cycle to DRAFT
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("f")})
	if got := m.serverStatusFilter(); got != "DRAFT" {
		t.Errorf("filter 3 should send DRAFT, got %q", got)
	}

	// Wrap to ALL
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("f")})
	if m.statusFilter != 0 {
		t.Errorf("after 4th f, filter should wrap to 0, got %d", m.statusFilter)
	}
	if got := m.serverStatusFilter(); got != "" {
		t.Errorf("ALL should send empty filter, got %q", got)
	}
}

func TestProjectDetailModel_SearchMode(t *testing.T) {
	t.Parallel()
	m := NewProjectDetailModel(&fakeFleetClient{}, testProject)
	m = m.SetSize(120, 40)
	m, _ = m.Update(epicsLoadedMsg{epics: testEpics(), total: 3})

	// Enter search mode
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("/")})
	if !m.searching {
		t.Error("should be in search mode after /")
	}

	// Cancel search
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyEsc})
	if m.searching {
		t.Error("should exit search after esc")
	}
}

func TestProjectDetailModel_SearchFiltering(t *testing.T) {
	t.Parallel()
	m := NewProjectDetailModel(&fakeFleetClient{}, testProject)
	m = m.SetSize(120, 40)
	m, _ = m.Update(epicsLoadedMsg{epics: testEpics(), total: 3})

	// Search for "auth"
	m.searchTerm = "auth"
	filtered := m.filteredEpics()
	if len(filtered) != 1 || filtered[0].Title != "User Auth" {
		t.Errorf("search 'auth' should match User Auth, got %d", len(filtered))
	}

	// No match
	m.searchTerm = "zzz"
	filtered = m.filteredEpics()
	if len(filtered) != 0 {
		t.Errorf("search 'zzz' should return 0, got %d", len(filtered))
	}
}

func TestProjectDetailModel_SearchAndStatusFilter(t *testing.T) {
	t.Parallel()
	// Server already filtered to ACTIVE-only epics
	activeEpics := []domain.EpicSummary{
		{ID: "e1", Title: "Auth Module", Status: "ACTIVE"},
		{ID: "e3", Title: "Dashboard", Status: "ACTIVE"},
	}
	m := NewProjectDetailModel(&fakeFleetClient{}, testProject)
	m = m.SetSize(120, 40)
	m.statusFilter = 1 // ACTIVE (server-side)
	m, _ = m.Update(epicsLoadedMsg{epics: activeEpics, total: 2})

	// Client-side text search on server-filtered set
	m.searchTerm = "auth"
	filtered := m.filteredEpics()
	if len(filtered) != 1 || filtered[0].Title != "Auth Module" {
		t.Errorf("ACTIVE(server) + 'auth'(client) should match Auth Module, got %d", len(filtered))
	}
}

func TestProjectDetailModel_Pagination(t *testing.T) {
	t.Parallel()
	m := NewProjectDetailModel(&fakeFleetClient{}, testProject)
	m = m.SetSize(120, 40)
	m, _ = m.Update(epicsLoadedMsg{epics: testEpics(), total: 50})

	if !m.paginator.HasNext() {
		t.Error("should have next page with total=50")
	}

	// Next page
	m, cmd := m.Update(tea.KeyMsg{Type: tea.KeyRight})
	if cmd == nil {
		t.Error("page change should trigger load command")
	}
	if !m.loading {
		t.Error("should be loading after page change")
	}
}

func TestProjectDetailModel_CreateForm(t *testing.T) {
	t.Parallel()
	m := NewProjectDetailModel(&fakeFleetClient{}, testProject)
	m = m.SetSize(120, 40)
	m, _ = m.Update(epicsLoadedMsg{epics: nil, total: 0})

	// Enter create mode
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("n")})
	if !m.creating {
		t.Error("should be in create mode")
	}

	view := m.View()
	if !strings.Contains(view, "Create New Epic") {
		t.Error("create form should show title")
	}

	// Cancel
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyEsc})
	if m.creating {
		t.Error("should exit create mode after esc")
	}
}

func TestProjectDetailModel_CreateFormValidation(t *testing.T) {
	t.Parallel()
	m := NewProjectDetailModel(&fakeFleetClient{}, testProject)
	m = m.SetSize(120, 40)
	m, _ = m.Update(epicsLoadedMsg{epics: nil, total: 0})

	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("n")})
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})

	if m.err == nil || !strings.Contains(m.err.Error(), "title is required") {
		t.Errorf("expected title required error, got %v", m.err)
	}
}

func TestProjectDetailModel_Refresh(t *testing.T) {
	t.Parallel()
	m := NewProjectDetailModel(&fakeFleetClient{}, testProject)
	m = m.SetSize(120, 40)
	m, _ = m.Update(epicsLoadedMsg{epics: testEpics(), total: 3})

	m, cmd := m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("r")})
	if !m.loading {
		t.Error("refresh should set loading")
	}
	if cmd == nil {
		t.Error("refresh should return a command")
	}
}

func TestProjectDetailModel_ProjectCard(t *testing.T) {
	t.Parallel()
	proj := domain.ProjectSummary{
		ID: "p1", Name: "My Project", Description: "Cool project", Status: "ACTIVE", Owner: "alice",
		CreatedAt: "2026-01-01", UpdatedAt: "2026-01-15",
	}
	m := NewProjectDetailModel(&fakeFleetClient{}, proj)
	m = m.SetSize(120, 40)
	m, _ = m.Update(epicsLoadedMsg{epics: nil, total: 0})

	view := m.View()
	if !strings.Contains(view, "My Project") {
		t.Error("card should show project name")
	}
	if !strings.Contains(view, "Cool project") {
		t.Error("card should show description")
	}
	if !strings.Contains(view, "ACTIVE") {
		t.Error("card should show status")
	}
}

func TestProjectDetailModel_SearchCommit(t *testing.T) {
	t.Parallel()
	m := NewProjectDetailModel(&fakeFleetClient{}, testProject)
	m = m.SetSize(120, 40)
	m, _ = m.Update(epicsLoadedMsg{epics: testEpics(), total: 3})

	// Enter search, set term, commit with enter
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("/")})
	m.searchInput.SetValue("dashboard")
	m.searchTerm = "dashboard"
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})

	if m.searching {
		t.Error("should exit search after enter")
	}
	if m.searchTerm != "dashboard" {
		t.Errorf("term should be 'dashboard', got %q", m.searchTerm)
	}
}

func TestProjectDetailModel_ViewShowsSearchTerm(t *testing.T) {
	t.Parallel()
	m := NewProjectDetailModel(&fakeFleetClient{}, testProject)
	m = m.SetSize(120, 40)
	m, _ = m.Update(epicsLoadedMsg{epics: testEpics(), total: 3})

	m.searchTerm = "auth"
	view := m.View()
	if !strings.Contains(view, "auth") {
		t.Error("view should show active search term")
	}
}
