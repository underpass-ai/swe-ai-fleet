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

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/command"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/query"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/tui/components"
)

// ---------------------------------------------------------------------------
// Status filter options
// ---------------------------------------------------------------------------

var projectStatusFilters = []string{"ALL", "ACTIVE", "ARCHIVED", "DRAFT"}

// ---------------------------------------------------------------------------
// Messages
// ---------------------------------------------------------------------------

type projectsLoadedMsg struct {
	projects []domain.ProjectSummary
	total    int32
}
type projectCreatedMsg struct{ project domain.ProjectSummary }
type projectsErrMsg struct{ err error }

// ---------------------------------------------------------------------------
// Model
// ---------------------------------------------------------------------------

// ProjectsModel is the sub-model for the projects list view.
type ProjectsModel struct {
	createProject *command.CreateProjectHandler
	listProjects  *query.ListProjectsHandler
	table         table.Model
	projects []domain.ProjectSummary

	// Status filter (client-side)
	statusFilter int // index into projectStatusFilters

	// Search (client-side)
	searching   bool
	searchInput textinput.Model
	searchTerm  string

	// Pagination
	paginator components.Paginator

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

// NewProjectsModel creates a ProjectsModel wired to the given handlers.
func NewProjectsModel(createProject *command.CreateProjectHandler, listProjects *query.ListProjectsHandler) ProjectsModel {
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

	searchIn := textinput.New()
	searchIn.Placeholder = "search projects..."
	searchIn.CharLimit = 120
	searchIn.Width = 40

	return ProjectsModel{
		createProject: createProject,
		listProjects:  listProjects,
		table:         t,
		searchInput:   searchIn,
		paginator:     components.NewPaginator(20),
		nameInput:     nameIn,
		descInput:     descIn,
		spinner:       components.NewSpinner(),
		loading:       true,
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
		m.paginator = m.paginator.SetTotal(msg.total)
		m.table.SetRows(m.filteredProjectRows())
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
		if m.searching {
			return m.updateSearch(msg)
		}
		if m.creating {
			return m.updateCreateForm(msg)
		}
		return m.handleNormalKey(msg)
	}

	return m, tea.Batch(cmds...)
}

func (m ProjectsModel) handleNormalKey(msg tea.KeyMsg) (ProjectsModel, tea.Cmd) {
	switch msg.String() {
	case "/":
		m.searching = true
		m.searchInput.Focus()
		return m, textinput.Blink
	case "enter":
		if len(m.projects) > 0 {
			row := m.table.SelectedRow()
			if row != nil {
				proj := m.selectedProject(row[0])
				if proj != nil {
					return m, func() tea.Msg { return ProjectSelectedMsg{Project: *proj} }
				}
			}
		}
	case "n":
		m.creating = true
		m.focusIdx = 0
		m.nameInput.Focus()
		m.descInput.Blur()
		return m, textinput.Blink
	case "f":
		m.statusFilter = (m.statusFilter + 1) % len(projectStatusFilters)
		m.paginator = components.NewPaginator(int(m.paginator.Limit()))
		m.loading = true
		return m, tea.Batch(m.spinner.Tick, m.loadProjects())
	case "left", "h":
		m.paginator = m.paginator.PrevPage()
		m.loading = true
		return m, tea.Batch(m.spinner.Tick, m.loadProjects())
	case "right", "l":
		m.paginator = m.paginator.NextPage()
		m.loading = true
		return m, tea.Batch(m.spinner.Tick, m.loadProjects())
	case "r":
		m.loading = true
		return m, tea.Batch(m.spinner.Tick, m.loadProjects())
	}

	// Delegate to table for navigation.
	var cmd tea.Cmd
	m.table, cmd = m.table.Update(msg)
	return m, cmd
}

// updateSearch handles key events in search mode.
func (m ProjectsModel) updateSearch(msg tea.KeyMsg) (ProjectsModel, tea.Cmd) {
	switch msg.String() {
	case "esc":
		m.searching = false
		m.searchInput.Reset()
		m.searchTerm = ""
		m.searchInput.Blur()
		m.table.SetRows(m.filteredProjectRows())
		return m, nil
	case "enter":
		m.searching = false
		m.searchTerm = strings.ToLower(strings.TrimSpace(m.searchInput.Value()))
		m.searchInput.Blur()
		m.table.SetRows(m.filteredProjectRows())
		return m, nil
	}
	var cmd tea.Cmd
	m.searchInput, cmd = m.searchInput.Update(msg)
	m.searchTerm = strings.ToLower(strings.TrimSpace(m.searchInput.Value()))
	m.table.SetRows(m.filteredProjectRows())
	return m, cmd
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
		return m, tea.Batch(m.spinner.Tick, m.doCreateProject(name, desc))
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

	// Status filter + search
	filterDim := lipgloss.NewStyle().Foreground(lipgloss.Color("246"))
	filterSel := lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("115"))
	b.WriteString(filterDim.Render("Filter: ") + filterSel.Render(projectStatusFilters[m.statusFilter]))
	if m.searching {
		b.WriteString("  " + filterDim.Render("/") + " " + m.searchInput.View())
	} else if m.searchTerm != "" {
		b.WriteString("  " + filterDim.Render("Search: ") + filterSel.Render(m.searchTerm))
	}
	b.WriteString("\n\n")

	if len(m.filteredProjects()) == 0 {
		dim := lipgloss.NewStyle().Foreground(lipgloss.Color("246"))
		b.WriteString(dim.Render("No projects match the filter. Press n to create one or f to change filter."))
		return b.String()
	}

	b.WriteString(m.table.View())
	b.WriteString("\n")
	b.WriteString(m.paginator.View())
	b.WriteString("\n")

	hint := lipgloss.NewStyle().Foreground(lipgloss.Color("246"))
	b.WriteString(hint.Render("enter: open  n: new  /: search  f: filter  <</>>: page  r: refresh  esc: back"))

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
	handler := m.listProjects
	limit := m.paginator.Limit()
	offset := m.paginator.Offset()
	statusFilter := m.serverStatusFilter()
	return func() tea.Msg {
		projects, total, err := handler.Handle(context.Background(), statusFilter, limit, offset)
		if err != nil {
			return projectsErrMsg{err: err}
		}
		return projectsLoadedMsg{projects: projects, total: total}
	}
}

func (m ProjectsModel) doCreateProject(name, desc string) tea.Cmd {
	handler := m.createProject
	return func() tea.Msg {
		p, err := handler.Handle(context.Background(), command.CreateProjectCmd{
			Name:        name,
			Description: desc,
		})
		if err != nil {
			return projectsErrMsg{err: err}
		}
		return projectCreatedMsg{project: p}
	}
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

func (m ProjectsModel) selectedProject(idPrefix string) *domain.ProjectSummary {
	for i := range m.projects {
		id := m.projects[i].ID
		if len(id) > 12 {
			id = id[:12]
		}
		if id == idPrefix {
			return &m.projects[i]
		}
	}
	return nil
}

// serverStatusFilter returns the status string to send to the server.
// Returns "" when the filter is ALL (index 0) so the server returns everything.
func (m ProjectsModel) serverStatusFilter() string {
	if m.statusFilter == 0 {
		return ""
	}
	return strings.ToUpper(projectStatusFilters[m.statusFilter])
}

func (m ProjectsModel) filteredProjects() []domain.ProjectSummary {
	// Status filtering is now server-side; only apply client-side text search.
	if m.searchTerm == "" {
		return m.projects
	}
	filtered := make([]domain.ProjectSummary, 0, len(m.projects))
	for _, p := range m.projects {
		if strings.Contains(strings.ToLower(p.Name), m.searchTerm) ||
			strings.Contains(strings.ToLower(p.Description), m.searchTerm) {
			filtered = append(filtered, p)
		}
	}
	return filtered
}

func (m ProjectsModel) filteredProjectRows() []table.Row {
	return projectRows(m.filteredProjects())
}

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
