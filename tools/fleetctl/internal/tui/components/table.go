package components

import (
	"github.com/charmbracelet/bubbles/table"
	"github.com/charmbracelet/lipgloss"
)

// NewTable creates a pre-styled bubbles/table.Model suitable for use across
// all TUI views. It applies consistent header and selection styling using
// the pastel palette.
func NewTable(columns []table.Column, rows []table.Row, height int) table.Model {
	t := table.New(
		table.WithColumns(columns),
		table.WithRows(rows),
		table.WithFocused(true),
		table.WithHeight(height),
	)
	s := table.DefaultStyles()
	s.Header = s.Header.
		BorderStyle(lipgloss.NormalBorder()).
		BorderForeground(lipgloss.Color("240")).
		BorderBottom(true).
		Bold(true).
		Foreground(lipgloss.Color("147")) // pastel periwinkle headers
	s.Selected = s.Selected.
		Foreground(lipgloss.Color("252")).
		Background(lipgloss.Color("237")). // subtle dark selection
		Bold(false)
	t.SetStyles(s)
	return t
}
