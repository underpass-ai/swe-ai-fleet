package views

import (
	"context"
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"fmt"
	"strings"

	"github.com/charmbracelet/bubbles/spinner"
	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/tui/components"
)

// ---------------------------------------------------------------------------
// Messages
// ---------------------------------------------------------------------------

type enrollSuccessMsg struct {
	clientID  string
	expiresAt string
}
type enrollErrMsg struct{ err error }

// ---------------------------------------------------------------------------
// Steps
// ---------------------------------------------------------------------------

type enrollStep int

const (
	enrollStepAPIKey     enrollStep = iota // Enter API key
	enrollStepConfirm                      // Confirm before enrolling
	enrollStepProcessing                   // Waiting for server response
	enrollStepDone                         // Success or error
)

// ---------------------------------------------------------------------------
// Model
// ---------------------------------------------------------------------------

// EnrollmentModel is the sub-model for the first-run enrollment wizard.
type EnrollmentModel struct {
	client      ports.FleetClient
	step        enrollStep
	apiKeyInput textinput.Model

	spinner   spinner.Model
	err       error
	resultMsg string
	width     int
	height    int
}

// NewEnrollmentModel creates an EnrollmentModel wired to the given FleetClient.
func NewEnrollmentModel(client ports.FleetClient) EnrollmentModel {
	apiIn := textinput.New()
	apiIn.Placeholder = "fleet-api-key-..."
	apiIn.CharLimit = 256
	apiIn.Width = 50
	apiIn.EchoMode = textinput.EchoPassword
	apiIn.EchoCharacter = '*'

	return EnrollmentModel{
		client:      client,
		step:        enrollStepAPIKey,
		apiKeyInput: apiIn,
		spinner:     components.NewSpinner(),
	}
}

// SetSize updates the available layout dimensions.
func (m EnrollmentModel) SetSize(w, h int) EnrollmentModel {
	m.width = w
	m.height = h
	return m
}

// ---------------------------------------------------------------------------
// tea.Model interface
// ---------------------------------------------------------------------------

// Init focuses the API key input.
func (m EnrollmentModel) Init() tea.Cmd {
	m.apiKeyInput.Focus()
	return textinput.Blink
}

// Update handles messages for the enrollment wizard.
func (m EnrollmentModel) Update(msg tea.Msg) (EnrollmentModel, tea.Cmd) {
	switch msg := msg.(type) {

	case enrollSuccessMsg:
		m.step = enrollStepDone
		m.err = nil
		m.resultMsg = fmt.Sprintf("Enrollment successful!\n\n  Client ID:  %s\n  Expires:    %s", msg.clientID, msg.expiresAt)
		return m, nil

	case enrollErrMsg:
		m.step = enrollStepDone
		m.err = msg.err
		m.resultMsg = ""
		return m, nil

	case spinner.TickMsg:
		var cmd tea.Cmd
		m.spinner, cmd = m.spinner.Update(msg)
		return m, cmd

	case tea.KeyMsg:
		switch m.step {
		case enrollStepAPIKey:
			return m.updateAPIKeyStep(msg)
		case enrollStepConfirm:
			return m.updateConfirmStep(msg)
		case enrollStepDone:
			// Any key returns to dashboard (handled by parent).
			return m, nil
		}
	}

	return m, nil
}

func (m EnrollmentModel) updateAPIKeyStep(msg tea.KeyMsg) (EnrollmentModel, tea.Cmd) {
	switch msg.String() {
	case "enter":
		apiKey := strings.TrimSpace(m.apiKeyInput.Value())
		if apiKey == "" {
			m.err = fmt.Errorf("API key is required")
			return m, nil
		}
		m.err = nil
		m.step = enrollStepConfirm
		return m, nil
	case "esc":
		return m, nil
	}

	var cmd tea.Cmd
	m.apiKeyInput, cmd = m.apiKeyInput.Update(msg)
	return m, cmd
}

func (m EnrollmentModel) updateConfirmStep(msg tea.KeyMsg) (EnrollmentModel, tea.Cmd) {
	switch msg.String() {
	case "y", "Y", "enter":
		m.step = enrollStepProcessing
		apiKey := strings.TrimSpace(m.apiKeyInput.Value())
		return m, tea.Batch(m.spinner.Tick, m.doEnroll(apiKey))
	case "n", "N", "esc":
		m.step = enrollStepAPIKey
		m.apiKeyInput.Focus()
		return m, textinput.Blink
	}
	return m, nil
}

// View renders the enrollment wizard.
func (m EnrollmentModel) View() string {
	var b strings.Builder

	bc := components.NewBreadcrumb("Home", "Enrollment")
	b.WriteString(bc.View())
	b.WriteString("\n\n")

	title := lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("39"))
	hint := lipgloss.NewStyle().Foreground(lipgloss.Color("241"))
	success := lipgloss.NewStyle().Foreground(lipgloss.Color("82")).Bold(true)
	errStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("196")).Bold(true)

	b.WriteString(title.Render("Device Enrollment Wizard"))
	b.WriteString("\n\n")

	// Progress indicator
	b.WriteString(m.stepIndicator())
	b.WriteString("\n\n")

	switch m.step {
	case enrollStepAPIKey:
		b.WriteString("Enter your API key to register this device with the fleet control plane.\n\n")
		b.WriteString("API Key:\n")
		b.WriteString(m.apiKeyInput.View())
		b.WriteString("\n\n")
		if m.err != nil {
			b.WriteString(errStyle.Render("Error: "+m.err.Error()) + "\n\n")
		}
		b.WriteString(hint.Render("enter: continue  esc: back"))

	case enrollStepConfirm:
		b.WriteString("Ready to enroll this device.\n\n")
		b.WriteString(hint.Render("  API Key: ") + "****" + "\n")
		b.WriteString(hint.Render("  A new key pair and CSR will be generated.\n\n"))
		b.WriteString("Proceed? ")
		b.WriteString(lipgloss.NewStyle().Bold(true).Render("[Y/n]"))
		b.WriteString("\n\n")
		b.WriteString(hint.Render("y: enroll  n: go back"))

	case enrollStepProcessing:
		b.WriteString(m.spinner.View() + " Enrolling device...")
		b.WriteString("\n\n")
		b.WriteString(hint.Render("Generating key pair, creating CSR, and contacting control plane..."))

	case enrollStepDone:
		if m.err != nil {
			b.WriteString(errStyle.Render("Enrollment failed: " + m.err.Error()))
			b.WriteString("\n\n")
			b.WriteString(hint.Render("Press esc to go back and try again."))
		} else {
			b.WriteString(success.Render(m.resultMsg))
			b.WriteString("\n\n")
			b.WriteString(hint.Render("Press esc to return to dashboard."))
		}
	}

	return b.String()
}

func (m EnrollmentModel) stepIndicator() string {
	steps := []string{"API Key", "Confirm", "Processing", "Done"}
	active := lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("82"))
	done := lipgloss.NewStyle().Foreground(lipgloss.Color("82"))
	pending := lipgloss.NewStyle().Foreground(lipgloss.Color("241"))

	var parts []string
	for i, s := range steps {
		step := enrollStep(i)
		if step == m.step {
			parts = append(parts, active.Render("("+s+")"))
		} else if step < m.step {
			parts = append(parts, done.Render(s))
		} else {
			parts = append(parts, pending.Render(s))
		}
	}
	return strings.Join(parts, " > ")
}

// ---------------------------------------------------------------------------
// Commands
// ---------------------------------------------------------------------------

func (m EnrollmentModel) doEnroll(apiKey string) tea.Cmd {
	return func() tea.Msg {
		// Generate an ECDSA P-256 key pair.
		privateKey, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
		if err != nil {
			return enrollErrMsg{err: fmt.Errorf("key generation failed: %w", err)}
		}

		// Create a CSR.
		csrTemplate := &x509.CertificateRequest{
			Subject: pkix.Name{
				CommonName:   "fleetctl-device",
				Organization: []string{"swe-ai-fleet"},
			},
		}
		csrDER, err := x509.CreateCertificateRequest(rand.Reader, csrTemplate, privateKey)
		if err != nil {
			return enrollErrMsg{err: fmt.Errorf("CSR creation failed: %w", err)}
		}
		csrPEM := pem.EncodeToMemory(&pem.Block{
			Type:  "CERTIFICATE REQUEST",
			Bytes: csrDER,
		})

		// Generate a device ID.
		deviceID := fmt.Sprintf("fleetctl-%x", mustRandBytes(8))

		// Call the enrollment endpoint.
		_, _, clientID, expiresAt, err := m.client.Enroll(
			context.Background(),
			apiKey,
			deviceID,
			csrPEM,
		)
		if err != nil {
			return enrollErrMsg{err: err}
		}

		return enrollSuccessMsg{
			clientID:  clientID,
			expiresAt: expiresAt,
		}
	}
}

func mustRandBytes(n int) []byte {
	b := make([]byte, n)
	_, err := rand.Read(b)
	if err != nil {
		panic("crypto/rand failed: " + err.Error())
	}
	return b
}
