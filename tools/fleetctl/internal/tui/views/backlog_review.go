package views

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/spinner"
	"github.com/charmbracelet/bubbles/table"
	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/command"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/query"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/tui/components"
)

// ---------------------------------------------------------------------------
// Internal messages
// ---------------------------------------------------------------------------

type backlogReviewLoadedMsg struct{ review domain.BacklogReview }
type backlogReviewCreatedMsg struct{ review domain.BacklogReview }
type backlogReviewStartedMsg struct {
	review domain.BacklogReview
	total  int32
}
type backlogReviewApprovedMsg struct {
	review domain.BacklogReview
	planID string
}
type backlogReviewRejectedMsg struct{ review domain.BacklogReview }
type backlogReviewCompletedMsg struct{ review domain.BacklogReview }
type backlogReviewCancelledMsg struct{ review domain.BacklogReview }
type backlogReviewErrMsg struct{ err error }
type backlogReviewStoriesLoadedMsg struct {
	stories []domain.StorySummary
	total   int32
}
type backlogReviewEventMsg struct{ event domain.FleetEvent }
type backlogReviewWatchStartedMsg struct {
	ch     <-chan domain.FleetEvent
	cancel context.CancelFunc
}
type backlogReviewStreamClosedMsg struct{}
type backlogReviewReconnectMsg struct{}

// ---------------------------------------------------------------------------
// Modes
// ---------------------------------------------------------------------------

// BacklogReviewMode controls which sub-screen the view renders.
type BacklogReviewMode int

const (
	brModeDashboard BacklogReviewMode = iota
	brModeCreateSelect
	brModeReview
	brModeApproveForm
	brModeRejectForm
)

// ---------------------------------------------------------------------------
// Model
// ---------------------------------------------------------------------------

// BacklogReviewHandlers groups the handler dependencies for BacklogReviewModel.
type BacklogReviewHandlers struct {
	ListStories           *query.ListStoriesHandler
	CreateBacklogReview   *command.CreateBacklogReviewHandler
	StartBacklogReview    *command.StartBacklogReviewHandler
	GetBacklogReview      *query.GetBacklogReviewHandler
	ApproveReviewPlan     *command.ApproveReviewPlanHandler
	RejectReviewPlan      *command.RejectReviewPlanHandler
	CompleteBacklogReview *command.CompleteBacklogReviewHandler
	CancelBacklogReview   *command.CancelBacklogReviewHandler
	WatchEvents           *query.WatchEventsHandler
}

// BacklogReviewModel is the sub-model for the backlog review ceremony view.
type BacklogReviewModel struct {
	handlers BacklogReviewHandlers

	epic    domain.EpicSummary
	project domain.ProjectSummary
	review  *domain.BacklogReview
	stories []domain.StorySummary
	mode    BacklogReviewMode

	// Story multi-select (create mode)
	selected   map[int]bool // index → selected
	selectIdx  int          // cursor in story list
	storyTable table.Model

	// Review mode table
	reviewTable table.Model

	// Approve form (4 fields)
	approveStoryID    string
	poNotesInput      textinput.Model
	poConcernsInput   textinput.Model
	prioAdjInput      textinput.Model
	prioReasonInput   textinput.Model
	approveFocusIdx   int // 0..3

	// Reject form (1 field)
	rejectStoryID  string
	rejectInput    textinput.Model

	// Event subscription
	eventCh          <-chan domain.FleetEvent
	cancel           context.CancelFunc
	reconnectBackoff time.Duration

	spinner spinner.Model
	loading bool
	err     error
	width   int
	height  int
}

// NewBacklogReviewModel creates a BacklogReviewModel for the given epic.
func NewBacklogReviewModel(
	h BacklogReviewHandlers,
	epic domain.EpicSummary,
	project domain.ProjectSummary,
) BacklogReviewModel {
	storyTbl := components.NewTable(brStorySelectColumns(), nil, 10)
	reviewTbl := components.NewTable(brReviewColumns(), nil, 10)

	poNotes := textinput.New()
	poNotes.Placeholder = "PO notes (required)"
	poNotes.CharLimit = 512
	poNotes.Width = 60

	poConcerns := textinput.New()
	poConcerns.Placeholder = "PO concerns"
	poConcerns.CharLimit = 512
	poConcerns.Width = 60

	prioAdj := textinput.New()
	prioAdj.Placeholder = "Priority adjustment (e.g. +1, -1, same)"
	prioAdj.CharLimit = 20
	prioAdj.Width = 30

	prioReason := textinput.New()
	prioReason.Placeholder = "Priority reason"
	prioReason.CharLimit = 256
	prioReason.Width = 60

	rejectIn := textinput.New()
	rejectIn.Placeholder = "Rejection reason (required)"
	rejectIn.CharLimit = 512
	rejectIn.Width = 60

	return BacklogReviewModel{
		handlers:        h,
		epic:            epic,
		project:               project,
		mode:                  brModeDashboard,
		selected:              make(map[int]bool),
		storyTable:            storyTbl,
		reviewTable:           reviewTbl,
		poNotesInput:          poNotes,
		poConcernsInput:       poConcerns,
		prioAdjInput:          prioAdj,
		prioReasonInput:       prioReason,
		rejectInput:           rejectIn,
		spinner:               components.NewSpinner(),
		loading:               true,
	}
}

func brStorySelectColumns() []table.Column {
	return []table.Column{
		{Title: "Sel", Width: 4},
		{Title: "ID", Width: 12},
		{Title: "Title", Width: 28},
		{Title: "State", Width: 12},
	}
}

func brReviewColumns() []table.Column {
	return []table.Column{
		{Title: "ID", Width: 12},
		{Title: "Title", Width: 22},
		{Title: "Status", Width: 12},
		{Title: "Complexity", Width: 10},
		{Title: "Reviewed", Width: 18},
	}
}

// SetSize updates the available layout dimensions.
func (m BacklogReviewModel) SetSize(w, h int) BacklogReviewModel {
	m.width = w
	m.height = h
	tblH := max(h-16, 4)
	m.storyTable.SetHeight(tblH)
	m.reviewTable.SetHeight(tblH)
	return m
}

// ---------------------------------------------------------------------------
// tea.Model interface
// ---------------------------------------------------------------------------

// Init fires the initial data load.
func (m BacklogReviewModel) Init() tea.Cmd {
	return tea.Batch(m.spinner.Tick, m.loadStories())
}

// Update handles messages for the backlog review view.
func (m BacklogReviewModel) Update(msg tea.Msg) (BacklogReviewModel, tea.Cmd) {
	switch msg := msg.(type) {
	case backlogReviewStoriesLoadedMsg, backlogReviewLoadedMsg,
		backlogReviewCreatedMsg, backlogReviewStartedMsg,
		backlogReviewApprovedMsg, backlogReviewRejectedMsg,
		backlogReviewCompletedMsg, backlogReviewCancelledMsg,
		backlogReviewErrMsg:
		return m.handleDataMsg(msg)

	case backlogReviewWatchStartedMsg, backlogReviewEventMsg,
		backlogReviewStreamClosedMsg, backlogReviewReconnectMsg:
		return m.handleStreamMsg(msg)

	case spinner.TickMsg:
		var cmd tea.Cmd
		m.spinner, cmd = m.spinner.Update(msg)
		return m, cmd

	case tea.KeyMsg:
		return m.handleKeyMsg(msg)
	}

	return m, nil
}

// handleDataMsg processes data load and mutation response messages.
func (m BacklogReviewModel) handleDataMsg(msg tea.Msg) (BacklogReviewModel, tea.Cmd) {
	switch msg := msg.(type) {
	case backlogReviewStoriesLoadedMsg:
		m.stories = msg.stories
		m.loading = false
		m.err = nil
		m.storyTable.SetRows(brStorySelectRows(m.stories, m.selected))
		return m, nil

	case backlogReviewLoadedMsg:
		m.loading = false
		m.err = nil
		m.review = &msg.review
		if m.review.Status == "REVIEWING" || m.review.Status == "COMPLETED" {
			m.mode = brModeReview
			m.reviewTable.SetRows(brReviewRows(m.review, m.stories))
		}
		return m, nil

	case backlogReviewCreatedMsg:
		m.loading = false
		m.err = nil
		m.review = &msg.review
		m.mode = brModeDashboard
		return m, nil

	case backlogReviewStartedMsg:
		m.loading = false
		m.err = nil
		m.review = &msg.review
		return m, m.subscribeEvents()

	case backlogReviewApprovedMsg:
		m.loading = false
		m.err = nil
		m.review = &msg.review
		m.mode = brModeReview
		m.reviewTable.SetRows(brReviewRows(m.review, m.stories))
		return m, nil

	case backlogReviewRejectedMsg:
		m.loading = false
		m.err = nil
		m.review = &msg.review
		m.mode = brModeReview
		m.reviewTable.SetRows(brReviewRows(m.review, m.stories))
		return m, nil

	case backlogReviewCompletedMsg:
		m.loading = false
		m.err = nil
		m.review = &msg.review
		return m, nil

	case backlogReviewCancelledMsg:
		m.Stop()
		m.loading = false
		m.err = nil
		m.review = nil
		m.mode = brModeDashboard
		return m, nil

	case backlogReviewErrMsg:
		m.loading = false
		m.err = msg.err
		return m, nil
	}

	return m, nil
}

// handleStreamMsg processes event stream lifecycle messages.
func (m BacklogReviewModel) handleStreamMsg(msg tea.Msg) (BacklogReviewModel, tea.Cmd) {
	switch msg := msg.(type) {
	case backlogReviewWatchStartedMsg:
		m.eventCh = msg.ch
		m.cancel = msg.cancel
		m.reconnectBackoff = 0
		return m, m.waitForEvent()

	case backlogReviewEventMsg:
		m.reconnectBackoff = 0
		return m, tea.Batch(m.refreshReview(), m.waitForEvent())

	case backlogReviewStreamClosedMsg:
		m.eventCh = nil
		if m.reconnectBackoff == 0 {
			m.reconnectBackoff = time.Second
		} else {
			m.reconnectBackoff = min(m.reconnectBackoff*2, 30*time.Second)
		}
		return m, tea.Tick(m.reconnectBackoff, func(time.Time) tea.Msg {
			return backlogReviewReconnectMsg{}
		})

	case backlogReviewReconnectMsg:
		return m, m.subscribeEvents()
	}

	return m, nil
}

// handleKeyMsg dispatches key events to the active mode's handler.
func (m BacklogReviewModel) handleKeyMsg(msg tea.KeyMsg) (BacklogReviewModel, tea.Cmd) {
	switch m.mode {
	case brModeDashboard:
		return m.updateDashboard(msg)
	case brModeCreateSelect:
		return m.updateCreateSelect(msg)
	case brModeReview:
		return m.updateReview(msg)
	case brModeApproveForm:
		return m.updateApproveForm(msg)
	case brModeRejectForm:
		return m.updateRejectForm(msg)
	}
	return m, nil
}

// Stop cancels the event subscription if active.
func (m *BacklogReviewModel) Stop() {
	if m.cancel != nil {
		m.cancel()
		m.cancel = nil
	}
}

// ---------------------------------------------------------------------------
// Dashboard mode
// ---------------------------------------------------------------------------

func (m BacklogReviewModel) updateDashboard(msg tea.KeyMsg) (BacklogReviewModel, tea.Cmd) {
	switch msg.String() {
	case "n":
		// Switch to create/select mode.
		m.mode = brModeCreateSelect
		m.selected = make(map[int]bool)
		m.selectIdx = 0
		m.storyTable.SetRows(brStorySelectRows(m.stories, m.selected))
		return m, nil
	case "s":
		// Start the ceremony.
		if m.review == nil || m.review.Status != "DRAFT" {
			m.err = fmt.Errorf("no DRAFT ceremony to start")
			return m, nil
		}
		m.loading = true
		m.err = nil
		return m, tea.Batch(m.spinner.Tick, m.startReview())
	case "v":
		// View review results.
		if m.review != nil && (m.review.Status == "REVIEWING" || m.review.Status == "COMPLETED") {
			m.mode = brModeReview
			m.reviewTable.SetRows(brReviewRows(m.review, m.stories))
		}
		return m, nil
	case "f":
		// Finish/complete the ceremony.
		if m.review == nil {
			m.err = fmt.Errorf("no ceremony to complete")
			return m, nil
		}
		m.loading = true
		m.err = nil
		return m, tea.Batch(m.spinner.Tick, m.completeReview())
	case "x":
		// Cancel the ceremony.
		if m.review == nil {
			m.err = fmt.Errorf("no ceremony to cancel")
			return m, nil
		}
		m.loading = true
		m.err = nil
		return m, tea.Batch(m.spinner.Tick, m.cancelReview())
	case "r":
		// Refresh.
		if m.review != nil {
			m.loading = true
			return m, tea.Batch(m.spinner.Tick, m.refreshReview())
		}
		m.loading = true
		return m, tea.Batch(m.spinner.Tick, m.loadStories())
	case "esc":
		m.Stop()
		return m, func() tea.Msg { return BackToEpicDetailFromReviewMsg{} }
	}
	return m, nil
}

// ---------------------------------------------------------------------------
// Create/Select mode — multi-select stories
// ---------------------------------------------------------------------------

func (m BacklogReviewModel) updateCreateSelect(msg tea.KeyMsg) (BacklogReviewModel, tea.Cmd) {
	switch msg.String() {
	case "esc":
		m.mode = brModeDashboard
		return m, nil
	case " ":
		// Toggle selection.
		row := m.storyTable.SelectedRow()
		if row != nil {
			idx := m.storyIndexByPrefix(row[1])
			if idx >= 0 {
				m.selected[idx] = !m.selected[idx]
				if !m.selected[idx] {
					delete(m.selected, idx)
				}
				m.storyTable.SetRows(brStorySelectRows(m.stories, m.selected))
			}
		}
		return m, nil
	case "enter":
		// Create the ceremony with selected stories.
		storyIDs := m.selectedStoryIDs()
		if len(storyIDs) == 0 {
			m.err = fmt.Errorf("select at least one story")
			return m, nil
		}
		m.loading = true
		m.err = nil
		return m, tea.Batch(m.spinner.Tick, m.createReview(storyIDs))
	}

	// Delegate navigation to table.
	var cmd tea.Cmd
	m.storyTable, cmd = m.storyTable.Update(msg)
	return m, cmd
}

// ---------------------------------------------------------------------------
// Review mode — view story review results
// ---------------------------------------------------------------------------

func (m BacklogReviewModel) updateReview(msg tea.KeyMsg) (BacklogReviewModel, tea.Cmd) {
	switch msg.String() {
	case "a":
		// Approve selected story.
		row := m.reviewTable.SelectedRow()
		if row == nil {
			return m, nil
		}
		storyID := m.fullStoryIDByPrefix(row[0])
		if storyID == "" {
			return m, nil
		}
		m.approveStoryID = storyID
		m.mode = brModeApproveForm
		m.approveFocusIdx = 0
		m.poNotesInput.Reset()
		m.poConcernsInput.Reset()
		m.prioAdjInput.Reset()
		m.prioReasonInput.Reset()
		m.poNotesInput.Focus()
		return m, textinput.Blink
	case "x":
		// Reject selected story.
		row := m.reviewTable.SelectedRow()
		if row == nil {
			return m, nil
		}
		storyID := m.fullStoryIDByPrefix(row[0])
		if storyID == "" {
			return m, nil
		}
		m.rejectStoryID = storyID
		m.mode = brModeRejectForm
		m.rejectInput.Reset()
		m.rejectInput.Focus()
		return m, textinput.Blink
	case "r":
		m.loading = true
		return m, tea.Batch(m.spinner.Tick, m.refreshReview())
	case "esc":
		m.mode = brModeDashboard
		return m, nil
	}

	var cmd tea.Cmd
	m.reviewTable, cmd = m.reviewTable.Update(msg)
	return m, cmd
}

// ---------------------------------------------------------------------------
// Approve form
// ---------------------------------------------------------------------------

func (m BacklogReviewModel) updateApproveForm(msg tea.KeyMsg) (BacklogReviewModel, tea.Cmd) {
	switch msg.String() {
	case "esc":
		m.mode = brModeReview
		return m, nil
	case "tab":
		m.blurApproveAll()
		m.approveFocusIdx = (m.approveFocusIdx + 1) % 4
		m.focusApproveCurrent()
		return m, textinput.Blink
	case "shift+tab":
		m.blurApproveAll()
		m.approveFocusIdx = (m.approveFocusIdx + 3) % 4 // backward
		m.focusApproveCurrent()
		return m, textinput.Blink
	case "enter":
		notes := strings.TrimSpace(m.poNotesInput.Value())
		if notes == "" {
			m.err = fmt.Errorf("PO notes are required")
			return m, nil
		}
		concerns := strings.TrimSpace(m.poConcernsInput.Value())
		adj := strings.TrimSpace(m.prioAdjInput.Value())
		reason := strings.TrimSpace(m.prioReasonInput.Value())
		m.loading = true
		m.err = nil
		return m, tea.Batch(m.spinner.Tick, m.approveStory(m.approveStoryID, notes, concerns, adj, reason))
	}

	var cmd tea.Cmd
	switch m.approveFocusIdx {
	case 0:
		m.poNotesInput, cmd = m.poNotesInput.Update(msg)
	case 1:
		m.poConcernsInput, cmd = m.poConcernsInput.Update(msg)
	case 2:
		m.prioAdjInput, cmd = m.prioAdjInput.Update(msg)
	case 3:
		m.prioReasonInput, cmd = m.prioReasonInput.Update(msg)
	}
	return m, cmd
}

func (m *BacklogReviewModel) blurApproveAll() {
	m.poNotesInput.Blur()
	m.poConcernsInput.Blur()
	m.prioAdjInput.Blur()
	m.prioReasonInput.Blur()
}

func (m *BacklogReviewModel) focusApproveCurrent() {
	switch m.approveFocusIdx {
	case 0:
		m.poNotesInput.Focus()
	case 1:
		m.poConcernsInput.Focus()
	case 2:
		m.prioAdjInput.Focus()
	case 3:
		m.prioReasonInput.Focus()
	}
}

// ---------------------------------------------------------------------------
// Reject form
// ---------------------------------------------------------------------------

func (m BacklogReviewModel) updateRejectForm(msg tea.KeyMsg) (BacklogReviewModel, tea.Cmd) {
	switch msg.String() {
	case "esc":
		m.mode = brModeReview
		return m, nil
	case "enter":
		reason := strings.TrimSpace(m.rejectInput.Value())
		if reason == "" {
			m.err = fmt.Errorf("rejection reason is required")
			return m, nil
		}
		m.loading = true
		m.err = nil
		return m, tea.Batch(m.spinner.Tick, m.rejectStory(m.rejectStoryID, reason))
	}

	var cmd tea.Cmd
	m.rejectInput, cmd = m.rejectInput.Update(msg)
	return m, cmd
}

// ---------------------------------------------------------------------------
// View
// ---------------------------------------------------------------------------

// View renders the backlog review view.
func (m BacklogReviewModel) View() string {
	var b strings.Builder

	bc := components.NewBreadcrumb("Home", "Projects", m.project.Name, m.epic.Title, "Backlog Review")
	b.WriteString(bc.View())
	b.WriteString("\n\n")

	if m.loading {
		b.WriteString(m.spinner.View() + " Loading...")
		return b.String()
	}

	if m.err != nil {
		errStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("210")).Bold(true)
		b.WriteString(errStyle.Render("Error: "+m.err.Error()) + "\n\n")
	}

	switch m.mode {
	case brModeDashboard:
		b.WriteString(m.dashboardView())
	case brModeCreateSelect:
		b.WriteString(m.createSelectView())
	case brModeReview:
		b.WriteString(m.reviewView())
	case brModeApproveForm:
		b.WriteString(m.approveFormView())
	case brModeRejectForm:
		b.WriteString(m.rejectFormView())
	}

	return b.String()
}

func (m BacklogReviewModel) dashboardView() string {
	var b strings.Builder

	if m.review == nil {
		b.WriteString(pdDim.Render("No backlog review ceremony yet."))
		b.WriteString("\n\n")
		b.WriteString(pdDim.Render("n: create  r: refresh  esc: back"))
		return b.String()
	}

	// Ceremony card
	b.WriteString(m.ceremonyCardView())
	b.WriteString("\n\n")

	// Timeline
	b.WriteString(m.timelineView())
	b.WriteString("\n\n")

	// Key hints based on status
	var hints []string
	switch m.review.Status {
	case "DRAFT":
		hints = append(hints, "s: start", "x: cancel")
	case "IN_PROGRESS":
		hints = append(hints, "r: refresh")
	case "REVIEWING":
		hints = append(hints, "v: view results", "f: complete", "x: cancel")
	case "COMPLETED":
		hints = append(hints, "v: view results")
	}
	hints = append(hints, "n: new", "esc: back")
	b.WriteString(pdDim.Render(strings.Join(hints, "  ")))

	return b.String()
}

func (m BacklogReviewModel) ceremonyCardView() string {
	r := m.review
	var lines []string
	lines = append(lines, pdHeading.Render("Backlog Review Ceremony"))
	lines = append(lines, "")
	lines = append(lines, pdLabel.Render("ID:      ")+pdDim.Render(brTruncID(r.CeremonyID)))
	lines = append(lines, pdLabel.Render("Status:  ")+pdValue.Render(r.Status))
	lines = append(lines, pdLabel.Render("Stories: ")+pdValue.Render(fmt.Sprintf("%d", len(r.StoryIDs))))

	reviewed := 0
	for _, rr := range r.ReviewResults {
		if rr.ReviewedAt != "" {
			reviewed++
		}
	}
	if len(r.StoryIDs) > 0 {
		lines = append(lines, pdLabel.Render("Progress: ")+pdValue.Render(fmt.Sprintf("%d/%d reviewed", reviewed, len(r.StoryIDs))))
	}

	if r.CreatedBy != "" {
		lines = append(lines, pdLabel.Render("Created by: ")+pdValue.Render(r.CreatedBy))
	}
	lines = append(lines, pdLabel.Render("Created: ")+pdDim.Render(r.CreatedAt))
	if r.StartedAt != "" {
		lines = append(lines, pdLabel.Render("Started: ")+pdDim.Render(r.StartedAt))
	}
	if r.CompletedAt != "" {
		lines = append(lines, pdLabel.Render("Completed: ")+pdDim.Render(r.CompletedAt))
	}

	cardWidth := max(m.width-4, 40)
	return pdCard.Width(cardWidth).Render(strings.Join(lines, "\n"))
}

func (m BacklogReviewModel) timelineView() string {
	r := m.review
	if r == nil {
		return ""
	}

	var b strings.Builder
	brRenderPhaseTimeline(&b, r)
	brRenderStoryProgress(&b, r.ReviewResults, m.stories)
	return b.String()
}

// brRenderPhaseTimeline writes the phase progress bar (Created→Started→Reviewing→Completed).
func brRenderPhaseTimeline(b *strings.Builder, r *domain.BacklogReview) {
	active := lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("82"))
	done := lipgloss.NewStyle().Foreground(lipgloss.Color("82"))
	pending := lipgloss.NewStyle().Foreground(lipgloss.Color("241"))
	label := lipgloss.NewStyle().Foreground(lipgloss.Color("246"))

	phases := []struct {
		name string
		at   string
	}{
		{"Created", r.CreatedAt},
		{"Started", r.StartedAt},
		{"Reviewing", ""},
		{"Completed", r.CompletedAt},
	}

	currentPhase := brStatusToPhase(r.Status)

	for i, p := range phases {
		if i > 0 {
			if i-1 < currentPhase {
				b.WriteString(done.Render(" ── "))
			} else {
				b.WriteString(pending.Render(" ── "))
			}
		}
		switch {
		case i < currentPhase:
			b.WriteString(done.Render("● " + p.name))
		case i == currentPhase:
			b.WriteString(active.Render("◉ " + p.name))
		default:
			b.WriteString(pending.Render("○ " + p.name))
		}
	}
	b.WriteString("\n")

	var times []string
	for _, p := range phases {
		if ts := brShortTime(p.at); ts != "" {
			times = append(times, label.Render(ts))
		}
	}
	if len(times) > 0 {
		b.WriteString("  " + strings.Join(times, "    ") + "\n")
	}
}

// brStatusToPhase maps a backlog review status to a phase index.
func brStatusToPhase(status string) int {
	switch status {
	case "IN_PROGRESS":
		return 1
	case "REVIEWING":
		return 2
	case "COMPLETED":
		return 3
	default:
		return 0
	}
}

// brRenderStoryProgress writes per-story approval status lines.
func brRenderStoryProgress(b *strings.Builder, results []domain.StoryReviewResult, stories []domain.StorySummary) {
	if len(results) == 0 {
		return
	}

	label := lipgloss.NewStyle().Foreground(lipgloss.Color("246"))
	b.WriteString("\n")
	b.WriteString(label.Render("Story Progress:"))
	b.WriteString("\n")

	titleByID := make(map[string]string, len(stories))
	for _, s := range stories {
		titleByID[s.ID] = s.Title
	}

	for _, rr := range results {
		brRenderStoryLine(b, rr, titleByID)
	}
}

// brRenderStoryLine writes a single story progress line.
func brRenderStoryLine(b *strings.Builder, rr domain.StoryReviewResult, titleByID map[string]string) {
	done := lipgloss.NewStyle().Foreground(lipgloss.Color("82"))
	pending := lipgloss.NewStyle().Foreground(lipgloss.Color("241"))
	label := lipgloss.NewStyle().Foreground(lipgloss.Color("246"))

	title := titleByID[rr.StoryID]
	if title == "" {
		title = brTruncID(rr.StoryID)
	}
	if len(title) > 20 {
		title = title[:17] + "..."
	}

	statusIcon, statusText := brApprovalIndicator(rr, done, pending)

	ts := brReviewTimestamp(rr)
	line := fmt.Sprintf("  %s %-20s  %s", statusIcon, title, statusText)
	if ts != "" {
		line += "  " + label.Render(ts)
	}
	b.WriteString(line + "\n")
}

// brApprovalIndicator returns icon and text for a story's approval status.
func brApprovalIndicator(rr domain.StoryReviewResult, done, pending lipgloss.Style) (string, string) {
	switch rr.ApprovalStatus {
	case "APPROVED":
		return done.Render("✔"), done.Render("APPROVED")
	case "REJECTED":
		reject := lipgloss.NewStyle().Foreground(lipgloss.Color("210"))
		return reject.Render("✘"), reject.Render("REJECTED")
	case "PENDING":
		if rr.ReviewedAt != "" {
			warn := lipgloss.NewStyle().Foreground(lipgloss.Color("220"))
			return warn.Render("◆"), warn.Render("REVIEWED")
		}
		return pending.Render("○"), pending.Render("PENDING")
	default:
		return pending.Render("○"), pending.Render(rr.ApprovalStatus)
	}
}

// brReviewTimestamp returns the most relevant timestamp for a review result.
func brReviewTimestamp(rr domain.StoryReviewResult) string {
	switch {
	case rr.ApprovedAt != "":
		return brShortTime(rr.ApprovedAt)
	case rr.RejectedAt != "":
		return brShortTime(rr.RejectedAt)
	case rr.ReviewedAt != "":
		return brShortTime(rr.ReviewedAt)
	default:
		return ""
	}
}

// brShortTime extracts a short time representation from an ISO timestamp.
func brShortTime(ts string) string {
	if ts == "" {
		return ""
	}
	// Try to extract "HH:MM" from formats like "2006-01-02T15:04:05Z" or similar.
	if len(ts) >= 16 && (ts[10] == 'T' || ts[10] == ' ') {
		return ts[11:16]
	}
	if len(ts) > 16 {
		return ts[:16]
	}
	return ts
}

func (m BacklogReviewModel) createSelectView() string {
	var b strings.Builder

	title := lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("147"))
	hint := lipgloss.NewStyle().Foreground(lipgloss.Color("246"))

	b.WriteString(title.Render("Select Stories for Backlog Review"))
	b.WriteString("\n\n")

	if len(m.stories) == 0 {
		b.WriteString(pdDim.Render("No stories in this epic."))
		b.WriteString("\n\n")
		b.WriteString(hint.Render("esc: cancel"))
		return b.String()
	}

	b.WriteString(m.storyTable.View())
	b.WriteString("\n\n")

	count := len(m.selectedStoryIDs())
	b.WriteString(pdValue.Render(fmt.Sprintf("%d stories selected", count)))
	b.WriteString("\n")
	b.WriteString(hint.Render("space: toggle  enter: create review  esc: cancel"))

	return b.String()
}

func (m BacklogReviewModel) reviewView() string {
	var b strings.Builder

	b.WriteString(pdHeading.Render("Story Review Results"))
	b.WriteString("\n\n")

	if m.review == nil || len(m.review.ReviewResults) == 0 {
		b.WriteString(pdDim.Render("No review results yet."))
	} else {
		b.WriteString(m.reviewTable.View())
	}

	b.WriteString("\n")
	b.WriteString(pdDim.Render("a: approve  x: reject  r: refresh  esc: back to dashboard"))

	return b.String()
}

func (m BacklogReviewModel) approveFormView() string {
	var b strings.Builder

	title := lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("147"))
	hint := lipgloss.NewStyle().Foreground(lipgloss.Color("246"))

	b.WriteString(title.Render("Approve Review Plan"))
	b.WriteString("\n")
	b.WriteString(pdDim.Render("Story: " + brTruncID(m.approveStoryID)))
	b.WriteString("\n\n")
	b.WriteString("PO Notes:\n")
	b.WriteString(m.poNotesInput.View())
	b.WriteString("\n\n")
	b.WriteString("PO Concerns:\n")
	b.WriteString(m.poConcernsInput.View())
	b.WriteString("\n\n")
	b.WriteString("Priority Adjustment:\n")
	b.WriteString(m.prioAdjInput.View())
	b.WriteString("\n\n")
	b.WriteString("Priority Reason:\n")
	b.WriteString(m.prioReasonInput.View())
	b.WriteString("\n\n")
	b.WriteString(hint.Render("tab: next field  enter: submit  esc: cancel"))

	return b.String()
}

func (m BacklogReviewModel) rejectFormView() string {
	var b strings.Builder

	title := lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("147"))
	hint := lipgloss.NewStyle().Foreground(lipgloss.Color("246"))

	b.WriteString(title.Render("Reject Review Plan"))
	b.WriteString("\n")
	b.WriteString(pdDim.Render("Story: " + brTruncID(m.rejectStoryID)))
	b.WriteString("\n\n")
	b.WriteString("Reason:\n")
	b.WriteString(m.rejectInput.View())
	b.WriteString("\n\n")
	b.WriteString(hint.Render("enter: submit  esc: cancel"))

	return b.String()
}

// ---------------------------------------------------------------------------
// Commands
// ---------------------------------------------------------------------------

func (m BacklogReviewModel) loadStories() tea.Cmd {
	handler := m.handlers.ListStories
	epicID := m.epic.ID
	return func() tea.Msg {
		stories, total, err := handler.Handle(context.Background(), epicID, "", 100, 0)
		if err != nil {
			return backlogReviewErrMsg{err: err}
		}
		return backlogReviewStoriesLoadedMsg{stories: stories, total: total}
	}
}

func (m BacklogReviewModel) createReview(storyIDs []string) tea.Cmd {
	handler := m.handlers.CreateBacklogReview
	return func() tea.Msg {
		review, err := handler.Handle(context.Background(), command.CreateBacklogReviewCmd{StoryIDs: storyIDs})
		if err != nil {
			return backlogReviewErrMsg{err: err}
		}
		return backlogReviewCreatedMsg{review: review}
	}
}

func (m BacklogReviewModel) startReview() tea.Cmd {
	handler := m.handlers.StartBacklogReview
	ceremonyID := m.review.CeremonyID
	return func() tea.Msg {
		result, err := handler.Handle(context.Background(), command.StartBacklogReviewCmd{CeremonyID: ceremonyID})
		if err != nil {
			return backlogReviewErrMsg{err: err}
		}
		return backlogReviewStartedMsg{review: result.Review, total: result.Total}
	}
}

func (m BacklogReviewModel) refreshReview() tea.Cmd {
	if m.review == nil {
		return nil
	}
	handler := m.handlers.GetBacklogReview
	ceremonyID := m.review.CeremonyID
	return func() tea.Msg {
		review, err := handler.Handle(context.Background(), query.GetBacklogReviewQuery{CeremonyID: ceremonyID})
		if err != nil {
			return backlogReviewErrMsg{err: err}
		}
		return backlogReviewLoadedMsg{review: review}
	}
}

func (m BacklogReviewModel) approveStory(storyID, notes, concerns, adj, reason string) tea.Cmd {
	handler := m.handlers.ApproveReviewPlan
	ceremonyID := m.review.CeremonyID
	return func() tea.Msg {
		result, err := handler.Handle(context.Background(), command.ApproveReviewPlanCmd{
			CeremonyID:  ceremonyID,
			StoryID:     storyID,
			PONotes:     notes,
			POConcerns:  concerns,
			PriorityAdj: adj,
			PrioReason:  reason,
		})
		if err != nil {
			return backlogReviewErrMsg{err: err}
		}
		return backlogReviewApprovedMsg{review: result.Review, planID: result.PlanID}
	}
}

func (m BacklogReviewModel) rejectStory(storyID, reason string) tea.Cmd {
	handler := m.handlers.RejectReviewPlan
	ceremonyID := m.review.CeremonyID
	return func() tea.Msg {
		review, err := handler.Handle(context.Background(), command.RejectReviewPlanCmd{
			CeremonyID: ceremonyID,
			StoryID:    storyID,
			Reason:     reason,
		})
		if err != nil {
			return backlogReviewErrMsg{err: err}
		}
		return backlogReviewRejectedMsg{review: review}
	}
}

func (m BacklogReviewModel) completeReview() tea.Cmd {
	handler := m.handlers.CompleteBacklogReview
	ceremonyID := m.review.CeremonyID
	return func() tea.Msg {
		review, err := handler.Handle(context.Background(), command.CompleteBacklogReviewCmd{CeremonyID: ceremonyID})
		if err != nil {
			return backlogReviewErrMsg{err: err}
		}
		return backlogReviewCompletedMsg{review: review}
	}
}

func (m BacklogReviewModel) cancelReview() tea.Cmd {
	handler := m.handlers.CancelBacklogReview
	ceremonyID := m.review.CeremonyID
	return func() tea.Msg {
		review, err := handler.Handle(context.Background(), command.CancelBacklogReviewCmd{CeremonyID: ceremonyID})
		if err != nil {
			return backlogReviewErrMsg{err: err}
		}
		return backlogReviewCancelledMsg{review: review}
	}
}

func (m BacklogReviewModel) subscribeEvents() tea.Cmd {
	handler := m.handlers.WatchEvents
	return func() tea.Msg {
		ctx, cancel := context.WithCancel(context.Background())
		ch, err := handler.Handle(ctx, query.WatchEventsQuery{
			EventTypes: []string{
				"backlog_review.deliberation_complete",
				"backlog_review.story_reviewed",
				"backlog_review.completed",
				"backlog_review.cancelled",
			},
		})
		if err != nil {
			cancel()
			return backlogReviewErrMsg{err: err}
		}
		return backlogReviewWatchStartedMsg{ch: ch, cancel: cancel}
	}
}

func (m BacklogReviewModel) waitForEvent() tea.Cmd {
	ch := m.eventCh
	if ch == nil {
		return nil
	}
	return func() tea.Msg {
		evt, ok := <-ch
		if !ok {
			return backlogReviewStreamClosedMsg{}
		}
		return backlogReviewEventMsg{event: evt}
	}
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

func (m BacklogReviewModel) selectedStoryIDs() []string {
	ids := make([]string, 0, len(m.selected))
	for idx, sel := range m.selected {
		if sel && idx < len(m.stories) {
			ids = append(ids, m.stories[idx].ID)
		}
	}
	return ids
}

func (m BacklogReviewModel) storyIndexByPrefix(prefix string) int {
	for i, s := range m.stories {
		id := s.ID
		if len(id) > 12 {
			id = id[:12]
		}
		if id == prefix {
			return i
		}
	}
	return -1
}

func (m BacklogReviewModel) fullStoryIDByPrefix(prefix string) string {
	for _, s := range m.stories {
		id := s.ID
		if len(id) > 12 {
			id = id[:12]
		}
		if id == prefix {
			return s.ID
		}
	}
	// Also check review results.
	if m.review != nil {
		for _, rr := range m.review.ReviewResults {
			id := rr.StoryID
			if len(id) > 12 {
				id = id[:12]
			}
			if id == prefix {
				return rr.StoryID
			}
		}
	}
	return ""
}

func brStorySelectRows(stories []domain.StorySummary, selected map[int]bool) []table.Row {
	rows := make([]table.Row, 0, len(stories))
	for i, s := range stories {
		id := s.ID
		if len(id) > 12 {
			id = id[:12]
		}
		sel := " "
		if selected[i] {
			sel = "*"
		}
		rows = append(rows, table.Row{sel, id, s.Title, s.State})
	}
	return rows
}

func brReviewRows(review *domain.BacklogReview, stories []domain.StorySummary) []table.Row {
	if review == nil {
		return nil
	}
	// Build a quick lookup for story titles.
	titleByID := make(map[string]string, len(stories))
	for _, s := range stories {
		titleByID[s.ID] = s.Title
	}

	rows := make([]table.Row, 0, len(review.ReviewResults))
	for _, rr := range review.ReviewResults {
		id := rr.StoryID
		if len(id) > 12 {
			id = id[:12]
		}
		title := titleByID[rr.StoryID]
		if title == "" {
			title = rr.StoryID
		}
		if len(title) > 22 {
			title = title[:19] + "..."
		}
		complexity := ""
		if rr.PlanPreliminary.EstimatedComplexity != "" {
			complexity = rr.PlanPreliminary.EstimatedComplexity
		}
		rows = append(rows, table.Row{id, title, rr.ApprovalStatus, complexity, rr.ReviewedAt})
	}
	return rows
}

// brTruncID shortens UUIDs for display (avoids redeclaring truncID from ceremonies.go).
func brTruncID(id string) string {
	if len(id) > 12 {
		return id[:12]
	}
	return id
}
