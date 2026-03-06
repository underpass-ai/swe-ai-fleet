package components

import (
	"strings"

	"github.com/charmbracelet/lipgloss"
)

var (
	fsmActive   = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("120")).Background(lipgloss.Color("236")) // mint on dark
	fsmInactive = lipgloss.NewStyle().Foreground(lipgloss.Color("246"))                                            // warm grey
	fsmArrow    = lipgloss.NewStyle().Foreground(lipgloss.Color("183"))                                            // lavender
)

// fsmStates defines the canonical story lifecycle states in order.
var fsmStates = []string{
	"DRAFT",
	"PO_REVIEW",
	"READY_FOR_PLANNING",
	"IN_PROGRESS",
	"DONE",
}

// RenderFSMDiagram produces an ASCII visualization of the story state machine
// with the current state highlighted. The diagram is rendered as:
//
//	[DRAFT] ---> [PO_REVIEW] ---> [READY_FOR_PLANNING] ---> [IN_PROGRESS] ---> [DONE]
//
// The active state is rendered with a green highlight.
func RenderFSMDiagram(currentState string) string {
	var b strings.Builder

	normalised := strings.ToUpper(strings.TrimSpace(currentState))

	arrow := fsmArrow.Render(" ---> ")

	for i, state := range fsmStates {
		if i > 0 {
			b.WriteString(arrow)
		}

		label := "[ " + state + " ]"
		if state == normalised {
			b.WriteString(fsmActive.Render(label))
		} else {
			b.WriteString(fsmInactive.Render(label))
		}
	}

	b.WriteString("\n")

	return b.String()
}
