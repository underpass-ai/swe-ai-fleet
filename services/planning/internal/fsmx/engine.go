// Package fsmx implements a statechart-style FSM engine with guards
package fsmx

import (
	"context"
	"encoding/json"
	"fmt"
	"os"

	"github.com/looplab/fsm"
	"gopkg.in/yaml.v3"
)

// Transition defines a state transition with guards
type Transition struct {
	From        string   `yaml:"from"`
	To          string   `yaml:"to"`
	Event       string   `yaml:"event"`
	Guards      []string `yaml:"guards"`
	Description string   `yaml:"description"`
}

// State defines a state in the FSM
type State struct {
	ID          string `yaml:"id"`
	Description string `yaml:"description"`
}

// GuardConfig defines guard metadata
type GuardConfig struct {
	Description string `yaml:"description"`
	Type        string `yaml:"type"` // automated or human
	Threshold   int    `yaml:"threshold,omitempty"`
	Role        string `yaml:"role,omitempty"`
}

// RigorModifier defines rigor-specific settings
type RigorModifier struct {
	Description  string `yaml:"description"`
	DorThreshold int    `yaml:"dor_threshold"`
}

// Config represents the FSM YAML configuration
type Config struct {
	States         []State                  `yaml:"states"`
	Transitions    []Transition             `yaml:"transitions"`
	HumanGates     []string                 `yaml:"human_gates"`
	Guards         map[string]GuardConfig   `yaml:"guards"`
	RigorModifiers map[string]RigorModifier `yaml:"rigor_modifiers"`
}

// GuardContext provides context for guard evaluation
type GuardContext struct {
	StoryID    string
	DorScore   int
	POApproved bool
	QAApproved bool
	RigorLevel string
	Metadata   map[string]interface{}
}

// GuardFn is a function that evaluates a guard condition
type GuardFn func(ctx GuardContext) error

// Engine manages the FSM with guards
type Engine struct {
	fsm        *fsm.FSM
	config     Config
	guards     map[string]GuardFn
	currentCtx GuardContext
}

// LoadFromFile loads FSM config from a YAML file
func LoadFromFile(path string) (*Engine, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read file: %w", err)
	}

	var cfg Config
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("unmarshal yaml: %w", err)
	}

	return New(cfg), nil
}

// New creates an Engine from config
func New(cfg Config) *Engine {
	// Build FSM events
	events := []fsm.EventDesc{}
	for _, t := range cfg.Transitions {
		events = append(events, fsm.EventDesc{
			Name: t.Event,
			Src:  []string{t.From},
			Dst:  t.To,
		})
	}

	// Start in first state
	initialState := "BACKLOG"
	if len(cfg.States) > 0 {
		initialState = cfg.States[0].ID
	}

	f := fsm.NewFSM(initialState, events, fsm.Callbacks{})

	engine := &Engine{
		fsm:    f,
		config: cfg,
		guards: make(map[string]GuardFn),
	}

	// Register default guards
	engine.registerDefaultGuards()

	return engine
}

// registerDefaultGuards sets up built-in guard functions
func (e *Engine) registerDefaultGuards() {
	e.guards["dor_ok"] = func(ctx GuardContext) error {
		threshold := 75
		if cfg, ok := e.config.Guards["dor_ok"]; ok {
			threshold = cfg.Threshold
		}
		// Apply rigor modifier
		if mod, ok := e.config.RigorModifiers[ctx.RigorLevel]; ok {
			threshold = mod.DorThreshold
		}

		if ctx.DorScore < threshold {
			return fmt.Errorf("DoR score %d below threshold %d", ctx.DorScore, threshold)
		}
		return nil
	}

	e.guards["po_approved"] = func(ctx GuardContext) error {
		if !ctx.POApproved {
			return fmt.Errorf("PO approval required")
		}
		return nil
	}

	e.guards["qa_signoff"] = func(ctx GuardContext) error {
		if !ctx.QAApproved {
			return fmt.Errorf("QA signoff required")
		}
		return nil
	}

	e.guards["design_complete"] = func(ctx GuardContext) error {
		// Placeholder: check for design artifacts
		if v, ok := ctx.Metadata["design_complete"].(bool); ok && v {
			return nil
		}
		return fmt.Errorf("design artifacts incomplete")
	}

	e.guards["all_subtasks_done"] = func(ctx GuardContext) error {
		// Placeholder: check subtask completion
		if v, ok := ctx.Metadata["subtasks_done"].(bool); ok && v {
			return nil
		}
		return fmt.Errorf("subtasks not complete")
	}

	e.guards["builds_passing"] = func(ctx GuardContext) error {
		if v, ok := ctx.Metadata["builds_passing"].(bool); ok && v {
			return nil
		}
		return fmt.Errorf("builds not passing")
	}

	e.guards["tests_passing"] = func(ctx GuardContext) error {
		if v, ok := ctx.Metadata["tests_passing"].(bool); ok && v {
			return nil
		}
		return fmt.Errorf("tests not passing")
	}

	e.guards["docs_complete"] = func(ctx GuardContext) error {
		if v, ok := ctx.Metadata["docs_complete"].(bool); ok && v {
			return nil
		}
		return fmt.Errorf("documentation incomplete")
	}
}

// RegisterGuard adds a custom guard function
func (e *Engine) RegisterGuard(name string, fn GuardFn) {
	e.guards[name] = fn
}

// Try attempts to execute an event with guard checks
func (e *Engine) Try(event string, ctx GuardContext) error {
	// Find transition
	var trans *Transition
	for _, t := range e.config.Transitions {
		if t.Event == event && t.From == e.fsm.Current() {
			trans = &t
			break
		}
	}

	if trans == nil {
		return fmt.Errorf("no transition for event %s from state %s", event, e.fsm.Current())
	}

	// Evaluate guards
	for _, guardName := range trans.Guards {
		guardFn, ok := e.guards[guardName]
		if !ok {
			return fmt.Errorf("unknown guard: %s", guardName)
		}

		if err := guardFn(ctx); err != nil {
			return fmt.Errorf("guard %s failed: %w", guardName, err)
		}
	}

	// Execute transition
	e.currentCtx = ctx
	return e.fsm.Event(context.Background(), event)
}

// Current returns the current state
func (e *Engine) Current() string {
	return e.fsm.Current()
}

// SetState forces a state (for initialization/testing)
func (e *Engine) SetState(state string) {
	e.fsm.SetState(state)
}

// AvailableTransitions returns events that can be triggered from current state
func (e *Engine) AvailableTransitions() []string {
	return e.fsm.AvailableTransitions()
}

// Marshal returns JSON representation of current state
func (e *Engine) Marshal() ([]byte, error) {
	data := map[string]interface{}{
		"state":       e.fsm.Current(),
		"transitions": e.AvailableTransitions(),
	}
	return json.Marshal(data)
}

// IsHumanGate checks if an event requires human approval
func (e *Engine) IsHumanGate(event string) bool {
	for _, gate := range e.config.HumanGates {
		if gate == event {
			return true
		}
	}
	return false
}

// GetTransition returns transition details for an event
func (e *Engine) GetTransition(event string) *Transition {
	for _, t := range e.config.Transitions {
		if t.Event == event && t.From == e.fsm.Current() {
			return &t
		}
	}
	return nil
}

// GetConfig returns the FSM configuration
func (e *Engine) GetConfig() Config {
	return e.config
}
