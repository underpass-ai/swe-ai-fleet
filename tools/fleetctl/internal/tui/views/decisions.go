package views

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/spinner"
	"github.com/charmbracelet/bubbles/textarea"
	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/tui/components"
)

// ---------------------------------------------------------------------------
// Messages
// ---------------------------------------------------------------------------

type decisionApprovedMsg struct{}
type decisionRejectedMsg struct{}
type decisionErrMsg struct{ err error }
type decisionResultDoneMsg struct{}

// ---------------------------------------------------------------------------
// Pastel styles
// ---------------------------------------------------------------------------

var (
	decHeading    = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("147")) // periwinkle
	decLabel      = lipgloss.NewStyle().Foreground(lipgloss.Color("152"))            // blue-grey
	decValue      = lipgloss.NewStyle().Foreground(lipgloss.Color("252"))            // light
	decDim        = lipgloss.NewStyle().Foreground(lipgloss.Color("246"))            // warm grey
	decSelected   = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("115")) // teal
	decSuccess    = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("120")) // mint
	decDanger     = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("210")) // coral
	decApproveTag = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("120")).Background(lipgloss.Color("235")).Padding(0, 1)
	decRejectTag  = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("210")).Background(lipgloss.Color("235")).Padding(0, 1)
)

// ---------------------------------------------------------------------------
// Decision item (simplified — pending decisions for a story)
// ---------------------------------------------------------------------------

// DecisionItem represents a pending decision for display.
type DecisionItem struct {
	ID     string
	Type   string
	Status string
}

// ---------------------------------------------------------------------------
// State machine: Select → ApproveForm/RejectForm → Submitting → Result
// ---------------------------------------------------------------------------

type decisionMode int

const (
	decisionModeSelect decisionMode = iota
	decisionModeApproveForm
	decisionModeRejectForm
	decisionModeSubmitting
	decisionModeResult
)

// ---------------------------------------------------------------------------
// Model
// ---------------------------------------------------------------------------

// DecisionsModel handles the interactive approve/reject flow for ceremony
// decisions.
type DecisionsModel struct {
	client  ports.FleetClient
	storyID string

	// Decision items (injected from parent)
	decisions []DecisionItem
	selected  int
	mode      decisionMode

	// Approve form
	commentInput textinput.Model

	// Reject form
	reasonArea textarea.Model

	// Submitting / result
	resultOK  bool
	resultMsg string

	// Shared
	helpBar components.HelpBar
	spinner spinner.Model
	err     error
	width   int
	height  int
}

// NewDecisionsModel creates a DecisionsModel for the given story.
func NewDecisionsModel(client ports.FleetClient, storyID string) DecisionsModel {
	// Comment input (single line, for approve)
	ci := textinput.New()
	ci.Placeholder = "optional comment..."
	ci.CharLimit = 500
	ci.Width = 50
	ci.PromptStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("152"))
	ci.TextStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("252"))

	// Reason textarea (multi-line, for reject)
	ra := textarea.New()
	ra.Placeholder = "reason for rejection (required)..."
	ra.CharLimit = 2000
	ra.SetWidth(60)
	ra.SetHeight(5)
	ra.FocusedStyle.Base = lipgloss.NewStyle().Border(lipgloss.RoundedBorder()).BorderForeground(lipgloss.Color("210"))
	ra.BlurredStyle.Base = lipgloss.NewStyle().Border(lipgloss.RoundedBorder()).BorderForeground(lipgloss.Color("240"))

	return DecisionsModel{
		client:       client,
		storyID:      storyID,
		commentInput: ci,
		reasonArea:   ra,
		spinner:      components.NewSpinner(),
		helpBar:      components.NewHelpBar(decisionSelectBindings()...),
	}
}

// SetDecisions injects the list of pending decisions to display.
func (m DecisionsModel) SetDecisions(items []DecisionItem) DecisionsModel {
	m.decisions = items
	if m.selected >= len(items) {
		m.selected = 0
	}
	return m
}

// SetSize updates layout dimensions.
func (m DecisionsModel) SetSize(w, h int) DecisionsModel {
	m.width = w
	m.height = h
	m.helpBar = m.helpBar.SetWidth(w)
	m.commentInput.Width = max(w-20, 30)
	m.reasonArea.SetWidth(max(w-10, 40))
	return m
}

// HelpBindings returns context-specific hints.
func (m DecisionsModel) HelpBindings() []components.HelpBinding {
	switch m.mode {
	case decisionModeApproveForm:
		return decisionApproveBindings()
	case decisionModeRejectForm:
		return decisionRejectBindings()
	default:
		return decisionSelectBindings()
	}
}

// ---------------------------------------------------------------------------
// tea.Model interface
// ---------------------------------------------------------------------------

func (m DecisionsModel) Init() tea.Cmd {
	return m.spinner.Tick
}

func (m DecisionsModel) Update(msg tea.Msg) (DecisionsModel, tea.Cmd) {
	switch msg := msg.(type) {

	case decisionApprovedMsg:
		m.mode = decisionModeResult
		m.resultOK = true
		m.resultMsg = "Decision approved successfully."
		return m, tea.Tick(2*time.Second, func(time.Time) tea.Msg { return decisionResultDoneMsg{} })

	case decisionRejectedMsg:
		m.mode = decisionModeResult
		m.resultOK = true
		m.resultMsg = "Decision rejected."
		return m, tea.Tick(2*time.Second, func(time.Time) tea.Msg { return decisionResultDoneMsg{} })

	case decisionErrMsg:
		m.mode = decisionModeResult
		m.resultOK = false
		m.resultMsg = msg.err.Error()
		return m, tea.Tick(2*time.Second, func(time.Time) tea.Msg { return decisionResultDoneMsg{} })

	case decisionResultDoneMsg:
		m.mode = decisionModeSelect
		m.err = nil
		return m, nil

	case spinner.TickMsg:
		var cmd tea.Cmd
		m.spinner, cmd = m.spinner.Update(msg)
		return m, cmd

	case tea.KeyMsg:
		switch m.mode {
		case decisionModeSelect:
			return m.updateSelect(msg)
		case decisionModeApproveForm:
			return m.updateApproveForm(msg)
		case decisionModeRejectForm:
			return m.updateRejectForm(msg)
		}
	}

	return m, nil
}

// ---------------------------------------------------------------------------
// Select mode
// ---------------------------------------------------------------------------

func (m DecisionsModel) updateSelect(msg tea.KeyMsg) (DecisionsModel, tea.Cmd) {
	switch msg.String() {
	case "up", "k":
		if m.selected > 0 {
			m.selected--
		}
	case "down", "j":
		if m.selected < len(m.decisions)-1 {
			m.selected++
		}
	case "a":
		if len(m.decisions) > 0 {
			m.mode = decisionModeApproveForm
			m.commentInput.Reset()
			m.commentInput.Focus()
			m.helpBar = m.helpBar.SetBindings(m.HelpBindings()...)
			return m, m.commentInput.Cursor.BlinkCmd()
		}
	case "x":
		if len(m.decisions) > 0 {
			m.mode = decisionModeRejectForm
			m.reasonArea.Reset()
			m.reasonArea.Focus()
			m.helpBar = m.helpBar.SetBindings(m.HelpBindings()...)
			return m, m.reasonArea.Cursor.BlinkCmd()
		}
	}
	return m, nil
}

// ---------------------------------------------------------------------------
// Approve form
// ---------------------------------------------------------------------------

func (m DecisionsModel) updateApproveForm(msg tea.KeyMsg) (DecisionsModel, tea.Cmd) {
	switch msg.String() {
	case "esc":
		m.mode = decisionModeSelect
		m.helpBar = m.helpBar.SetBindings(m.HelpBindings()...)
		return m, nil
	case "enter":
		// Submit approval
		m.mode = decisionModeSubmitting
		d := m.decisions[m.selected]
		return m, tea.Batch(m.spinner.Tick, m.submitApprove(d.ID, m.commentInput.Value()))
	}
	var cmd tea.Cmd
	m.commentInput, cmd = m.commentInput.Update(msg)
	return m, cmd
}

// ---------------------------------------------------------------------------
// Reject form
// ---------------------------------------------------------------------------

func (m DecisionsModel) updateRejectForm(msg tea.KeyMsg) (DecisionsModel, tea.Cmd) {
	switch msg.String() {
	case "esc":
		m.mode = decisionModeSelect
		m.helpBar = m.helpBar.SetBindings(m.HelpBindings()...)
		return m, nil
	case "ctrl+d":
		// Submit rejection
		reason := strings.TrimSpace(m.reasonArea.Value())
		if reason == "" {
			m.err = fmt.Errorf("reason is required for rejection")
			return m, nil
		}
		m.mode = decisionModeSubmitting
		d := m.decisions[m.selected]
		return m, tea.Batch(m.spinner.Tick, m.submitReject(d.ID, reason))
	}
	var cmd tea.Cmd
	m.reasonArea, cmd = m.reasonArea.Update(msg)
	return m, cmd
}

// ---------------------------------------------------------------------------
// View
// ---------------------------------------------------------------------------

func (m DecisionsModel) View() string {
	var b strings.Builder

	bc := components.NewBreadcrumb("Home", "Ceremonies", "Decisions")
	b.WriteString(bc.View())
	b.WriteString("\n\n")

	switch m.mode {
	case decisionModeSelect:
		b.WriteString(m.viewSelect())
	case decisionModeApproveForm:
		b.WriteString(m.viewApproveForm())
	case decisionModeRejectForm:
		b.WriteString(m.viewRejectForm())
	case decisionModeSubmitting:
		b.WriteString(m.spinner.View() + " " + decDim.Render("Submitting decision..."))
	case decisionModeResult:
		b.WriteString(m.viewResult())
	}

	if m.err != nil && m.mode != decisionModeResult {
		b.WriteString("\n")
		b.WriteString(decDanger.Render("Error: " + m.err.Error()))
	}

	b.WriteString("\n\n")
	b.WriteString(m.helpBar.View())

	return b.String()
}

func (m DecisionsModel) viewSelect() string {
	var b strings.Builder

	b.WriteString(decHeading.Render("Pending Decisions"))
	b.WriteString("\n\n")

	if len(m.decisions) == 0 {
		b.WriteString(decDim.Render("No pending decisions for this story."))
		return b.String()
	}

	// Table header
	headerStyle := lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("147")).Underline(true)
	b.WriteString(fmt.Sprintf("  %s  %-14s %-12s\n",
		headerStyle.Render("Decision"),
		headerStyle.Render("Type"),
		headerStyle.Render("Status"),
	))

	for i, d := range m.decisions {
		cursor := "  "
		style := decDim
		if i == m.selected {
			cursor = decSelected.Render("> ")
			style = decValue
		}
		line := fmt.Sprintf("%-20s %-14s %-12s", truncID(d.ID), d.Type, d.Status)
		b.WriteString(cursor + style.Render(line) + "\n")
	}

	return b.String()
}

func (m DecisionsModel) viewApproveForm() string {
	var b strings.Builder

	b.WriteString(decApproveTag.Render("APPROVE"))
	b.WriteString("\n\n")

	if m.selected < len(m.decisions) {
		d := m.decisions[m.selected]
		b.WriteString(decLabel.Render("Decision: ") + decValue.Render(d.ID) + "\n")
		b.WriteString(decLabel.Render("Type:     ") + decValue.Render(d.Type) + "\n\n")
	}

	b.WriteString(decLabel.Render("Comment (optional):"))
	b.WriteString("\n")
	b.WriteString(m.commentInput.View())

	return b.String()
}

func (m DecisionsModel) viewRejectForm() string {
	var b strings.Builder

	b.WriteString(decRejectTag.Render("REJECT"))
	b.WriteString("\n\n")

	if m.selected < len(m.decisions) {
		d := m.decisions[m.selected]
		b.WriteString(decLabel.Render("Decision: ") + decValue.Render(d.ID) + "\n")
		b.WriteString(decLabel.Render("Type:     ") + decValue.Render(d.Type) + "\n\n")
	}

	b.WriteString(decLabel.Render("Reason (required):"))
	b.WriteString("\n")
	b.WriteString(m.reasonArea.View())

	return b.String()
}

func (m DecisionsModel) viewResult() string {
	if m.resultOK {
		check := lipgloss.NewStyle().Foreground(lipgloss.Color("120")).Render("✓")
		return check + " " + decSuccess.Render(m.resultMsg)
	}
	cross := lipgloss.NewStyle().Foreground(lipgloss.Color("210")).Render("✗")
	return cross + " " + decDanger.Render(m.resultMsg)
}

// ---------------------------------------------------------------------------
// Commands
// ---------------------------------------------------------------------------

func (m DecisionsModel) submitApprove(decisionID, comment string) tea.Cmd {
	storyID := m.storyID
	return func() tea.Msg {
		err := m.client.ApproveDecision(context.Background(), storyID, decisionID, comment)
		if err != nil {
			return decisionErrMsg{err: err}
		}
		return decisionApprovedMsg{}
	}
}

func (m DecisionsModel) submitReject(decisionID, reason string) tea.Cmd {
	storyID := m.storyID
	return func() tea.Msg {
		err := m.client.RejectDecision(context.Background(), storyID, decisionID, reason)
		if err != nil {
			return decisionErrMsg{err: err}
		}
		return decisionRejectedMsg{}
	}
}

// ---------------------------------------------------------------------------
// Help binding presets
// ---------------------------------------------------------------------------

func decisionSelectBindings() []components.HelpBinding {
	return []components.HelpBinding{
		{Key: "j/k", Description: "navigate"},
		{Key: "a", Description: "approve"},
		{Key: "x", Description: "reject"},
		{Key: "esc", Description: "back"},
	}
}

func decisionApproveBindings() []components.HelpBinding {
	return []components.HelpBinding{
		{Key: "enter", Description: "submit"},
		{Key: "esc", Description: "cancel"},
	}
}

func decisionRejectBindings() []components.HelpBinding {
	return []components.HelpBinding{
		{Key: "ctrl+d", Description: "submit"},
		{Key: "esc", Description: "cancel"},
	}
}
