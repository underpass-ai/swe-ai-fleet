package components

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

// Pastel progress bar styles.
var (
	progressFilled  = lipgloss.NewStyle().Foreground(lipgloss.Color("120")) // soft mint green
	progressEmpty   = lipgloss.NewStyle().Foreground(lipgloss.Color("240")) // dim grey
	progressLabel   = lipgloss.NewStyle().Foreground(lipgloss.Color("246")) // warm grey
	progressPercent = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("115")) // pastel teal
)

// ProgressBar renders a horizontal bar indicating step completion.
type ProgressBar struct {
	total   int
	current int
	width   int
}

// NewProgressBar creates a ProgressBar with the given total steps.
func NewProgressBar(total int) ProgressBar {
	if total < 0 {
		total = 0
	}
	return ProgressBar{total: total, width: 24}
}

// SetCurrent updates the current step count.
func (p ProgressBar) SetCurrent(n int) ProgressBar {
	if n < 0 {
		n = 0
	}
	if n > p.total {
		n = p.total
	}
	p.current = n
	return p
}

// SetWidth sets the bar character width.
func (p ProgressBar) SetWidth(w int) ProgressBar {
	if w < 4 {
		w = 4
	}
	p.width = w
	return p
}

// View renders the progress bar.
func (p ProgressBar) View() string {
	if p.total <= 0 {
		return progressLabel.Render("No steps")
	}

	filled := p.width * p.current / p.total
	empty := p.width - filled

	var b strings.Builder
	b.WriteString(progressFilled.Render(strings.Repeat("█", filled)))
	b.WriteString(progressEmpty.Render(strings.Repeat("░", empty)))
	b.WriteString(" ")
	b.WriteString(progressPercent.Render(fmt.Sprintf("%d/%d", p.current, p.total)))
	b.WriteString(" ")
	b.WriteString(progressLabel.Render("steps"))

	return b.String()
}
