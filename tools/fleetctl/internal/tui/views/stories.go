package views

import (
	"context"
	"fmt"
	"strings"

	"github.com/charmbracelet/bubbles/spinner"
	"github.com/charmbracelet/bubbles/table"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/tui/components"
)

// ---------------------------------------------------------------------------
// Valid story state transitions
// ---------------------------------------------------------------------------

var storyTransitions = map[string][]string{
	"DRAFT":              {"PO_REVIEW"},
	"PO_REVIEW":          {"DRAFT", "READY_FOR_PLANNING"},
	"READY_FOR_PLANNING": {"IN_PROGRESS"},
	"IN_PROGRESS":        {"DONE"},
	"DONE":               {},
}

// ---------------------------------------------------------------------------
// State filter options
// ---------------------------------------------------------------------------

var storyStateFilters = []string{"ALL", "DRAFT", "PO_REVIEW", "READY_FOR_PLANNING", "IN_PROGRESS", "DONE"}

// ---------------------------------------------------------------------------
// Pastel styles
// ---------------------------------------------------------------------------

var (
	storyHeading  = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("147")) // periwinkle
	storyActive   = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("120")) // mint
	storyInactive = lipgloss.NewStyle().Foreground(lipgloss.Color("252"))
	storyDim      = lipgloss.NewStyle().Foreground(lipgloss.Color("246"))   // warm grey
	storySelected = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("115")) // teal
)

// ---------------------------------------------------------------------------
// Messages
// ---------------------------------------------------------------------------

type storiesLoadedMsg struct {
	stories []domain.StorySummary
	total   int32
}
type storyTransitionedMsg struct{}
type storiesErrMsg struct{ err error }

// ---------------------------------------------------------------------------
// Model
// ---------------------------------------------------------------------------

// StoriesModel is the sub-model for the stories list view.
type StoriesModel struct {
	client  ports.FleetClient
	table   table.Model
	stories []domain.StorySummary
	epicID  string // filter context

	// Pagination + filter
	paginator   components.Paginator
	stateFilter int // index into storyStateFilters

	// Transition selector state
	transitioning bool
	targetStates  []string
	selectedIdx   int

	// Shared
	helpBar components.HelpBar
	spinner spinner.Model
	loading bool
	err     error
	width   int
	height  int
}

// NewStoriesModel creates a StoriesModel wired to the given FleetClient.
func NewStoriesModel(client ports.FleetClient, epicID string) StoriesModel {
	cols := storyColumns()
	t := components.NewTable(cols, nil, 10)

	return StoriesModel{
		client:    client,
		table:     t,
		epicID:    epicID,
		spinner:   components.NewSpinner(),
		paginator: components.NewPaginator(20),
		helpBar:   components.NewHelpBar(storiesBindings()...),
	}
}

func storyColumns() []table.Column {
	return []table.Column{
		{Title: "ID", Width: 12},
		{Title: "Title", Width: 30},
		{Title: "State", Width: 20},
		{Title: "DoR Score", Width: 10},
		{Title: "Created By", Width: 18},
	}
}

// SetSize updates the available layout dimensions.
func (m StoriesModel) SetSize(w, h int) StoriesModel {
	m.width = w
	m.height = h
	tblH := max(h-14, 4)
	m.table.SetHeight(tblH)
	m.helpBar = m.helpBar.SetWidth(w)
	return m
}

// SetEpicID changes the epic filter and returns the updated model.
func (m StoriesModel) SetEpicID(id string) StoriesModel {
	m.epicID = id
	return m
}

// HelpBindings returns the context-specific key hints.
func (m StoriesModel) HelpBindings() []components.HelpBinding {
	if m.transitioning {
		return storyTransitionBindings()
	}
	return storiesBindings()
}

// ---------------------------------------------------------------------------
// tea.Model interface
// ---------------------------------------------------------------------------

func (m StoriesModel) Init() tea.Cmd {
	m.loading = true
	return tea.Batch(m.spinner.Tick, m.loadStories())
}

func (m StoriesModel) Update(msg tea.Msg) (StoriesModel, tea.Cmd) {
	var cmds []tea.Cmd

	switch msg := msg.(type) {

	case storiesLoadedMsg:
		m.loading = false
		m.err = nil
		m.stories = msg.stories
		m.paginator = m.paginator.SetTotal(msg.total)
		m.table.SetRows(storyRows(m.stories))
		return m, nil

	case storyTransitionedMsg:
		m.loading = false
		m.transitioning = false
		m.err = nil
		m.helpBar = m.helpBar.SetBindings(m.HelpBindings()...)
		return m, m.loadStories()

	case storiesErrMsg:
		m.loading = false
		m.err = msg.err
		return m, nil

	case spinner.TickMsg:
		var cmd tea.Cmd
		m.spinner, cmd = m.spinner.Update(msg)
		return m, cmd

	case tea.KeyMsg:
		if m.transitioning {
			return m.updateTransitionSelector(msg)
		}

		switch msg.String() {
		case "t":
			return m.enterTransitionMode()
		case "f":
			m.stateFilter = (m.stateFilter + 1) % len(storyStateFilters)
			m.loading = true
			return m, tea.Batch(m.spinner.Tick, m.loadStories())
		case "r":
			m.loading = true
			return m, tea.Batch(m.spinner.Tick, m.loadStories())
		case "left", "h":
			m.paginator = m.paginator.PrevPage()
			m.loading = true
			return m, tea.Batch(m.spinner.Tick, m.loadStories())
		case "right", "l":
			m.paginator = m.paginator.NextPage()
			m.loading = true
			return m, tea.Batch(m.spinner.Tick, m.loadStories())
		}

		var cmd tea.Cmd
		m.table, cmd = m.table.Update(msg)
		cmds = append(cmds, cmd)
	}

	return m, tea.Batch(cmds...)
}

// enterTransitionMode prepares the state transition selector for the
// currently selected story.
func (m StoriesModel) enterTransitionMode() (StoriesModel, tea.Cmd) {
	row := m.table.SelectedRow()
	if row == nil || len(m.stories) == 0 {
		return m, nil
	}

	selectedID := row[0]
	var currentState string
	for _, s := range m.stories {
		id := s.ID
		if len(id) > 12 {
			id = id[:12]
		}
		if id == selectedID {
			currentState = s.State
			break
		}
	}

	targets, ok := storyTransitions[currentState]
	if !ok || len(targets) == 0 {
		m.err = fmt.Errorf("no valid transitions from state %q", currentState)
		return m, nil
	}

	m.transitioning = true
	m.targetStates = targets
	m.selectedIdx = 0
	m.helpBar = m.helpBar.SetBindings(m.HelpBindings()...)
	return m, nil
}

func (m StoriesModel) updateTransitionSelector(msg tea.KeyMsg) (StoriesModel, tea.Cmd) {
	switch msg.String() {
	case "esc":
		m.transitioning = false
		m.helpBar = m.helpBar.SetBindings(m.HelpBindings()...)
		return m, nil

	case "up", "k":
		if m.selectedIdx > 0 {
			m.selectedIdx--
		}
		return m, nil

	case "down", "j":
		if m.selectedIdx < len(m.targetStates)-1 {
			m.selectedIdx++
		}
		return m, nil

	case "enter":
		row := m.table.SelectedRow()
		if row == nil {
			m.transitioning = false
			return m, nil
		}
		selectedID := row[0]
		var fullID string
		for _, s := range m.stories {
			id := s.ID
			if len(id) > 12 {
				id = id[:12]
			}
			if id == selectedID {
				fullID = s.ID
				break
			}
		}
		if fullID == "" {
			m.transitioning = false
			m.err = fmt.Errorf("could not resolve story ID")
			return m, nil
		}
		target := m.targetStates[m.selectedIdx]
		m.loading = true
		return m, tea.Batch(m.spinner.Tick, m.transitionStory(fullID, target))
	}

	return m, nil
}

// ---------------------------------------------------------------------------
// View
// ---------------------------------------------------------------------------

func (m StoriesModel) View() string {
	var b strings.Builder

	crumbs := []string{"Home", "Stories"}
	if m.epicID != "" {
		crumbs = append(crumbs, "Epic:"+m.epicID)
	}
	bc := components.NewBreadcrumb(crumbs...)
	b.WriteString(bc.View())
	b.WriteString("\n\n")

	// State filter
	filterLabel := storyDim.Render("Filter: ")
	filterValue := storySelected.Render(storyStateFilters[m.stateFilter])
	b.WriteString(filterLabel + filterValue + "\n\n")

	if m.loading {
		b.WriteString(m.spinner.View() + " " + storyDim.Render("Loading stories..."))
		return b.String()
	}

	if m.err != nil {
		errStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("210")).Bold(true)
		b.WriteString(errStyle.Render("Error: "+m.err.Error()) + "\n\n")
	}

	// FSM diagram for selected story.
	row := m.table.SelectedRow()
	if len(row) > 2 {
		b.WriteString(components.RenderFSMDiagram(row[2]))
		b.WriteString("\n")
	}

	if m.transitioning {
		b.WriteString(m.transitionView())
		return b.String()
	}

	if len(m.stories) == 0 {
		b.WriteString(storyDim.Render("No stories found."))
		return b.String()
	}

	b.WriteString(m.table.View())
	b.WriteString("\n")
	b.WriteString(m.paginator.View())
	b.WriteString("\n")
	b.WriteString(m.helpBar.View())

	return b.String()
}

func (m StoriesModel) transitionView() string {
	var b strings.Builder

	b.WriteString(storyHeading.Render("Select target state:"))
	b.WriteString("\n\n")

	for i, state := range m.targetStates {
		cursor := "  "
		style := storyInactive
		if i == m.selectedIdx {
			cursor = storySelected.Render("> ")
			style = storyActive
		}
		b.WriteString(cursor + style.Render(state) + "\n")
	}

	b.WriteString("\n")
	b.WriteString(storyDim.Render("enter: confirm  esc: cancel"))

	return b.String()
}

// ---------------------------------------------------------------------------
// Commands
// ---------------------------------------------------------------------------

func (m StoriesModel) loadStories() tea.Cmd {
	filter := ""
	if m.stateFilter > 0 {
		filter = storyStateFilters[m.stateFilter]
	}
	limit := m.paginator.Limit()
	offset := m.paginator.Offset()
	epicID := m.epicID
	return func() tea.Msg {
		stories, total, err := m.client.ListStories(context.Background(), epicID, filter, limit, offset)
		if err != nil {
			return storiesErrMsg{err: err}
		}
		return storiesLoadedMsg{stories: stories, total: total}
	}
}

func (m StoriesModel) transitionStory(storyID, targetState string) tea.Cmd {
	return func() tea.Msg {
		err := m.client.TransitionStory(context.Background(), storyID, targetState)
		if err != nil {
			return storiesErrMsg{err: err}
		}
		return storyTransitionedMsg{}
	}
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

func storyRows(stories []domain.StorySummary) []table.Row {
	rows := make([]table.Row, 0, len(stories))
	for _, s := range stories {
		id := s.ID
		if len(id) > 12 {
			id = id[:12]
		}
		rows = append(rows, table.Row{
			id,
			s.Title,
			s.State,
			fmt.Sprintf("%d", s.DorScore),
			s.CreatedBy,
		})
	}
	return rows
}

// ---------------------------------------------------------------------------
// Help binding presets
// ---------------------------------------------------------------------------

func storiesBindings() []components.HelpBinding {
	return []components.HelpBinding{
		{Key: "t", Description: "transition"},
		{Key: "f", Description: "filter"},
		{Key: "<</>>" , Description: "page"},
		{Key: "r", Description: "refresh"},
		{Key: "esc", Description: "back"},
	}
}

func storyTransitionBindings() []components.HelpBinding {
	return []components.HelpBinding{
		{Key: "j/k", Description: "navigate"},
		{Key: "enter", Description: "confirm"},
		{Key: "esc", Description: "cancel"},
	}
}
