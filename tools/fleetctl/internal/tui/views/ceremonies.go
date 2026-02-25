package views

import (
	"context"
	"fmt"
	"sort"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/spinner"
	"github.com/charmbracelet/bubbles/table"
	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/tui/components"
)

// ---------------------------------------------------------------------------
// Messages
// ---------------------------------------------------------------------------

type ceremoniesLoadedMsg struct {
	ceremonies []domain.CeremonyStatus
	total      int32
}
type ceremoniesErrMsg struct{ err error }
type ceremonyWatchTickMsg struct{}

// ---------------------------------------------------------------------------
// Pastel styles — colors express intent
// ---------------------------------------------------------------------------

var (
	// Headings & labels
	cerHeading  = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("147")) // periwinkle
	cerLabel    = lipgloss.NewStyle().Foreground(lipgloss.Color("152"))            // blue-grey
	cerValue    = lipgloss.NewStyle().Foreground(lipgloss.Color("252"))            // light
	cerDim      = lipgloss.NewStyle().Foreground(lipgloss.Color("246"))            // warm grey
	cerSelected = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("115")) // pastel teal

	// Step status dots (pastel intent)
	stepDone    = lipgloss.NewStyle().Foreground(lipgloss.Color("120")).Render("●") // mint = success
	stepRunning = lipgloss.NewStyle().Foreground(lipgloss.Color("222")).Render("●") // peach = in-progress
	stepPending = lipgloss.NewStyle().Foreground(lipgloss.Color("246")).Render("○") // grey = pending
	stepFailed  = lipgloss.NewStyle().Foreground(lipgloss.Color("210")).Render("●") // coral = error

	// Status badge styles
	cerStatusOK   = lipgloss.NewStyle().Foreground(lipgloss.Color("120")) // mint
	cerStatusWarn = lipgloss.NewStyle().Foreground(lipgloss.Color("222")) // peach
	cerStatusErr  = lipgloss.NewStyle().Foreground(lipgloss.Color("210")) // coral
)

// ---------------------------------------------------------------------------
// State machine: List → Detail → Watch
// ---------------------------------------------------------------------------

type ceremonyMode int

const (
	ceremonyModeList ceremonyMode = iota
	ceremonyModeDetail
	ceremonyModeWatch
)

// ---------------------------------------------------------------------------
// Status filter options
// ---------------------------------------------------------------------------

var ceremonyStatusFilters = []string{"ALL", "RUNNING", "COMPLETED", "FAILED"}

// ---------------------------------------------------------------------------
// Model
// ---------------------------------------------------------------------------

// CeremoniesModel is the sub-model for the ceremonies view with paginated
// list, step-level detail, and live watch mode.
type CeremoniesModel struct {
	client     ports.FleetClient
	ceremonies []domain.CeremonyStatus
	selected   int
	mode       ceremonyMode

	// Pagination
	paginator    components.Paginator
	statusFilter int // index into ceremonyStatusFilters

	// Detail
	stepTable table.Model
	progress  components.ProgressBar

	// Watch mode
	watchViewport viewport.Model
	watchActive   bool

	// Shared
	helpBar components.HelpBar
	spinner spinner.Model
	loading bool
	err     error
	width   int
	height  int
}

// NewCeremoniesModel creates a CeremoniesModel wired to the given FleetClient.
func NewCeremoniesModel(client ports.FleetClient) CeremoniesModel {
	return CeremoniesModel{
		client:    client,
		spinner:   components.NewSpinner(),
		paginator: components.NewPaginator(20),
		progress:  components.NewProgressBar(0),
		helpBar:   components.NewHelpBar(ceremoniesListBindings()...),
	}
}

// SetSize updates the available layout dimensions.
func (m CeremoniesModel) SetSize(w, h int) CeremoniesModel {
	m.width = w
	m.height = h
	m.watchViewport.Width = w
	m.watchViewport.Height = max(h-14, 4)
	m.helpBar = m.helpBar.SetWidth(w)
	return m
}

// HelpBindings returns the current context-specific key hints.
func (m CeremoniesModel) HelpBindings() []components.HelpBinding {
	switch m.mode {
	case ceremonyModeWatch:
		return ceremoniesWatchBindings()
	case ceremonyModeDetail:
		return ceremoniesDetailBindings()
	default:
		return ceremoniesListBindings()
	}
}

// ---------------------------------------------------------------------------
// tea.Model interface
// ---------------------------------------------------------------------------

func (m CeremoniesModel) Init() tea.Cmd {
	m.loading = true
	return tea.Batch(m.spinner.Tick, m.loadCeremonies())
}

func (m CeremoniesModel) Update(msg tea.Msg) (CeremoniesModel, tea.Cmd) {
	switch msg := msg.(type) {

	case ceremoniesLoadedMsg:
		m.loading = false
		m.err = nil
		m.ceremonies = msg.ceremonies
		m.paginator = m.paginator.SetTotal(msg.total)
		if m.selected >= len(m.ceremonies) {
			m.selected = 0
		}
		m.helpBar = m.helpBar.SetBindings(m.HelpBindings()...)
		return m, nil

	case ceremoniesErrMsg:
		m.loading = false
		m.err = msg.err
		return m, nil

	case ceremonyWatchTickMsg:
		if !m.watchActive || m.selected >= len(m.ceremonies) {
			return m, nil
		}
		return m, tea.Batch(m.refreshCeremony(m.ceremonies[m.selected].InstanceID), m.watchTick())

	case spinner.TickMsg:
		var cmd tea.Cmd
		m.spinner, cmd = m.spinner.Update(msg)
		return m, cmd

	case tea.KeyMsg:
		switch m.mode {
		case ceremonyModeWatch:
			return m.updateWatch(msg)
		case ceremonyModeDetail:
			return m.updateDetail(msg)
		default:
			return m.updateList(msg)
		}
	}

	// Forward viewport messages in watch mode.
	if m.mode == ceremonyModeWatch {
		var cmd tea.Cmd
		m.watchViewport, cmd = m.watchViewport.Update(msg)
		return m, cmd
	}

	return m, nil
}

// ---------------------------------------------------------------------------
// List mode
// ---------------------------------------------------------------------------

func (m CeremoniesModel) updateList(msg tea.KeyMsg) (CeremoniesModel, tea.Cmd) {
	switch msg.String() {
	case "up", "k":
		if m.selected > 0 {
			m.selected--
		}
	case "down", "j":
		if m.selected < len(m.ceremonies)-1 {
			m.selected++
		}
	case "enter":
		if len(m.ceremonies) > 0 {
			m.mode = ceremonyModeDetail
			m.updateStepTable()
			m.helpBar = m.helpBar.SetBindings(m.HelpBindings()...)
		}
	case "f":
		m.statusFilter = (m.statusFilter + 1) % len(ceremonyStatusFilters)
		m.loading = true
		return m, tea.Batch(m.spinner.Tick, m.loadCeremonies())
	case "r":
		m.loading = true
		return m, tea.Batch(m.spinner.Tick, m.loadCeremonies())
	case "left", "h":
		m.paginator = m.paginator.PrevPage()
		m.loading = true
		return m, tea.Batch(m.spinner.Tick, m.loadCeremonies())
	case "right", "l":
		m.paginator = m.paginator.NextPage()
		m.loading = true
		return m, tea.Batch(m.spinner.Tick, m.loadCeremonies())
	}
	return m, nil
}

// ---------------------------------------------------------------------------
// Detail mode
// ---------------------------------------------------------------------------

func (m CeremoniesModel) updateDetail(msg tea.KeyMsg) (CeremoniesModel, tea.Cmd) {
	switch msg.String() {
	case "esc":
		m.mode = ceremonyModeList
		m.helpBar = m.helpBar.SetBindings(m.HelpBindings()...)
	case "w":
		m.mode = ceremonyModeWatch
		m.watchActive = true
		m.watchViewport = viewport.New(m.width, max(m.height-14, 4))
		m.updateWatchContent()
		m.helpBar = m.helpBar.SetBindings(m.HelpBindings()...)
		return m, tea.Batch(m.watchTick(), m.spinner.Tick)
	case "r":
		if m.selected < len(m.ceremonies) {
			m.loading = true
			return m, tea.Batch(m.spinner.Tick, m.refreshCeremony(m.ceremonies[m.selected].InstanceID))
		}
	case "d":
		// Navigate to decisions (handled by parent via returned msg)
		return m, nil
	}
	return m, nil
}

func (m *CeremoniesModel) updateStepTable() {
	if m.selected >= len(m.ceremonies) {
		return
	}
	c := m.ceremonies[m.selected]

	steps := sortedSteps(c.StepStatuses)
	cols := []table.Column{
		{Title: "Step", Width: 24},
		{Title: "Status", Width: 14},
		{Title: "Output", Width: max(m.width-48, 20)},
	}
	rows := make([]table.Row, 0, len(steps))
	doneCount := 0
	for _, name := range steps {
		status := c.StepStatuses[name]
		output := ""
		if c.StepOutputs != nil {
			output = c.StepOutputs[name]
		}
		if len(output) > 60 {
			output = output[:57] + "..."
		}
		rows = append(rows, table.Row{name, status, output})
		if isStepDone(status) {
			doneCount++
		}
	}
	m.stepTable = components.NewTable(cols, rows, min(len(rows)+1, 10))
	m.progress = components.NewProgressBar(len(steps)).SetCurrent(doneCount)
}

// ---------------------------------------------------------------------------
// Watch mode
// ---------------------------------------------------------------------------

func (m CeremoniesModel) updateWatch(msg tea.KeyMsg) (CeremoniesModel, tea.Cmd) {
	switch msg.String() {
	case "esc":
		m.watchActive = false
		m.mode = ceremonyModeDetail
		m.helpBar = m.helpBar.SetBindings(m.HelpBindings()...)
		return m, nil
	case "r":
		if m.selected < len(m.ceremonies) {
			return m, m.refreshCeremony(m.ceremonies[m.selected].InstanceID)
		}
	}
	// Forward scroll keys to viewport
	var cmd tea.Cmd
	m.watchViewport, cmd = m.watchViewport.Update(msg)
	return m, cmd
}

func (m *CeremoniesModel) updateWatchContent() {
	if m.selected >= len(m.ceremonies) {
		return
	}
	c := m.ceremonies[m.selected]

	var b strings.Builder
	outHeading := lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("183")) // lavender
	outLabel := lipgloss.NewStyle().Foreground(lipgloss.Color("117"))              // sky blue
	outValue := lipgloss.NewStyle().Foreground(lipgloss.Color("252"))

	steps := sortedSteps(c.StepStatuses)
	for _, name := range steps {
		status := c.StepStatuses[name]
		dot := stepStatusDot(status)
		b.WriteString(fmt.Sprintf("%s %s  %s\n", dot, outHeading.Render(name), renderStatusBadge(status)))

		if c.StepOutputs != nil {
			if output, ok := c.StepOutputs[name]; ok && output != "" {
				lines := strings.Split(output, "\n")
				for _, line := range lines {
					b.WriteString(outLabel.Render("  | ") + outValue.Render(line) + "\n")
				}
			}
		}
		b.WriteString("\n")
	}

	m.watchViewport.SetContent(b.String())
}

func (m CeremoniesModel) watchTick() tea.Cmd {
	return tea.Tick(2*time.Second, func(time.Time) tea.Msg {
		return ceremonyWatchTickMsg{}
	})
}

// ---------------------------------------------------------------------------
// View
// ---------------------------------------------------------------------------

func (m CeremoniesModel) View() string {
	var b strings.Builder

	switch m.mode {
	case ceremonyModeWatch:
		b.WriteString(m.viewWatch())
	case ceremonyModeDetail:
		b.WriteString(m.viewDetail())
	default:
		b.WriteString(m.viewList())
	}

	b.WriteString("\n")
	b.WriteString(m.helpBar.View())

	return b.String()
}

func (m CeremoniesModel) viewList() string {
	var b strings.Builder

	bc := components.NewBreadcrumb("Home", "Ceremonies")
	b.WriteString(bc.View())
	b.WriteString("\n\n")

	// Status filter indicator
	filterLabel := cerDim.Render("Filter: ")
	filterValue := cerSelected.Render(ceremonyStatusFilters[m.statusFilter])
	b.WriteString(filterLabel + filterValue + "\n\n")

	if m.loading {
		b.WriteString(m.spinner.View() + " " + cerDim.Render("Loading ceremonies..."))
		return b.String()
	}

	if m.err != nil {
		errStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("210")).Bold(true)
		b.WriteString(errStyle.Render("Error: "+m.err.Error()) + "\n\n")
	}

	if len(m.ceremonies) == 0 {
		b.WriteString(cerDim.Render("No ceremonies found."))
		b.WriteString("\n")
		return b.String()
	}

	// Table header
	headerStyle := lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("147")).Underline(true)
	b.WriteString(fmt.Sprintf("  %s  %-20s %-18s %-12s %-12s %s\n",
		headerStyle.Render(" "),
		headerStyle.Render("Instance"),
		headerStyle.Render("Definition"),
		headerStyle.Render("Story"),
		headerStyle.Render("Status"),
		headerStyle.Render("Updated"),
	))

	for i, c := range m.ceremonies {
		cursor := "  "
		style := cerDim
		if i == m.selected {
			cursor = cerSelected.Render("> ")
			style = cerValue
		}

		dot := stepStatusDot(c.Status)
		instID := truncID(c.InstanceID)
		storyID := truncID(c.StoryID)

		line := fmt.Sprintf("%s  %-20s %-18s %-12s %-12s %s",
			dot,
			instID,
			c.DefinitionName,
			storyID,
			renderStatusBadge(c.Status),
			cerDim.Render(c.UpdatedAt),
		)
		b.WriteString(cursor + style.Render(line) + "\n")
	}

	b.WriteString("\n")
	b.WriteString(m.paginator.View())

	return b.String()
}

func (m CeremoniesModel) viewDetail() string {
	var b strings.Builder

	if m.selected >= len(m.ceremonies) {
		b.WriteString(cerDim.Render("No ceremony selected."))
		return b.String()
	}
	c := m.ceremonies[m.selected]

	bc := components.NewBreadcrumb("Home", "Ceremonies", truncID(c.InstanceID))
	b.WriteString(bc.View())
	b.WriteString("\n\n")

	if m.loading {
		b.WriteString(m.spinner.View() + " " + cerDim.Render("Refreshing..."))
		return b.String()
	}

	// Ceremony header with status badge
	b.WriteString(cerHeading.Render("Ceremony Detail"))
	b.WriteString("  ")
	b.WriteString(renderStatusBadge(c.Status))
	b.WriteString("\n\n")

	// Fields in two-column layout
	fields := [][2]string{
		{"Instance", c.InstanceID},
		{"Ceremony", c.CeremonyID},
		{"Definition", c.DefinitionName},
		{"Story", c.StoryID},
		{"State", c.CurrentState},
		{"Correlation", c.CorrelationID},
		{"Created", c.CreatedAt},
		{"Updated", c.UpdatedAt},
	}
	for _, f := range fields {
		b.WriteString(fmt.Sprintf("  %s %s\n", cerLabel.Width(14).Render(f[0]+":"), cerValue.Render(f[1])))
	}

	// Progress bar
	if len(c.StepStatuses) > 0 {
		b.WriteString("\n")
		b.WriteString("  " + m.progress.View())
		b.WriteString("\n\n")

		// Step status table
		b.WriteString("  " + cerHeading.Render("Steps"))
		b.WriteString("\n\n")
		b.WriteString(m.stepTable.View())
	}

	b.WriteString("\n")
	return b.String()
}

func (m CeremoniesModel) viewWatch() string {
	var b strings.Builder

	if m.selected >= len(m.ceremonies) {
		return cerDim.Render("No ceremony selected.")
	}
	c := m.ceremonies[m.selected]

	bc := components.NewBreadcrumb("Home", "Ceremonies", truncID(c.InstanceID), "Watch")
	b.WriteString(bc.View())
	b.WriteString("\n")

	// Live indicator
	liveStyle := lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("210"))
	b.WriteString(liveStyle.Render("● LIVE") + "  ")
	b.WriteString(cerDim.Render(c.DefinitionName) + "  ")
	b.WriteString(renderStatusBadge(c.Status))
	b.WriteString("\n")

	// Progress bar
	b.WriteString("  " + m.progress.View())
	b.WriteString("\n\n")

	// Viewport with step outputs
	b.WriteString(m.watchViewport.View())

	return b.String()
}

// ---------------------------------------------------------------------------
// Commands
// ---------------------------------------------------------------------------

// LoadCeremony returns a Cmd that fetches a specific ceremony by instance ID
// and adds it to the list.
func (m CeremoniesModel) LoadCeremony(instanceID string) tea.Cmd {
	return func() tea.Msg {
		cs, err := m.client.GetCeremony(context.Background(), instanceID)
		if err != nil {
			return ceremoniesErrMsg{err: err}
		}
		return ceremoniesLoadedMsg{ceremonies: []domain.CeremonyStatus{cs}, total: 1}
	}
}

func (m CeremoniesModel) loadCeremonies() tea.Cmd {
	filter := ""
	if m.statusFilter > 0 {
		filter = ceremonyStatusFilters[m.statusFilter]
	}
	limit := m.paginator.Limit()
	offset := m.paginator.Offset()
	return func() tea.Msg {
		ceremonies, total, err := m.client.ListCeremonies(context.Background(), "", filter, limit, offset)
		if err != nil {
			return ceremoniesErrMsg{err: err}
		}
		return ceremoniesLoadedMsg{ceremonies: ceremonies, total: total}
	}
}

func (m CeremoniesModel) refreshCeremony(instanceID string) tea.Cmd {
	return func() tea.Msg {
		cs, err := m.client.GetCeremony(context.Background(), instanceID)
		if err != nil {
			return ceremoniesErrMsg{err: err}
		}
		return ceremoniesLoadedMsg{ceremonies: []domain.CeremonyStatus{cs}, total: 1}
	}
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

func stepStatusDot(status string) string {
	switch strings.ToUpper(status) {
	case "COMPLETED", "DONE", "PASSED":
		return stepDone
	case "RUNNING", "IN_PROGRESS", "ACTIVE":
		return stepRunning
	case "FAILED", "ERROR":
		return stepFailed
	default:
		return stepPending
	}
}

func renderStatusBadge(status string) string {
	switch strings.ToUpper(status) {
	case "COMPLETED", "DONE", "PASSED":
		return cerStatusOK.Render(status)
	case "RUNNING", "IN_PROGRESS", "ACTIVE":
		return cerStatusWarn.Render(status)
	case "FAILED", "ERROR":
		return cerStatusErr.Render(status)
	default:
		return cerDim.Render(status)
	}
}

func isStepDone(status string) bool {
	s := strings.ToUpper(status)
	return s == "COMPLETED" || s == "DONE" || s == "PASSED"
}

func sortedSteps(m map[string]string) []string {
	steps := make([]string, 0, len(m))
	for step := range m {
		steps = append(steps, step)
	}
	sort.Strings(steps)
	return steps
}

func truncID(id string) string {
	if len(id) > 8 {
		return id[:8]
	}
	return id
}

// ---------------------------------------------------------------------------
// Help binding presets
// ---------------------------------------------------------------------------

func ceremoniesListBindings() []components.HelpBinding {
	return []components.HelpBinding{
		{Key: "j/k", Description: "navigate"},
		{Key: "enter", Description: "detail"},
		{Key: "f", Description: "filter"},
		{Key: "<</>>" , Description: "page"},
		{Key: "r", Description: "refresh"},
		{Key: "esc", Description: "back"},
	}
}

func ceremoniesDetailBindings() []components.HelpBinding {
	return []components.HelpBinding{
		{Key: "w", Description: "watch"},
		{Key: "d", Description: "decisions"},
		{Key: "r", Description: "refresh"},
		{Key: "esc", Description: "back"},
	}
}

func ceremoniesWatchBindings() []components.HelpBinding {
	return []components.HelpBinding{
		{Key: "r", Description: "refresh"},
		{Key: "scroll", Description: "up/down"},
		{Key: "esc", Description: "back"},
	}
}
