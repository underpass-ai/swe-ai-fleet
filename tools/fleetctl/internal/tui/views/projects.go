package views

import (
	"context"
	"fmt"
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
// Messages
// ---------------------------------------------------------------------------

type projectsLoadedMsg struct{ projects []domain.ProjectSummary }
type projectCreatedMsg struct{ project domain.ProjectSummary }
type projectsErrMsg struct{ err error }

// ---------------------------------------------------------------------------
// Model
// ---------------------------------------------------------------------------

// ProjectsModel is the sub-model for the projects list view.
type ProjectsModel struct {
	client   ports.FleetClient
	table    table.Model
	projects []domain.ProjectSummary

	// Create-form state
	creating  bool
	nameInput textinput.Model
	descInput textinput.Model
	focusIdx  int // 0 = name, 1 = desc

	spinner spinner.Model
	loading bool
	err     error
	width   int
	height  int
}

// NewProjectsModel creates a ProjectsModel wired to the given FleetClient.
func NewProjectsModel(client ports.FleetClient) ProjectsModel {
	cols := projectColumns()
	t := components.NewTable(cols, nil, 10)

	nameIn := textinput.New()
	nameIn.Placeholder = "Project name"
	nameIn.CharLimit = 120
	nameIn.Width = 40

	descIn := textinput.New()
	descIn.Placeholder = "Short description"
	descIn.CharLimit = 256
	descIn.Width = 60

	return ProjectsModel{
		client:    client,
		table:     t,
		nameInput: nameIn,
		descInput: descIn,
		spinner:   components.NewSpinner(),
	}
}

func projectColumns() []table.Column {
	return []table.Column{
		{Title: "ID", Width: 12},
		{Title: "Name", Width: 24},
		{Title: "Status", Width: 14},
		{Title: "Owner", Width: 18},
		{Title: "Created", Width: 20},
	}
}

// SetSize updates the available layout dimensions.
func (m ProjectsModel) SetSize(w, h int) ProjectsModel {
	m.width = w
	m.height = h
	tblH := max(h-8, 4) // leave room for header/footer
	m.table.SetHeight(tblH)
	return m
}

// ---------------------------------------------------------------------------
// tea.Model interface
// ---------------------------------------------------------------------------

// Init fires the initial data load.
func (m ProjectsModel) Init() tea.Cmd {
	return tea.Batch(m.spinner.Tick, m.loadProjects())
}

// Update handles messages for the projects view.
func (m ProjectsModel) Update(msg tea.Msg) (ProjectsModel, tea.Cmd) {
	var cmds []tea.Cmd

	switch msg := msg.(type) {

	// --- data messages ---------------------------------------------------
	case projectsLoadedMsg:
		m.loading = false
		m.err = nil
		m.projects = msg.projects
		m.table.SetRows(projectRows(m.projects))
		return m, nil

	case projectCreatedMsg:
		m.loading = false
		m.creating = false
		m.err = nil
		m.nameInput.Reset()
		m.descInput.Reset()
		// Refresh the list to include the new project.
		return m, m.loadProjects()

	case projectsErrMsg:
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
			m.focusIdx = 0
			m.nameInput.Focus()
			m.descInput.Blur()
			return m, textinput.Blink
		case "r":
			m.loading = true
			return m, tea.Batch(m.spinner.Tick, m.loadProjects())
		}

		// Delegate to table for navigation.
		var cmd tea.Cmd
		m.table, cmd = m.table.Update(msg)
		cmds = append(cmds, cmd)
	}

	return m, tea.Batch(cmds...)
}

// updateCreateForm handles key events while the create-project form is active.
func (m ProjectsModel) updateCreateForm(msg tea.KeyMsg) (ProjectsModel, tea.Cmd) {
	switch msg.String() {
	case "esc":
		m.creating = false
		m.nameInput.Reset()
		m.descInput.Reset()
		return m, nil

	case "tab", "shift+tab":
		if m.focusIdx == 0 {
			m.focusIdx = 1
			m.nameInput.Blur()
			m.descInput.Focus()
		} else {
			m.focusIdx = 0
			m.nameInput.Focus()
			m.descInput.Blur()
		}
		return m, textinput.Blink

	case "enter":
		name := strings.TrimSpace(m.nameInput.Value())
		desc := strings.TrimSpace(m.descInput.Value())
		if name == "" {
			m.err = fmt.Errorf("project name is required")
			return m, nil
		}
		m.loading = true
		m.err = nil
		return m, tea.Batch(m.spinner.Tick, m.createProject(name, desc))
	}

	// Forward to the focused input.
	var cmd tea.Cmd
	if m.focusIdx == 0 {
		m.nameInput, cmd = m.nameInput.Update(msg)
	} else {
		m.descInput, cmd = m.descInput.Update(msg)
	}
	return m, cmd
}

// View renders the projects view.
func (m ProjectsModel) View() string {
	var b strings.Builder

	bc := components.NewBreadcrumb("Home", "Projects")
	b.WriteString(bc.View())
	b.WriteString("\n\n")

	if m.loading {
		b.WriteString(m.spinner.View() + " Loading projects...")
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

	if len(m.projects) == 0 {
		dim := lipgloss.NewStyle().Foreground(lipgloss.Color("246"))
		b.WriteString(dim.Render("No projects found. Press n to create one."))
		return b.String()
	}

	b.WriteString(m.table.View())
	b.WriteString("\n")

	hint := lipgloss.NewStyle().Foreground(lipgloss.Color("246"))
	b.WriteString(hint.Render("n: new project  r: refresh  esc: back"))

	return b.String()
}

func (m ProjectsModel) createFormView() string {
	var b strings.Builder

	title := lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("147")) // periwinkle
	hint := lipgloss.NewStyle().Foreground(lipgloss.Color("246"))            // warm grey

	b.WriteString(title.Render("Create New Project"))
	b.WriteString("\n\n")
	b.WriteString("Name:\n")
	b.WriteString(m.nameInput.View())
	b.WriteString("\n\n")
	b.WriteString("Description:\n")
	b.WriteString(m.descInput.View())
	b.WriteString("\n\n")
	b.WriteString(hint.Render("tab: next field  enter: submit  esc: cancel"))

	return b.String()
}

// ---------------------------------------------------------------------------
// Commands
// ---------------------------------------------------------------------------

func (m ProjectsModel) loadProjects() tea.Cmd {
	return func() tea.Msg {
		m.loading = true
		projects, err := m.client.ListProjects(context.Background())
		if err != nil {
			return projectsErrMsg{err: err}
		}
		return projectsLoadedMsg{projects: projects}
	}
}

func (m ProjectsModel) createProject(name, desc string) tea.Cmd {
	return func() tea.Msg {
		reqID := uuid.NewString()
		p, err := m.client.CreateProject(context.Background(), reqID, name, desc)
		if err != nil {
			return projectsErrMsg{err: err}
		}
		return projectCreatedMsg{project: p}
	}
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

func projectRows(projects []domain.ProjectSummary) []table.Row {
	rows := make([]table.Row, 0, len(projects))
	for _, p := range projects {
		id := p.ID
		if len(id) > 12 {
			id = id[:12]
		}
		rows = append(rows, table.Row{id, p.Name, p.Status, p.Owner, p.CreatedAt})
	}
	return rows
}
