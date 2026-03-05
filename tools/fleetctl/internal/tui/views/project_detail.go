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
// Navigation messages (handled by app.go)
// ---------------------------------------------------------------------------

// ProjectSelectedMsg is emitted when the user presses Enter on a project.
type ProjectSelectedMsg struct{ Project domain.ProjectSummary }

// BackToProjectsMsg is emitted when the user presses Esc in project detail.
type BackToProjectsMsg struct{}

// EpicSelectedMsg is emitted when the user presses Enter on an epic.
type EpicSelectedMsg struct {
	Epic    domain.EpicSummary
	Project domain.ProjectSummary
}

// BackToProjectDetailMsg is emitted when the user presses Esc in epic detail.
type BackToProjectDetailMsg struct{}

// StorySelectedMsg is emitted when the user presses Enter on a story.
type StorySelectedMsg struct {
	Story   domain.StorySummary
	Epic    domain.EpicSummary
	Project domain.ProjectSummary
}

// BackToEpicDetailMsg is emitted when the user presses Esc in story detail.
type BackToEpicDetailMsg struct{}

// BacklogReviewRequestedMsg is emitted when the user presses 'b' to open backlog review.
type BacklogReviewRequestedMsg struct {
	Epic    domain.EpicSummary
	Project domain.ProjectSummary
}

// BackToEpicDetailFromReviewMsg is emitted when the user presses Esc from the backlog review view.
type BackToEpicDetailFromReviewMsg struct{}

// ---------------------------------------------------------------------------
// Status filter options
// ---------------------------------------------------------------------------

var epicStatusFilters = []string{"ALL", "ACTIVE", "ARCHIVED", "DRAFT"}

// ---------------------------------------------------------------------------
// Internal messages
// ---------------------------------------------------------------------------

type epicsLoadedMsg struct {
	epics []domain.EpicSummary
	total int32
}
type epicCreatedMsg struct{ epic domain.EpicSummary }
type epicsErrMsg struct{ err error }

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

var (
	pdHeading = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("147")) // periwinkle
	pdLabel   = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("152")) // blue-grey
	pdValue   = lipgloss.NewStyle().Foreground(lipgloss.Color("252"))
	pdDim     = lipgloss.NewStyle().Foreground(lipgloss.Color("246")) // warm grey
	pdCard    = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(lipgloss.Color("240")).
			Padding(1, 2)
)

// ---------------------------------------------------------------------------
// Model
// ---------------------------------------------------------------------------

// ProjectDetailModel is the sub-model for the project detail view.
type ProjectDetailModel struct {
	client  ports.FleetClient
	project domain.ProjectSummary
	epics   []domain.EpicSummary
	table   table.Model

	// Status filter (client-side)
	statusFilter int // index into epicStatusFilters

	// Search (client-side)
	searching      bool
	searchInput    textinput.Model
	searchTerm     string

	// Pagination
	paginator components.Paginator

	// Create-epic form state
	creating       bool
	titleInput     textinput.Model
	epicDescInput  textinput.Model
	createFocusIdx int // 0 = title, 1 = description

	spinner spinner.Model
	loading bool
	err     error
	width   int
	height  int
}

// NewProjectDetailModel creates a ProjectDetailModel for the given project.
func NewProjectDetailModel(client ports.FleetClient, project domain.ProjectSummary) ProjectDetailModel {
	cols := epicColumns()
	t := components.NewTable(cols, nil, 10)

	titleIn := textinput.New()
	titleIn.Placeholder = "Epic title"
	titleIn.CharLimit = 120
	titleIn.Width = 40

	descIn := textinput.New()
	descIn.Placeholder = "Short description"
	descIn.CharLimit = 256
	descIn.Width = 60

	searchIn := textinput.New()
	searchIn.Placeholder = "search epics..."
	searchIn.CharLimit = 120
	searchIn.Width = 40

	return ProjectDetailModel{
		client:        client,
		project:       project,
		table:         t,
		searchInput:   searchIn,
		paginator:     components.NewPaginator(20),
		titleInput:    titleIn,
		epicDescInput: descIn,
		spinner:       components.NewSpinner(),
	}
}

func epicColumns() []table.Column {
	return []table.Column{
		{Title: "ID", Width: 12},
		{Title: "Title", Width: 28},
		{Title: "Status", Width: 14},
		{Title: "Created", Width: 20},
	}
}

// SetSize updates the available layout dimensions.
func (m ProjectDetailModel) SetSize(w, h int) ProjectDetailModel {
	m.width = w
	m.height = h
	tblH := max(h-16, 4) // leave room for project card + header/footer
	m.table.SetHeight(tblH)
	return m
}

// ---------------------------------------------------------------------------
// tea.Model interface
// ---------------------------------------------------------------------------

// Init fires the initial data load.
func (m ProjectDetailModel) Init() tea.Cmd {
	return tea.Batch(m.spinner.Tick, m.loadEpics())
}

// Update handles messages for the project detail view.
func (m ProjectDetailModel) Update(msg tea.Msg) (ProjectDetailModel, tea.Cmd) {
	var cmds []tea.Cmd

	switch msg := msg.(type) {

	// --- data messages ---------------------------------------------------
	case epicsLoadedMsg:
		m.loading = false
		m.err = nil
		m.epics = msg.epics
		m.paginator = m.paginator.SetTotal(msg.total)
		m.table.SetRows(m.filteredEpicRows())
		return m, nil

	case epicCreatedMsg:
		m.loading = false
		m.creating = false
		m.err = nil
		m.titleInput.Reset()
		m.epicDescInput.Reset()
		return m, m.loadEpics()

	case epicsErrMsg:
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

		switch msg.String() {
		case "/":
			m.searching = true
			m.searchInput.Focus()
			return m, textinput.Blink
		case "enter":
			if len(m.epics) > 0 {
				row := m.table.SelectedRow()
				if row != nil {
					epic := m.selectedEpic(row[0])
					if epic != nil {
						proj := m.project
						return m, func() tea.Msg { return EpicSelectedMsg{Epic: *epic, Project: proj} }
					}
				}
			}
		case "n":
			m.creating = true
			m.createFocusIdx = 0
			m.titleInput.Focus()
			m.epicDescInput.Blur()
			return m, textinput.Blink
		case "f":
			m.statusFilter = (m.statusFilter + 1) % len(epicStatusFilters)
			m.paginator = components.NewPaginator(int(m.paginator.Limit()))
			m.loading = true
			return m, tea.Batch(m.spinner.Tick, m.loadEpics())
		case "left", "h":
			m.paginator = m.paginator.PrevPage()
			m.loading = true
			return m, tea.Batch(m.spinner.Tick, m.loadEpics())
		case "right", "l":
			m.paginator = m.paginator.NextPage()
			m.loading = true
			return m, tea.Batch(m.spinner.Tick, m.loadEpics())
		case "r":
			m.loading = true
			return m, tea.Batch(m.spinner.Tick, m.loadEpics())
		case "esc":
			return m, func() tea.Msg { return BackToProjectsMsg{} }
		}

		// Delegate to table for navigation.
		var cmd tea.Cmd
		m.table, cmd = m.table.Update(msg)
		cmds = append(cmds, cmd)
	}

	return m, tea.Batch(cmds...)
}

// updateSearch handles key events in search mode.
func (m ProjectDetailModel) updateSearch(msg tea.KeyMsg) (ProjectDetailModel, tea.Cmd) {
	switch msg.String() {
	case "esc":
		m.searching = false
		m.searchInput.Reset()
		m.searchTerm = ""
		m.searchInput.Blur()
		m.table.SetRows(m.filteredEpicRows())
		return m, nil
	case "enter":
		m.searching = false
		m.searchTerm = strings.ToLower(strings.TrimSpace(m.searchInput.Value()))
		m.searchInput.Blur()
		m.table.SetRows(m.filteredEpicRows())
		return m, nil
	}
	var cmd tea.Cmd
	m.searchInput, cmd = m.searchInput.Update(msg)
	m.searchTerm = strings.ToLower(strings.TrimSpace(m.searchInput.Value()))
	m.table.SetRows(m.filteredEpicRows())
	return m, cmd
}

// updateCreateForm handles key events while the create-epic form is active.
func (m ProjectDetailModel) updateCreateForm(msg tea.KeyMsg) (ProjectDetailModel, tea.Cmd) {
	switch msg.String() {
	case "esc":
		m.creating = false
		m.titleInput.Reset()
		m.epicDescInput.Reset()
		return m, nil

	case "tab", "shift+tab":
		if m.createFocusIdx == 0 {
			m.createFocusIdx = 1
			m.titleInput.Blur()
			m.epicDescInput.Focus()
		} else {
			m.createFocusIdx = 0
			m.titleInput.Focus()
			m.epicDescInput.Blur()
		}
		return m, textinput.Blink

	case "enter":
		title := strings.TrimSpace(m.titleInput.Value())
		desc := strings.TrimSpace(m.epicDescInput.Value())
		if title == "" {
			m.err = fmt.Errorf("epic title is required")
			return m, nil
		}
		m.loading = true
		m.err = nil
		return m, tea.Batch(m.spinner.Tick, m.createEpic(title, desc))
	}

	// Forward to the focused input.
	var cmd tea.Cmd
	if m.createFocusIdx == 0 {
		m.titleInput, cmd = m.titleInput.Update(msg)
	} else {
		m.epicDescInput, cmd = m.epicDescInput.Update(msg)
	}
	return m, cmd
}

// View renders the project detail view.
func (m ProjectDetailModel) View() string {
	var b strings.Builder

	bc := components.NewBreadcrumb("Home", "Projects", m.project.Name)
	b.WriteString(bc.View())
	b.WriteString("\n\n")

	// Project info card
	b.WriteString(m.projectCardView())
	b.WriteString("\n\n")

	if m.loading {
		b.WriteString(m.spinner.View() + " Loading epics...")
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

	// Epics section
	b.WriteString(pdHeading.Render("Epics"))
	b.WriteString("\n")

	// Status filter + search
	filterDim := lipgloss.NewStyle().Foreground(lipgloss.Color("246"))
	filterSel := lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("115"))
	b.WriteString(filterDim.Render("Filter: ") + filterSel.Render(epicStatusFilters[m.statusFilter]))
	if m.searching {
		b.WriteString("  " + filterDim.Render("/") + " " + m.searchInput.View())
	} else if m.searchTerm != "" {
		b.WriteString("  " + filterDim.Render("Search: ") + filterSel.Render(m.searchTerm))
	}
	b.WriteString("\n\n")

	if len(m.filteredEpics()) == 0 {
		b.WriteString(pdDim.Render("No epics match the filter. Press n to create one or f to change filter."))
	} else {
		b.WriteString(m.table.View())
		b.WriteString("\n")
		b.WriteString(m.paginator.View())
	}

	b.WriteString("\n")
	b.WriteString(pdDim.Render("enter: open  n: new  /: search  f: filter  <</>>: page  r: refresh  esc: back"))

	return b.String()
}

func (m ProjectDetailModel) projectCardView() string {
	var lines []string
	lines = append(lines, pdHeading.Render(m.project.Name))
	if m.project.Description != "" {
		lines = append(lines, pdValue.Render(m.project.Description))
	}
	lines = append(lines, "")
	lines = append(lines, pdLabel.Render("Status: ")+pdValue.Render(m.project.Status))
	if m.project.Owner != "" {
		lines = append(lines, pdLabel.Render("Owner:  ")+pdValue.Render(m.project.Owner))
	}
	lines = append(lines, pdLabel.Render("Created: ")+pdDim.Render(m.project.CreatedAt))
	if m.project.UpdatedAt != "" {
		lines = append(lines, pdLabel.Render("Updated: ")+pdDim.Render(m.project.UpdatedAt))
	}

	cardWidth := m.width - 4
	if cardWidth < 40 {
		cardWidth = 40
	}
	return pdCard.Width(cardWidth).Render(strings.Join(lines, "\n"))
}

func (m ProjectDetailModel) createFormView() string {
	var b strings.Builder

	title := lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("147"))
	hint := lipgloss.NewStyle().Foreground(lipgloss.Color("246"))

	b.WriteString(title.Render("Create New Epic"))
	b.WriteString("\n\n")
	b.WriteString("Title:\n")
	b.WriteString(m.titleInput.View())
	b.WriteString("\n\n")
	b.WriteString("Description:\n")
	b.WriteString(m.epicDescInput.View())
	b.WriteString("\n\n")
	b.WriteString(hint.Render("tab: next field  enter: submit  esc: cancel"))

	return b.String()
}

// ---------------------------------------------------------------------------
// Commands
// ---------------------------------------------------------------------------

// serverStatusFilter returns the status string to send to the server.
func (m ProjectDetailModel) serverStatusFilter() string {
	if m.statusFilter == 0 {
		return ""
	}
	return strings.ToUpper(epicStatusFilters[m.statusFilter])
}

func (m ProjectDetailModel) loadEpics() tea.Cmd {
	limit := m.paginator.Limit()
	offset := m.paginator.Offset()
	statusFilter := m.serverStatusFilter()
	return func() tea.Msg {
		epics, total, err := m.client.ListEpics(context.Background(), m.project.ID, statusFilter, limit, offset)
		if err != nil {
			return epicsErrMsg{err: err}
		}
		return epicsLoadedMsg{epics: epics, total: total}
	}
}

func (m ProjectDetailModel) createEpic(title, desc string) tea.Cmd {
	return func() tea.Msg {
		reqID := uuid.NewString()
		e, err := m.client.CreateEpic(context.Background(), reqID, m.project.ID, title, desc)
		if err != nil {
			return epicsErrMsg{err: err}
		}
		return epicCreatedMsg{epic: e}
	}
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

func (m ProjectDetailModel) selectedEpic(idPrefix string) *domain.EpicSummary {
	for i := range m.epics {
		id := m.epics[i].ID
		if len(id) > 12 {
			id = id[:12]
		}
		if id == idPrefix {
			return &m.epics[i]
		}
	}
	return nil
}

func (m ProjectDetailModel) filteredEpics() []domain.EpicSummary {
	// Status filtering is now server-side; only apply client-side text search.
	if m.searchTerm == "" {
		return m.epics
	}
	filtered := make([]domain.EpicSummary, 0, len(m.epics))
	for _, e := range m.epics {
		if strings.Contains(strings.ToLower(e.Title), m.searchTerm) {
			filtered = append(filtered, e)
		}
	}
	return filtered
}

func (m ProjectDetailModel) filteredEpicRows() []table.Row {
	return epicRows(m.filteredEpics())
}

func epicRows(epics []domain.EpicSummary) []table.Row {
	rows := make([]table.Row, 0, len(epics))
	for _, e := range epics {
		id := e.ID
		if len(id) > 12 {
			id = id[:12]
		}
		rows = append(rows, table.Row{id, e.Title, e.Status, e.CreatedAt})
	}
	return rows
}
