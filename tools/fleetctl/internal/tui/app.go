package tui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/bubbles/key"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
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
	client      ports.FleetClient
	keys        KeyMap
	err         error

	// Sub-models
	dashboard  views.DashboardModel
	projects   views.ProjectsModel
	stories    views.StoriesModel
	tasks      views.TasksModel
	ceremonies views.CeremoniesModel
	events     views.EventsModel
	enrollment views.EnrollmentModel
	decisions  views.DecisionsModel

	// Tracks which sub-models have been initialised (Init called).
	initialised map[View]bool

	helpBar   components.HelpBar
	statusBar components.StatusBar
}

// NewModel creates the root TUI model wired to the given FleetClient.
func NewModel(client ports.FleetClient) Model {
	return Model{
		currentView: ViewDashboard,
		client:      client,
		keys:        DefaultKeyMap(),

		dashboard:  views.NewDashboardModel(),
		projects:   views.NewProjectsModel(client),
		stories:    views.NewStoriesModel(client, ""),
		tasks:      views.NewTasksModel(client, ""),
		ceremonies: views.NewCeremoniesModel(client),
		events:     views.NewEventsModel(client),
		enrollment: views.NewEnrollmentModel(client),
		decisions:  views.NewDecisionsModel(client, ""),

		initialised: make(map[View]bool),
		helpBar:     components.NewHelpBar(dashboardBindings()...),
		statusBar:   components.NewStatusBar().SetView("Dashboard").SetConnected(client != nil),
	}
}

// Init implements tea.Model.
func (m Model) Init() tea.Cmd {
	m.initialised[ViewDashboard] = true
	return m.dashboard.Init()
}

// Update implements tea.Model.
func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
		bodyH := msg.Height - 10 // reserve header + helpbar + statusbar
		m.statusBar = m.statusBar.SetWidth(msg.Width)
		m.helpBar = m.helpBar.SetWidth(msg.Width)
		m.dashboard = m.dashboard.SetSize(msg.Width, bodyH)
		m.projects = m.projects.SetSize(msg.Width, bodyH)
		m.stories = m.stories.SetSize(msg.Width, bodyH)
		m.tasks = m.tasks.SetSize(msg.Width, bodyH)
		m.ceremonies = m.ceremonies.SetSize(msg.Width, bodyH)
		m.events = m.events.SetSize(msg.Width, bodyH)
		m.enrollment = m.enrollment.SetSize(msg.Width, bodyH)
		m.decisions = m.decisions.SetSize(msg.Width, bodyH)

	case tea.KeyMsg:
		// Global key bindings handled before view-specific ones.
		if key.Matches(msg, m.keys.Quit) {
			m.events.Stop()
			return m, tea.Quit
		}

		// View navigation shortcuts (only from dashboard).
		if m.currentView == ViewDashboard {
			var nextView View
			switch msg.String() {
			case "p":
				nextView = ViewProjects
			case "s":
				nextView = ViewStories
			case "t":
				nextView = ViewTasks
			case "c":
				nextView = ViewCeremonies
			case "e":
				nextView = ViewEvents
			default:
				// Fall through to delegate to dashboard.
				goto delegate
			}
			return m.switchView(nextView)
		}

		// Navigate to decisions from ceremonies detail (key "d").
		if m.currentView == ViewCeremonies && msg.String() == "d" {
			return m.switchView(ViewDecisions)
		}

		// Back to dashboard from any sub-view.
		if key.Matches(msg, m.keys.Back) && m.currentView != ViewDashboard {
			// From decisions, go back to ceremonies.
			if m.currentView == ViewDecisions {
				return m.switchView(ViewCeremonies)
			}
			if m.currentView == ViewEvents {
				m.events.Stop()
			}
			return m.switchView(ViewDashboard)
		}
	}

delegate:
	// Delegate to the active sub-model.
	return m.delegateUpdate(msg)
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
	}

	return m, cmd
}

// activeBindings returns the help bindings for the current view.
func (m Model) activeBindings() []components.HelpBinding {
	switch m.currentView {
	case ViewCeremonies:
		return m.ceremonies.HelpBindings()
	case ViewStories:
		return m.stories.HelpBindings()
	case ViewTasks:
		return m.tasks.HelpBindings()
	case ViewDecisions:
		return m.decisions.HelpBindings()
	default:
		return dashboardBindings()
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
		{Key: "q", Description: "quit"},
	}
}
