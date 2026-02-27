package views

import (
	"context"
	"fmt"
	"strconv"
	"strings"

	"github.com/charmbracelet/bubbles/spinner"
	"github.com/charmbracelet/bubbles/table"
	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/google/uuid"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/tui/components"
)

// ---------------------------------------------------------------------------
// Internal messages
// ---------------------------------------------------------------------------

type tasksForStoryLoadedMsg struct {
	tasks []domain.TaskSummary
	total int32
}
type taskInStoryCreatedMsg struct{ task domain.TaskSummary }
type storyDetailErrMsg struct{ err error }

// ---------------------------------------------------------------------------
// Model
// ---------------------------------------------------------------------------

// StoryDetailModel is the sub-model for the story detail view.
type StoryDetailModel struct {
	client  ports.FleetClient
	story   domain.StorySummary
	epic    domain.EpicSummary
	project domain.ProjectSummary
	tasks   []domain.TaskSummary
	table   table.Model

	// Create-task form state (4 fields: title, description, type, priority)
	creating       bool
	titleInput     textinput.Model
	descInput      textinput.Model
	typeInput      textinput.Model
	priorityInput  textinput.Model
	createFocusIdx int // 0..3

	spinner spinner.Model
	loading bool
	err     error
	width   int
	height  int
}

// NewStoryDetailModel creates a StoryDetailModel for the given story.
func NewStoryDetailModel(client ports.FleetClient, story domain.StorySummary, epic domain.EpicSummary, project domain.ProjectSummary) StoryDetailModel {
	cols := storyDetailTaskColumns()
	t := components.NewTable(cols, nil, 10)

	titleIn := textinput.New()
	titleIn.Placeholder = "Task title"
	titleIn.CharLimit = 120
	titleIn.Width = 40

	descIn := textinput.New()
	descIn.Placeholder = "Description"
	descIn.CharLimit = 256
	descIn.Width = 60

	typeIn := textinput.New()
	typeIn.Placeholder = "Type (e.g. coding, review, testing)"
	typeIn.CharLimit = 40
	typeIn.Width = 40

	prioIn := textinput.New()
	prioIn.Placeholder = "Priority (0-9, default 0)"
	prioIn.CharLimit = 2
	prioIn.Width = 10

	return StoryDetailModel{
		client:        client,
		story:         story,
		epic:          epic,
		project:       project,
		table:         t,
		titleInput:    titleIn,
		descInput:     descIn,
		typeInput:     typeIn,
		priorityInput: prioIn,
		spinner:       components.NewSpinner(),
	}
}

func storyDetailTaskColumns() []table.Column {
	return []table.Column{
		{Title: "ID", Width: 12},
		{Title: "Title", Width: 24},
		{Title: "Type", Width: 10},
		{Title: "Status", Width: 10},
		{Title: "Assignee", Width: 14},
		{Title: "Pri", Width: 4},
		{Title: "Created", Width: 20},
	}
}

// SetSize updates the available layout dimensions.
func (m StoryDetailModel) SetSize(w, h int) StoryDetailModel {
	m.width = w
	m.height = h
	tblH := max(h-16, 4)
	m.table.SetHeight(tblH)
	return m
}

// ---------------------------------------------------------------------------
// tea.Model interface
// ---------------------------------------------------------------------------

// Init fires the initial data load.
func (m StoryDetailModel) Init() tea.Cmd {
	return tea.Batch(m.spinner.Tick, m.loadTasks())
}

// Update handles messages for the story detail view.
func (m StoryDetailModel) Update(msg tea.Msg) (StoryDetailModel, tea.Cmd) {
	var cmds []tea.Cmd

	switch msg := msg.(type) {

	// --- data messages ---------------------------------------------------
	case tasksForStoryLoadedMsg:
		m.loading = false
		m.err = nil
		m.tasks = msg.tasks
		m.table.SetRows(storyDetailTaskRows(m.tasks))
		return m, nil

	case taskInStoryCreatedMsg:
		m.loading = false
		m.creating = false
		m.err = nil
		m.titleInput.Reset()
		m.descInput.Reset()
		m.typeInput.Reset()
		m.priorityInput.Reset()
		return m, m.loadTasks()

	case storyDetailErrMsg:
		m.loading = false
		m.err = msg.err
		return m, nil

	// --- spinner ---------------------------------------------------------
	case spinner.TickMsg:
		var cmd tea.Cmd
		m.spinner, cmd = m.spinner.Update(msg)
		return m, cmd

	// --- keyboard --------------------------------------------------------
	case tea.KeyMsg:
		if m.creating {
			return m.updateCreateForm(msg)
		}

		switch msg.String() {
		case "n":
			m.creating = true
			m.createFocusIdx = 0
			m.titleInput.Focus()
			m.descInput.Blur()
			m.typeInput.Blur()
			m.priorityInput.Blur()
			return m, textinput.Blink
		case "r":
			m.loading = true
			return m, tea.Batch(m.spinner.Tick, m.loadTasks())
		case "esc":
			return m, func() tea.Msg { return BackToEpicDetailMsg{} }
		}

		// Delegate to table for navigation.
		var cmd tea.Cmd
		m.table, cmd = m.table.Update(msg)
		cmds = append(cmds, cmd)
	}

	return m, tea.Batch(cmds...)
}

// updateCreateForm handles key events while the create-task form is active.
func (m StoryDetailModel) updateCreateForm(msg tea.KeyMsg) (StoryDetailModel, tea.Cmd) {
	switch msg.String() {
	case "esc":
		m.creating = false
		m.titleInput.Reset()
		m.descInput.Reset()
		m.typeInput.Reset()
		m.priorityInput.Reset()
		return m, nil

	case "tab", "shift+tab":
		m.blurAll()
		m.createFocusIdx = (m.createFocusIdx + 1) % 4
		m.focusCurrent()
		return m, textinput.Blink

	case "enter":
		title := strings.TrimSpace(m.titleInput.Value())
		desc := strings.TrimSpace(m.descInput.Value())
		taskType := strings.TrimSpace(m.typeInput.Value())
		prioStr := strings.TrimSpace(m.priorityInput.Value())

		if title == "" {
			m.err = fmt.Errorf("task title is required")
			return m, nil
		}

		var priority int32
		if prioStr != "" {
			p, err := strconv.Atoi(prioStr)
			if err != nil {
				m.err = fmt.Errorf("priority must be a number")
				return m, nil
			}
			priority = int32(p)
		}

		m.loading = true
		m.err = nil
		return m, tea.Batch(m.spinner.Tick, m.createTask(title, desc, taskType, priority))
	}

	// Forward to the focused input.
	var cmd tea.Cmd
	switch m.createFocusIdx {
	case 0:
		m.titleInput, cmd = m.titleInput.Update(msg)
	case 1:
		m.descInput, cmd = m.descInput.Update(msg)
	case 2:
		m.typeInput, cmd = m.typeInput.Update(msg)
	case 3:
		m.priorityInput, cmd = m.priorityInput.Update(msg)
	}
	return m, cmd
}

func (m *StoryDetailModel) blurAll() {
	m.titleInput.Blur()
	m.descInput.Blur()
	m.typeInput.Blur()
	m.priorityInput.Blur()
}

func (m *StoryDetailModel) focusCurrent() {
	switch m.createFocusIdx {
	case 0:
		m.titleInput.Focus()
	case 1:
		m.descInput.Focus()
	case 2:
		m.typeInput.Focus()
	case 3:
		m.priorityInput.Focus()
	}
}

// View renders the story detail view.
func (m StoryDetailModel) View() string {
	var b strings.Builder

	bc := components.NewBreadcrumb("Home", "Projects", m.project.Name, m.epic.Title, m.story.Title)
	b.WriteString(bc.View())
	b.WriteString("\n\n")

	// Story info card
	b.WriteString(m.storyCardView())
	b.WriteString("\n\n")

	if m.loading {
		b.WriteString(m.spinner.View() + " Loading tasks...")
		return b.String()
	}

	if m.err != nil {
		errStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("210")).Bold(true)
		b.WriteString(errStyle.Render("Error: "+m.err.Error()) + "\n\n")
	}

	if m.creating {
		b.WriteString(m.createFormView())
		return b.String()
	}

	// Tasks section
	b.WriteString(pdHeading.Render("Tasks"))
	b.WriteString("\n\n")

	if len(m.tasks) == 0 {
		b.WriteString(pdDim.Render("No tasks yet. Press n to create one."))
	} else {
		b.WriteString(m.table.View())
	}

	b.WriteString("\n")
	b.WriteString(pdDim.Render("n: new task  r: refresh  esc: back"))

	return b.String()
}

func (m StoryDetailModel) storyCardView() string {
	var lines []string
	lines = append(lines, pdHeading.Render(m.story.Title))
	if m.story.Brief != "" {
		lines = append(lines, pdValue.Render(m.story.Brief))
	}
	lines = append(lines, "")
	lines = append(lines, pdLabel.Render("State: ")+pdValue.Render(m.story.State))
	lines = append(lines, pdLabel.Render("DoR:   ")+pdValue.Render(fmt.Sprintf("%d", m.story.DorScore)))
	if m.story.CreatedBy != "" {
		lines = append(lines, pdLabel.Render("Author: ")+pdValue.Render(m.story.CreatedBy))
	}
	lines = append(lines, pdLabel.Render("Created: ")+pdDim.Render(m.story.CreatedAt))
	if m.story.UpdatedAt != "" {
		lines = append(lines, pdLabel.Render("Updated: ")+pdDim.Render(m.story.UpdatedAt))
	}

	cardWidth := m.width - 4
	if cardWidth < 40 {
		cardWidth = 40
	}
	return pdCard.Width(cardWidth).Render(strings.Join(lines, "\n"))
}

func (m StoryDetailModel) createFormView() string {
	var b strings.Builder

	title := lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("147"))
	hint := lipgloss.NewStyle().Foreground(lipgloss.Color("246"))

	b.WriteString(title.Render("Create New Task"))
	b.WriteString("\n\n")
	b.WriteString("Title:\n")
	b.WriteString(m.titleInput.View())
	b.WriteString("\n\n")
	b.WriteString("Description:\n")
	b.WriteString(m.descInput.View())
	b.WriteString("\n\n")
	b.WriteString("Type:\n")
	b.WriteString(m.typeInput.View())
	b.WriteString("\n\n")
	b.WriteString("Priority:\n")
	b.WriteString(m.priorityInput.View())
	b.WriteString("\n\n")
	b.WriteString(hint.Render("tab: next field  enter: submit  esc: cancel"))

	return b.String()
}

// ---------------------------------------------------------------------------
// Commands
// ---------------------------------------------------------------------------

func (m StoryDetailModel) loadTasks() tea.Cmd {
	return func() tea.Msg {
		tasks, total, err := m.client.ListTasks(context.Background(), m.story.ID, "", 100, 0)
		if err != nil {
			return storyDetailErrMsg{err: err}
		}
		return tasksForStoryLoadedMsg{tasks: tasks, total: total}
	}
}

func (m StoryDetailModel) createTask(title, desc, taskType string, priority int32) tea.Cmd {
	return func() tea.Msg {
		reqID := uuid.NewString()
		t, err := m.client.CreateTask(context.Background(), reqID, m.story.ID, title, desc, taskType, "", 0, priority)
		if err != nil {
			return storyDetailErrMsg{err: err}
		}
		return taskInStoryCreatedMsg{task: t}
	}
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

func storyDetailTaskRows(tasks []domain.TaskSummary) []table.Row {
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
			t.CreatedAt,
		})
	}
	return rows
}
