package views

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"sync"
	"time"

	"github.com/charmbracelet/bubbles/spinner"
	"github.com/charmbracelet/bubbles/textinput"
	"github.com/charmbracelet/bubbles/viewport"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/query"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/tui/components"
)

// ---------------------------------------------------------------------------
// Messages
// ---------------------------------------------------------------------------

// BackFromCommsMsg is emitted when the user presses Esc from the comms list view.
type BackFromCommsMsg struct{}

// CommsTickMsg triggers a display refresh so newly collected events appear.
// Exported so the root model can always route it to the comms sub-model.
type CommsTickMsg struct{}

// ---------------------------------------------------------------------------
// Category filter
// ---------------------------------------------------------------------------

// CommsCategory selects which events to show.
type CommsCategory int

const (
	CommsCatAll          CommsCategory = iota
	CommsCatDomain                     // domain events (story.*, ceremony.*, etc.)
	CommsCatGRPC                       // rpc.inbound / rpc.outbound
	CommsCatDeliberation               // deliberation.received, backlog_review.deliberation*
)

func commsCatLabel(c CommsCategory) string {
	switch c {
	case CommsCatAll:
		return "All"
	case CommsCatDomain:
		return "Domain"
	case CommsCatGRPC:
		return "gRPC"
	case CommsCatDeliberation:
		return "Deliberation"
	}
	return "?"
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------

var (
	commsHeading = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("147"))
	commsDim     = lipgloss.NewStyle().Foreground(lipgloss.Color("246"))
	commsGRPC    = lipgloss.NewStyle().Foreground(lipgloss.Color("183")) // lavender
	commsDomain  = lipgloss.NewStyle().Foreground(lipgloss.Color("117")) // sky blue
	commsDelib   = lipgloss.NewStyle().Foreground(lipgloss.Color("120")) // mint
	commsCatSel  = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("82"))
	commsCatDim  = lipgloss.NewStyle().Foreground(lipgloss.Color("241"))
	commsDetail  = lipgloss.NewStyle().Foreground(lipgloss.Color("252"))
	commsSearch  = lipgloss.NewStyle().Foreground(lipgloss.Color("214")) // orange
)

// ---------------------------------------------------------------------------
// Shared state — survives Bubble Tea value copies via pointer
// ---------------------------------------------------------------------------

// commsState holds the event subscription and collected events. It is shared
// by pointer so that the background collector goroutine and the Bubble Tea
// model always refer to the same data, regardless of which view is active.
type commsState struct {
	mu       sync.Mutex
	events   []domain.FleetEvent
	watching bool
	err      error
	cancel   context.CancelFunc
	started  bool
	lastLen  int // last known length, used by tick to detect new events
}

func (s *commsState) appendEvent(e domain.FleetEvent) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.events = append(s.events, e)
}

func (s *commsState) setError(err error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.err = err
	s.watching = false
}

func (s *commsState) snapshot() (events []domain.FleetEvent, watching bool, err error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	cp := make([]domain.FleetEvent, len(s.events))
	copy(cp, s.events)
	return cp, s.watching, s.err
}

func (s *commsState) clear() {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.events = nil
	s.lastLen = 0
}

func (s *commsState) stop() {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.cancel != nil {
		s.cancel()
		s.cancel = nil
	}
	s.watching = false
	s.started = false
}

// ---------------------------------------------------------------------------
// Model
// ---------------------------------------------------------------------------

// CommsModel is the sub-model for the Communications Monitor view.
type CommsModel struct {
	watchEvents *query.WatchEventsHandler
	state    *commsState // shared pointer — survives value copies
	viewport viewport.Model
	filtered []domain.FleetEvent

	category    CommsCategory
	showDetail  bool
	detailIdx   int // index in filtered list
	cursor      int // cursor position in filtered list
	searching   bool
	searchInput textinput.Model
	searchTerm  string // active search term (lowercased)
	helpBar     components.HelpBar
	spinner     spinner.Model
	width       int
	height      int
}

// NewCommsModel creates a CommsModel wired to the given WatchEventsHandler.
func NewCommsModel(watchEvents *query.WatchEventsHandler) CommsModel {
	vp := viewport.New(80, 20)
	vp.SetContent("Waiting for events...")

	si := textinput.New()
	si.Placeholder = "search payload..."
	si.CharLimit = 120
	si.Width = 40

	return CommsModel{
		watchEvents: watchEvents,
		state:       &commsState{},
		viewport:    vp,
		searchInput: si,
		spinner:     components.NewSpinner(),
		helpBar: components.NewHelpBar(
			components.HelpBinding{Key: "1-4", Description: "filter"},
			components.HelpBinding{Key: "/", Description: "search"},
			components.HelpBinding{Key: "enter", Description: "detail"},
			components.HelpBinding{Key: "r", Description: "reconnect"},
			components.HelpBinding{Key: "c", Description: "clear"},
			components.HelpBinding{Key: "esc", Description: "back"},
		),
	}
}

// SetSize updates the layout dimensions.
func (m CommsModel) SetSize(w, h int) CommsModel {
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

// Init starts the background event collector (only once for the app lifetime).
func (m CommsModel) Init() tea.Cmd {
	cmds := []tea.Cmd{m.spinner.Tick, commsTick()}

	m.state.mu.Lock()
	alreadyStarted := m.state.started
	m.state.mu.Unlock()

	if !alreadyStarted {
		cmds = append(cmds, m.startCollector())
	}
	return tea.Batch(cmds...)
}

// Update handles messages for the comms view.
func (m CommsModel) Update(msg tea.Msg) (CommsModel, tea.Cmd) {
	var cmds []tea.Cmd

	switch msg := msg.(type) {
	case CommsTickMsg:
		// Refresh display from shared state.
		events, watching, err := m.state.snapshot()
		m.state.mu.Lock()
		changed := len(events) != m.state.lastLen
		m.state.lastLen = len(events)
		m.state.mu.Unlock()

		_ = watching
		_ = err

		if changed || len(m.filtered) == 0 {
			m.applyFilterFrom(events)
			if !m.showDetail {
				m.viewport.SetContent(m.renderFiltered())
				if changed {
					m.viewport.GotoBottom()
				}
			}
		}
		return m, commsTick()

	case spinner.TickMsg:
		var cmd tea.Cmd
		m.spinner, cmd = m.spinner.Update(msg)
		cmds = append(cmds, cmd)

	case tea.KeyMsg:
		// --- Detail mode ---
		if m.showDetail {
			switch msg.String() {
			case "esc", "enter":
				m.showDetail = false
				m.viewport.SetContent(m.renderFiltered())
				return m, nil
			}
			var cmd tea.Cmd
			m.viewport, cmd = m.viewport.Update(msg)
			cmds = append(cmds, cmd)
			return m, tea.Batch(cmds...)
		}

		// --- Search input mode ---
		if m.searching {
			switch msg.String() {
			case "esc":
				// Cancel search, clear term.
				m.searching = false
				m.searchInput.Reset()
				m.searchTerm = ""
				m.searchInput.Blur()
				m.refreshFromState()
				return m, nil
			case "enter":
				// Commit search term.
				m.searching = false
				m.searchTerm = strings.ToLower(strings.TrimSpace(m.searchInput.Value()))
				m.searchInput.Blur()
				m.refreshFromState()
				return m, nil
			default:
				var cmd tea.Cmd
				m.searchInput, cmd = m.searchInput.Update(msg)
				// Live filter while typing.
				m.searchTerm = strings.ToLower(strings.TrimSpace(m.searchInput.Value()))
				m.refreshFromState()
				return m, cmd
			}
		}

		// --- Normal list mode ---
		switch msg.String() {
		case "esc":
			if m.searchTerm != "" {
				// First esc clears an active search filter.
				m.searchTerm = ""
				m.searchInput.Reset()
				m.refreshFromState()
				return m, nil
			}
			return m, func() tea.Msg { return BackFromCommsMsg{} }
		case "/":
			m.searching = true
			m.searchInput.Focus()
			return m, textinput.Blink
		case "1":
			m.category = CommsCatAll
			m.refreshFromState()
			return m, nil
		case "2":
			m.category = CommsCatDomain
			m.refreshFromState()
			return m, nil
		case "3":
			m.category = CommsCatGRPC
			m.refreshFromState()
			return m, nil
		case "4":
			m.category = CommsCatDeliberation
			m.refreshFromState()
			return m, nil
		case "up", "k":
			if m.cursor > 0 {
				m.cursor--
				m.viewport.SetContent(m.renderFiltered())
			}
			return m, nil
		case "down", "j":
			if m.cursor < len(m.filtered)-1 {
				m.cursor++
				m.viewport.SetContent(m.renderFiltered())
			}
			return m, nil
		case "enter":
			if len(m.filtered) > 0 && m.cursor < len(m.filtered) {
				m.detailIdx = m.cursor
				m.showDetail = true
				m.viewport.SetContent(m.renderDetail(m.filtered[m.cursor]))
				m.viewport.GotoTop()
				return m, nil
			}
		case "r":
			m.state.stop()
			m.state.clear()
			m.filtered = nil
			m.viewport.SetContent("Reconnecting...")
			return m, tea.Batch(m.spinner.Tick, m.startCollector())
		case "c":
			m.state.clear()
			m.filtered = nil
			m.viewport.SetContent("Events cleared. Waiting for new events...")
			return m, nil
		}

		var cmd tea.Cmd
		m.viewport, cmd = m.viewport.Update(msg)
		cmds = append(cmds, cmd)
	}

	return m, tea.Batch(cmds...)
}

// Stop cancels the background event collector. Called only on app quit.
func (m *CommsModel) Stop() {
	m.state.stop()
}

// View renders the comms view.
func (m CommsModel) View() string {
	var b strings.Builder

	bc := components.NewBreadcrumb("Home", "Communications")
	b.WriteString(bc.View())
	b.WriteString("\n")

	m.state.mu.Lock()
	watching := m.state.watching
	totalEvents := len(m.state.events)
	errVal := m.state.err
	m.state.mu.Unlock()

	statusDot := evtLiveOn
	if !watching {
		statusDot = evtLiveOff
	}

	fmt.Fprintf(&b, "%s %s  %s\n",
		statusDot,
		commsHeading.Render("Communications Monitor"),
		commsDim.Render(fmt.Sprintf("(%d/%d events)", len(m.filtered), totalEvents)),
	)

	// Category tabs.
	cats := []CommsCategory{CommsCatAll, CommsCatDomain, CommsCatGRPC, CommsCatDeliberation}
	labels := make([]string, len(cats))
	for i, c := range cats {
		label := fmt.Sprintf("[%d] %s", i+1, commsCatLabel(c))
		if c == m.category {
			labels[i] = commsCatSel.Render(label)
		} else {
			labels[i] = commsCatDim.Render(label)
		}
	}
	b.WriteString(strings.Join(labels, "  "))

	// Search indicator / input.
	if m.searching {
		b.WriteString("  " + commsSearch.Render("/") + " " + m.searchInput.View())
	} else if m.searchTerm != "" {
		b.WriteString("  " + commsSearch.Render("search: "+m.searchTerm) + " " + commsDim.Render("[esc to clear]"))
	}
	b.WriteString("\n\n")

	if errVal != nil {
		errStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("210")).Bold(true)
		b.WriteString(errStyle.Render("Error: "+errVal.Error()) + "\n\n")
	}

	if !watching && totalEvents == 0 {
		b.WriteString(m.spinner.View() + " " + commsDim.Render("Connecting to event stream..."))
		return b.String()
	}

	b.WriteString(m.viewport.View())
	b.WriteString("\n")
	b.WriteString(m.helpBar.View())

	return b.String()
}

// ---------------------------------------------------------------------------
// Background collector
// ---------------------------------------------------------------------------

// startCollector launches the background goroutine that subscribes to the
// event stream and collects events into shared state. It runs for the entire
// app lifetime, independent of which view is active. On stream drop it
// automatically reconnects with exponential backoff.
func (m CommsModel) startCollector() tea.Cmd {
	state := m.state
	handler := m.watchEvents
	return func() tea.Msg {
		ctx, cancel := context.WithCancel(context.Background())

		state.mu.Lock()
		state.started = true
		state.cancel = cancel
		state.watching = false
		state.err = nil
		state.mu.Unlock()

		ch, err := handler.Handle(ctx, query.WatchEventsQuery{})
		if err != nil {
			cancel()
			state.setError(err)
			return CommsTickMsg{}
		}

		state.mu.Lock()
		state.watching = true
		state.mu.Unlock()

		// Collect events in background with auto-reconnect.
		go func() {
			backoff := time.Second
			const maxBackoff = 30 * time.Second

			for {
				for evt := range ch {
					state.appendEvent(evt)
					backoff = time.Second // reset on successful event
				}

				// Channel closed — stream ended.
				state.mu.Lock()
				state.watching = false
				state.mu.Unlock()

				// Wait before reconnecting, respecting cancellation.
				select {
				case <-ctx.Done():
					return
				case <-time.After(backoff):
				}

				state.mu.Lock()
				state.err = fmt.Errorf("reconnecting (backoff %s)...", backoff)
				state.mu.Unlock()

				ch, err = handler.Handle(ctx, query.WatchEventsQuery{})
				if err != nil {
					state.setError(fmt.Errorf("reconnect failed: %w", err))
					backoff = min(backoff*2, maxBackoff)
					// Keep retrying until context is cancelled.
					select {
					case <-ctx.Done():
						return
					case <-time.After(backoff):
					}
					continue
				}

				state.mu.Lock()
				state.watching = true
				state.err = nil
				state.mu.Unlock()
				backoff = time.Second
			}
		}()

		return CommsTickMsg{} // trigger initial refresh
	}
}

// commsTick returns a cmd that sends a commsTickMsg after a short delay.
func commsTick() tea.Cmd {
	return tea.Tick(500*time.Millisecond, func(time.Time) tea.Msg {
		return CommsTickMsg{}
	})
}

// ---------------------------------------------------------------------------
// Filtering & rendering helpers
// ---------------------------------------------------------------------------

func (m *CommsModel) refreshFromState() {
	events, _, _ := m.state.snapshot()
	m.applyFilterFrom(events)
	m.viewport.SetContent(m.renderFiltered())
}

func (m *CommsModel) applyFilterFrom(events []domain.FleetEvent) {
	cat := commsCatLabel(m.category)
	filtered := make([]domain.FleetEvent, 0, len(events))
	for _, e := range events {
		if m.category != CommsCatAll && !matchesCategory(e, cat) {
			continue
		}
		if m.searchTerm != "" && !matchesSearch(e, m.searchTerm) {
			continue
		}
		filtered = append(filtered, e)
	}
	m.filtered = filtered
	if m.cursor >= len(m.filtered) {
		m.cursor = max(len(m.filtered)-1, 0)
	}
}

func matchesSearch(e domain.FleetEvent, term string) bool {
	// Search in payload (the main body content).
	if len(e.Payload) > 0 && strings.Contains(strings.ToLower(string(e.Payload)), term) {
		return true
	}
	// Also match against type, producer, correlation ID.
	if strings.Contains(strings.ToLower(e.Type), term) {
		return true
	}
	if strings.Contains(strings.ToLower(e.Producer), term) {
		return true
	}
	if strings.Contains(strings.ToLower(e.CorrelationID), term) {
		return true
	}
	return false
}

func matchesCategory(e domain.FleetEvent, cat string) bool {
	switch cat {
	case "Domain":
		return e.Category() == "domain"
	case "gRPC":
		return e.Category() == "grpc"
	case "Deliberation":
		return e.Category() == "deliberation"
	}
	return true
}

func (m CommsModel) renderFiltered() string {
	if len(m.filtered) == 0 {
		return "No events matching filter."
	}
	var b strings.Builder
	for i, e := range m.filtered {
		prefix := "  "
		if i == m.cursor {
			prefix = "> "
		}
		line := e.Summary()
		switch e.Category() {
		case "grpc":
			b.WriteString(commsGRPC.Render(prefix + line))
		case "deliberation":
			b.WriteString(commsDelib.Render(prefix + line))
		default:
			b.WriteString(commsDomain.Render(prefix + line))
		}
		b.WriteString("\n")
	}
	return b.String()
}

func (m CommsModel) renderDetail(e domain.FleetEvent) string {
	var b strings.Builder

	b.WriteString(commsHeading.Render("Event Detail"))
	b.WriteString("\n\n")

	fields := [][2]string{
		{"Type:", e.Type},
		{"Key:", e.IdempotencyKey},
		{"Corr:", e.CorrelationID},
		{"Time:", e.Timestamp},
		{"From:", e.Producer},
	}
	for _, f := range fields {
		fmt.Fprintf(&b, "%s  %s\n", commsDim.Render(f[0]), commsDetail.Render(f[1]))
	}

	if len(e.Payload) > 0 {
		b.WriteString("\n")
		b.WriteString(commsHeading.Render("Payload"))
		b.WriteString("\n")
		var pretty bytes.Buffer
		if err := json.Indent(&pretty, e.Payload, "", "  "); err == nil {
			b.WriteString(commsDetail.Render(pretty.String()))
		} else {
			b.WriteString(commsDetail.Render(string(e.Payload)))
		}
		b.WriteString("\n")
	}

	b.WriteString("\n")
	b.WriteString(commsDim.Render("Press Enter or Esc to go back"))

	return b.String()
}
