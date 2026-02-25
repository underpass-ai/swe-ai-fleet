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
// Status filter options
// ---------------------------------------------------------------------------

var taskStatusFilters = []string{"ALL", "PENDING", "IN_PROGRESS", "COMPLETED"}

// ---------------------------------------------------------------------------
// Pastel styles
// ---------------------------------------------------------------------------

var (
	taskDim      = lipgloss.NewStyle().Foreground(lipgloss.Color("246"))            // warm grey
	taskSelected = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("115")) // teal
)

// ---------------------------------------------------------------------------
// Messages
// ---------------------------------------------------------------------------

type tasksLoadedMsg struct {
	tasks []domain.TaskSummary
	total int32
}
type tasksErrMsg struct{ err error }

// ---------------------------------------------------------------------------
// Model
// ---------------------------------------------------------------------------

// TasksModel is the sub-model for the tasks list view.
type TasksModel struct {
	client  ports.FleetClient
	table   table.Model
	tasks   []domain.TaskSummary
	storyID string

	// Pagination + filter
	paginator    components.Paginator
	statusFilter int // index into taskStatusFilters

	// Shared
	helpBar components.HelpBar
	spinner spinner.Model
	loading bool
	err     error
	width   int
	height  int
}

// NewTasksModel creates a TasksModel wired to the given FleetClient.
func NewTasksModel(client ports.FleetClient, storyID string) TasksModel {
	cols := taskColumns()
	t := components.NewTable(cols, nil, 10)

	return TasksModel{
		client:    client,
		table:     t,
		storyID:   storyID,
		spinner:   components.NewSpinner(),
		paginator: components.NewPaginator(20),
		helpBar:   components.NewHelpBar(tasksBindings()...),
	}
}

func taskColumns() []table.Column {
	return []table.Column{
		{Title: "ID", Width: 12},
		{Title: "Title", Width: 28},
		{Title: "Type", Width: 12},
		{Title: "Status", Width: 14},
		{Title: "Assigned To", Width: 18},
		{Title: "Priority", Width: 8},
	}
}

// SetSize updates the available layout dimensions.
func (m TasksModel) SetSize(w, h int) TasksModel {
	m.width = w
	m.height = h
	tblH := max(h-12, 4)
	m.table.SetHeight(tblH)
	m.helpBar = m.helpBar.SetWidth(w)
	return m
}

// SetStoryID changes the story filter and returns the updated model.
func (m TasksModel) SetStoryID(id string) TasksModel {
	m.storyID = id
	return m
}

// HelpBindings returns the context-specific key hints.
func (m TasksModel) HelpBindings() []components.HelpBinding {
	return tasksBindings()
}

// ---------------------------------------------------------------------------
// tea.Model interface
// ---------------------------------------------------------------------------

func (m TasksModel) Init() tea.Cmd {
	m.loading = true
	return tea.Batch(m.spinner.Tick, m.loadTasks())
}

func (m TasksModel) Update(msg tea.Msg) (TasksModel, tea.Cmd) {
	var cmds []tea.Cmd

	switch msg := msg.(type) {

	case tasksLoadedMsg:
		m.loading = false
		m.err = nil
		m.tasks = msg.tasks
		m.paginator = m.paginator.SetTotal(msg.total)
		m.table.SetRows(taskRows(m.tasks))
		return m, nil

	case tasksErrMsg:
		m.loading = false
		m.err = msg.err
		return m, nil

	case spinner.TickMsg:
		var cmd tea.Cmd
		m.spinner, cmd = m.spinner.Update(msg)
		return m, cmd

	case tea.KeyMsg:
		switch msg.String() {
		case "f":
			m.statusFilter = (m.statusFilter + 1) % len(taskStatusFilters)
			m.loading = true
			return m, tea.Batch(m.spinner.Tick, m.loadTasks())
		case "r":
			m.loading = true
			return m, tea.Batch(m.spinner.Tick, m.loadTasks())
		case "left", "h":
			m.paginator = m.paginator.PrevPage()
			m.loading = true
			return m, tea.Batch(m.spinner.Tick, m.loadTasks())
		case "right", "l":
			m.paginator = m.paginator.NextPage()
			m.loading = true
			return m, tea.Batch(m.spinner.Tick, m.loadTasks())
		}

		var cmd tea.Cmd
		m.table, cmd = m.table.Update(msg)
		cmds = append(cmds, cmd)
	}

	return m, tea.Batch(cmds...)
}

// ---------------------------------------------------------------------------
// View
// ---------------------------------------------------------------------------

func (m TasksModel) View() string {
	var b strings.Builder

	crumbs := []string{"Home", "Tasks"}
	if m.storyID != "" {
		crumbs = append(crumbs, "Story:"+m.storyID)
	}
	bc := components.NewBreadcrumb(crumbs...)
	b.WriteString(bc.View())
	b.WriteString("\n\n")

	// Status filter
	filterLabel := taskDim.Render("Filter: ")
	filterValue := taskSelected.Render(taskStatusFilters[m.statusFilter])
	b.WriteString(filterLabel + filterValue + "\n\n")

	if m.loading {
		b.WriteString(m.spinner.View() + " " + taskDim.Render("Loading tasks..."))
		return b.String()
	}

	if m.err != nil {
		errStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("210")).Bold(true)
		b.WriteString(errStyle.Render("Error: "+m.err.Error()) + "\n\n")
	}

	if len(m.tasks) == 0 {
		b.WriteString(taskDim.Render("No tasks found."))
		return b.String()
	}

	b.WriteString(m.table.View())
	b.WriteString("\n")
	b.WriteString(m.paginator.View())
	b.WriteString("\n")
	b.WriteString(m.helpBar.View())

	return b.String()
}

// ---------------------------------------------------------------------------
// Commands
// ---------------------------------------------------------------------------

func (m TasksModel) loadTasks() tea.Cmd {
	filter := ""
	if m.statusFilter > 0 {
		filter = taskStatusFilters[m.statusFilter]
	}
	limit := m.paginator.Limit()
	offset := m.paginator.Offset()
	storyID := m.storyID
	return func() tea.Msg {
		tasks, total, err := m.client.ListTasks(context.Background(), storyID, filter, limit, offset)
		if err != nil {
			return tasksErrMsg{err: err}
		}
		return tasksLoadedMsg{tasks: tasks, total: total}
	}
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

func taskRows(tasks []domain.TaskSummary) []table.Row {
	rows := make([]table.Row, 0, len(tasks))
	for _, t := range tasks {
		id := t.ID
		if len(id) > 12 {
			id = id[:12]
		}
		rows = append(rows, table.Row{
			id,
			t.Title,
			t.Type,
			t.Status,
			t.AssignedTo,
			fmt.Sprintf("%d", t.Priority),
		})
	}
	return rows
}

// ---------------------------------------------------------------------------
// Help binding presets
// ---------------------------------------------------------------------------

func tasksBindings() []components.HelpBinding {
	return []components.HelpBinding{
		{Key: "f", Description: "filter"},
		{Key: "<</>>" , Description: "page"},
		{Key: "r", Description: "refresh"},
		{Key: "esc", Description: "back"},
	}
}
