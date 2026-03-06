package components

import (
	"strings"

	"github.com/charmbracelet/lipgloss"
)

// Pastel key-hint styles.
var (
	helpKeyStyle  = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("152"))  // pastel blue-grey
	helpDescStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("246"))              // warm grey
	helpSepStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("240"))              // subtle separator
	helpBarBg     = lipgloss.NewStyle().Background(lipgloss.Color("235")).Padding(0, 1)
)

// HelpBinding associates a key label with an action description.
type HelpBinding struct {
	Key         string
	Description string
}

// HelpBar renders a context-sensitive line of key hints at the bottom
// of the terminal.
type HelpBar struct {
	bindings []HelpBinding
	width    int
}

// NewHelpBar creates a HelpBar from the given bindings.
func NewHelpBar(bindings ...HelpBinding) HelpBar {
	return HelpBar{bindings: bindings}
}

// SetWidth returns a copy with the terminal width set.
func (h HelpBar) SetWidth(w int) HelpBar {
	h.width = w
	return h
}

// SetBindings returns a copy with the bindings replaced.
func (h HelpBar) SetBindings(bindings ...HelpBinding) HelpBar {
	h.bindings = bindings
	return h
}

// View renders the help bar as a styled single line.
func (h HelpBar) View() string {
	if len(h.bindings) == 0 {
		return ""
	}

	sep := helpSepStyle.Render(" | ")
	parts := make([]string, 0, len(h.bindings))
	for _, b := range h.bindings {
		parts = append(parts, helpKeyStyle.Render(b.Key)+" "+helpDescStyle.Render(b.Description))
	}
	line := strings.Join(parts, sep)

	if h.width > 0 {
		return helpBarBg.Width(h.width).Render(line)
	}
	return helpBarBg.Render(line)
}
