package views

import (
	"context"
	"fmt"
	"strings"
	"testing"
	"time"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
)

func testBacklogReviews() []domain.BacklogReview {
	return []domain.BacklogReview{
		{CeremonyID: "cer-001", Status: "REVIEWING", StoryIDs: []string{"s1", "s2"}, CreatedBy: "alice", CreatedAt: "2026-02-28"},
		{CeremonyID: "cer-002", Status: "COMPLETED", StoryIDs: []string{"s3"}, CreatedBy: "bob", CreatedAt: "2026-02-27"},
	}
}

func TestAgentConversationsModel_ReviewsLoaded(t *testing.T) {
	t.Parallel()
	client := &fakeFleetClient{backlogReviews: testBacklogReviews()}
	m := NewAgentConversationsModel(client)
	m = m.SetSize(120, 40)

	m, _ = m.Update(acReviewsLoadedMsg{reviews: client.backlogReviews, total: 2})

	if m.loading {
		t.Error("loading should be false after data load")
	}
	if len(m.reviews) != 2 {
		t.Errorf("reviews count = %d, want 2", len(m.reviews))
	}
	view := m.View()
	if !strings.Contains(view, "Backlog Review Ceremonies") {
		t.Error("view should show heading")
	}
}

func TestAgentConversationsModel_ErrMsg(t *testing.T) {
	t.Parallel()
	m := NewAgentConversationsModel(&fakeFleetClient{})
	m = m.SetSize(120, 40)

	m, _ = m.Update(acErrMsg{err: fmt.Errorf("network failure")})

	if m.err == nil {
		t.Fatal("err should be set")
	}
	if m.loading {
		t.Error("loading should be false after error")
	}
	view := m.View()
	if !strings.Contains(view, "network failure") {
		t.Error("view should show error message")
	}
}

func TestAgentConversationsModel_EmptyList(t *testing.T) {
	t.Parallel()
	m := NewAgentConversationsModel(&fakeFleetClient{})
	m = m.SetSize(120, 40)

	m, _ = m.Update(acReviewsLoadedMsg{reviews: nil, total: 0})

	view := m.View()
	if !strings.Contains(view, "No backlog reviews found") {
		t.Error("empty list should show no-reviews message")
	}
}

func TestAgentConversationsModel_ReviewDetailMsg(t *testing.T) {
	t.Parallel()
	m := NewAgentConversationsModel(&fakeFleetClient{})
	m = m.SetSize(120, 40)

	review := domain.BacklogReview{
		CeremonyID: "cer-001",
		Status:     "REVIEWING",
		StoryIDs:   []string{"s1"},
		ReviewResults: []domain.StoryReviewResult{
			{StoryID: "s1", ApprovalStatus: "PENDING", ArchitectFeedback: "looks good"},
		},
	}
	m, _ = m.Update(acReviewDetailMsg{review: review})

	if m.mode != acModeCeremonyDetail {
		t.Errorf("mode = %d, want acModeCeremonyDetail", m.mode)
	}
	if m.selectedReview == nil {
		t.Fatal("selectedReview should be set")
	}
	if m.loading {
		t.Error("loading should be false after detail load")
	}
	view := m.View()
	if !strings.Contains(view, "Ceremony") {
		t.Error("view should show ceremony detail heading")
	}
}

func TestAgentConversationsModel_WatchStartedMsg(t *testing.T) {
	t.Parallel()
	m := NewAgentConversationsModel(&fakeFleetClient{})
	m = m.SetSize(120, 40)

	ch := make(chan domain.FleetEvent, 1)
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	_ = ctx

	m, cmd := m.Update(acWatchStartedMsg{ch: ch, cancel: cancel})

	if m.eventCh == nil {
		t.Error("eventCh should be set")
	}
	if m.cancel == nil {
		t.Error("cancel should be set")
	}
	if cmd == nil {
		t.Error("should return waitForACEvent command")
	}
}

func TestAgentConversationsModel_EventMsg_WithSelectedReview(t *testing.T) {
	t.Parallel()
	client := &fakeFleetClient{
		backlogReview: &domain.BacklogReview{CeremonyID: "cer-001", Status: "REVIEWING"},
	}
	m := NewAgentConversationsModel(client)
	m = m.SetSize(120, 40)

	ch := make(chan domain.FleetEvent, 1)
	m.eventCh = ch
	m.selectedReview = &domain.BacklogReview{CeremonyID: "cer-001", Status: "REVIEWING"}

	m, cmd := m.Update(acEventMsg{event: domain.FleetEvent{Type: "deliberation.received"}})

	if cmd == nil {
		t.Error("event msg with selected review should return batch command (refresh + waitForEvent)")
	}
}

func TestAgentConversationsModel_EventMsg_NoSelectedReview(t *testing.T) {
	t.Parallel()
	m := NewAgentConversationsModel(&fakeFleetClient{})
	m = m.SetSize(120, 40)

	ch := make(chan domain.FleetEvent, 1)
	m.eventCh = ch

	m, cmd := m.Update(acEventMsg{event: domain.FleetEvent{Type: "deliberation.received"}})

	if cmd == nil {
		t.Error("event msg without selected review should still return waitForEvent command")
	}
}

func TestAgentConversationsModel_CeremonyList_Esc(t *testing.T) {
	t.Parallel()
	m := NewAgentConversationsModel(&fakeFleetClient{})
	m = m.SetSize(120, 40)
	m, _ = m.Update(acReviewsLoadedMsg{reviews: nil, total: 0})

	_, cmd := m.Update(tea.KeyMsg{Type: tea.KeyEsc})

	if cmd == nil {
		t.Error("esc should return BackFromAgentConversationsMsg command")
	}
}

func TestAgentConversationsModel_CeremonyList_Refresh(t *testing.T) {
	t.Parallel()
	m := NewAgentConversationsModel(&fakeFleetClient{})
	m = m.SetSize(120, 40)
	m, _ = m.Update(acReviewsLoadedMsg{reviews: nil, total: 0})

	m, cmd := m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("r")})

	if !m.loading {
		t.Error("refresh should set loading")
	}
	if cmd == nil {
		t.Error("refresh should return command")
	}
}

func TestAgentConversationsModel_CeremonyList_Pagination(t *testing.T) {
	t.Parallel()
	m := NewAgentConversationsModel(&fakeFleetClient{backlogReviews: testBacklogReviews()})
	m = m.SetSize(120, 40)
	m, _ = m.Update(acReviewsLoadedMsg{reviews: testBacklogReviews(), total: 50})

	// Right arrow → next page
	m, cmd := m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{rune(tea.KeyRight)}})
	// Use the string key instead
	m, cmd = m.Update(tea.KeyMsg{Type: tea.KeyRight})

	if !m.loading {
		t.Error("pagination should set loading")
	}
	if cmd == nil {
		t.Error("page change should return load command")
	}

	// Left arrow → prev page
	m, cmd = m.Update(tea.KeyMsg{Type: tea.KeyLeft})
	if cmd == nil {
		t.Error("prev page should return load command")
	}
}

func TestAgentConversationsModel_CeremonyDetail_Esc(t *testing.T) {
	t.Parallel()
	m := NewAgentConversationsModel(&fakeFleetClient{})
	m = m.SetSize(120, 40)
	m.mode = acModeCeremonyDetail
	m.selectedReview = &domain.BacklogReview{CeremonyID: "cer-001", Status: "REVIEWING"}

	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyEsc})

	if m.mode != acModeCeremonyList {
		t.Errorf("mode = %d, want acModeCeremonyList", m.mode)
	}
	if m.selectedReview != nil {
		t.Error("selectedReview should be nil after esc")
	}
}

func TestAgentConversationsModel_CeremonyDetail_Watch(t *testing.T) {
	t.Parallel()
	m := NewAgentConversationsModel(&fakeFleetClient{})
	m = m.SetSize(120, 40)
	m.mode = acModeCeremonyDetail
	m.selectedReview = &domain.BacklogReview{CeremonyID: "cer-001"}

	_, cmd := m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("w")})

	if cmd == nil {
		t.Error("w should return startWatchingDeliberations command")
	}
}

func TestAgentConversationsModel_CeremonyDetail_RefreshDetail(t *testing.T) {
	t.Parallel()
	client := &fakeFleetClient{
		backlogReview: &domain.BacklogReview{CeremonyID: "cer-001", Status: "REVIEWING"},
	}
	m := NewAgentConversationsModel(client)
	m = m.SetSize(120, 40)
	m.mode = acModeCeremonyDetail
	m.selectedReview = &domain.BacklogReview{CeremonyID: "cer-001"}

	m, cmd := m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("r")})

	if !m.loading {
		t.Error("refresh should set loading")
	}
	if cmd == nil {
		t.Error("refresh should return command")
	}
}

func TestAgentConversationsModel_CeremonyDetail_EnterStoryReview(t *testing.T) {
	t.Parallel()
	m := NewAgentConversationsModel(&fakeFleetClient{})
	m = m.SetSize(120, 40)

	review := domain.BacklogReview{
		CeremonyID: "cer-001",
		Status:     "REVIEWING",
		ReviewResults: []domain.StoryReviewResult{
			{StoryID: "s1", ApprovalStatus: "PENDING", ArchitectFeedback: "looks good"},
		},
	}
	m, _ = m.Update(acReviewDetailMsg{review: review})

	// Press enter to select the story
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})

	if m.mode != acModeStoryReview {
		t.Errorf("mode = %d, want acModeStoryReview", m.mode)
	}
	if m.selectedResult == nil {
		t.Error("selectedResult should be set")
	}
	if m.agentFocus != 0 {
		t.Error("agentFocus should start at 0")
	}
}

func TestAgentConversationsModel_StoryReview_AgentFocus(t *testing.T) {
	t.Parallel()
	m := NewAgentConversationsModel(&fakeFleetClient{})
	m = m.SetSize(120, 40)
	m.mode = acModeStoryReview
	m.selectedResult = &domain.StoryReviewResult{
		StoryID:           "s1",
		ArchitectFeedback: "arch feedback",
		QAFeedback:        "qa feedback",
		DevopsFeedback:    "devops feedback",
	}

	// Press 2 to focus QA
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("2")})
	if m.agentFocus != 1 {
		t.Errorf("agentFocus = %d, want 1 (QA)", m.agentFocus)
	}

	// Press 3 to focus DevOps
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("3")})
	if m.agentFocus != 2 {
		t.Errorf("agentFocus = %d, want 2 (DevOps)", m.agentFocus)
	}

	// Press 1 to focus Architect
	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune("1")})
	if m.agentFocus != 0 {
		t.Errorf("agentFocus = %d, want 0 (Architect)", m.agentFocus)
	}
}

func TestAgentConversationsModel_StoryReview_Esc(t *testing.T) {
	t.Parallel()
	m := NewAgentConversationsModel(&fakeFleetClient{})
	m = m.SetSize(120, 40)
	m.mode = acModeStoryReview
	m.selectedResult = &domain.StoryReviewResult{StoryID: "s1"}

	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyEsc})

	if m.mode != acModeCeremonyDetail {
		t.Errorf("mode = %d, want acModeCeremonyDetail", m.mode)
	}
	if m.selectedResult != nil {
		t.Error("selectedResult should be nil after esc")
	}
}

func TestAgentConversationsModel_StoryReview_EnterAgentDetail(t *testing.T) {
	t.Parallel()
	m := NewAgentConversationsModel(&fakeFleetClient{})
	m = m.SetSize(120, 40)
	m.mode = acModeStoryReview
	m.selectedResult = &domain.StoryReviewResult{
		StoryID:           "s1",
		ArchitectFeedback: "detailed arch feedback",
	}

	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyEnter})

	if m.mode != acModeAgentDetail {
		t.Errorf("mode = %d, want acModeAgentDetail", m.mode)
	}
}

func TestAgentConversationsModel_AgentDetail_Esc(t *testing.T) {
	t.Parallel()
	m := NewAgentConversationsModel(&fakeFleetClient{})
	m = m.SetSize(120, 40)
	m.mode = acModeAgentDetail

	m, _ = m.Update(tea.KeyMsg{Type: tea.KeyEsc})

	if m.mode != acModeStoryReview {
		t.Errorf("mode = %d, want acModeStoryReview", m.mode)
	}
}

func TestAgentConversationsModel_StoryReviewView(t *testing.T) {
	t.Parallel()
	m := NewAgentConversationsModel(&fakeFleetClient{})
	m = m.SetSize(120, 40)
	m.mode = acModeStoryReview
	m.selectedResult = &domain.StoryReviewResult{
		StoryID:           "s1",
		ApprovalStatus:    "PENDING",
		ArchitectFeedback: "Good architecture",
		QAFeedback:        "",
		DevopsFeedback:    "Needs CI pipeline",
		PlanPreliminary: domain.PlanPreliminary{
			Title:              "Auth Feature",
			EstimatedComplexity: "MEDIUM",
			Description:        "Implement authentication",
			AcceptanceCriteria: []string{"Login works", "Logout works"},
			TasksOutline:       []string{"Create login form", "Add auth middleware"},
		},
		Recommendations: []string{"Use JWT tokens", "Add rate limiting"},
	}

	view := m.View()

	if !strings.Contains(view, "Story Review") {
		t.Error("view should show breadcrumb")
	}
	if !strings.Contains(view, "ARCHITECT") {
		t.Error("view should show architect tab")
	}
	if !strings.Contains(view, "QA") {
		t.Error("view should show QA tab")
	}
	if !strings.Contains(view, "DEVOPS") {
		t.Error("view should show DevOps tab")
	}
	if !strings.Contains(view, "Auth Feature") {
		t.Error("view should show plan title")
	}
	if !strings.Contains(view, "MEDIUM") {
		t.Error("view should show complexity")
	}
	if !strings.Contains(view, "Recommendations") {
		t.Error("view should show recommendations heading")
	}
	if !strings.Contains(view, "No feedback yet") {
		t.Error("QA with empty feedback should show 'No feedback yet'")
	}
}

func TestAgentConversationsModel_CeremonyDetailView_NoResults(t *testing.T) {
	t.Parallel()
	m := NewAgentConversationsModel(&fakeFleetClient{})
	m = m.SetSize(120, 40)
	m.mode = acModeCeremonyDetail
	m.selectedReview = &domain.BacklogReview{
		CeremonyID:    "cer-001",
		Status:        "DRAFT",
		StoryIDs:      []string{"s1"},
		ReviewResults: nil,
		CreatedAt:     "2026-02-28",
	}

	view := m.View()
	if !strings.Contains(view, "No review results yet") {
		t.Error("ceremony detail with no results should show placeholder")
	}
	if !strings.Contains(view, "Press w to watch") {
		t.Error("should show watch hint when not watching")
	}
}

func TestAgentConversationsModel_CeremonyDetailView_Watching(t *testing.T) {
	t.Parallel()
	m := NewAgentConversationsModel(&fakeFleetClient{})
	m = m.SetSize(120, 40)
	m.mode = acModeCeremonyDetail
	m.selectedReview = &domain.BacklogReview{
		CeremonyID: "cer-001",
		Status:     "REVIEWING",
	}
	m.eventCh = make(<-chan domain.FleetEvent)

	view := m.View()
	if !strings.Contains(view, "Watching for live updates") {
		t.Error("should show watching indicator when eventCh is set")
	}
}

func TestAgentConversationsModel_CeremonyDetailView_NilReview(t *testing.T) {
	t.Parallel()
	m := NewAgentConversationsModel(&fakeFleetClient{})
	m = m.SetSize(120, 40)
	m.mode = acModeCeremonyDetail
	m.selectedReview = nil

	view := m.View()
	if !strings.Contains(view, "No ceremony selected") {
		t.Error("nil selectedReview should show placeholder")
	}
}

func TestAgentConversationsModel_StoryReviewView_NilResult(t *testing.T) {
	t.Parallel()
	m := NewAgentConversationsModel(&fakeFleetClient{})
	m = m.SetSize(120, 40)
	m.mode = acModeStoryReview
	m.selectedResult = nil

	view := m.View()
	if !strings.Contains(view, "No story selected") {
		t.Error("nil selectedResult should show placeholder")
	}
}

func TestAgentConversationsModel_Stop(t *testing.T) {
	t.Parallel()
	m := NewAgentConversationsModel(&fakeFleetClient{})

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
	if m.eventCh != nil {
		t.Error("eventCh should be nil after Stop")
	}
}

func TestAgentConversationsModel_Stop_NilCancel(t *testing.T) {
	t.Parallel()
	m := NewAgentConversationsModel(&fakeFleetClient{})
	m.cancel = nil
	m.eventCh = nil

	// Should not panic
	m.Stop()
}

func TestTruncate(t *testing.T) {
	t.Parallel()
	tests := []struct {
		input  string
		maxLen int
		want   string
	}{
		{"short", 10, "short"},
		{"exactly-ten", 11, "exactly-ten"},
		{"this is a long string", 10, "this is..."},
		{"abc", 3, "abc"},
		{"abcd", 3, "abc"},
		{"ab", 1, "a"},
	}
	for _, tt := range tests {
		got := truncate(tt.input, tt.maxLen)
		if got != tt.want {
			t.Errorf("truncate(%q, %d) = %q, want %q", tt.input, tt.maxLen, got, tt.want)
		}
	}
}

func TestStatusStyle(t *testing.T) {
	t.Parallel()
	// Verify that each known status returns a non-empty string
	statuses := []string{"APPROVED", "completed", "PENDING", "in_progress", "deliberating", "REJECTED", "cancelled", "UNKNOWN"}
	for _, s := range statuses {
		got := statusStyle(s)
		if got == "" {
			t.Errorf("statusStyle(%q) should not be empty", s)
		}
		if !strings.Contains(got, s) {
			t.Errorf("statusStyle(%q) = %q, should contain the status text", s, got)
		}
	}
}

func TestAgentConversationsModel_AgentDetailView(t *testing.T) {
	t.Parallel()
	m := NewAgentConversationsModel(&fakeFleetClient{})
	m = m.SetSize(120, 40)
	m.mode = acModeAgentDetail
	m.selectedResult = &domain.StoryReviewResult{
		StoryID:           "s1",
		ArchitectFeedback: "detailed architect notes",
		PlanPreliminary: domain.PlanPreliminary{
			Title:          "Auth Feature",
			TechnicalNotes: "Use JWT with short-lived tokens",
			Dependencies:   []string{"user-service", "token-service"},
			Roles:          []string{"backend", "frontend"},
		},
	}
	m.agentFocus = 0
	m.detailViewport.SetContent(m.renderAgentDetail())

	view := m.View()
	if !strings.Contains(view, "Agent") {
		t.Error("agent detail view should show breadcrumb with Agent")
	}
}

func TestRenderAgentDetail_NilResult(t *testing.T) {
	t.Parallel()
	m := NewAgentConversationsModel(&fakeFleetClient{})
	m.selectedResult = nil

	got := m.renderAgentDetail()
	if got != "No data." {
		t.Errorf("renderAgentDetail with nil result = %q, want 'No data.'", got)
	}
}

func TestRenderAgentDetail_WithFeedback(t *testing.T) {
	t.Parallel()
	m := NewAgentConversationsModel(&fakeFleetClient{})
	m.selectedResult = &domain.StoryReviewResult{
		StoryID:           "s1",
		ArchitectFeedback: "arch notes",
		QAFeedback:        "qa notes",
		DevopsFeedback:    "devops notes",
		PlanPreliminary: domain.PlanPreliminary{
			Title:          "Feature X",
			TechnicalNotes: "Use gRPC streaming",
			Dependencies:   []string{"dep-a"},
			Roles:          []string{"sre"},
		},
	}

	// Test architect focus
	m.agentFocus = 0
	got := m.renderAgentDetail()
	if !strings.Contains(got, "ARCHITECT") {
		t.Error("should show ARCHITECT heading")
	}
	if !strings.Contains(got, "arch notes") {
		t.Error("should show architect feedback")
	}

	// Test QA focus
	m.agentFocus = 1
	got = m.renderAgentDetail()
	if !strings.Contains(got, "QA") {
		t.Error("should show QA heading")
	}

	// Test DevOps focus
	m.agentFocus = 2
	got = m.renderAgentDetail()
	if !strings.Contains(got, "DEVOPS") {
		t.Error("should show DEVOPS heading")
	}
	if !strings.Contains(got, "Feature X") {
		t.Error("should show plan title")
	}
}

func TestRenderAgentDetail_NoFeedback(t *testing.T) {
	t.Parallel()
	m := NewAgentConversationsModel(&fakeFleetClient{})
	m.selectedResult = &domain.StoryReviewResult{
		StoryID: "s1",
	}
	m.agentFocus = 0

	got := m.renderAgentDetail()
	if !strings.Contains(got, "No feedback from this agent") {
		t.Error("empty feedback should show placeholder")
	}
}

func TestAgentConversationsModel_StreamClosedReconnect(t *testing.T) {
	t.Parallel()
	m := NewAgentConversationsModel(&fakeFleetClient{})
	m = m.SetSize(120, 40)

	// Simulate active event channel that gets closed
	ch := make(chan domain.FleetEvent)
	close(ch)
	m.eventCh = ch

	// Stream closed → should schedule reconnect with initial backoff
	m, cmd := m.Update(acStreamClosedMsg{})
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
	m, _ = m.Update(acStreamClosedMsg{})
	if m.reconnectBackoff != 2*time.Second {
		t.Errorf("second backoff should be 2s, got %v", m.reconnectBackoff)
	}

	// Third close → backoff doubles again
	m, _ = m.Update(acStreamClosedMsg{})
	if m.reconnectBackoff != 4*time.Second {
		t.Errorf("third backoff should be 4s, got %v", m.reconnectBackoff)
	}
}

func TestAgentConversationsModel_ReconnectMsg(t *testing.T) {
	t.Parallel()
	m := NewAgentConversationsModel(&fakeFleetClient{})
	m = m.SetSize(120, 40)

	// Reconnect message should trigger startWatchingDeliberations
	m, cmd := m.Update(acReconnectMsg{})
	if cmd == nil {
		t.Error("reconnect should return a subscribe command")
	}
}

func TestAgentConversationsModel_WatchResetsBackoff(t *testing.T) {
	t.Parallel()
	m := NewAgentConversationsModel(&fakeFleetClient{})
	m = m.SetSize(120, 40)
	m.reconnectBackoff = 8 * time.Second

	ch := make(chan domain.FleetEvent)
	m, _ = m.Update(acWatchStartedMsg{
		ch:     ch,
		cancel: func() {},
	})
	if m.reconnectBackoff != 0 {
		t.Errorf("watch started should reset backoff, got %v", m.reconnectBackoff)
	}
	if m.eventCh == nil {
		t.Error("eventCh should be set after watch started")
	}
}

func TestAgentConversationsModel_EventResetsBackoff(t *testing.T) {
	t.Parallel()
	m := NewAgentConversationsModel(&fakeFleetClient{})
	m = m.SetSize(120, 40)
	m.reconnectBackoff = 4 * time.Second

	ch := make(chan domain.FleetEvent, 1)
	m.eventCh = ch

	m, _ = m.Update(acEventMsg{event: domain.FleetEvent{Type: "test"}})
	if m.reconnectBackoff != 0 {
		t.Errorf("event should reset backoff, got %v", m.reconnectBackoff)
	}
}

func TestAgentConversationsModel_BackoffCapsAt30s(t *testing.T) {
	t.Parallel()
	m := NewAgentConversationsModel(&fakeFleetClient{})
	m = m.SetSize(120, 40)
	m.reconnectBackoff = 16 * time.Second

	// Close triggers doubling but should cap at 30s
	m, _ = m.Update(acStreamClosedMsg{})
	if m.reconnectBackoff != 30*time.Second {
		t.Errorf("backoff should cap at 30s, got %v", m.reconnectBackoff)
	}

	// Already at cap, should stay at 30s
	m, _ = m.Update(acStreamClosedMsg{})
	if m.reconnectBackoff != 30*time.Second {
		t.Errorf("backoff should stay at 30s cap, got %v", m.reconnectBackoff)
	}
}
