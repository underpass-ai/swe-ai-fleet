package tui

import "github.com/charmbracelet/lipgloss"

// Pastel color palette — each color expresses intent.
const (
	// Core intent colors (pastel)
	ColorInfo      = lipgloss.Color("117") // soft sky blue — informational
	ColorSuccess   = lipgloss.Color("120") // soft mint green — success, approved, done
	ColorWarning   = lipgloss.Color("222") // soft peach — caution, in-progress
	ColorDanger    = lipgloss.Color("210") // soft coral — error, rejected
	ColorAccent    = lipgloss.Color("183") // soft lavender — highlights, active elements
	ColorMuted     = lipgloss.Color("246") // warm grey — secondary, dim text
	ColorSubtle    = lipgloss.Color("240") // darker grey — hints, separators
	ColorKeyHint   = lipgloss.Color("152") // pastel blue-grey — key binding labels
	ColorSelected  = lipgloss.Color("115") // pastel teal — selected items
	ColorHeading   = lipgloss.Color("147") // pastel periwinkle — section headings
	ColorBarBg     = lipgloss.Color("236") // dark bg for bars
	ColorBarFg     = lipgloss.Color("252") // light fg for bars
	ColorProgressA = lipgloss.Color("120") // filled progress (mint)
	ColorProgressB = lipgloss.Color("240") // unfilled progress (dim)
)

// Application-wide Lip Gloss styles used by all TUI views and components.
var (
	AppStyle       = lipgloss.NewStyle().Padding(1, 2)
	TitleStyle     = lipgloss.NewStyle().Bold(true).Foreground(ColorAccent)
	SubtitleStyle  = lipgloss.NewStyle().Foreground(ColorMuted)
	ErrorStyle     = lipgloss.NewStyle().Foreground(ColorDanger).Bold(true)
	SuccessStyle   = lipgloss.NewStyle().Foreground(ColorSuccess)
	WarningStyle   = lipgloss.NewStyle().Foreground(ColorWarning)
	ActiveStyle    = lipgloss.NewStyle().Foreground(ColorSelected).Bold(true)
	DimStyle       = lipgloss.NewStyle().Foreground(ColorMuted)
	BorderStyle    = lipgloss.NewStyle().Border(lipgloss.RoundedBorder()).Padding(0, 1)
	StatusBarStyle = lipgloss.NewStyle().Background(ColorBarBg).Foreground(ColorBarFg).Padding(0, 1)
)
