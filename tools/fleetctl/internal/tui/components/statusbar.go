package components

import (
	"strings"

	"github.com/charmbracelet/lipgloss"
)

var (
	barStyle = lipgloss.NewStyle().
			Background(lipgloss.Color("236")).
			Foreground(lipgloss.Color("252")).
			Padding(0, 1)

	connectedDot    = lipgloss.NewStyle().Foreground(lipgloss.Color("120")).Render("●") // pastel mint
	disconnectedDot = lipgloss.NewStyle().Foreground(lipgloss.Color("210")).Render("●") // pastel coral
)

// StatusBar renders a bottom-of-screen status line showing the current
// view name and connection status.
type StatusBar struct {
	width     int
	connected bool
	view      string
}

// NewStatusBar creates a StatusBar with sensible defaults.
func NewStatusBar() StatusBar {
	return StatusBar{
		view: "Dashboard",
	}
}

// SetWidth returns a copy with the given terminal width.
func (s StatusBar) SetWidth(w int) StatusBar {
	s.width = w
	return s
}

// SetConnected returns a copy with the connection indicator set.
func (s StatusBar) SetConnected(c bool) StatusBar {
	s.connected = c
	return s
}

// SetView returns a copy with the current view label set.
func (s StatusBar) SetView(v string) StatusBar {
	s.view = v
	return s
}

// View renders the status bar as a single line.
func (s StatusBar) View() string {
	dot := disconnectedDot
	connLabel := "disconnected"
	if s.connected {
		dot = connectedDot
		connLabel = "connected"
	}

	left := "  " + s.view
	right := dot + " " + connLabel + "  "

	// Pad between left and right so the bar fills the terminal width.
	gap := max(s.width-lipgloss.Width(left)-lipgloss.Width(right), 0)
	line := left + strings.Repeat(" ", gap) + right

	return barStyle.Width(s.width).Render(line)
}
