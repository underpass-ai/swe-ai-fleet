package views

import (
	"fmt"
	"strings"
	"testing"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/command"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/query"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// newTestProjectsModel builds a ProjectsModel wired to the given fake client
// through real command/query handlers.
func newTestProjectsModel(client *fakeFleetClient) ProjectsModel {
	return NewProjectsModel(
		command.NewCreateProjectHandler(client),
		query.NewListProjectsHandler(client),
	)
}

func testProjects() []domain.ProjectSummary {
	return []domain.ProjectSummary{
		{ID: "proj-001-abcdef", Name: "Alpha", Description: "First project", Status: "ACTIVE", Owner: "alice", CreatedAt: "2026-01-01"},
		{ID: "proj-002-abcdef", Name: "Beta", Description: "Second project", Status: "ARCHIVED", Owner: "bob", CreatedAt: "2026-01-02"},
		{ID: "proj-003-abcdef", Name: "Gamma", Description: "Third project", Status: "DRAFT", Owner: "carol", CreatedAt: "2026-01-03"},
	}
}

func TestProjectsModel_LoadedMsg(t *testing.T) {
	t.Parallel()
	client := &fakeFleetClient{projects: testProjects()}
	m := newTestProjectsModel(client)
	m = m.SetSize(120, 40)

	m, _ = m.Update(projectsLoadedMsg{projects: client.projects, total: 3})

	if m.loading {
		t.Error("loading should be false after data load")
	}
	if len(m.projects) != 3 {
		t.Errorf("projects count = %d, want 3", len(m.projects))
	}
	view := m.View()
	if !strings.Contains(view, "Alpha") {
		t.Error("view should show project name Alpha")
	}
	if !strings.Contains(view, "Beta") {
		t.Error("view should show project name Beta")
	}
}

func TestProjectsModel_ErrMsg(t *testing.T) {
	t.Parallel()
	m := newTestProjectsModel(&fakeFleetClient{})
	m = m.SetSize(120, 40)

	m, _ = m.Update(projectsErrMsg{err: fmt.Errorf("connection refused")})

	if m.err == nil {
		t.Fatal("err should be set")
	}
	view := m.View()
	if !strings.Contains(view, "connection refused") {
		t.Error("view should show error message")
	}
}

func TestProjectsModel_StatusFilter(t *testing.T) {
	t.Parallel()
	client := &fakeFleetClient{projects: testProjects()}
	m := newTestProjectsModel(client)
	m = m.SetSize(120, 40)
	m, _ = m.Update(projectsLoadedMsg{projects: client.projects, total: 3})

	// Initially ALL
	if m.statusFilter != 0 {
		t.Errorf("initial filter = %d, want 0", m.statusFilter)
	}
	if got := m.serverStatusFilter(); got != "" {
		t.Errorf("ALL should send empty filter, got %q", got)
	}

	// Press 'f' to cycle to ACTIVE — triggers server reload
	m, cmd := m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("f")})
	if m.statusFilter != 1 {
		t.Errorf("after f, filter = %d, want 1 (ACTIVE)", m.statusFilter)
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

	// Simulate server response for ACTIVE filter
	m, _ = m.Update(projectsLoadedMsg{
		projects: []domain.ProjectSummary{{ID: "proj-001-abcdef", Name: "Alpha", Status: "ACTIVE"}},
		total:    1,
	})
	if len(m.projects) != 1 || m.projects[0].Name != "Alpha" {
		t.Errorf("after ACTIVE load, should have 1 project, got %d", len(m.projects))
	}

	// Press 'f' to ARCHIVED
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("f")})
	if got := m.serverStatusFilter(); got != "ARCHIVED" {
		t.Errorf("filter 2 should send ARCHIVED, got %q", got)
	}

	// Press 'f' to DRAFT
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("f")})
	if got := m.serverStatusFilter(); got != "DRAFT" {
		t.Errorf("filter 3 should send DRAFT, got %q", got)
	}

	// Press 'f' wraps back to ALL
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("f")})
	if m.statusFilter != 0 {
		t.Errorf("after 4th f, filter should wrap to 0, got %d", m.statusFilter)
	}
	if got := m.serverStatusFilter(); got != "" {
		t.Errorf("ALL should send empty filter, got %q", got)
	}
}

func TestProjectsModel_SearchMode(t *testing.T) {
	t.Parallel()
	client := &fakeFleetClient{projects: testProjects()}
	m := newTestProjectsModel(client)
	m = m.SetSize(120, 40)
	m, _ = m.Update(projectsLoadedMsg{projects: client.projects, total: 3})

	// Press '/' to enter search
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("/")})
	if !m.searching {
		t.Error("should be in search mode after /")
	}

	// Press 'esc' to cancel
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyEsc})
	if m.searching {
		t.Error("should exit search mode after esc")
	}
	if m.searchTerm != "" {
		t.Error("search term should be cleared after esc")
	}
}

func TestProjectsModel_SearchFiltering(t *testing.T) {
	t.Parallel()
	client := &fakeFleetClient{projects: testProjects()}
	m := newTestProjectsModel(client)
	m = m.SetSize(120, 40)
	m, _ = m.Update(projectsLoadedMsg{projects: client.projects, total: 3})

	// Set search term directly and verify filtering
	m.searchTerm = "alpha"
	filtered := m.filteredProjects()
	if len(filtered) != 1 || filtered[0].Name != "Alpha" {
		t.Errorf("search 'alpha' should match Alpha, got %d results", len(filtered))
	}

	// Search by description
	m.searchTerm = "second"
	filtered = m.filteredProjects()
	if len(filtered) != 1 || filtered[0].Name != "Beta" {
		t.Errorf("search 'second' should match Beta, got %d results", len(filtered))
	}

	// No match
	m.searchTerm = "nonexistent"
	filtered = m.filteredProjects()
	if len(filtered) != 0 {
		t.Errorf("search 'nonexistent' should return 0, got %d", len(filtered))
	}
}

func TestProjectsModel_SearchAndStatusFilter(t *testing.T) {
	t.Parallel()
	// With server-side status filter, simulate server already returned ACTIVE-only projects
	activeProjects := []domain.ProjectSummary{
		{ID: "p1", Name: "Frontend App", Status: "ACTIVE"},
		{ID: "p3", Name: "Backend API", Status: "ACTIVE"},
	}
	client := &fakeFleetClient{projects: activeProjects}
	m := newTestProjectsModel(client)
	m = m.SetSize(120, 40)
	m.statusFilter = 1 // ACTIVE (already filtered server-side)
	m, _ = m.Update(projectsLoadedMsg{projects: activeProjects, total: 2})

	// Client-side text search on the already-filtered set
	m.searchTerm = "frontend"
	filtered := m.filteredProjects()
	if len(filtered) != 1 || filtered[0].Name != "Frontend App" {
		t.Errorf("ACTIVE(server) + 'frontend'(client) should return 1, got %d", len(filtered))
	}
}

func TestProjectsModel_PaginationNextPrev(t *testing.T) {
	t.Parallel()
	client := &fakeFleetClient{projects: testProjects()}
	m := newTestProjectsModel(client)
	m = m.SetSize(120, 40)
	m, _ = m.Update(projectsLoadedMsg{projects: client.projects, total: 50})

	// After load, paginator should know total
	if !m.paginator.HasNext() {
		t.Error("should have next page with total=50")
	}

	// Press right arrow
	m, cmd := m.Update(tea.KeyMsg{Type: tea.KeyRight})
	if cmd == nil {
		t.Error("page change should trigger load command")
	}
	if !m.loading {
		t.Error("should be loading after page change")
	}
}

func TestProjectsModel_CreateForm(t *testing.T) {
	t.Parallel()
	m := newTestProjectsModel(&fakeFleetClient{})
	m = m.SetSize(120, 40)
	m, _ = m.Update(projectsLoadedMsg{projects: nil, total: 0})

	// Press 'n' to enter create mode
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("n")})
	if !m.creating {
		t.Error("should be in creating mode after 'n'")
	}

	view := m.View()
	if !strings.Contains(view, "Create New Project") {
		t.Error("create form should show title")
	}

	// Press 'esc' to cancel
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyEsc})
	if m.creating {
		t.Error("should exit create mode after esc")
	}
}

func TestProjectsModel_CreateFormValidation(t *testing.T) {
	t.Parallel()
	m := newTestProjectsModel(&fakeFleetClient{})
	m = m.SetSize(120, 40)
	m, _ = m.Update(projectsLoadedMsg{projects: nil, total: 0})

	// Enter create mode
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("n")})

	// Press enter with empty name
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	if m.err == nil {
		t.Error("should have validation error for empty name")
	}
	if !strings.Contains(m.err.Error(), "name is required") {
		t.Errorf("error should mention name required, got: %v", m.err)
	}
}

func TestProjectsModel_Refresh(t *testing.T) {
	t.Parallel()
	m := newTestProjectsModel(&fakeFleetClient{})
	m = m.SetSize(120, 40)
	m, _ = m.Update(projectsLoadedMsg{projects: nil, total: 0})

	m, cmd := m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("r")})
	if !m.loading {
		t.Error("refresh should set loading")
	}
	if cmd == nil {
		t.Error("refresh should return a command")
	}
}

func TestProjectsModel_EmptyView(t *testing.T) {
	t.Parallel()
	m := newTestProjectsModel(&fakeFleetClient{})
	m = m.SetSize(120, 40)
	m, _ = m.Update(projectsLoadedMsg{projects: nil, total: 0})

	view := m.View()
	if !strings.Contains(view, "No projects match the filter") {
		t.Error("empty view should show no-match message")
	}
}

func TestProjectsModel_ViewShowsFilter(t *testing.T) {
	t.Parallel()
	m := newTestProjectsModel(&fakeFleetClient{projects: testProjects()})
	m = m.SetSize(120, 40)
	m, _ = m.Update(projectsLoadedMsg{projects: testProjects(), total: 3})

	view := m.View()
	if !strings.Contains(view, "ALL") {
		t.Error("view should show current filter label")
	}
	if !strings.Contains(view, "/: search") {
		t.Error("help text should mention search shortcut")
	}
}

func TestProjectsModel_SearchEnterCommits(t *testing.T) {
	t.Parallel()
	client := &fakeFleetClient{projects: testProjects()}
	m := newTestProjectsModel(client)
	m = m.SetSize(120, 40)
	m, _ = m.Update(projectsLoadedMsg{projects: client.projects, total: 3})

	// Enter search mode
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("/")})

	// Type search term by setting input value directly
	m.searchInput.SetValue("gamma")
	m.searchTerm = "gamma"

	// Press enter to commit
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})
	if m.searching {
		t.Error("should exit search mode after enter")
	}
	if m.searchTerm != "gamma" {
		t.Errorf("search term should be 'gamma', got %q", m.searchTerm)
	}
}
