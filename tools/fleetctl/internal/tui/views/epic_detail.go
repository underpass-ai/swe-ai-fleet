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

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/command"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/query"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/tui/components"
)

// ---------------------------------------------------------------------------
// Internal messages
// ---------------------------------------------------------------------------

type storiesForEpicLoadedMsg struct {
	stories []domain.StorySummary
	total   int32
}
type storyInEpicCreatedMsg struct{ story domain.StorySummary }
type epicDetailErrMsg struct{ err error }

// CeremonyStartedMsg is emitted when a planning ceremony is started from
// the epic detail view. Handled by app.go to navigate to the ceremonies view.
type CeremonyStartedMsg struct{ InstanceID string }

// ---------------------------------------------------------------------------
// Model
// ---------------------------------------------------------------------------

// EpicDetailModel is the sub-model for the epic detail view.
type EpicDetailModel struct {
	createStory   *command.CreateStoryHandler
	startCeremony *command.StartCeremonyHandler
	listStories   *query.ListStoriesHandler
	epic          domain.EpicSummary
	project       domain.ProjectSummary
	stories       []domain.StorySummary
	table         table.Model

	// Create-story form state
	creating       bool
	titleInput     textinput.Model
	briefInput     textinput.Model
	createFocusIdx int // 0 = title, 1 = brief

	// Plan ceremony form state
	planningCeremony bool
	planStory        *domain.StorySummary // captured at 'p' press time
	defNameInput     textinput.Model
	stepIDsInput     textinput.Model
	planFocusIdx     int // 0 = defName, 1 = stepIDs

	spinner spinner.Model
	loading bool
	err     error
	width   int
	height  int
}

// NewEpicDetailModel creates an EpicDetailModel for the given epic.
func NewEpicDetailModel(createStory *command.CreateStoryHandler, startCeremony *command.StartCeremonyHandler, listStories *query.ListStoriesHandler, epic domain.EpicSummary, project domain.ProjectSummary) EpicDetailModel {
	cols := epicDetailStoryColumns()
	t := components.NewTable(cols, nil, 10)

	titleIn := textinput.New()
	titleIn.Placeholder = "Story title"
	titleIn.CharLimit = 120
	titleIn.Width = 40

	briefIn := textinput.New()
	briefIn.Placeholder = "Brief description"
	briefIn.CharLimit = 256
	briefIn.Width = 60

	defNameIn := textinput.New()
	defNameIn.Placeholder = "Definition name (e.g. dummy_ceremony)"
	defNameIn.CharLimit = 80
	defNameIn.Width = 40

	stepIDsIn := textinput.New()
	stepIDsIn.Placeholder = "Step IDs (comma-separated)"
	stepIDsIn.CharLimit = 256
	stepIDsIn.Width = 60

	return EpicDetailModel{
		createStory:   createStory,
		startCeremony: startCeremony,
		listStories:   listStories,
		epic:          epic,
		project:       project,
		table:        t,
		titleInput:   titleIn,
		briefInput:   briefIn,
		defNameInput: defNameIn,
		stepIDsInput: stepIDsIn,
		spinner:      components.NewSpinner(),
	}
}

func epicDetailStoryColumns() []table.Column {
	return []table.Column{
		{Title: "ID", Width: 12},
		{Title: "Title", Width: 28},
		{Title: "State", Width: 12},
		{Title: "DoR", Width: 5},
		{Title: "Created By", Width: 16},
		{Title: "Created", Width: 20},
	}
}

// SetSize updates the available layout dimensions.
func (m EpicDetailModel) SetSize(w, h int) EpicDetailModel {
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
func (m EpicDetailModel) Init() tea.Cmd {
	return tea.Batch(m.spinner.Tick, m.loadStories())
}

// Update handles messages for the epic detail view.
func (m EpicDetailModel) Update(msg tea.Msg) (EpicDetailModel, tea.Cmd) {
	switch msg := msg.(type) {
	case storiesForEpicLoadedMsg, storyInEpicCreatedMsg, epicDetailErrMsg:
		return m.handleDataMsg(msg)

	case spinner.TickMsg:
		var cmd tea.Cmd
		m.spinner, cmd = m.spinner.Update(msg)
		return m, cmd

	case tea.KeyMsg:
		return m.handleKeyMsg(msg)
	}

	return m, nil
}

// handleDataMsg processes data load and mutation response messages.
func (m EpicDetailModel) handleDataMsg(msg tea.Msg) (EpicDetailModel, tea.Cmd) {
	switch msg := msg.(type) {
	case storiesForEpicLoadedMsg:
		m.loading = false
		m.err = nil
		m.stories = msg.stories
		m.table.SetRows(epicDetailStoryRows(m.stories))
		return m, nil

	case storyInEpicCreatedMsg:
		m.loading = false
		m.creating = false
		m.err = nil
		m.titleInput.Reset()
		m.briefInput.Reset()
		return m, m.loadStories()

	case epicDetailErrMsg:
		m.loading = false
		m.err = msg.err
		return m, nil
	}

	return m, nil
}

// handleKeyMsg dispatches key events based on the current form state.
func (m EpicDetailModel) handleKeyMsg(msg tea.KeyMsg) (EpicDetailModel, tea.Cmd) {
	if m.creating {
		return m.updateCreateForm(msg)
	}
	if m.planningCeremony {
		return m.updateCeremonyForm(msg)
	}
	return m.handleListKey(msg)
}

// handleListKey processes keys in the normal story list mode.
func (m EpicDetailModel) handleListKey(msg tea.KeyMsg) (EpicDetailModel, tea.Cmd) {
	switch msg.String() {
	case "enter":
		if story := m.tableSelectedStory(); story != nil {
			epic := m.epic
			proj := m.project
			return m, func() tea.Msg {
				return StorySelectedMsg{Story: *story, Epic: epic, Project: proj}
			}
		}
	case "n":
		m.creating = true
		m.createFocusIdx = 0
		m.titleInput.Focus()
		m.briefInput.Blur()
		return m, textinput.Blink
	case "p":
		if story := m.tableSelectedStory(); story != nil {
			m.planningCeremony = true
			m.planStory = story
			m.planFocusIdx = 0
			m.defNameInput.Focus()
			m.stepIDsInput.Blur()
			return m, textinput.Blink
		}
	case "b":
		epic := m.epic
		proj := m.project
		return m, func() tea.Msg {
			return BacklogReviewRequestedMsg{Epic: epic, Project: proj}
		}
	case "r":
		m.loading = true
		return m, tea.Batch(m.spinner.Tick, m.loadStories())
	case "esc":
		return m, func() tea.Msg { return BackToProjectDetailMsg{} }
	}

	// Delegate to table for navigation.
	var cmd tea.Cmd
	m.table, cmd = m.table.Update(msg)
	return m, cmd
}

// tableSelectedStory returns the story currently highlighted in the table,
// or nil if no valid selection exists.
func (m EpicDetailModel) tableSelectedStory() *domain.StorySummary {
	if len(m.stories) == 0 {
		return nil
	}
	row := m.table.SelectedRow()
	if row == nil {
		return nil
	}
	return m.selectedStory(row[0])
}

// updateCreateForm handles key events while the create-story form is active.
func (m EpicDetailModel) updateCreateForm(msg tea.KeyMsg) (EpicDetailModel, tea.Cmd) {
	switch msg.String() {
	case "esc":
		m.creating = false
		m.titleInput.Reset()
		m.briefInput.Reset()
		return m, nil

	case "tab", "shift+tab":
		if m.createFocusIdx == 0 {
			m.createFocusIdx = 1
			m.titleInput.Blur()
			m.briefInput.Focus()
		} else {
			m.createFocusIdx = 0
			m.titleInput.Focus()
			m.briefInput.Blur()
		}
		return m, textinput.Blink

	case "enter":
		title := strings.TrimSpace(m.titleInput.Value())
		brief := strings.TrimSpace(m.briefInput.Value())
		if title == "" {
			m.err = fmt.Errorf("story title is required")
			return m, nil
		}
		m.loading = true
		m.err = nil
		return m, tea.Batch(m.spinner.Tick, m.cmdCreateStory(title, brief))
	}

	// Forward to the focused input.
	var cmd tea.Cmd
	if m.createFocusIdx == 0 {
		m.titleInput, cmd = m.titleInput.Update(msg)
	} else {
		m.briefInput, cmd = m.briefInput.Update(msg)
	}
	return m, cmd
}

// View renders the epic detail view.
func (m EpicDetailModel) View() string {
	var b strings.Builder

	bc := components.NewBreadcrumb("Home", "Projects", m.project.Name, m.epic.Title)
	b.WriteString(bc.View())
	b.WriteString("\n\n")

	// Epic info card
	b.WriteString(m.epicCardView())
	b.WriteString("\n\n")

	if m.loading {
		b.WriteString(m.spinner.View() + " Loading stories...")
		return b.String()
	}

	if m.err != nil {
		errStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("210")).Bold(true)
		b.WriteString(errStyle.Render("Error: "+m.err.Error()) + "\n\n")
	}

	if m.planningCeremony {
		b.WriteString(m.ceremonyFormView())
		return b.String()
	}

	if m.creating {
		b.WriteString(m.createFormView())
		return b.String()
	}

	// Stories section
	b.WriteString(pdHeading.Render("Stories"))
	b.WriteString("\n\n")

	if len(m.stories) == 0 {
		b.WriteString(pdDim.Render("No stories yet. Press n to create one."))
	} else {
		b.WriteString(m.table.View())
	}

	b.WriteString("\n")
	b.WriteString(pdDim.Render("enter: open  n: new story  p: plan ceremony  b: backlog review  r: refresh  esc: back"))

	return b.String()
}

func (m EpicDetailModel) epicCardView() string {
	var lines []string
	lines = append(lines, pdHeading.Render(m.epic.Title))
	if m.epic.Description != "" {
		lines = append(lines, pdValue.Render(m.epic.Description))
	}
	lines = append(lines, "")
	lines = append(lines, pdLabel.Render("Status: ")+pdValue.Render(m.epic.Status))
	lines = append(lines, pdLabel.Render("Created: ")+pdDim.Render(m.epic.CreatedAt))
	if m.epic.UpdatedAt != "" {
		lines = append(lines, pdLabel.Render("Updated: ")+pdDim.Render(m.epic.UpdatedAt))
	}

	cardWidth := m.width - 4
	if cardWidth < 40 {
		cardWidth = 40
	}
	return pdCard.Width(cardWidth).Render(strings.Join(lines, "\n"))
}

func (m EpicDetailModel) createFormView() string {
	var b strings.Builder

	title := lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("147"))
	hint := lipgloss.NewStyle().Foreground(lipgloss.Color("246"))

	b.WriteString(title.Render("Create New Story"))
	b.WriteString("\n\n")
	b.WriteString("Title:\n")
	b.WriteString(m.titleInput.View())
	b.WriteString("\n\n")
	b.WriteString("Brief:\n")
	b.WriteString(m.briefInput.View())
	b.WriteString("\n\n")
	b.WriteString(hint.Render("tab: next field  enter: submit  esc: cancel"))

	return b.String()
}

// updateCeremonyForm handles key events while the ceremony form is active.
func (m EpicDetailModel) updateCeremonyForm(msg tea.KeyMsg) (EpicDetailModel, tea.Cmd) {
	switch msg.String() {
	case "esc":
		m.planningCeremony = false
		m.planStory = nil
		m.defNameInput.Reset()
		m.stepIDsInput.Reset()
		return m, nil

	case "tab", "shift+tab":
		if m.planFocusIdx == 0 {
			m.planFocusIdx = 1
			m.defNameInput.Blur()
			m.stepIDsInput.Focus()
		} else {
			m.planFocusIdx = 0
			m.defNameInput.Focus()
			m.stepIDsInput.Blur()
		}
		return m, textinput.Blink

	case "enter":
		defName := strings.TrimSpace(m.defNameInput.Value())
		stepIDsRaw := strings.TrimSpace(m.stepIDsInput.Value())
		if defName == "" {
			m.err = fmt.Errorf("definition name is required")
			return m, nil
		}
		if m.planStory == nil {
			m.err = fmt.Errorf("no story selected")
			return m, nil
		}
		stepIDs := parseCommaSeparated(stepIDsRaw)
		m.loading = true
		m.err = nil
		return m, tea.Batch(m.spinner.Tick, m.cmdStartCeremony(defName, m.planStory.ID, stepIDs))
	}

	// Forward to the focused input.
	var cmd tea.Cmd
	if m.planFocusIdx == 0 {
		m.defNameInput, cmd = m.defNameInput.Update(msg)
	} else {
		m.stepIDsInput, cmd = m.stepIDsInput.Update(msg)
	}
	return m, cmd
}

func (m EpicDetailModel) ceremonyFormView() string {
	var b strings.Builder

	title := lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("147"))
	hint := lipgloss.NewStyle().Foreground(lipgloss.Color("246"))

	b.WriteString(title.Render("Start Planning Ceremony"))
	if m.planStory != nil {
		b.WriteString("  " + pdDim.Render("for: "+m.planStory.Title))
	}
	b.WriteString("\n\n")
	b.WriteString("Definition Name:\n")
	b.WriteString(m.defNameInput.View())
	b.WriteString("\n\n")
	b.WriteString("Step IDs:\n")
	b.WriteString(m.stepIDsInput.View())
	b.WriteString("\n\n")
	b.WriteString(hint.Render("tab: next field  enter: submit  esc: cancel"))

	return b.String()
}

// ---------------------------------------------------------------------------
// Commands
// ---------------------------------------------------------------------------

func (m EpicDetailModel) cmdStartCeremony(defName, storyID string, stepIDs []string) tea.Cmd {
	handler := m.startCeremony
	return func() tea.Msg {
		ceremonyID := uuid.NewString()
		cs, err := handler.Handle(context.Background(), command.StartCeremonyCmd{
			CeremonyID:     ceremonyID,
			DefinitionName: defName,
			StoryID:        storyID,
			StepIDs:        stepIDs,
		})
		if err != nil {
			return epicDetailErrMsg{err: err}
		}
		return CeremonyStartedMsg{InstanceID: cs.InstanceID}
	}
}

func (m EpicDetailModel) loadStories() tea.Cmd {
	handler := m.listStories
	epicID := m.epic.ID
	return func() tea.Msg {
		stories, total, err := handler.Handle(context.Background(), epicID, "", 0, 0)
		if err != nil {
			return epicDetailErrMsg{err: err}
		}
		return storiesForEpicLoadedMsg{stories: stories, total: total}
	}
}

func (m EpicDetailModel) cmdCreateStory(title, brief string) tea.Cmd {
	handler := m.createStory
	epicID := m.epic.ID
	return func() tea.Msg {
		s, err := handler.Handle(context.Background(), command.CreateStoryCmd{
			EpicID: epicID,
			Title:  title,
			Brief:  brief,
		})
		if err != nil {
			return epicDetailErrMsg{err: err}
		}
		return storyInEpicCreatedMsg{story: s}
	}
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

func parseCommaSeparated(raw string) []string {
	if raw == "" {
		return nil
	}
	var result []string
	for _, s := range strings.Split(raw, ",") {
		s = strings.TrimSpace(s)
		if s != "" {
			result = append(result, s)
		}
	}
	return result
}

func (m EpicDetailModel) selectedStory(idPrefix string) *domain.StorySummary {
	for i := range m.stories {
		id := m.stories[i].ID
		if len(id) > 12 {
			id = id[:12]
		}
		if id == idPrefix {
			return &m.stories[i]
		}
	}
	return nil
}

func epicDetailStoryRows(stories []domain.StorySummary) []table.Row {
	rows := make([]table.Row, 0, len(stories))
	for _, s := range stories {
		id := s.ID
		if len(id) > 12 {
			id = id[:12]
		}
		rows = append(rows, table.Row{id, s.Title, s.State, fmt.Sprintf("%d", s.DorScore), s.CreatedBy, s.CreatedAt})
	}
	return rows
}
