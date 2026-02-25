package views

import (
	"strings"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

var (
	dashWelcome = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("39"))
	dashHint    = lipgloss.NewStyle().Foreground(lipgloss.Color("241"))
	dashKey     = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("82"))
)

// DashboardModel is the sub-model for the dashboard / home view.
type DashboardModel struct {
	width  int
	height int
}

// NewDashboardModel creates a zero-value dashboard model.
func NewDashboardModel() DashboardModel {
	return DashboardModel{}
}

// SetSize updates the layout dimensions available to the dashboard.
func (m DashboardModel) SetSize(w, h int) DashboardModel {
	m.width = w
	m.height = h
	return m
}

// Init implements tea.Model (called once at startup).
func (m DashboardModel) Init() tea.Cmd {
	return nil
}

// Update implements tea.Model.
func (m DashboardModel) Update(msg tea.Msg) (DashboardModel, tea.Cmd) {
	// The dashboard has no interactive state of its own yet.
	// All key handling is done by the root Model.
	return m, nil
}

// View implements tea.Model.
func (m DashboardModel) View() string {
	var b strings.Builder

	b.WriteString(dashWelcome.Render("Welcome to the SWE AI Fleet control plane"))
	b.WriteString("\n\n")
	b.WriteString(dashHint.Render("Navigate to a view using the keys below:"))
	b.WriteString("\n\n")

	entries := []struct {
		key  string
		desc string
	}{
		{"p", "Projects"},
		{"s", "Stories"},
		{"t", "Tasks"},
		{"c", "Ceremonies"},
		{"e", "Events"},
	}

	for _, e := range entries {
		b.WriteString("  ")
		b.WriteString(dashKey.Render(e.key))
		b.WriteString(dashHint.Render("  " + e.desc))
		b.WriteString("\n")
	}

	b.WriteString("\n")
	b.WriteString(dashHint.Render("Press q or ctrl+c to quit."))

	return b.String()
}
