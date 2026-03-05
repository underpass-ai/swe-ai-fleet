package command

import (
	"context"
	"crypto/x509"
	"encoding/pem"
	"errors"
	"strings"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/domain/identity"
)

// ---------------------------------------------------------------------------
// Hand-written fakes
// ---------------------------------------------------------------------------

// fakeFleetClient implements ports.FleetClient for command-handler tests.
// Each method records its inputs and returns pre-configured results/errors.
type fakeFleetClient struct {
	// --- CreateProject ---
	createProjectResult domain.ProjectSummary
	createProjectErr    error
	cpRequestID         string
	cpName              string
	cpDescription       string

	// --- CreateStory ---
	createStoryResult domain.StorySummary
	createStoryErr    error
	csRequestID       string
	csEpicID          string
	csTitle           string
	csBrief           string

	// --- TransitionStory ---
	transitionErr    error
	tsStoryID        string
	tsTargetState    string

	// --- StartCeremony ---
	startCeremonyResult domain.CeremonyStatus
	startCeremonyErr    error
	scRequestID         string
	scCeremonyID        string
	scDefinitionName    string
	scStoryID           string
	scStepIDs           []string

	// --- Enroll ---
	enrollCertPEM  []byte
	enrollCAPEM    []byte
	enrollClientID string
	enrollExpires  string
	enrollErr      error
	enAPIKey       string
	enDeviceID     string
	enCSRPEM       []byte
}

func (f *fakeFleetClient) Enroll(_ context.Context, apiKey, deviceID string, csrPEM []byte) ([]byte, []byte, string, string, error) {
	f.enAPIKey = apiKey
	f.enDeviceID = deviceID
	f.enCSRPEM = csrPEM
	return f.enrollCertPEM, f.enrollCAPEM, f.enrollClientID, f.enrollExpires, f.enrollErr
}

func (f *fakeFleetClient) Renew(context.Context, []byte) ([]byte, []byte, string, error) {
	return nil, nil, "", nil
}

func (f *fakeFleetClient) CreateProject(_ context.Context, requestID, name, description string) (domain.ProjectSummary, error) {
	f.cpRequestID = requestID
	f.cpName = name
	f.cpDescription = description
	return f.createProjectResult, f.createProjectErr
}

func (f *fakeFleetClient) CreateStory(_ context.Context, requestID, epicID, title, brief string) (domain.StorySummary, error) {
	f.csRequestID = requestID
	f.csEpicID = epicID
	f.csTitle = title
	f.csBrief = brief
	return f.createStoryResult, f.createStoryErr
}

func (f *fakeFleetClient) TransitionStory(_ context.Context, storyID, targetState string) error {
	f.tsStoryID = storyID
	f.tsTargetState = targetState
	return f.transitionErr
}

func (f *fakeFleetClient) StartCeremony(_ context.Context, requestID, ceremonyID, definitionName, storyID string, stepIDs []string) (domain.CeremonyStatus, error) {
	f.scRequestID = requestID
	f.scCeremonyID = ceremonyID
	f.scDefinitionName = definitionName
	f.scStoryID = storyID
	f.scStepIDs = stepIDs
	return f.startCeremonyResult, f.startCeremonyErr
}

func (f *fakeFleetClient) CreateEpic(context.Context, string, string, string, string) (domain.EpicSummary, error) {
	return domain.EpicSummary{}, nil
}

func (f *fakeFleetClient) ListProjects(context.Context, string, int32, int32) ([]domain.ProjectSummary, int32, error) {
	return nil, 0, nil
}

func (f *fakeFleetClient) ListEpics(context.Context, string, string, int32, int32) ([]domain.EpicSummary, int32, error) {
	return nil, 0, nil
}

func (f *fakeFleetClient) ListStories(context.Context, string, string, int32, int32) ([]domain.StorySummary, int32, error) {
	return nil, 0, nil
}

func (f *fakeFleetClient) CreateTask(context.Context, string, string, string, string, string, string, int32, int32) (domain.TaskSummary, error) {
	return domain.TaskSummary{}, nil
}

func (f *fakeFleetClient) ListTasks(context.Context, string, string, int32, int32) ([]domain.TaskSummary, int32, error) {
	return nil, 0, nil
}

func (f *fakeFleetClient) ListCeremonies(context.Context, string, string, int32, int32) ([]domain.CeremonyStatus, int32, error) {
	return nil, 0, nil
}

func (f *fakeFleetClient) GetCeremony(context.Context, string) (domain.CeremonyStatus, error) {
	return domain.CeremonyStatus{}, nil
}

func (f *fakeFleetClient) ApproveDecision(context.Context, string, string, string) error {
	return nil
}

func (f *fakeFleetClient) RejectDecision(context.Context, string, string, string) error {
	return nil
}

func (f *fakeFleetClient) WatchEvents(_ context.Context, _ []string, _ string) (<-chan domain.FleetEvent, error) {
	ch := make(chan domain.FleetEvent)
	close(ch)
	return ch, nil
}

func (f *fakeFleetClient) CreateBacklogReview(context.Context, string, []string) (domain.BacklogReview, error) {
	return domain.BacklogReview{}, nil
}

func (f *fakeFleetClient) StartBacklogReview(context.Context, string, string) (domain.BacklogReview, int32, error) {
	return domain.BacklogReview{}, 0, nil
}

func (f *fakeFleetClient) GetBacklogReview(context.Context, string) (domain.BacklogReview, error) {
	return domain.BacklogReview{}, nil
}

func (f *fakeFleetClient) ListBacklogReviews(context.Context, string, int32, int32) ([]domain.BacklogReview, int32, error) {
	return nil, 0, nil
}

func (f *fakeFleetClient) ApproveReviewPlan(context.Context, string, string, string, string, string, string, string) (domain.BacklogReview, string, error) {
	return domain.BacklogReview{}, "", nil
}

func (f *fakeFleetClient) RejectReviewPlan(context.Context, string, string, string, string) (domain.BacklogReview, error) {
	return domain.BacklogReview{}, nil
}

func (f *fakeFleetClient) CompleteBacklogReview(context.Context, string, string) (domain.BacklogReview, error) {
	return domain.BacklogReview{}, nil
}

func (f *fakeFleetClient) CancelBacklogReview(context.Context, string, string) (domain.BacklogReview, error) {
	return domain.BacklogReview{}, nil
}

func (f *fakeFleetClient) Close() error { return nil }

// fakeCredentialStore implements ports.CredentialStore for tests.
type fakeCredentialStore struct {
	loadResult identity.Credentials
	loadErr    error
	saveErr    error
	saved      bool
	savedCert  []byte
	savedKey   []byte
	savedCA    []byte
	savedSN    string
	exists     bool
}

func (f *fakeCredentialStore) Load() (identity.Credentials, error) {
	return f.loadResult, f.loadErr
}

func (f *fakeCredentialStore) Save(certPEM, keyPEM, caPEM []byte, serverName string) error {
	f.saved = true
	f.savedCert = certPEM
	f.savedKey = keyPEM
	f.savedCA = caPEM
	f.savedSN = serverName
	return f.saveErr
}

func (f *fakeCredentialStore) Exists() bool {
	return f.exists
}

// fakeConfigStore implements ports.ConfigStore for tests.
type fakeConfigStore struct {
	loadResult domain.Config
	loadErr    error
	saveErr    error
}

func (f *fakeConfigStore) Load() (domain.Config, error) {
	return f.loadResult, f.loadErr
}

func (f *fakeConfigStore) Save(_ domain.Config) error {
	return f.saveErr
}

// ---------------------------------------------------------------------------
// generateRequestID tests
// ---------------------------------------------------------------------------

func TestGenerateRequestID(t *testing.T) {
	t.Run("returns 32 hex characters", func(t *testing.T) {
		id, err := generateRequestID()
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if len(id) != 32 {
			t.Fatalf("expected 32 hex chars, got %d: %q", len(id), id)
		}
		for _, c := range id {
			if !((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f')) {
				t.Fatalf("non-hex character %q in request ID %q", c, id)
			}
		}
	})

	t.Run("produces unique values", func(t *testing.T) {
		seen := make(map[string]struct{}, 100)
		for i := 0; i < 100; i++ {
			id, err := generateRequestID()
			if err != nil {
				t.Fatalf("unexpected error on iteration %d: %v", i, err)
			}
			if _, dup := seen[id]; dup {
				t.Fatalf("duplicate request ID %q on iteration %d", id, i)
			}
			seen[id] = struct{}{}
		}
	})
}

// ---------------------------------------------------------------------------
// CreateProjectHandler tests
// ---------------------------------------------------------------------------

func TestCreateProjectHandler_Success(t *testing.T) {
	want := domain.ProjectSummary{
		ID:          "proj-1",
		Name:        "My Project",
		Description: "A description",
		Status:      "ACTIVE",
		Owner:       "alice",
		CreatedAt:   "2026-01-01T00:00:00Z",
		UpdatedAt:   "2026-01-01T00:00:00Z",
	}
	fc := &fakeFleetClient{createProjectResult: want}
	h := NewCreateProjectHandler(fc)

	got, err := h.Handle(context.Background(), CreateProjectCmd{
		Name:        "My Project",
		Description: "A description",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got.ID != want.ID {
		t.Errorf("project ID: got %q, want %q", got.ID, want.ID)
	}
	if got.Name != want.Name {
		t.Errorf("project Name: got %q, want %q", got.Name, want.Name)
	}
	if got.Description != want.Description {
		t.Errorf("project Description: got %q, want %q", got.Description, want.Description)
	}
	// Verify delegation
	if fc.cpName != "My Project" {
		t.Errorf("client received name %q, want %q", fc.cpName, "My Project")
	}
	if fc.cpDescription != "A description" {
		t.Errorf("client received description %q, want %q", fc.cpDescription, "A description")
	}
	if fc.cpRequestID == "" {
		t.Error("client received empty requestID")
	}
	if len(fc.cpRequestID) != 32 {
		t.Errorf("requestID length: got %d, want 32", len(fc.cpRequestID))
	}
}

func TestCreateProjectHandler_EmptyName(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewCreateProjectHandler(fc)

	_, err := h.Handle(context.Background(), CreateProjectCmd{
		Name: "",
	})
	if err == nil {
		t.Fatal("expected error for empty name")
	}
	if !strings.Contains(err.Error(), "name is required") {
		t.Errorf("error message %q does not mention 'name is required'", err.Error())
	}
}

func TestCreateProjectHandler_ClientError(t *testing.T) {
	clientErr := errors.New("connection refused")
	fc := &fakeFleetClient{createProjectErr: clientErr}
	h := NewCreateProjectHandler(fc)

	_, err := h.Handle(context.Background(), CreateProjectCmd{
		Name: "valid",
	})
	if err == nil {
		t.Fatal("expected error from client")
	}
	if !strings.Contains(err.Error(), "create_project:") {
		t.Errorf("error should be prefixed with 'create_project:', got %q", err.Error())
	}
	if !errors.Is(err, clientErr) {
		t.Errorf("error should wrap client error; got %q", err.Error())
	}
}

func TestCreateProjectHandler_DescriptionOptional(t *testing.T) {
	fc := &fakeFleetClient{
		createProjectResult: domain.ProjectSummary{ID: "proj-2", Name: "No Desc"},
	}
	h := NewCreateProjectHandler(fc)

	got, err := h.Handle(context.Background(), CreateProjectCmd{
		Name:        "No Desc",
		Description: "",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got.ID != "proj-2" {
		t.Errorf("project ID: got %q, want %q", got.ID, "proj-2")
	}
	if fc.cpDescription != "" {
		t.Errorf("client received description %q, want empty", fc.cpDescription)
	}
}

// ---------------------------------------------------------------------------
// CreateStoryHandler tests
// ---------------------------------------------------------------------------

func TestCreateStoryHandler_Success(t *testing.T) {
	want := domain.StorySummary{
		ID:     "story-1",
		EpicID: "epic-42",
		Title:  "Build the thing",
		Brief:  "Details about building",
		State:  "DRAFT",
	}
	fc := &fakeFleetClient{createStoryResult: want}
	h := NewCreateStoryHandler(fc)

	got, err := h.Handle(context.Background(), CreateStoryCmd{
		EpicID: "epic-42",
		Title:  "Build the thing",
		Brief:  "Details about building",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got.ID != want.ID {
		t.Errorf("story ID: got %q, want %q", got.ID, want.ID)
	}
	if got.EpicID != want.EpicID {
		t.Errorf("story EpicID: got %q, want %q", got.EpicID, want.EpicID)
	}
	if got.Title != want.Title {
		t.Errorf("story Title: got %q, want %q", got.Title, want.Title)
	}
	if got.Brief != want.Brief {
		t.Errorf("story Brief: got %q, want %q", got.Brief, want.Brief)
	}
	// Verify delegation
	if fc.csEpicID != "epic-42" {
		t.Errorf("client received epicID %q, want %q", fc.csEpicID, "epic-42")
	}
	if fc.csTitle != "Build the thing" {
		t.Errorf("client received title %q, want %q", fc.csTitle, "Build the thing")
	}
	if fc.csBrief != "Details about building" {
		t.Errorf("client received brief %q, want %q", fc.csBrief, "Details about building")
	}
	if fc.csRequestID == "" {
		t.Error("client received empty requestID")
	}
}

func TestCreateStoryHandler_EmptyEpicID(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewCreateStoryHandler(fc)

	_, err := h.Handle(context.Background(), CreateStoryCmd{
		EpicID: "",
		Title:  "Has a title",
	})
	if err == nil {
		t.Fatal("expected error for empty epic_id")
	}
	if !strings.Contains(err.Error(), "epic_id is required") {
		t.Errorf("error message %q does not mention 'epic_id is required'", err.Error())
	}
}

func TestCreateStoryHandler_EmptyTitle(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewCreateStoryHandler(fc)

	_, err := h.Handle(context.Background(), CreateStoryCmd{
		EpicID: "epic-1",
		Title:  "",
	})
	if err == nil {
		t.Fatal("expected error for empty title")
	}
	if !strings.Contains(err.Error(), "title is required") {
		t.Errorf("error message %q does not mention 'title is required'", err.Error())
	}
}

func TestCreateStoryHandler_BothFieldsMissing(t *testing.T) {
	// When both are empty, epic_id is validated first.
	fc := &fakeFleetClient{}
	h := NewCreateStoryHandler(fc)

	_, err := h.Handle(context.Background(), CreateStoryCmd{})
	if err == nil {
		t.Fatal("expected error")
	}
	if !strings.Contains(err.Error(), "epic_id is required") {
		t.Errorf("expected epic_id validation first, got %q", err.Error())
	}
}

func TestCreateStoryHandler_ClientError(t *testing.T) {
	clientErr := errors.New("deadline exceeded")
	fc := &fakeFleetClient{createStoryErr: clientErr}
	h := NewCreateStoryHandler(fc)

	_, err := h.Handle(context.Background(), CreateStoryCmd{
		EpicID: "epic-1",
		Title:  "valid",
	})
	if err == nil {
		t.Fatal("expected error from client")
	}
	if !strings.Contains(err.Error(), "create_story:") {
		t.Errorf("error should be prefixed with 'create_story:', got %q", err.Error())
	}
	if !errors.Is(err, clientErr) {
		t.Errorf("error should wrap client error; got %q", err.Error())
	}
}

func TestCreateStoryHandler_BriefOptional(t *testing.T) {
	fc := &fakeFleetClient{
		createStoryResult: domain.StorySummary{ID: "story-2", Title: "No Brief"},
	}
	h := NewCreateStoryHandler(fc)

	got, err := h.Handle(context.Background(), CreateStoryCmd{
		EpicID: "epic-1",
		Title:  "No Brief",
		Brief:  "",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got.ID != "story-2" {
		t.Errorf("story ID: got %q, want %q", got.ID, "story-2")
	}
	if fc.csBrief != "" {
		t.Errorf("client received brief %q, want empty", fc.csBrief)
	}
}

// ---------------------------------------------------------------------------
// TransitionStoryHandler tests
// ---------------------------------------------------------------------------

func TestTransitionStoryHandler_Success(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewTransitionStoryHandler(fc)

	err := h.Handle(context.Background(), TransitionStoryCmd{
		StoryID:     "story-99",
		TargetState: "IN_PROGRESS",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if fc.tsStoryID != "story-99" {
		t.Errorf("client received storyID %q, want %q", fc.tsStoryID, "story-99")
	}
	if fc.tsTargetState != "IN_PROGRESS" {
		t.Errorf("client received targetState %q, want %q", fc.tsTargetState, "IN_PROGRESS")
	}
}

func TestTransitionStoryHandler_EmptyStoryID(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewTransitionStoryHandler(fc)

	err := h.Handle(context.Background(), TransitionStoryCmd{
		StoryID:     "",
		TargetState: "DONE",
	})
	if err == nil {
		t.Fatal("expected error for empty story_id")
	}
	if !strings.Contains(err.Error(), "story_id is required") {
		t.Errorf("error message %q does not mention 'story_id is required'", err.Error())
	}
}

func TestTransitionStoryHandler_EmptyTargetState(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewTransitionStoryHandler(fc)

	err := h.Handle(context.Background(), TransitionStoryCmd{
		StoryID:     "story-1",
		TargetState: "",
	})
	if err == nil {
		t.Fatal("expected error for empty target_state")
	}
	if !strings.Contains(err.Error(), "target_state is required") {
		t.Errorf("error message %q does not mention 'target_state is required'", err.Error())
	}
}

func TestTransitionStoryHandler_BothFieldsMissing(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewTransitionStoryHandler(fc)

	err := h.Handle(context.Background(), TransitionStoryCmd{})
	if err == nil {
		t.Fatal("expected error")
	}
	// story_id is validated first
	if !strings.Contains(err.Error(), "story_id is required") {
		t.Errorf("expected story_id validation first, got %q", err.Error())
	}
}

func TestTransitionStoryHandler_ClientError(t *testing.T) {
	clientErr := errors.New("story not found")
	fc := &fakeFleetClient{transitionErr: clientErr}
	h := NewTransitionStoryHandler(fc)

	err := h.Handle(context.Background(), TransitionStoryCmd{
		StoryID:     "story-1",
		TargetState: "IN_PROGRESS",
	})
	if err == nil {
		t.Fatal("expected error from client")
	}
	if !strings.Contains(err.Error(), "transition_story:") {
		t.Errorf("error should be prefixed with 'transition_story:', got %q", err.Error())
	}
	if !errors.Is(err, clientErr) {
		t.Errorf("error should wrap client error; got %q", err.Error())
	}
}

// ---------------------------------------------------------------------------
// StartCeremonyHandler tests
// ---------------------------------------------------------------------------

func TestStartCeremonyHandler_Success(t *testing.T) {
	want := domain.CeremonyStatus{
		InstanceID:     "inst-1",
		CeremonyID:     "cer-1",
		StoryID:        "story-5",
		DefinitionName: "planning",
		CurrentState:   "STARTED",
		Status:         "RUNNING",
	}
	fc := &fakeFleetClient{startCeremonyResult: want}
	h := NewStartCeremonyHandler(fc)

	got, err := h.Handle(context.Background(), StartCeremonyCmd{
		CeremonyID:     "cer-1",
		DefinitionName: "planning",
		StoryID:        "story-5",
		StepIDs:        []string{"step-a", "step-b"},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got.InstanceID != want.InstanceID {
		t.Errorf("InstanceID: got %q, want %q", got.InstanceID, want.InstanceID)
	}
	if got.Status != want.Status {
		t.Errorf("Status: got %q, want %q", got.Status, want.Status)
	}
	// Verify delegation
	if fc.scCeremonyID != "cer-1" {
		t.Errorf("client received ceremonyID %q, want %q", fc.scCeremonyID, "cer-1")
	}
	if fc.scDefinitionName != "planning" {
		t.Errorf("client received definitionName %q, want %q", fc.scDefinitionName, "planning")
	}
	if fc.scStoryID != "story-5" {
		t.Errorf("client received storyID %q, want %q", fc.scStoryID, "story-5")
	}
	if len(fc.scStepIDs) != 2 || fc.scStepIDs[0] != "step-a" || fc.scStepIDs[1] != "step-b" {
		t.Errorf("client received stepIDs %v, want [step-a step-b]", fc.scStepIDs)
	}
	if fc.scRequestID == "" {
		t.Error("client received empty requestID")
	}
}

func TestStartCeremonyHandler_EmptyCeremonyID(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewStartCeremonyHandler(fc)

	_, err := h.Handle(context.Background(), StartCeremonyCmd{
		CeremonyID:     "",
		DefinitionName: "planning",
		StoryID:        "story-1",
		StepIDs:        []string{"s1"},
	})
	if err == nil {
		t.Fatal("expected error for empty ceremony_id")
	}
	if !strings.Contains(err.Error(), "ceremony_id is required") {
		t.Errorf("error message %q does not mention 'ceremony_id is required'", err.Error())
	}
}

func TestStartCeremonyHandler_EmptyDefinitionName(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewStartCeremonyHandler(fc)

	_, err := h.Handle(context.Background(), StartCeremonyCmd{
		CeremonyID:     "cer-1",
		DefinitionName: "",
		StoryID:        "story-1",
		StepIDs:        []string{"s1"},
	})
	if err == nil {
		t.Fatal("expected error for empty definition_name")
	}
	if !strings.Contains(err.Error(), "definition_name is required") {
		t.Errorf("error message %q does not mention 'definition_name is required'", err.Error())
	}
}

func TestStartCeremonyHandler_EmptyStoryID(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewStartCeremonyHandler(fc)

	_, err := h.Handle(context.Background(), StartCeremonyCmd{
		CeremonyID:     "cer-1",
		DefinitionName: "planning",
		StoryID:        "",
		StepIDs:        []string{"s1"},
	})
	if err == nil {
		t.Fatal("expected error for empty story_id")
	}
	if !strings.Contains(err.Error(), "story_id is required") {
		t.Errorf("error message %q does not mention 'story_id is required'", err.Error())
	}
}

func TestStartCeremonyHandler_EmptyStepIDs(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewStartCeremonyHandler(fc)

	_, err := h.Handle(context.Background(), StartCeremonyCmd{
		CeremonyID:     "cer-1",
		DefinitionName: "planning",
		StoryID:        "story-1",
		StepIDs:        []string{},
	})
	if err == nil {
		t.Fatal("expected error for empty step_ids")
	}
	if !strings.Contains(err.Error(), "at least one step_id is required") {
		t.Errorf("error message %q does not mention 'at least one step_id is required'", err.Error())
	}
}

func TestStartCeremonyHandler_NilStepIDs(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewStartCeremonyHandler(fc)

	_, err := h.Handle(context.Background(), StartCeremonyCmd{
		CeremonyID:     "cer-1",
		DefinitionName: "planning",
		StoryID:        "story-1",
		StepIDs:        nil,
	})
	if err == nil {
		t.Fatal("expected error for nil step_ids")
	}
	if !strings.Contains(err.Error(), "at least one step_id is required") {
		t.Errorf("error message %q does not mention 'at least one step_id is required'", err.Error())
	}
}

func TestStartCeremonyHandler_ValidationOrder(t *testing.T) {
	// With all fields missing, ceremony_id should be validated first.
	fc := &fakeFleetClient{}
	h := NewStartCeremonyHandler(fc)

	_, err := h.Handle(context.Background(), StartCeremonyCmd{})
	if err == nil {
		t.Fatal("expected error")
	}
	if !strings.Contains(err.Error(), "ceremony_id is required") {
		t.Errorf("expected ceremony_id validation first, got %q", err.Error())
	}
}

func TestStartCeremonyHandler_ClientError(t *testing.T) {
	clientErr := errors.New("internal server error")
	fc := &fakeFleetClient{startCeremonyErr: clientErr}
	h := NewStartCeremonyHandler(fc)

	_, err := h.Handle(context.Background(), StartCeremonyCmd{
		CeremonyID:     "cer-1",
		DefinitionName: "planning",
		StoryID:        "story-1",
		StepIDs:        []string{"s1"},
	})
	if err == nil {
		t.Fatal("expected error from client")
	}
	if !strings.Contains(err.Error(), "start_ceremony:") {
		t.Errorf("error should be prefixed with 'start_ceremony:', got %q", err.Error())
	}
	if !errors.Is(err, clientErr) {
		t.Errorf("error should wrap client error; got %q", err.Error())
	}
}

// ---------------------------------------------------------------------------
// EnrollHandler tests
// ---------------------------------------------------------------------------

func TestEnrollHandler_Success(t *testing.T) {
	fc := &fakeFleetClient{
		enrollCertPEM:  []byte("CERT-PEM"),
		enrollCAPEM:    []byte("CA-PEM"),
		enrollClientID: "client-abc",
		enrollExpires:  "2027-01-01T00:00:00Z",
	}
	credStore := &fakeCredentialStore{}
	cfgStore := &fakeConfigStore{
		loadResult: domain.Config{ServerName: "fleet.example.com"},
	}
	h := NewEnrollHandler(fc, credStore, cfgStore)

	result, err := h.Handle(context.Background(), EnrollCmd{
		APIKey:   "my-api-key",
		DeviceID: "dev-01",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Verify returned result
	if result.ClientID != "client-abc" {
		t.Errorf("ClientID: got %q, want %q", result.ClientID, "client-abc")
	}
	if result.ExpiresAt != "2027-01-01T00:00:00Z" {
		t.Errorf("ExpiresAt: got %q, want %q", result.ExpiresAt, "2027-01-01T00:00:00Z")
	}

	// Verify client received correct inputs
	if fc.enAPIKey != "my-api-key" {
		t.Errorf("client received apiKey %q, want %q", fc.enAPIKey, "my-api-key")
	}
	if fc.enDeviceID != "dev-01" {
		t.Errorf("client received deviceID %q, want %q", fc.enDeviceID, "dev-01")
	}
	if len(fc.enCSRPEM) == 0 {
		t.Fatal("client received empty CSR PEM")
	}
	// CSR should be PEM-encoded
	if !strings.Contains(string(fc.enCSRPEM), "CERTIFICATE REQUEST") {
		t.Error("CSR PEM does not contain 'CERTIFICATE REQUEST' header")
	}

	// Verify credentials were saved
	if !credStore.saved {
		t.Fatal("credentials were not saved")
	}
	if string(credStore.savedCert) != "CERT-PEM" {
		t.Errorf("saved cert: got %q, want %q", credStore.savedCert, "CERT-PEM")
	}
	if string(credStore.savedCA) != "CA-PEM" {
		t.Errorf("saved CA: got %q, want %q", credStore.savedCA, "CA-PEM")
	}
	if credStore.savedSN != "fleet.example.com" {
		t.Errorf("saved serverName: got %q, want %q", credStore.savedSN, "fleet.example.com")
	}
	// Key should be PEM-encoded EC private key
	if !strings.Contains(string(credStore.savedKey), "EC PRIVATE KEY") {
		t.Error("saved key does not contain 'EC PRIVATE KEY' header")
	}
}

func TestEnrollHandler_EmptyAPIKey(t *testing.T) {
	h := NewEnrollHandler(&fakeFleetClient{}, &fakeCredentialStore{}, &fakeConfigStore{})

	_, err := h.Handle(context.Background(), EnrollCmd{
		APIKey:   "",
		DeviceID: "dev-01",
	})
	if err == nil {
		t.Fatal("expected error for empty api key")
	}
	if !strings.Contains(err.Error(), "api key is required") {
		t.Errorf("error message %q does not mention 'api key is required'", err.Error())
	}
}

func TestEnrollHandler_EmptyDeviceID(t *testing.T) {
	h := NewEnrollHandler(&fakeFleetClient{}, &fakeCredentialStore{}, &fakeConfigStore{})

	_, err := h.Handle(context.Background(), EnrollCmd{
		APIKey:   "key-1",
		DeviceID: "",
	})
	if err == nil {
		t.Fatal("expected error for empty device id")
	}
	if !strings.Contains(err.Error(), "device id is required") {
		t.Errorf("error message %q does not mention 'device id is required'", err.Error())
	}
}

func TestEnrollHandler_BothFieldsMissing(t *testing.T) {
	h := NewEnrollHandler(&fakeFleetClient{}, &fakeCredentialStore{}, &fakeConfigStore{})

	_, err := h.Handle(context.Background(), EnrollCmd{})
	if err == nil {
		t.Fatal("expected error")
	}
	// api key is validated first
	if !strings.Contains(err.Error(), "api key is required") {
		t.Errorf("expected api key validation first, got %q", err.Error())
	}
}

func TestEnrollHandler_ClientEnrollError(t *testing.T) {
	clientErr := errors.New("invalid api key")
	fc := &fakeFleetClient{enrollErr: clientErr}
	credStore := &fakeCredentialStore{}
	cfgStore := &fakeConfigStore{
		loadResult: domain.Config{ServerName: "fleet.example.com"},
	}
	h := NewEnrollHandler(fc, credStore, cfgStore)

	_, err := h.Handle(context.Background(), EnrollCmd{
		APIKey:   "bad-key",
		DeviceID: "dev-01",
	})
	if err == nil {
		t.Fatal("expected error from client enroll")
	}
	if !strings.Contains(err.Error(), "server call failed") {
		t.Errorf("error message %q does not mention 'server call failed'", err.Error())
	}
	if !errors.Is(err, clientErr) {
		t.Errorf("error should wrap client error; got %q", err.Error())
	}
	// Credentials must NOT be saved on enroll failure
	if credStore.saved {
		t.Error("credentials should not be saved when enroll fails")
	}
}

func TestEnrollHandler_ConfigLoadError(t *testing.T) {
	fc := &fakeFleetClient{
		enrollCertPEM:  []byte("CERT"),
		enrollCAPEM:    []byte("CA"),
		enrollClientID: "c1",
		enrollExpires:  "2027-01-01",
	}
	cfgErr := errors.New("config file not found")
	credStore := &fakeCredentialStore{}
	cfgStore := &fakeConfigStore{loadErr: cfgErr}
	h := NewEnrollHandler(fc, credStore, cfgStore)

	_, err := h.Handle(context.Background(), EnrollCmd{
		APIKey:   "key-1",
		DeviceID: "dev-01",
	})
	if err == nil {
		t.Fatal("expected error from config load")
	}
	if !strings.Contains(err.Error(), "failed to load config") {
		t.Errorf("error message %q does not mention 'failed to load config'", err.Error())
	}
	if !errors.Is(err, cfgErr) {
		t.Errorf("error should wrap config error; got %q", err.Error())
	}
	// Credentials must NOT be saved when config load fails
	if credStore.saved {
		t.Error("credentials should not be saved when config load fails")
	}
}

func TestEnrollHandler_CredStoreSaveError(t *testing.T) {
	fc := &fakeFleetClient{
		enrollCertPEM:  []byte("CERT"),
		enrollCAPEM:    []byte("CA"),
		enrollClientID: "c1",
		enrollExpires:  "2027-01-01",
	}
	saveErr := errors.New("permission denied")
	credStore := &fakeCredentialStore{saveErr: saveErr}
	cfgStore := &fakeConfigStore{
		loadResult: domain.Config{ServerName: "fleet.example.com"},
	}
	h := NewEnrollHandler(fc, credStore, cfgStore)

	_, err := h.Handle(context.Background(), EnrollCmd{
		APIKey:   "key-1",
		DeviceID: "dev-01",
	})
	if err == nil {
		t.Fatal("expected error from credential save")
	}
	if !strings.Contains(err.Error(), "failed to save credentials") {
		t.Errorf("error message %q does not mention 'failed to save credentials'", err.Error())
	}
	if !errors.Is(err, saveErr) {
		t.Errorf("error should wrap save error; got %q", err.Error())
	}
}

func TestEnrollHandler_CSRContainsDeviceID(t *testing.T) {
	// Verify the CSR that gets sent to the server embeds the device ID
	// as the common name and "swe-ai-fleet" as the organization.
	fc := &fakeFleetClient{
		enrollCertPEM:  []byte("CERT"),
		enrollCAPEM:    []byte("CA"),
		enrollClientID: "c1",
		enrollExpires:  "2027-01-01",
	}
	credStore := &fakeCredentialStore{}
	cfgStore := &fakeConfigStore{
		loadResult: domain.Config{ServerName: "fleet.example.com"},
	}
	h := NewEnrollHandler(fc, credStore, cfgStore)

	_, err := h.Handle(context.Background(), EnrollCmd{
		APIKey:   "key-1",
		DeviceID: "dev-special-42",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Parse the CSR PEM that was sent to the client.
	csrPEM := fc.enCSRPEM
	if len(csrPEM) == 0 {
		t.Fatal("no CSR was sent to client")
	}

	block, _ := pem.Decode(csrPEM)
	if block == nil {
		t.Fatal("failed to decode CSR PEM block")
	}
	if block.Type != "CERTIFICATE REQUEST" {
		t.Fatalf("PEM block type: got %q, want %q", block.Type, "CERTIFICATE REQUEST")
	}

	csr, err := x509.ParseCertificateRequest(block.Bytes)
	if err != nil {
		t.Fatalf("failed to parse CSR DER: %v", err)
	}

	if csr.Subject.CommonName != "dev-special-42" {
		t.Errorf("CSR CN: got %q, want %q", csr.Subject.CommonName, "dev-special-42")
	}
	if len(csr.Subject.Organization) == 0 || csr.Subject.Organization[0] != "swe-ai-fleet" {
		t.Errorf("CSR Organization: got %v, want [swe-ai-fleet]", csr.Subject.Organization)
	}
}

func TestEnrollHandler_GeneratesUniqueKey(t *testing.T) {
	// Two enrollments should produce different private keys.
	fc := &fakeFleetClient{
		enrollCertPEM:  []byte("CERT"),
		enrollCAPEM:    []byte("CA"),
		enrollClientID: "c1",
		enrollExpires:  "2027-01-01",
	}
	cfgStore := &fakeConfigStore{
		loadResult: domain.Config{ServerName: "fleet.example.com"},
	}

	credStore1 := &fakeCredentialStore{}
	h1 := NewEnrollHandler(fc, credStore1, cfgStore)
	_, err := h1.Handle(context.Background(), EnrollCmd{APIKey: "k", DeviceID: "d"})
	if err != nil {
		t.Fatalf("first enroll: %v", err)
	}

	credStore2 := &fakeCredentialStore{}
	h2 := NewEnrollHandler(fc, credStore2, cfgStore)
	_, err = h2.Handle(context.Background(), EnrollCmd{APIKey: "k", DeviceID: "d"})
	if err != nil {
		t.Fatalf("second enroll: %v", err)
	}

	if string(credStore1.savedKey) == string(credStore2.savedKey) {
		t.Error("two enrollments produced the same private key PEM")
	}
}

// ---------------------------------------------------------------------------
// Constructor tests — verify that New* functions wire dependencies correctly
// ---------------------------------------------------------------------------

func TestNewCreateProjectHandler(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewCreateProjectHandler(fc)
	if h == nil {
		t.Fatal("NewCreateProjectHandler returned nil")
	}
	if h.client != fc {
		t.Error("handler client is not the one passed to constructor")
	}
}

func TestNewCreateStoryHandler(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewCreateStoryHandler(fc)
	if h == nil {
		t.Fatal("NewCreateStoryHandler returned nil")
	}
	if h.client != fc {
		t.Error("handler client is not the one passed to constructor")
	}
}

func TestNewTransitionStoryHandler(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewTransitionStoryHandler(fc)
	if h == nil {
		t.Fatal("NewTransitionStoryHandler returned nil")
	}
	if h.client != fc {
		t.Error("handler client is not the one passed to constructor")
	}
}

func TestNewStartCeremonyHandler(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewStartCeremonyHandler(fc)
	if h == nil {
		t.Fatal("NewStartCeremonyHandler returned nil")
	}
	if h.client != fc {
		t.Error("handler client is not the one passed to constructor")
	}
}

func TestNewEnrollHandler(t *testing.T) {
	fc := &fakeFleetClient{}
	cs := &fakeCredentialStore{}
	cfg := &fakeConfigStore{}
	h := NewEnrollHandler(fc, cs, cfg)
	if h == nil {
		t.Fatal("NewEnrollHandler returned nil")
	}
	if h.client != fc {
		t.Error("handler client is not the one passed to constructor")
	}
	if h.credStore != cs {
		t.Error("handler credStore is not the one passed to constructor")
	}
	if h.cfgStore != cfg {
		t.Error("handler cfgStore is not the one passed to constructor")
	}
}
