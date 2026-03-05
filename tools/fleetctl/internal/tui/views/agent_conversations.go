package views

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/spinner"
	"github.com/charmbracelet/bubbles/table"
	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/query"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/tui/components"
)

// ---------------------------------------------------------------------------
// Messages
// ---------------------------------------------------------------------------

// BackFromAgentConversationsMsg is emitted when the user presses Esc
// from the top-level ceremony list.
type BackFromAgentConversationsMsg struct{}

type acReviewsLoadedMsg struct {
	reviews []domain.BacklogReview
	total   int32
}
type acReviewDetailMsg struct{ review domain.BacklogReview }
type acEventMsg struct{ event domain.FleetEvent }
type acWatchStartedMsg struct {
	ch     <-chan domain.FleetEvent
	cancel context.CancelFunc
}
type acErrMsg struct{ err error }
type acStreamClosedMsg struct{}
type acReconnectMsg struct{}

// ---------------------------------------------------------------------------
// Modes
// ---------------------------------------------------------------------------

// AgentConvMode identifies the active sub-screen.
type AgentConvMode int

const (
	acModeCeremonyList   AgentConvMode = iota // list of backlog reviews
	acModeCeremonyDetail                      // single review + story table
	acModeStoryReview                         // per-story agent feedback
	acModeAgentDetail                         // full agent detail viewport
)

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

var (
	acHeading     = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("147"))
	acDim         = lipgloss.NewStyle().Foreground(lipgloss.Color("246"))
	acAgentTitle  = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("117"))
	acContent     = lipgloss.NewStyle().Foreground(lipgloss.Color("252"))
	acFocused     = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("82"))
	acUnfocused   = lipgloss.NewStyle().Foreground(lipgloss.Color("241"))
	acStatusOK    = lipgloss.NewStyle().Foreground(lipgloss.Color("120"))
	acStatusPend  = lipgloss.NewStyle().Foreground(lipgloss.Color("214"))
	acStatusRej   = lipgloss.NewStyle().Foreground(lipgloss.Color("210"))
	acFeedbackHas = lipgloss.NewStyle().Foreground(lipgloss.Color("120")).Render("*")
	acFeedbackNo  = lipgloss.NewStyle().Foreground(lipgloss.Color("241")).Render("-")
)

// ---------------------------------------------------------------------------
// Model
// ---------------------------------------------------------------------------

// AgentConversationsModel is the sub-model for the Agent Conversations view.
type AgentConversationsModel struct {
	listBacklogReviews *query.ListBacklogReviewsHandler
	getBacklogReview   *query.GetBacklogReviewHandler
	watchEvents        *query.WatchEventsHandler
	mode               AgentConvMode

	// CeremonyList
	reviews     []domain.BacklogReview
	reviewTable table.Model

	// CeremonyDetail
	selectedReview *domain.BacklogReview
	storyTable     table.Model

	// StoryReview
	selectedResult *domain.StoryReviewResult
	agentFocus     int // 0=architect, 1=qa, 2=devops

	// AgentDetail
	detailViewport viewport.Model

	// Pagination
	paginator components.Paginator

	// Live updates
	eventCh          <-chan domain.FleetEvent
	cancel           context.CancelFunc
	reconnectBackoff time.Duration

	spinner spinner.Model
	helpBar components.HelpBar
	loading bool
	err     error
	width   int
	height  int
}

// NewAgentConversationsModel creates the model wired to the given handlers.
func NewAgentConversationsModel(listBacklogReviews *query.ListBacklogReviewsHandler, getBacklogReview *query.GetBacklogReviewHandler, watchEvents *query.WatchEventsHandler) AgentConversationsModel {
	return AgentConversationsModel{
		listBacklogReviews: listBacklogReviews,
		getBacklogReview:   getBacklogReview,
		watchEvents:        watchEvents,
		paginator:      components.NewPaginator(20),
		spinner:        components.NewSpinner(),
		detailViewport: viewport.New(80, 20),
		loading:        true,
		helpBar: components.NewHelpBar(
			components.HelpBinding{Key: "enter", Description: "select"},
			components.HelpBinding{Key: "r", Description: "refresh"},
			components.HelpBinding{Key: "esc", Description: "back"},
		),
	}
}

// SetSize updates the layout dimensions.
func (m AgentConversationsModel) SetSize(w, h int) AgentConversationsModel {
	m.width = w
	m.height = h
	m.detailViewport.Width = w
	m.detailViewport.Height = max(h-10, 4)
	m.helpBar = m.helpBar.SetWidth(w)
	return m
}

// ---------------------------------------------------------------------------
// tea.Model interface
// ---------------------------------------------------------------------------

// Init loads the ceremony list.
func (m AgentConversationsModel) Init() tea.Cmd {
	return tea.Batch(m.spinner.Tick, m.loadReviews())
}

// Update handles messages.
func (m AgentConversationsModel) Update(msg tea.Msg) (AgentConversationsModel, tea.Cmd) {
	var cmds []tea.Cmd

	switch msg := msg.(type) {

	case acReviewsLoadedMsg:
		m.loading = false
		m.reviews = msg.reviews
		m.paginator = m.paginator.SetTotal(msg.total)
		m.reviewTable = m.buildReviewTable()
		return m, nil

	case acReviewDetailMsg:
		m.loading = false
		review := msg.review
		m.selectedReview = &review
		m.storyTable = m.buildStoryTable(review)
		m.mode = acModeCeremonyDetail
		return m, nil

	case acEventMsg:
		// Auto-refresh on deliberation events and keep listening.
		m.reconnectBackoff = 0
		if m.selectedReview != nil {
			return m, tea.Batch(m.fetchReviewDetail(m.selectedReview.CeremonyID), m.waitForACEvent())
		}
		return m, m.waitForACEvent()

	case acWatchStartedMsg:
		m.eventCh = msg.ch
		m.cancel = msg.cancel
		m.reconnectBackoff = 0
		return m, m.waitForACEvent()

	case acStreamClosedMsg:
		m.eventCh = nil
		if m.reconnectBackoff == 0 {
			m.reconnectBackoff = time.Second
		} else {
			m.reconnectBackoff = min(m.reconnectBackoff*2, 30*time.Second)
		}
		return m, tea.Tick(m.reconnectBackoff, func(time.Time) tea.Msg {
			return acReconnectMsg{}
		})

	case acReconnectMsg:
		return m, m.startWatchingDeliberations()

	case acErrMsg:
		m.err = msg.err
		m.loading = false
		return m, nil

	case spinner.TickMsg:
		var cmd tea.Cmd
		m.spinner, cmd = m.spinner.Update(msg)
		cmds = append(cmds, cmd)

	case tea.KeyMsg:
		switch m.mode {
		case acModeCeremonyList:
			return m.updateCeremonyList(msg)
		case acModeCeremonyDetail:
			return m.updateCeremonyDetail(msg)
		case acModeStoryReview:
			return m.updateStoryReview(msg)
		case acModeAgentDetail:
			return m.updateAgentDetail(msg)
		}
	}

	return m, tea.Batch(cmds...)
}

// Stop cancels the event watch.
func (m *AgentConversationsModel) Stop() {
	if m.cancel != nil {
		m.cancel()
		m.cancel = nil
	}
	m.eventCh = nil
}

// View renders the current sub-screen.
func (m AgentConversationsModel) View() string {
	var b strings.Builder

	switch m.mode {
	case acModeCeremonyList:
		b.WriteString(m.viewCeremonyList())
	case acModeCeremonyDetail:
		b.WriteString(m.viewCeremonyDetail())
	case acModeStoryReview:
		b.WriteString(m.viewStoryReview())
	case acModeAgentDetail:
		b.WriteString(m.viewAgentDetail())
	}

	return b.String()
}

// ---------------------------------------------------------------------------
// CeremonyList mode
// ---------------------------------------------------------------------------

func (m AgentConversationsModel) updateCeremonyList(msg tea.KeyMsg) (AgentConversationsModel, tea.Cmd) {
	switch msg.String() {
	case "esc":
		m.Stop()
		return m, func() tea.Msg { return BackFromAgentConversationsMsg{} }
	case "r":
		m.loading = true
		return m, tea.Batch(m.spinner.Tick, m.loadReviews())
	case "left":
		m.paginator = m.paginator.PrevPage()
		m.loading = true
		return m, tea.Batch(m.spinner.Tick, m.loadReviews())
	case "right":
		m.paginator = m.paginator.NextPage()
		m.loading = true
		return m, tea.Batch(m.spinner.Tick, m.loadReviews())
	case "enter":
		if len(m.reviews) > 0 {
			idx := m.reviewTable.Cursor()
			if idx < len(m.reviews) {
				m.loading = true
				return m, tea.Batch(m.spinner.Tick, m.fetchReviewDetail(m.reviews[idx].CeremonyID))
			}
		}
	default:
		var cmd tea.Cmd
		m.reviewTable, cmd = m.reviewTable.Update(msg)
		return m, cmd
	}
	return m, nil
}

func (m AgentConversationsModel) viewCeremonyList() string {
	var b strings.Builder

	bc := components.NewBreadcrumb("Home", "Agent Conversations")
	b.WriteString(bc.View())
	b.WriteString("\n")

	b.WriteString(acHeading.Render("Backlog Review Ceremonies"))
	b.WriteString("\n\n")

	if m.err != nil {
		errStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("210")).Bold(true)
		b.WriteString(errStyle.Render("Error: "+m.err.Error()) + "\n\n")
	}

	if m.loading && len(m.reviews) == 0 {
		b.WriteString(m.spinner.View() + " " + acDim.Render("Loading ceremonies..."))
		return b.String()
	}

	if len(m.reviews) == 0 {
		b.WriteString(acDim.Render("No backlog reviews found."))
		return b.String()
	}

	b.WriteString(m.reviewTable.View())
	b.WriteString("\n")
	b.WriteString(m.paginator.View())
	b.WriteString("\n")
	b.WriteString(m.helpBar.View())

	return b.String()
}

func (m AgentConversationsModel) buildReviewTable() table.Model {
	cols := []table.Column{
		{Title: "Ceremony ID", Width: 20},
		{Title: "Status", Width: 14},
		{Title: "Stories", Width: 8},
		{Title: "Created By", Width: 16},
		{Title: "Created", Width: 20},
	}

	rows := make([]table.Row, len(m.reviews))
	for i, r := range m.reviews {
		rows[i] = table.Row{
			truncate(r.CeremonyID, 20),
			r.Status,
			fmt.Sprintf("%d", len(r.StoryIDs)),
			truncate(r.CreatedBy, 16),
			truncate(r.CreatedAt, 20),
		}
	}

	t := table.New(
		table.WithColumns(cols),
		table.WithRows(rows),
		table.WithFocused(true),
		table.WithHeight(min(len(rows)+1, 15)),
	)
	s := table.DefaultStyles()
	s.Header = s.Header.Foreground(lipgloss.Color("147")).Bold(true)
	s.Selected = s.Selected.Foreground(lipgloss.Color("82")).Bold(true)
	t.SetStyles(s)
	return t
}

// ---------------------------------------------------------------------------
// CeremonyDetail mode
// ---------------------------------------------------------------------------

func (m AgentConversationsModel) updateCeremonyDetail(msg tea.KeyMsg) (AgentConversationsModel, tea.Cmd) {
	switch msg.String() {
	case "esc":
		m.mode = acModeCeremonyList
		m.selectedReview = nil
		m.Stop()
		return m, nil
	case "w":
		// Stop existing watch before starting a new one.
		m.Stop()
		return m, m.startWatchingDeliberations()
	case "enter":
		if m.selectedReview != nil && len(m.selectedReview.ReviewResults) > 0 {
			idx := m.storyTable.Cursor()
			if idx < len(m.selectedReview.ReviewResults) {
				result := m.selectedReview.ReviewResults[idx]
				m.selectedResult = &result
				m.agentFocus = 0
				m.mode = acModeStoryReview
				return m, nil
			}
		}
	case "r":
		if m.selectedReview != nil {
			m.loading = true
			return m, tea.Batch(m.spinner.Tick, m.fetchReviewDetail(m.selectedReview.CeremonyID))
		}
	default:
		var cmd tea.Cmd
		m.storyTable, cmd = m.storyTable.Update(msg)
		return m, cmd
	}
	return m, nil
}

func (m AgentConversationsModel) viewCeremonyDetail() string {
	var b strings.Builder

	bc := components.NewBreadcrumb("Home", "Agent Conversations", "Ceremony")
	b.WriteString(bc.View())
	b.WriteString("\n")

	if m.selectedReview == nil {
		b.WriteString(acDim.Render("No ceremony selected."))
		return b.String()
	}

	r := m.selectedReview

	b.WriteString(acHeading.Render("Ceremony: "+truncate(r.CeremonyID, 24)))
	b.WriteString("\n")
	fmt.Fprintf(&b, "%s %s  %s %s  %s %s\n",
		acDim.Render("Status:"), statusStyle(r.Status),
		acDim.Render("Stories:"), acContent.Render(fmt.Sprintf("%d", len(r.StoryIDs))),
		acDim.Render("Created:"), acContent.Render(truncate(r.CreatedAt, 20)),
	)
	b.WriteString("\n")

	if len(r.ReviewResults) == 0 {
		b.WriteString(acDim.Render("No review results yet."))
	} else {
		b.WriteString(acHeading.Render("Story Review Results"))
		b.WriteString("\n")
		b.WriteString(m.storyTable.View())
	}

	b.WriteString("\n")

	watchHint := acDim.Render("Press w to watch live updates")
	if m.eventCh != nil {
		watchHint = acStatusOK.Render("Watching for live updates...")
	}
	b.WriteString(watchHint)
	b.WriteString("\n")
	b.WriteString(m.helpBar.View())

	return b.String()
}

func (m AgentConversationsModel) buildStoryTable(review domain.BacklogReview) table.Model {
	cols := []table.Column{
		{Title: "Story", Width: 20},
		{Title: "Arch", Width: 5},
		{Title: "QA", Width: 5},
		{Title: "DevOps", Width: 7},
		{Title: "Status", Width: 12},
		{Title: "Complexity", Width: 11},
	}

	rows := make([]table.Row, len(review.ReviewResults))
	for i, rr := range review.ReviewResults {
		arch := acFeedbackNo
		if rr.ArchitectFeedback != "" {
			arch = acFeedbackHas
		}
		qa := acFeedbackNo
		if rr.QAFeedback != "" {
			qa = acFeedbackHas
		}
		devops := acFeedbackNo
		if rr.DevopsFeedback != "" {
			devops = acFeedbackHas
		}

		rows[i] = table.Row{
			truncate(rr.StoryID, 20),
			arch,
			qa,
			devops,
			rr.ApprovalStatus,
			rr.PlanPreliminary.EstimatedComplexity,
		}
	}

	t := table.New(
		table.WithColumns(cols),
		table.WithRows(rows),
		table.WithFocused(true),
		table.WithHeight(min(len(rows)+1, 15)),
	)
	s := table.DefaultStyles()
	s.Header = s.Header.Foreground(lipgloss.Color("147")).Bold(true)
	s.Selected = s.Selected.Foreground(lipgloss.Color("82")).Bold(true)
	t.SetStyles(s)
	return t
}

// ---------------------------------------------------------------------------
// StoryReview mode
// ---------------------------------------------------------------------------

func (m AgentConversationsModel) updateStoryReview(msg tea.KeyMsg) (AgentConversationsModel, tea.Cmd) {
	switch msg.String() {
	case "esc":
		m.mode = acModeCeremonyDetail
		m.selectedResult = nil
		return m, nil
	case "1":
		m.agentFocus = 0
		return m, nil
	case "2":
		m.agentFocus = 1
		return m, nil
	case "3":
		m.agentFocus = 2
		return m, nil
	case "enter":
		if m.selectedResult != nil {
			m.mode = acModeAgentDetail
			m.detailViewport.SetContent(m.renderAgentDetail())
			m.detailViewport.GotoTop()
			return m, nil
		}
	}
	return m, nil
}

func (m AgentConversationsModel) viewStoryReview() string {
	var b strings.Builder

	bc := components.NewBreadcrumb("Home", "Agent Conversations", "Ceremony", "Story Review")
	b.WriteString(bc.View())
	b.WriteString("\n")

	if m.selectedResult == nil {
		b.WriteString(acDim.Render("No story selected."))
		return b.String()
	}

	rr := m.selectedResult

	b.WriteString(acHeading.Render("Story: "+truncate(rr.StoryID, 24)))
	b.WriteString("\n\n")

	// Plan preliminary card.
	pp := rr.PlanPreliminary
	if pp.Title != "" {
		b.WriteString(acHeading.Render("Preliminary Plan"))
		b.WriteString("\n")
		fmt.Fprintf(&b, "%s %s\n", acDim.Render("Title:"), acContent.Render(pp.Title))
		fmt.Fprintf(&b, "%s %s\n", acDim.Render("Complexity:"), acContent.Render(pp.EstimatedComplexity))
		if pp.Description != "" {
			fmt.Fprintf(&b, "%s %s\n", acDim.Render("Description:"), acContent.Render(pp.Description))
		}
		if len(pp.AcceptanceCriteria) > 0 {
			b.WriteString(acDim.Render("Acceptance Criteria:") + "\n")
			for _, ac := range pp.AcceptanceCriteria {
				fmt.Fprintf(&b, "  - %s\n", acContent.Render(ac))
			}
		}
		if len(pp.TasksOutline) > 0 {
			b.WriteString(acDim.Render("Tasks:") + "\n")
			for _, t := range pp.TasksOutline {
				fmt.Fprintf(&b, "  - %s\n", acContent.Render(t))
			}
		}
		b.WriteString("\n")
	}

	// Agent feedback tabs.
	agents := []struct {
		idx   int
		label string
		text  string
	}{
		{0, "ARCHITECT", rr.ArchitectFeedback},
		{1, "QA", rr.QAFeedback},
		{2, "DEVOPS", rr.DevopsFeedback},
	}

	for _, a := range agents {
		label := a.label
		if a.idx == m.agentFocus {
			label = acFocused.Render(fmt.Sprintf("[%d] %s", a.idx+1, a.label))
		} else {
			label = acUnfocused.Render(fmt.Sprintf("[%d] %s", a.idx+1, a.label))
		}
		b.WriteString(label)
		b.WriteString("\n")
		if a.text != "" {
			b.WriteString(acContent.Render(a.text))
		} else {
			b.WriteString(acDim.Render("No feedback yet."))
		}
		b.WriteString("\n\n")
	}

	// Recommendations.
	if len(rr.Recommendations) > 0 {
		b.WriteString(acHeading.Render("Recommendations"))
		b.WriteString("\n")
		for _, rec := range rr.Recommendations {
			fmt.Fprintf(&b, "  - %s\n", acContent.Render(rec))
		}
		b.WriteString("\n")
	}

	fmt.Fprintf(&b, "%s %s\n", acDim.Render("Status:"), statusStyle(rr.ApprovalStatus))

	b.WriteString("\n")
	b.WriteString(acDim.Render("1/2/3: focus agent  Enter: expand  Esc: back"))
	b.WriteString("\n")
	b.WriteString(m.helpBar.View())

	return b.String()
}

// ---------------------------------------------------------------------------
// AgentDetail mode
// ---------------------------------------------------------------------------

func (m AgentConversationsModel) updateAgentDetail(msg tea.KeyMsg) (AgentConversationsModel, tea.Cmd) {
	switch msg.String() {
	case "esc":
		m.mode = acModeStoryReview
		return m, nil
	default:
		var cmd tea.Cmd
		m.detailViewport, cmd = m.detailViewport.Update(msg)
		return m, cmd
	}
}

func (m AgentConversationsModel) viewAgentDetail() string {
	var b strings.Builder

	bc := components.NewBreadcrumb("Home", "Agent Conversations", "Ceremony", "Story", "Agent")
	b.WriteString(bc.View())
	b.WriteString("\n")

	b.WriteString(m.detailViewport.View())
	b.WriteString("\n")
	b.WriteString(acDim.Render("Esc: back  Scroll: up/down"))

	return b.String()
}

func (m AgentConversationsModel) renderAgentDetail() string {
	if m.selectedResult == nil {
		return "No data."
	}
	rr := m.selectedResult
	var b strings.Builder

	agentNames := []string{"ARCHITECT", "QA", "DEVOPS"}
	feedbacks := []string{rr.ArchitectFeedback, rr.QAFeedback, rr.DevopsFeedback}

	name := agentNames[m.agentFocus]
	feedback := feedbacks[m.agentFocus]

	b.WriteString(acAgentTitle.Render(name+" Feedback"))
	b.WriteString("\n\n")

	if feedback != "" {
		b.WriteString(acContent.Render(feedback))
	} else {
		b.WriteString(acDim.Render("No feedback from this agent."))
	}
	b.WriteString("\n\n")

	// Plan context.
	pp := rr.PlanPreliminary
	if pp.Title != "" {
		b.WriteString(acHeading.Render("Plan Context"))
		b.WriteString("\n")
		fmt.Fprintf(&b, "%s %s\n", acDim.Render("Title:"), acContent.Render(pp.Title))
		fmt.Fprintf(&b, "%s %s\n", acDim.Render("Complexity:"), acContent.Render(pp.EstimatedComplexity))
		if pp.TechnicalNotes != "" {
			fmt.Fprintf(&b, "%s %s\n", acDim.Render("Technical Notes:"), acContent.Render(pp.TechnicalNotes))
		}
		if len(pp.Dependencies) > 0 {
			b.WriteString(acDim.Render("Dependencies:") + "\n")
			for _, d := range pp.Dependencies {
				fmt.Fprintf(&b, "  - %s\n", acContent.Render(d))
			}
		}
		if len(pp.Roles) > 0 {
			b.WriteString(acDim.Render("Roles:") + "\n")
			for _, r := range pp.Roles {
				fmt.Fprintf(&b, "  - %s\n", acContent.Render(r))
			}
		}
	}

	return b.String()
}

// ---------------------------------------------------------------------------
// Commands
// ---------------------------------------------------------------------------

func (m AgentConversationsModel) loadReviews() tea.Cmd {
	limit := m.paginator.Limit()
	offset := m.paginator.Offset()
	handler := m.listBacklogReviews
	return func() tea.Msg {
		reviews, total, err := handler.Handle(context.Background(), "", limit, offset)
		if err != nil {
			return acErrMsg{err: err}
		}
		return acReviewsLoadedMsg{reviews: reviews, total: total}
	}
}

func (m AgentConversationsModel) fetchReviewDetail(ceremonyID string) tea.Cmd {
	handler := m.getBacklogReview
	return func() tea.Msg {
		review, err := handler.Handle(context.Background(), query.GetBacklogReviewQuery{CeremonyID: ceremonyID})
		if err != nil {
			return acErrMsg{err: err}
		}
		return acReviewDetailMsg{review: review}
	}
}

func (m AgentConversationsModel) startWatchingDeliberations() tea.Cmd {
	handler := m.watchEvents
	return func() tea.Msg {
		ctx, cancel := context.WithCancel(context.Background())
		types := []string{
			"deliberation.received",
			"backlog_review.deliberation_complete",
			"backlog_review.story_reviewed",
		}
		ch, err := handler.Handle(ctx, query.WatchEventsQuery{EventTypes: types})
		if err != nil {
			cancel()
			return acErrMsg{err: err}
		}
		return acWatchStartedMsg{ch: ch, cancel: cancel}
	}
}

func (m AgentConversationsModel) waitForACEvent() tea.Cmd {
	ch := m.eventCh
	if ch == nil {
		return nil
	}
	return func() tea.Msg {
		evt, ok := <-ch
		if !ok {
			return acStreamClosedMsg{}
		}
		return acEventMsg{event: evt}
	}
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

func statusStyle(s string) string {
	switch s {
	case "APPROVED", "completed":
		return acStatusOK.Render(s)
	case "PENDING", "in_progress", "deliberating":
		return acStatusPend.Render(s)
	case "REJECTED", "cancelled":
		return acStatusRej.Render(s)
	default:
		return acContent.Render(s)
	}
}

func truncate(s string, maxLen int) string {
	runes := []rune(s)
	if len(runes) <= maxLen {
		return s
	}
	if maxLen <= 3 {
		return string(runes[:maxLen])
	}
	return string(runes[:maxLen-3]) + "..."
}
