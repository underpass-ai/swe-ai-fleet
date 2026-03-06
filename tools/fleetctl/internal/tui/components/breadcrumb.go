package components

import (
	"strings"

	"github.com/charmbracelet/lipgloss"
)

var (
	crumbSeparator = lipgloss.NewStyle().Foreground(lipgloss.Color("240")).Render(" > ")
	crumbActive    = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("147")) // pastel periwinkle
	crumbInactive  = lipgloss.NewStyle().Foreground(lipgloss.Color("246"))            // warm grey
)

// Breadcrumb renders a navigation breadcrumb trail such as
// "Home > Projects > Story-123".
type Breadcrumb struct {
	items []string
}

// NewBreadcrumb creates a breadcrumb from the given path segments.
// The last item is rendered as the active (highlighted) segment.
func NewBreadcrumb(items ...string) Breadcrumb {
	return Breadcrumb{items: items}
}

// View renders the breadcrumb as a styled single-line string.
func (b Breadcrumb) View() string {
	if len(b.items) == 0 {
		return ""
	}

	var sb strings.Builder
	for i, item := range b.items {
		if i > 0 {
			sb.WriteString(crumbSeparator)
		}
		if i == len(b.items)-1 {
			sb.WriteString(crumbActive.Render(item))
		} else {
			sb.WriteString(crumbInactive.Render(item))
		}
	}
	return sb.String()
}
