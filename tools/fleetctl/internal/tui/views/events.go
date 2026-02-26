package views

import (
	"context"
	"fmt"
	"strings"

	"github.com/charmbracelet/bubbles/spinner"
	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/tui/components"
)

// ---------------------------------------------------------------------------
// Messages
// ---------------------------------------------------------------------------

type eventReceivedMsg struct{ event domain.FleetEvent }
type eventsWatchStartedMsg struct{ ch <-chan domain.FleetEvent }
type eventsErrMsg struct{ err error }

// ---------------------------------------------------------------------------
// Pastel styles
// ---------------------------------------------------------------------------

var (
	evtHeading   = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("147")) // periwinkle
	evtDim       = lipgloss.NewStyle().Foreground(lipgloss.Color("246"))            // warm grey
	evtType      = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("117")) // sky blue
	evtTimestamp = lipgloss.NewStyle().Foreground(lipgloss.Color("246"))             // warm grey
	evtLiveOn    = lipgloss.NewStyle().Foreground(lipgloss.Color("120")).Render("●") // mint = connected
	evtLiveOff   = lipgloss.NewStyle().Foreground(lipgloss.Color("210")).Render("●") // coral = disconnected
)

// ---------------------------------------------------------------------------
// Model
// ---------------------------------------------------------------------------

// EventsModel is the sub-model for the real-time event feed view.
type EventsModel struct {
	client   ports.FleetClient
	viewport viewport.Model
	events   []domain.FleetEvent
	eventCh  <-chan domain.FleetEvent
	cancel   context.CancelFunc

	helpBar  components.HelpBar
	spinner  spinner.Model
	watching bool
	err      error
	width    int
	height   int
}

// NewEventsModel creates an EventsModel wired to the given FleetClient.
func NewEventsModel(client ports.FleetClient) EventsModel {
	vp := viewport.New(80, 20)
	vp.SetContent("Waiting for events...")

	return EventsModel{
		client:   client,
		viewport: vp,
		spinner:  components.NewSpinner(),
		helpBar: components.NewHelpBar(
			components.HelpBinding{Key: "r", Description: "reconnect"},
			components.HelpBinding{Key: "c", Description: "clear"},
			components.HelpBinding{Key: "scroll", Description: "up/down"},
			components.HelpBinding{Key: "esc", Description: "back"},
		),
	}
}

// SetSize updates the available layout dimensions.
func (m EventsModel) SetSize(w, h int) EventsModel {
	m.width = w
	m.height = h
	vpH := max(h-10, 4)
	m.viewport.Width = w
	m.viewport.Height = vpH
	m.helpBar = m.helpBar.SetWidth(w)
	return m
}

// ---------------------------------------------------------------------------
// tea.Model interface
// ---------------------------------------------------------------------------

// Init starts watching events.
func (m EventsModel) Init() tea.Cmd {
	return tea.Batch(m.spinner.Tick, m.startWatching())
}

// Update handles messages for the events view.
func (m EventsModel) Update(msg tea.Msg) (EventsModel, tea.Cmd) {
	var cmds []tea.Cmd

	switch msg := msg.(type) {

	case eventsWatchStartedMsg:
		m.watching = true
		m.eventCh = msg.ch
		m.err = nil
		return m, m.waitForEvent()

	case eventReceivedMsg:
		m.events = append(m.events, msg.event)
		m.viewport.SetContent(m.renderEvents())
		m.viewport.GotoBottom()
		return m, m.waitForEvent()

	case eventsErrMsg:
		m.err = msg.err
		m.watching = false
		return m, nil

	case spinner.TickMsg:
		var cmd tea.Cmd
		m.spinner, cmd = m.spinner.Update(msg)
		cmds = append(cmds, cmd)

	case tea.KeyMsg:
		switch msg.String() {
		case "r":
			m.stopWatching()
			m.events = nil
			m.viewport.SetContent("Reconnecting...")
			return m, tea.Batch(m.spinner.Tick, m.startWatching())
		case "c":
			m.events = nil
			m.viewport.SetContent("Events cleared. Waiting for new events...")
			return m, nil
		}

		var cmd tea.Cmd
		m.viewport, cmd = m.viewport.Update(msg)
		cmds = append(cmds, cmd)
	}

	return m, tea.Batch(cmds...)
}

// Stop cancels the event watch context when leaving the view.
func (m *EventsModel) Stop() {
	m.stopWatching()
}

func (m *EventsModel) stopWatching() {
	if m.cancel != nil {
		m.cancel()
		m.cancel = nil
	}
	m.watching = false
	m.eventCh = nil
}

// View renders the events view.
func (m EventsModel) View() string {
	var b strings.Builder

	bc := components.NewBreadcrumb("Home", "Events")
	b.WriteString(bc.View())
	b.WriteString("\n")

	// Header with event count.
	statusDot := evtLiveOn
	if !m.watching {
		statusDot = evtLiveOff
	}

	fmt.Fprintf(&b, "%s %s  %s\n\n",
		statusDot,
		evtHeading.Render("Event Stream"),
		evtDim.Render(fmt.Sprintf("(%d events)", len(m.events))),
	)

	if m.err != nil {
		errStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("210")).Bold(true)
		b.WriteString(errStyle.Render("Error: "+m.err.Error()) + "\n\n")
	}

	if !m.watching && m.eventCh == nil && len(m.events) == 0 {
		b.WriteString(m.spinner.View() + " " + evtDim.Render("Connecting to event stream..."))
		return b.String()
	}

	b.WriteString(m.viewport.View())
	b.WriteString("\n")
	b.WriteString(m.helpBar.View())

	return b.String()
}

// ---------------------------------------------------------------------------
// Commands
// ---------------------------------------------------------------------------

func (m EventsModel) startWatching() tea.Cmd {
	return func() tea.Msg {
		ctx, cancel := context.WithCancel(context.Background())
		ch, err := m.client.WatchEvents(ctx, nil, "")
		if err != nil {
			cancel()
			return eventsErrMsg{err: err}
		}
		_ = cancel
		return eventsWatchStartedMsg{ch: ch}
	}
}

func (m EventsModel) waitForEvent() tea.Cmd {
	ch := m.eventCh
	if ch == nil {
		return nil
	}
	return func() tea.Msg {
		event, ok := <-ch
		if !ok {
			return eventsErrMsg{err: fmt.Errorf("event stream closed")}
		}
		return eventReceivedMsg{event: event}
	}
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

func (m EventsModel) renderEvents() string {
	if len(m.events) == 0 {
		return "Waiting for events..."
	}

	var b strings.Builder
	for _, e := range m.events {
		ts := evtTimestamp.Render("[" + e.Timestamp + "]")
		et := evtType.Render("[" + e.Type + "]")
		fmt.Fprintf(&b, "%s %s %s\n", ts, et, e.Summary())
	}

	return b.String()
}
