package tui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/bubbles/key"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/tui/components"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/tui/views"
)

// View identifies the currently active TUI screen.
type View int

const (
	ViewDashboard View = iota
	ViewProjects
	ViewStories
	ViewTasks
	ViewCeremonies
	ViewEvents
	ViewEnrollment
	ViewDecisions
	ViewProjectDetail
	ViewEpicDetail
	ViewStoryDetail
	ViewBacklogReview
	ViewComms
	ViewAgentConversations
)

// viewName returns a human-readable label for the view.
func viewName(v View) string {
	switch v {
	case ViewDashboard:
		return "Dashboard"
	case ViewProjects:
		return "Projects"
	case ViewStories:
		return "Stories"
	case ViewTasks:
		return "Tasks"
	case ViewCeremonies:
		return "Ceremonies"
	case ViewEvents:
		return "Events"
	case ViewEnrollment:
		return "Enrollment"
	case ViewDecisions:
		return "Decisions"
	case ViewProjectDetail:
		return "Project"
	case ViewEpicDetail:
		return "Epic"
	case ViewStoryDetail:
		return "Story"
	case ViewBacklogReview:
		return "Backlog Review"
	case ViewComms:
		return "Communications"
	case ViewAgentConversations:
		return "Agent Conversations"
	default:
		return "Unknown"
	}
}

// ASCII logo rendered in pastel lavender.
var logoStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("183"))

const logo = `  _____ _           _
 |  ___| | ___  ___| |_
 | |_  | |/ _ \/ _ \ __|
 |  _| | |  __/  __/ |_
 |_|   |_|\___|\___|\__| `

// Model is the root Bubble Tea model for the fleetctl TUI.
type Model struct {
	currentView View
	prevView    View // for returning from sub-navigation
	width       int
	height      int
	handlers    app.Handlers
	keys        KeyMap
	err         error

	// Sub-models
	dashboard     views.DashboardModel
	projects      views.ProjectsModel
	projectDetail views.ProjectDetailModel
	epicDetail    views.EpicDetailModel
	storyDetail    views.StoryDetailModel
	backlogReview  views.BacklogReviewModel
	stories       views.StoriesModel
	tasks         views.TasksModel
	ceremonies    views.CeremoniesModel
	events        views.EventsModel
	enrollment         views.EnrollmentModel
	decisions          views.DecisionsModel
	comms              views.CommsModel
	agentConversations views.AgentConversationsModel

	// Tracks which sub-models have been initialised (Init called).
	initialised map[View]bool

	helpBar   components.HelpBar
	statusBar components.StatusBar
}

// NewModel creates the root TUI model wired to the given Handlers.
func NewModel(h app.Handlers) Model {
	return Model{
		currentView: ViewDashboard,
		handlers:    h,
		keys:        DefaultKeyMap(),

		dashboard:          views.NewDashboardModel(),
		projects:           views.NewProjectsModel(h.CreateProject, h.ListProjects),
		stories:            views.NewStoriesModel(h.ListStories, h.TransitionStory, ""),
		tasks:              views.NewTasksModel(h.ListTasks, ""),
		ceremonies:         views.NewCeremoniesModel(h.ListCeremonies, h.GetCeremony),
		events:             views.NewEventsModel(h.WatchEvents),
		enrollment:         views.NewEnrollmentModel(h.Enroll, h.Renew),
		decisions:          views.NewDecisionsModel(h.ApproveDecision, h.RejectDecision, ""),
		comms:              views.NewCommsModel(h.WatchEvents),
		agentConversations: views.NewAgentConversationsModel(h.ListBacklogReviews, h.GetBacklogReview, h.WatchEvents),

		initialised: make(map[View]bool),
		helpBar:     components.NewHelpBar(dashboardBindings()...),
		statusBar:   components.NewStatusBar().SetView("Dashboard").SetConnected(h.ListProjects != nil),
	}
}

// Init implements tea.Model.
func (m Model) Init() tea.Cmd {
	m.initialised[ViewDashboard] = true
	// Start the comms event collector at app startup so it captures events
	// from all views, not just when the comms view is active.
	m.initialised[ViewComms] = true
	return tea.Batch(m.dashboard.Init(), m.comms.Init())
}

// Update implements tea.Model.
func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case views.ProjectSelectedMsg,
		views.BackToProjectsMsg,
		views.EpicSelectedMsg,
		views.BackToProjectDetailMsg,
		views.StorySelectedMsg,
		views.BackToEpicDetailMsg,
		views.CeremonyStartedMsg,
		views.BacklogReviewRequestedMsg,
		views.BackToEpicDetailFromReviewMsg,
		views.CommsTickMsg,
		views.BackFromCommsMsg,
		views.BackFromAgentConversationsMsg:
		return m.routeNavigationMsg(msg)

	case tea.WindowSizeMsg:
		return m.handleWindowSize(msg), nil

	case tea.KeyMsg:
		result, cmd, handled := m.handleKeyMsg(msg)
		if handled {
			return result, cmd
		}
	}

	// Delegate to the active sub-model.
	return m.delegateUpdate(msg)
}

// routeNavigationMsg handles navigation messages emitted by child views.
func (m Model) routeNavigationMsg(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case views.ProjectSelectedMsg:
		m.projectDetail = views.NewProjectDetailModel(m.handlers.CreateEpic, m.handlers.ListEpics, msg.Project)
		m.initialised[ViewProjectDetail] = false
		return m.switchView(ViewProjectDetail)

	case views.BackToProjectsMsg:
		return m.switchView(ViewProjects)

	case views.EpicSelectedMsg:
		m.epicDetail = views.NewEpicDetailModel(
			m.handlers.CreateStory,
			m.handlers.StartCeremony,
			m.handlers.ListStories,
			msg.Epic, msg.Project,
		)
		m.initialised[ViewEpicDetail] = false
		return m.switchView(ViewEpicDetail)

	case views.BackToProjectDetailMsg:
		return m.switchView(ViewProjectDetail)

	case views.StorySelectedMsg:
		m.storyDetail = views.NewStoryDetailModel(
			m.handlers.CreateTask,
			m.handlers.TransitionStory,
			m.handlers.ListTasks,
			msg.Story, msg.Epic, msg.Project,
		)
		m.initialised[ViewStoryDetail] = false
		return m.switchView(ViewStoryDetail)

	case views.BackToEpicDetailMsg:
		return m.switchView(ViewEpicDetail)

	case views.CeremonyStartedMsg:
		m.initialised[ViewEpicDetail] = false
		m.initialised[ViewCeremonies] = false
		return m.switchView(ViewCeremonies)

	case views.BacklogReviewRequestedMsg:
		m.backlogReview = views.NewBacklogReviewModel(
			views.BacklogReviewHandlers{
				ListStories:           m.handlers.ListStories,
				CreateBacklogReview:   m.handlers.CreateBacklogReview,
				StartBacklogReview:    m.handlers.StartBacklogReview,
				GetBacklogReview:      m.handlers.GetBacklogReview,
				ApproveReviewPlan:     m.handlers.ApproveReviewPlan,
				RejectReviewPlan:      m.handlers.RejectReviewPlan,
				CompleteBacklogReview: m.handlers.CompleteBacklogReview,
				CancelBacklogReview:   m.handlers.CancelBacklogReview,
				WatchEvents:           m.handlers.WatchEvents,
			},
			msg.Epic, msg.Project,
		)
		m.initialised[ViewBacklogReview] = false
		return m.switchView(ViewBacklogReview)

	case views.BackToEpicDetailFromReviewMsg:
		return m.switchView(ViewEpicDetail)

	case views.CommsTickMsg:
		var cmd tea.Cmd
		m.comms, cmd = m.comms.Update(msg)
		return m, cmd

	case views.BackFromCommsMsg:
		return m.switchView(ViewDashboard)

	case views.BackFromAgentConversationsMsg:
		m.initialised[ViewAgentConversations] = false
		return m.switchView(ViewDashboard)
	}

	return m, nil
}

// handleWindowSize propagates the new terminal size to all sub-models.
func (m Model) handleWindowSize(msg tea.WindowSizeMsg) Model {
	m.width = msg.Width
	m.height = msg.Height
	bodyH := msg.Height - 10
	m.statusBar = m.statusBar.SetWidth(msg.Width)
	m.helpBar = m.helpBar.SetWidth(msg.Width)
	m.dashboard = m.dashboard.SetSize(msg.Width, bodyH)
	m.projects = m.projects.SetSize(msg.Width, bodyH)
	m.projectDetail = m.projectDetail.SetSize(msg.Width, bodyH)
	m.epicDetail = m.epicDetail.SetSize(msg.Width, bodyH)
	m.storyDetail = m.storyDetail.SetSize(msg.Width, bodyH)
	m.backlogReview = m.backlogReview.SetSize(msg.Width, bodyH)
	m.stories = m.stories.SetSize(msg.Width, bodyH)
	m.tasks = m.tasks.SetSize(msg.Width, bodyH)
	m.ceremonies = m.ceremonies.SetSize(msg.Width, bodyH)
	m.events = m.events.SetSize(msg.Width, bodyH)
	m.enrollment = m.enrollment.SetSize(msg.Width, bodyH)
	m.decisions = m.decisions.SetSize(msg.Width, bodyH)
	m.comms = m.comms.SetSize(msg.Width, bodyH)
	m.agentConversations = m.agentConversations.SetSize(msg.Width, bodyH)
	return m
}

// handleKeyMsg processes global key bindings. It returns handled=true when the
// key was consumed, or handled=false to indicate the caller should delegate.
func (m Model) handleKeyMsg(msg tea.KeyMsg) (tea.Model, tea.Cmd, bool) {
	// Global quit.
	if key.Matches(msg, m.keys.Quit) {
		m.events.Stop()
		m.comms.Stop()
		return m, tea.Quit, true
	}

	// Dashboard navigation shortcuts.
	if m.currentView == ViewDashboard {
		if next, ok := m.dashboardNav(msg); ok {
			result, cmd := m.switchView(next)
			return result, cmd, true
		}
		return m, nil, false // delegate to dashboard sub-model
	}

	// Decisions from ceremonies (key "d").
	if m.currentView == ViewCeremonies && msg.String() == "d" {
		if sel := m.ceremonies.SelectedCeremony(); sel != nil {
			m.decisions = views.NewDecisionsModel(m.handlers.ApproveDecision, m.handlers.RejectDecision, sel.StoryID)
			m.decisions = m.decisions.SetSize(m.width, m.height-10)
			m.initialised[ViewDecisions] = false
		}
		result, cmd := m.switchView(ViewDecisions)
		return result, cmd, true
	}

	// Back navigation.
	if key.Matches(msg, m.keys.Back) && m.currentView != ViewDashboard {
		return m.handleBackNav()
	}

	return m, nil, false
}

// dashboardNav maps a dashboard key press to a target view.
func (m Model) dashboardNav(msg tea.KeyMsg) (View, bool) {
	switch msg.String() {
	case "p":
		return ViewProjects, true
	case "s":
		return ViewStories, true
	case "t":
		return ViewTasks, true
	case "c":
		return ViewCeremonies, true
	case "e":
		return ViewEvents, true
	case "m":
		return ViewComms, true
	case "a":
		return ViewAgentConversations, true
	}
	return 0, false
}

// handleBackNav handles the Esc/back key from sub-views. Returns handled=false
// when the sub-view should handle Esc itself (delegate).
func (m Model) handleBackNav() (tea.Model, tea.Cmd, bool) {
	switch m.currentView {
	case ViewDecisions:
		result, cmd := m.switchView(ViewCeremonies)
		return result, cmd, true
	case ViewProjectDetail, ViewEpicDetail, ViewStoryDetail,
		ViewBacklogReview, ViewAgentConversations, ViewComms:
		return m, nil, false // delegate to sub-view
	case ViewEvents:
		m.events.Stop()
		m.initialised[ViewEvents] = false
	}
	result, cmd := m.switchView(ViewDashboard)
	return result, cmd, true
}

// switchView transitions to the target view, initialising the sub-model on
// first entry and returning the appropriate Init command.
func (m Model) switchView(target View) (tea.Model, tea.Cmd) {
	m.prevView = m.currentView
	m.currentView = target
	m.statusBar = m.statusBar.SetView(viewName(target))
	m.helpBar = m.helpBar.SetBindings(m.activeBindings()...)

	if m.initialised[target] {
		return m, nil
	}
	m.initialised[target] = true

	var cmd tea.Cmd
	switch target {
	case ViewDashboard:
		cmd = m.dashboard.Init()
	case ViewProjects:
		cmd = m.projects.Init()
	case ViewProjectDetail:
		cmd = m.projectDetail.Init()
	case ViewEpicDetail:
		cmd = m.epicDetail.Init()
	case ViewStoryDetail:
		cmd = m.storyDetail.Init()
	case ViewBacklogReview:
		cmd = m.backlogReview.Init()
	case ViewStories:
		cmd = m.stories.Init()
	case ViewTasks:
		cmd = m.tasks.Init()
	case ViewCeremonies:
		cmd = m.ceremonies.Init()
	case ViewEvents:
		cmd = m.events.Init()
	case ViewEnrollment:
		cmd = m.enrollment.Init()
	case ViewDecisions:
		cmd = m.decisions.Init()
	case ViewComms:
		cmd = m.comms.Init()
	case ViewAgentConversations:
		cmd = m.agentConversations.Init()
	}
	return m, cmd
}

// delegateUpdate forwards the message to the currently active sub-model.
func (m Model) delegateUpdate(msg tea.Msg) (tea.Model, tea.Cmd) {
	var cmd tea.Cmd

	switch m.currentView {
	case ViewDashboard:
		m.dashboard, cmd = m.dashboard.Update(msg)
	case ViewProjects:
		m.projects, cmd = m.projects.Update(msg)
	case ViewProjectDetail:
		m.projectDetail, cmd = m.projectDetail.Update(msg)
	case ViewEpicDetail:
		m.epicDetail, cmd = m.epicDetail.Update(msg)
	case ViewStoryDetail:
		m.storyDetail, cmd = m.storyDetail.Update(msg)
	case ViewBacklogReview:
		m.backlogReview, cmd = m.backlogReview.Update(msg)
	case ViewStories:
		m.stories, cmd = m.stories.Update(msg)
	case ViewTasks:
		m.tasks, cmd = m.tasks.Update(msg)
	case ViewCeremonies:
		m.ceremonies, cmd = m.ceremonies.Update(msg)
	case ViewEvents:
		m.events, cmd = m.events.Update(msg)
	case ViewEnrollment:
		m.enrollment, cmd = m.enrollment.Update(msg)
	case ViewDecisions:
		m.decisions, cmd = m.decisions.Update(msg)
	case ViewComms:
		m.comms, cmd = m.comms.Update(msg)
	case ViewAgentConversations:
		m.agentConversations, cmd = m.agentConversations.Update(msg)
	}

	return m, cmd
}

// activeBindings returns the help bindings for the current view.
// Views that render their own embedded help bar return nil here to
// avoid duplicate hints.
func (m Model) activeBindings() []components.HelpBinding {
	switch m.currentView {
	case ViewDashboard:
		return dashboardBindings()
	default:
		// All other views render their own help inline or via an
		// embedded helpBar, so the app-level bar stays empty.
		return nil
	}
}

// View implements tea.Model.
func (m Model) View() string {
	var b strings.Builder

	// Header with logo
	b.WriteString(logoStyle.Render(logo))
	b.WriteString("\n")
	header := TitleStyle.Render("fleetctl") + "  " + SubtitleStyle.Render(viewName(m.currentView))
	b.WriteString(header)
	b.WriteString("\n\n")

	// Active view body
	switch m.currentView {
	case ViewDashboard:
		b.WriteString(m.dashboard.View())
	case ViewProjects:
		b.WriteString(m.projects.View())
	case ViewProjectDetail:
		b.WriteString(m.projectDetail.View())
	case ViewEpicDetail:
		b.WriteString(m.epicDetail.View())
	case ViewStoryDetail:
		b.WriteString(m.storyDetail.View())
	case ViewBacklogReview:
		b.WriteString(m.backlogReview.View())
	case ViewStories:
		b.WriteString(m.stories.View())
	case ViewTasks:
		b.WriteString(m.tasks.View())
	case ViewCeremonies:
		b.WriteString(m.ceremonies.View())
	case ViewEvents:
		b.WriteString(m.events.View())
	case ViewEnrollment:
		b.WriteString(m.enrollment.View())
	case ViewDecisions:
		b.WriteString(m.decisions.View())
	case ViewComms:
		b.WriteString(m.comms.View())
	case ViewAgentConversations:
		b.WriteString(m.agentConversations.View())
	default:
		fmt.Fprintf(&b, "Unknown view: %d", m.currentView)
	}

	b.WriteString("\n")

	// Error display
	if m.err != nil {
		b.WriteString(ErrorStyle.Render("Error: " + m.err.Error()))
		b.WriteString("\n")
	}

	// Help bar
	b.WriteString(m.helpBar.View())
	b.WriteString("\n")

	// Status bar at the bottom
	b.WriteString(m.statusBar.View())

	return AppStyle.Render(b.String())
}

// ---------------------------------------------------------------------------
// Dashboard help bindings
// ---------------------------------------------------------------------------

func dashboardBindings() []components.HelpBinding {
	return []components.HelpBinding{
		{Key: "p", Description: "projects"},
		{Key: "s", Description: "stories"},
		{Key: "t", Description: "tasks"},
		{Key: "c", Description: "ceremonies"},
		{Key: "e", Description: "events"},
		{Key: "m", Description: "comms"},
		{Key: "a", Description: "agents"},
		{Key: "q", Description: "quit"},
	}
}
