package views

import (
	"context"
	"strings"
	"testing"
	"time"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/command"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/query"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

// newTestBacklogReviewModel builds a BacklogReviewModel wired to the given fake
// client through real command/query handlers.
func newTestBacklogReviewModel(fc *fakeFleetClient, epic domain.EpicSummary, project domain.ProjectSummary) BacklogReviewModel {
	return NewBacklogReviewModel(
		query.NewListStoriesHandler(fc),
		command.NewCreateBacklogReviewHandler(fc),
		command.NewStartBacklogReviewHandler(fc),
		query.NewGetBacklogReviewHandler(fc),
		command.NewApproveReviewPlanHandler(fc),
		command.NewRejectReviewPlanHandler(fc),
		command.NewCompleteBacklogReviewHandler(fc),
		command.NewCancelBacklogReviewHandler(fc),
		query.NewWatchEventsHandler(fc),
		epic,
		project,
	)
}

var brTestEpic = domain.EpicSummary{ID: "epic-001", Title: "Test Epic"}
var brTestProject = domain.ProjectSummary{ID: "proj-001", Name: "Test Project"}

func TestBacklogReviewModel_Dashboard_NoReview(t *testing.T) {
	t.Parallel()
	client := &fakeFleetClient{
		stories: []domain.StorySummary{
			{ID: "s1", Title: "Story One", State: "DRAFT"},
		},
	}
	m := newTestBacklogReviewModel(client, brTestEpic, brTestProject)
	m = m.SetSize(120, 40)

	// Simulate stories loaded
	m, _ = m.Update(backlogReviewStoriesLoadedMsg{
		stories: client.stories,
		total:   1,
	})

	if m.mode != brModeDashboard {
		t.Errorf("mode = %d, want brModeDashboard", m.mode)
	}
	view := m.View()
	if !strings.Contains(view, "No backlog review ceremony yet") {
		t.Error("dashboard with no review should show placeholder message")
	}
}

func TestBacklogReviewModel_Dashboard_WithReview(t *testing.T) {
	t.Parallel()
	client := &fakeFleetClient{}
	m := newTestBacklogReviewModel(client, brTestEpic, brTestProject)
	m = m.SetSize(120, 40)

	review := domain.BacklogReview{
		CeremonyID: "cer-001-abcdef",
		Status:     "DRAFT",
		StoryIDs:   []string{"s1", "s2"},
		CreatedAt:  "2026-02-28T10:00:00Z",
	}
	m, _ = m.Update(backlogReviewStoriesLoadedMsg{stories: nil, total: 0})
	m, _ = m.Update(backlogReviewCreatedMsg{review: review})

	view := m.View()
	if !strings.Contains(view, "Backlog Review Ceremony") {
		t.Error("dashboard should show ceremony card heading")
	}
	if !strings.Contains(view, "DRAFT") {
		t.Error("dashboard should show ceremony status")
	}
	if !strings.Contains(view, "s: start") {
		t.Error("DRAFT ceremony should show start hint")
	}
}

func TestBacklogReviewModel_WatchStartedMsg(t *testing.T) {
	t.Parallel()
	client := &fakeFleetClient{}
	m := newTestBacklogReviewModel(client, brTestEpic, brTestProject)
	m = m.SetSize(120, 40)

	ch := make(chan domain.FleetEvent, 1)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	_ = ctx

	m, cmd := m.Update(backlogReviewWatchStartedMsg{ch: ch, cancel: cancel})

	if m.eventCh == nil {
		t.Error("eventCh should be set after WatchStartedMsg")
	}
	if m.cancel == nil {
		t.Error("cancel should be set after WatchStartedMsg")
	}
	if cmd == nil {
		t.Error("should return waitForEvent command")
	}
}

func TestBacklogReviewModel_EventMsg_RefreshAndKeepListening(t *testing.T) {
	t.Parallel()
	client := &fakeFleetClient{
		backlogReview: &domain.BacklogReview{
			CeremonyID: "cer-001",
			Status:     "REVIEWING",
		},
	}
	m := newTestBacklogReviewModel(client, brTestEpic, brTestProject)
	m = m.SetSize(120, 40)

	// Set up event channel so waitForEvent has something to wait on
	ch := make(chan domain.FleetEvent, 1)
	m.eventCh = ch
	m.review = &domain.BacklogReview{CeremonyID: "cer-001", Status: "IN_PROGRESS"}

	m, cmd := m.Update(backlogReviewEventMsg{event: domain.FleetEvent{Type: "backlog_review.story_reviewed"}})

	if cmd == nil {
		t.Error("event msg should return batch of refresh + waitForEvent commands")
	}
}

func TestBacklogReviewModel_Timeline_Draft(t *testing.T) {
	t.Parallel()
	client := &fakeFleetClient{}
	m := newTestBacklogReviewModel(client, brTestEpic, brTestProject)
	m = m.SetSize(120, 40)

	m.review = &domain.BacklogReview{
		CeremonyID: "cer-001",
		Status:     "DRAFT",
		CreatedAt:  "2026-02-28T10:00:00Z",
	}

	timeline := m.timelineView()
	if !strings.Contains(timeline, "Created") {
		t.Error("timeline should show Created phase")
	}
	if !strings.Contains(timeline, "Completed") {
		t.Error("timeline should show Completed phase")
	}
}

func TestBacklogReviewModel_Timeline_Completed(t *testing.T) {
	t.Parallel()
	client := &fakeFleetClient{}
	m := newTestBacklogReviewModel(client, brTestEpic, brTestProject)
	m = m.SetSize(120, 40)

	m.review = &domain.BacklogReview{
		CeremonyID:  "cer-001",
		Status:      "COMPLETED",
		CreatedAt:   "2026-02-28T10:00:00Z",
		StartedAt:   "2026-02-28T10:05:00Z",
		CompletedAt: "2026-02-28T10:30:00Z",
	}

	timeline := m.timelineView()
	if !strings.Contains(timeline, "10:00") {
		t.Error("timeline should show created time")
	}
	if !strings.Contains(timeline, "10:05") {
		t.Error("timeline should show started time")
	}
}

func TestBacklogReviewModel_Timeline_WithResults(t *testing.T) {
	t.Parallel()
	client := &fakeFleetClient{
		stories: []domain.StorySummary{
			{ID: "s1", Title: "Auth Story"},
			{ID: "s2", Title: "Dashboard Story"},
		},
	}
	m := newTestBacklogReviewModel(client, brTestEpic, brTestProject)
	m = m.SetSize(120, 40)
	m.stories = client.stories

	m.review = &domain.BacklogReview{
		CeremonyID: "cer-001",
		Status:     "REVIEWING",
		ReviewResults: []domain.StoryReviewResult{
			{StoryID: "s1", ApprovalStatus: "APPROVED", ReviewedAt: "2026-02-28T10:15:00Z", ApprovedAt: "2026-02-28T10:20:00Z"},
			{StoryID: "s2", ApprovalStatus: "PENDING"},
		},
	}

	timeline := m.timelineView()
	if !strings.Contains(timeline, "Story Progress") {
		t.Error("timeline should show Story Progress label")
	}
	if !strings.Contains(timeline, "APPROVED") {
		t.Error("timeline should show APPROVED status")
	}
	if !strings.Contains(timeline, "PENDING") {
		t.Error("timeline should show PENDING status")
	}
}

func TestBacklogReviewModel_Timeline_Nil(t *testing.T) {
	t.Parallel()
	m := newTestBacklogReviewModel(&fakeFleetClient{}, brTestEpic, brTestProject)
	m.review = nil

	timeline := m.timelineView()
	if timeline != "" {
		t.Error("timeline should be empty when review is nil")
	}
}

func TestBacklogReviewModel_Timeline_RejectedStory(t *testing.T) {
	t.Parallel()
	m := newTestBacklogReviewModel(&fakeFleetClient{}, brTestEpic, brTestProject)
	m = m.SetSize(120, 40)

	m.review = &domain.BacklogReview{
		CeremonyID: "cer-001",
		Status:     "REVIEWING",
		ReviewResults: []domain.StoryReviewResult{
			{StoryID: "s1", ApprovalStatus: "REJECTED", ReviewedAt: "2026-02-28T10:15:00Z", RejectedAt: "2026-02-28T10:22:00Z"},
		},
	}

	timeline := m.timelineView()
	if !strings.Contains(timeline, "REJECTED") {
		t.Error("timeline should show REJECTED status")
	}
}

func TestBacklogReviewModel_Timeline_ReviewedPending(t *testing.T) {
	t.Parallel()
	m := newTestBacklogReviewModel(&fakeFleetClient{}, brTestEpic, brTestProject)
	m = m.SetSize(120, 40)

	m.review = &domain.BacklogReview{
		CeremonyID: "cer-001",
		Status:     "REVIEWING",
		ReviewResults: []domain.StoryReviewResult{
			{StoryID: "s1", ApprovalStatus: "PENDING", ReviewedAt: "2026-02-28T10:15:00Z"},
		},
	}

	timeline := m.timelineView()
	if !strings.Contains(timeline, "REVIEWED") {
		t.Error("reviewed but pending approval should show REVIEWED")
	}
}

func TestBacklogReviewModel_CreateMode(t *testing.T) {
	t.Parallel()
	client := &fakeFleetClient{
		stories: []domain.StorySummary{
			{ID: "s1", Title: "Story One", State: "DRAFT"},
			{ID: "s2", Title: "Story Two", State: "READY"},
		},
	}
	m := newTestBacklogReviewModel(client, brTestEpic, brTestProject)
	m = m.SetSize(120, 40)
	m, _ = m.Update(backlogReviewStoriesLoadedMsg{stories: client.stories, total: 2})

	// Press 'n' to enter create mode
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("n")})
	if m.mode != brModeCreateSelect {
		t.Errorf("mode should be create select, got %d", m.mode)
	}

	view := m.View()
	if !strings.Contains(view, "Select Stories") {
		t.Error("create view should show story selection heading")
	}

	// Press esc to go back
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyEsc})
	if m.mode != brModeDashboard {
		t.Error("esc should return to dashboard")
	}
}

func TestBacklogReviewModel_Stop(t *testing.T) {
	t.Parallel()
	m := newTestBacklogReviewModel(&fakeFleetClient{}, brTestEpic, brTestProject)

	called := false
	m.cancel = func() { called = true }
	m.eventCh = make(<-chan domain.FleetEvent)

	m.Stop()

	if !called {
		t.Error("Stop should call cancel function")
	}
	if m.cancel != nil {
		t.Error("cancel should be nil after Stop")
	}
}

func TestBrShortTime(t *testing.T) {
	t.Parallel()
	tests := []struct {
		input string
		want  string
	}{
		{"", ""},
		{"2026-02-28T10:05:30Z", "10:05"},
		{"2026-02-28 10:05:30", "10:05"},
		{"short", "short"},
	}
	for _, tt := range tests {
		got := brShortTime(tt.input)
		if got != tt.want {
			t.Errorf("brShortTime(%q) = %q, want %q", tt.input, got, tt.want)
		}
	}
}

func TestBacklogReviewModel_StreamClosedReconnect(t *testing.T) {
	t.Parallel()
	m := newTestBacklogReviewModel(&fakeFleetClient{}, brTestEpic, brTestProject)
	m = m.SetSize(120, 40)

	// Simulate an active event channel
	ch := make(chan domain.FleetEvent)
	close(ch)
	m.eventCh = ch

	// Stream closed → should schedule reconnect with initial backoff
	m, cmd := m.Update(backlogReviewStreamClosedMsg{})
	if m.eventCh != nil {
		t.Error("eventCh should be nil after stream close")
	}
	if m.reconnectBackoff != time.Second {
		t.Errorf("initial backoff should be 1s, got %v", m.reconnectBackoff)
	}
	if cmd == nil {
		t.Error("stream close should return a tick command")
	}

	// Second close → backoff doubles
	m, _ = m.Update(backlogReviewStreamClosedMsg{})
	if m.reconnectBackoff != 2*time.Second {
		t.Errorf("second backoff should be 2s, got %v", m.reconnectBackoff)
	}

	// Third close → backoff doubles again
	m, _ = m.Update(backlogReviewStreamClosedMsg{})
	if m.reconnectBackoff != 4*time.Second {
		t.Errorf("third backoff should be 4s, got %v", m.reconnectBackoff)
	}
}

func TestBacklogReviewModel_ReconnectMsg(t *testing.T) {
	t.Parallel()
	m := newTestBacklogReviewModel(&fakeFleetClient{}, brTestEpic, brTestProject)
	m = m.SetSize(120, 40)
	m.review = &domain.BacklogReview{CeremonyID: "c1", Status: "REVIEWING"}

	// Reconnect message should trigger subscribeEvents
	m, cmd := m.Update(backlogReviewReconnectMsg{})
	if cmd == nil {
		t.Error("reconnect should return a subscribe command")
	}
}

func TestBacklogReviewModel_WatchResetsBackoff(t *testing.T) {
	t.Parallel()
	m := newTestBacklogReviewModel(&fakeFleetClient{}, brTestEpic, brTestProject)
	m = m.SetSize(120, 40)
	m.reconnectBackoff = 8 * time.Second

	ch := make(chan domain.FleetEvent)
	m, _ = m.Update(backlogReviewWatchStartedMsg{
		ch:     ch,
		cancel: func() {},
	})
	if m.reconnectBackoff != 0 {
		t.Errorf("watch started should reset backoff, got %v", m.reconnectBackoff)
	}
	if m.eventCh == nil {
		t.Error("eventCh should be set")
	}
}

func TestBacklogReviewModel_EventResetsBackoff(t *testing.T) {
	t.Parallel()
	client := &fakeFleetClient{}
	m := newTestBacklogReviewModel(client, brTestEpic, brTestProject)
	m = m.SetSize(120, 40)
	m.review = &domain.BacklogReview{CeremonyID: "c1", Status: "REVIEWING"}
	m.reconnectBackoff = 4 * time.Second

	ch := make(chan domain.FleetEvent, 1)
	m.eventCh = ch

	m, _ = m.Update(backlogReviewEventMsg{event: domain.FleetEvent{Type: "test"}})
	if m.reconnectBackoff != 0 {
		t.Errorf("event should reset backoff, got %v", m.reconnectBackoff)
	}
}

func TestBacklogReviewModel_DashboardHints(t *testing.T) {
	t.Parallel()
	tests := []struct {
		status string
		want   string
	}{
		{"DRAFT", "s: start"},
		{"REVIEWING", "v: view results"},
		{"COMPLETED", "v: view results"},
	}
	for _, tt := range tests {
		m := newTestBacklogReviewModel(&fakeFleetClient{}, brTestEpic, brTestProject)
		m = m.SetSize(120, 40)
		m, _ = m.Update(backlogReviewStoriesLoadedMsg{stories: nil, total: 0})
		m.review = &domain.BacklogReview{CeremonyID: "c1", Status: tt.status}
		view := m.dashboardView()
		if !strings.Contains(view, tt.want) {
			t.Errorf("status %s: view should contain %q", tt.status, tt.want)
		}
	}
}
