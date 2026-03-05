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

	// --- CreateEpic ---
	createEpicResult domain.EpicSummary
	createEpicErr    error
	ceRequestID      string
	ceProjectID      string
	ceTitle          string
	ceDescription    string

	// --- CreateTask ---
	createTaskResult domain.TaskSummary
	createTaskErr    error
	ctRequestID      string
	ctStoryID        string
	ctTitle          string
	ctDescription    string
	ctTaskType       string
	ctAssignedTo     string
	ctEstimatedHours int32
	ctPriority       int32

	// --- ApproveDecision ---
	approveDecisionErr error
	adStoryID          string
	adDecisionID       string
	adComment          string

	// --- RejectDecision ---
	rejectDecisionErr error
	rdStoryID         string
	rdDecisionID      string
	rdReason          string

	// --- Renew ---
	renewCertPEM []byte
	renewCAPEM   []byte
	renewExpires string
	renewErr     error
	rnCSRPEM     []byte

	// --- CreateBacklogReview ---
	createBRResult domain.BacklogReview
	createBRErr    error
	cbrRequestID   string
	cbrStoryIDs    []string

	// --- StartBacklogReview ---
	startBRResult domain.BacklogReview
	startBRTotal  int32
	startBRErr    error
	sbrRequestID  string
	sbrCeremonyID string

	// --- ApproveReviewPlan ---
	approvePlanResult domain.BacklogReview
	approvePlanID     string
	approvePlanErr    error
	aprRequestID      string
	aprCeremonyID     string
	aprStoryID        string
	aprPONotes        string
	aprPOConcerns     string
	aprPriorityAdj    string
	aprPrioReason     string

	// --- RejectReviewPlan ---
	rejectPlanResult domain.BacklogReview
	rejectPlanErr    error
	rprRequestID     string
	rprCeremonyID    string
	rprStoryID       string
	rprReason        string

	// --- CompleteBacklogReview ---
	completeBRResult domain.BacklogReview
	completeBRErr    error
	combrRequestID   string
	combrCeremonyID  string

	// --- CancelBacklogReview ---
	cancelBRResult domain.BacklogReview
	cancelBRErr    error
	canbrRequestID string
	canbrCeremonyID string
}

func (f *fakeFleetClient) Enroll(_ context.Context, apiKey, deviceID string, csrPEM []byte) ([]byte, []byte, string, string, error) {
	f.enAPIKey = apiKey
	f.enDeviceID = deviceID
	f.enCSRPEM = csrPEM
	return f.enrollCertPEM, f.enrollCAPEM, f.enrollClientID, f.enrollExpires, f.enrollErr
}

func (f *fakeFleetClient) Renew(_ context.Context, csrPEM []byte) ([]byte, []byte, string, error) {
	f.rnCSRPEM = csrPEM
	return f.renewCertPEM, f.renewCAPEM, f.renewExpires, f.renewErr
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

func (f *fakeFleetClient) CreateEpic(_ context.Context, requestID, projectID, title, description string) (domain.EpicSummary, error) {
	f.ceRequestID = requestID
	f.ceProjectID = projectID
	f.ceTitle = title
	f.ceDescription = description
	return f.createEpicResult, f.createEpicErr
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

func (f *fakeFleetClient) CreateTask(_ context.Context, requestID, storyID, title, description, taskType, assignedTo string, estimatedHours, priority int32) (domain.TaskSummary, error) {
	f.ctRequestID = requestID
	f.ctStoryID = storyID
	f.ctTitle = title
	f.ctDescription = description
	f.ctTaskType = taskType
	f.ctAssignedTo = assignedTo
	f.ctEstimatedHours = estimatedHours
	f.ctPriority = priority
	return f.createTaskResult, f.createTaskErr
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

func (f *fakeFleetClient) ApproveDecision(_ context.Context, storyID, decisionID, comment string) error {
	f.adStoryID = storyID
	f.adDecisionID = decisionID
	f.adComment = comment
	return f.approveDecisionErr
}

func (f *fakeFleetClient) RejectDecision(_ context.Context, storyID, decisionID, reason string) error {
	f.rdStoryID = storyID
	f.rdDecisionID = decisionID
	f.rdReason = reason
	return f.rejectDecisionErr
}

func (f *fakeFleetClient) WatchEvents(_ context.Context, _ []string, _ string) (<-chan domain.FleetEvent, error) {
	ch := make(chan domain.FleetEvent)
	close(ch)
	return ch, nil
}

func (f *fakeFleetClient) CreateBacklogReview(_ context.Context, requestID string, storyIDs []string) (domain.BacklogReview, error) {
	f.cbrRequestID = requestID
	f.cbrStoryIDs = storyIDs
	return f.createBRResult, f.createBRErr
}

func (f *fakeFleetClient) StartBacklogReview(_ context.Context, requestID, ceremonyID string) (domain.BacklogReview, int32, error) {
	f.sbrRequestID = requestID
	f.sbrCeremonyID = ceremonyID
	return f.startBRResult, f.startBRTotal, f.startBRErr
}

func (f *fakeFleetClient) GetBacklogReview(context.Context, string) (domain.BacklogReview, error) {
	return domain.BacklogReview{}, nil
}

func (f *fakeFleetClient) ListBacklogReviews(context.Context, string, int32, int32) ([]domain.BacklogReview, int32, error) {
	return nil, 0, nil
}

func (f *fakeFleetClient) ApproveReviewPlan(_ context.Context, requestID, ceremonyID, storyID, poNotes, poConcerns, priorityAdj, prioReason string) (domain.BacklogReview, string, error) {
	f.aprRequestID = requestID
	f.aprCeremonyID = ceremonyID
	f.aprStoryID = storyID
	f.aprPONotes = poNotes
	f.aprPOConcerns = poConcerns
	f.aprPriorityAdj = priorityAdj
	f.aprPrioReason = prioReason
	return f.approvePlanResult, f.approvePlanID, f.approvePlanErr
}

func (f *fakeFleetClient) RejectReviewPlan(_ context.Context, requestID, ceremonyID, storyID, reason string) (domain.BacklogReview, error) {
	f.rprRequestID = requestID
	f.rprCeremonyID = ceremonyID
	f.rprStoryID = storyID
	f.rprReason = reason
	return f.rejectPlanResult, f.rejectPlanErr
}

func (f *fakeFleetClient) CompleteBacklogReview(_ context.Context, requestID, ceremonyID string) (domain.BacklogReview, error) {
	f.combrRequestID = requestID
	f.combrCeremonyID = ceremonyID
	return f.completeBRResult, f.completeBRErr
}

func (f *fakeFleetClient) CancelBacklogReview(_ context.Context, requestID, ceremonyID string) (domain.BacklogReview, error) {
	f.canbrRequestID = requestID
	f.canbrCeremonyID = ceremonyID
	return f.cancelBRResult, f.cancelBRErr
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

func TestNewCreateEpicHandler(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewCreateEpicHandler(fc)
	if h == nil {
		t.Fatal("NewCreateEpicHandler returned nil")
	}
	if h.client != fc {
		t.Error("handler client is not the one passed to constructor")
	}
}

func TestNewCreateTaskHandler(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewCreateTaskHandler(fc)
	if h == nil {
		t.Fatal("NewCreateTaskHandler returned nil")
	}
	if h.client != fc {
		t.Error("handler client is not the one passed to constructor")
	}
}

func TestNewApproveDecisionHandler(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewApproveDecisionHandler(fc)
	if h == nil {
		t.Fatal("NewApproveDecisionHandler returned nil")
	}
	if h.client != fc {
		t.Error("handler client is not the one passed to constructor")
	}
}

func TestNewRejectDecisionHandler(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewRejectDecisionHandler(fc)
	if h == nil {
		t.Fatal("NewRejectDecisionHandler returned nil")
	}
	if h.client != fc {
		t.Error("handler client is not the one passed to constructor")
	}
}

func TestNewRenewHandler(t *testing.T) {
	fc := &fakeFleetClient{}
	cs := &fakeCredentialStore{}
	cfg := &fakeConfigStore{}
	h := NewRenewHandler(fc, cs, cfg)
	if h == nil {
		t.Fatal("NewRenewHandler returned nil")
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

func TestNewCreateBacklogReviewHandler(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewCreateBacklogReviewHandler(fc)
	if h == nil {
		t.Fatal("NewCreateBacklogReviewHandler returned nil")
	}
	if h.client != fc {
		t.Error("handler client is not the one passed to constructor")
	}
}

func TestNewStartBacklogReviewHandler(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewStartBacklogReviewHandler(fc)
	if h == nil {
		t.Fatal("NewStartBacklogReviewHandler returned nil")
	}
	if h.client != fc {
		t.Error("handler client is not the one passed to constructor")
	}
}

func TestNewApproveReviewPlanHandler(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewApproveReviewPlanHandler(fc)
	if h == nil {
		t.Fatal("NewApproveReviewPlanHandler returned nil")
	}
	if h.client != fc {
		t.Error("handler client is not the one passed to constructor")
	}
}

func TestNewRejectReviewPlanHandler(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewRejectReviewPlanHandler(fc)
	if h == nil {
		t.Fatal("NewRejectReviewPlanHandler returned nil")
	}
	if h.client != fc {
		t.Error("handler client is not the one passed to constructor")
	}
}

func TestNewCompleteBacklogReviewHandler(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewCompleteBacklogReviewHandler(fc)
	if h == nil {
		t.Fatal("NewCompleteBacklogReviewHandler returned nil")
	}
	if h.client != fc {
		t.Error("handler client is not the one passed to constructor")
	}
}

func TestNewCancelBacklogReviewHandler(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewCancelBacklogReviewHandler(fc)
	if h == nil {
		t.Fatal("NewCancelBacklogReviewHandler returned nil")
	}
	if h.client != fc {
		t.Error("handler client is not the one passed to constructor")
	}
}

// ---------------------------------------------------------------------------
// CreateEpicHandler tests
// ---------------------------------------------------------------------------

func TestCreateEpicHandler_Success(t *testing.T) {
	want := domain.EpicSummary{
		ID:          "epic-1",
		ProjectID:   "proj-42",
		Title:       "Build auth system",
		Description: "OAuth2 and mTLS",
		Status:      "ACTIVE",
		CreatedAt:   "2026-01-01T00:00:00Z",
		UpdatedAt:   "2026-01-01T00:00:00Z",
	}
	fc := &fakeFleetClient{createEpicResult: want}
	h := NewCreateEpicHandler(fc)

	got, err := h.Handle(context.Background(), CreateEpicCmd{
		ProjectID:   "proj-42",
		Title:       "Build auth system",
		Description: "OAuth2 and mTLS",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got.ID != want.ID {
		t.Errorf("epic ID: got %q, want %q", got.ID, want.ID)
	}
	if got.ProjectID != want.ProjectID {
		t.Errorf("epic ProjectID: got %q, want %q", got.ProjectID, want.ProjectID)
	}
	if got.Title != want.Title {
		t.Errorf("epic Title: got %q, want %q", got.Title, want.Title)
	}
	if got.Description != want.Description {
		t.Errorf("epic Description: got %q, want %q", got.Description, want.Description)
	}
	// Verify delegation
	if fc.ceProjectID != "proj-42" {
		t.Errorf("client received projectID %q, want %q", fc.ceProjectID, "proj-42")
	}
	if fc.ceTitle != "Build auth system" {
		t.Errorf("client received title %q, want %q", fc.ceTitle, "Build auth system")
	}
	if fc.ceDescription != "OAuth2 and mTLS" {
		t.Errorf("client received description %q, want %q", fc.ceDescription, "OAuth2 and mTLS")
	}
	if fc.ceRequestID == "" {
		t.Error("client received empty requestID")
	}
	if len(fc.ceRequestID) != 32 {
		t.Errorf("requestID length: got %d, want 32", len(fc.ceRequestID))
	}
}

func TestCreateEpicHandler_EmptyProjectID(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewCreateEpicHandler(fc)

	_, err := h.Handle(context.Background(), CreateEpicCmd{
		ProjectID: "",
		Title:     "Has a title",
	})
	if err == nil {
		t.Fatal("expected error for empty project_id")
	}
	if !strings.Contains(err.Error(), "project_id is required") {
		t.Errorf("error message %q does not mention 'project_id is required'", err.Error())
	}
}

func TestCreateEpicHandler_EmptyTitle(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewCreateEpicHandler(fc)

	_, err := h.Handle(context.Background(), CreateEpicCmd{
		ProjectID: "proj-1",
		Title:     "",
	})
	if err == nil {
		t.Fatal("expected error for empty title")
	}
	if !strings.Contains(err.Error(), "title is required") {
		t.Errorf("error message %q does not mention 'title is required'", err.Error())
	}
}

func TestCreateEpicHandler_BothFieldsMissing(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewCreateEpicHandler(fc)

	_, err := h.Handle(context.Background(), CreateEpicCmd{})
	if err == nil {
		t.Fatal("expected error")
	}
	if !strings.Contains(err.Error(), "project_id is required") {
		t.Errorf("expected project_id validation first, got %q", err.Error())
	}
}

func TestCreateEpicHandler_ClientError(t *testing.T) {
	clientErr := errors.New("connection refused")
	fc := &fakeFleetClient{createEpicErr: clientErr}
	h := NewCreateEpicHandler(fc)

	_, err := h.Handle(context.Background(), CreateEpicCmd{
		ProjectID: "proj-1",
		Title:     "valid",
	})
	if err == nil {
		t.Fatal("expected error from client")
	}
	if !strings.Contains(err.Error(), "create_epic:") {
		t.Errorf("error should be prefixed with 'create_epic:', got %q", err.Error())
	}
	if !errors.Is(err, clientErr) {
		t.Errorf("error should wrap client error; got %q", err.Error())
	}
}

func TestCreateEpicHandler_DescriptionOptional(t *testing.T) {
	fc := &fakeFleetClient{
		createEpicResult: domain.EpicSummary{ID: "epic-2", Title: "No Desc"},
	}
	h := NewCreateEpicHandler(fc)

	got, err := h.Handle(context.Background(), CreateEpicCmd{
		ProjectID:   "proj-1",
		Title:       "No Desc",
		Description: "",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got.ID != "epic-2" {
		t.Errorf("epic ID: got %q, want %q", got.ID, "epic-2")
	}
	if fc.ceDescription != "" {
		t.Errorf("client received description %q, want empty", fc.ceDescription)
	}
}

// ---------------------------------------------------------------------------
// CreateTaskHandler tests
// ---------------------------------------------------------------------------

func TestCreateTaskHandler_Success(t *testing.T) {
	want := domain.TaskSummary{
		ID:             "task-1",
		StoryID:        "story-10",
		Title:          "Implement login",
		Description:    "Build the login page",
		Type:           "CODING",
		Status:         "TODO",
		AssignedTo:     "bob",
		EstimatedHours: 4,
		Priority:       1,
		CreatedAt:      "2026-01-01T00:00:00Z",
		UpdatedAt:      "2026-01-01T00:00:00Z",
	}
	fc := &fakeFleetClient{createTaskResult: want}
	h := NewCreateTaskHandler(fc)

	got, err := h.Handle(context.Background(), CreateTaskCmd{
		StoryID:        "story-10",
		Title:          "Implement login",
		Description:    "Build the login page",
		TaskType:       "CODING",
		AssignedTo:     "bob",
		EstimatedHours: 4,
		Priority:       1,
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got.ID != want.ID {
		t.Errorf("task ID: got %q, want %q", got.ID, want.ID)
	}
	if got.StoryID != want.StoryID {
		t.Errorf("task StoryID: got %q, want %q", got.StoryID, want.StoryID)
	}
	if got.Title != want.Title {
		t.Errorf("task Title: got %q, want %q", got.Title, want.Title)
	}
	if got.Description != want.Description {
		t.Errorf("task Description: got %q, want %q", got.Description, want.Description)
	}
	if got.Type != want.Type {
		t.Errorf("task Type: got %q, want %q", got.Type, want.Type)
	}
	if got.AssignedTo != want.AssignedTo {
		t.Errorf("task AssignedTo: got %q, want %q", got.AssignedTo, want.AssignedTo)
	}
	if got.EstimatedHours != want.EstimatedHours {
		t.Errorf("task EstimatedHours: got %d, want %d", got.EstimatedHours, want.EstimatedHours)
	}
	if got.Priority != want.Priority {
		t.Errorf("task Priority: got %d, want %d", got.Priority, want.Priority)
	}
	// Verify delegation
	if fc.ctStoryID != "story-10" {
		t.Errorf("client received storyID %q, want %q", fc.ctStoryID, "story-10")
	}
	if fc.ctTitle != "Implement login" {
		t.Errorf("client received title %q, want %q", fc.ctTitle, "Implement login")
	}
	if fc.ctDescription != "Build the login page" {
		t.Errorf("client received description %q, want %q", fc.ctDescription, "Build the login page")
	}
	if fc.ctTaskType != "CODING" {
		t.Errorf("client received taskType %q, want %q", fc.ctTaskType, "CODING")
	}
	if fc.ctAssignedTo != "bob" {
		t.Errorf("client received assignedTo %q, want %q", fc.ctAssignedTo, "bob")
	}
	if fc.ctEstimatedHours != 4 {
		t.Errorf("client received estimatedHours %d, want %d", fc.ctEstimatedHours, 4)
	}
	if fc.ctPriority != 1 {
		t.Errorf("client received priority %d, want %d", fc.ctPriority, 1)
	}
	if fc.ctRequestID == "" {
		t.Error("client received empty requestID")
	}
	if len(fc.ctRequestID) != 32 {
		t.Errorf("requestID length: got %d, want 32", len(fc.ctRequestID))
	}
}

func TestCreateTaskHandler_EmptyStoryID(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewCreateTaskHandler(fc)

	_, err := h.Handle(context.Background(), CreateTaskCmd{
		StoryID: "",
		Title:   "Has a title",
	})
	if err == nil {
		t.Fatal("expected error for empty story_id")
	}
	if !strings.Contains(err.Error(), "story_id is required") {
		t.Errorf("error message %q does not mention 'story_id is required'", err.Error())
	}
}

func TestCreateTaskHandler_EmptyTitle(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewCreateTaskHandler(fc)

	_, err := h.Handle(context.Background(), CreateTaskCmd{
		StoryID: "story-1",
		Title:   "",
	})
	if err == nil {
		t.Fatal("expected error for empty title")
	}
	if !strings.Contains(err.Error(), "title is required") {
		t.Errorf("error message %q does not mention 'title is required'", err.Error())
	}
}

func TestCreateTaskHandler_BothFieldsMissing(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewCreateTaskHandler(fc)

	_, err := h.Handle(context.Background(), CreateTaskCmd{})
	if err == nil {
		t.Fatal("expected error")
	}
	if !strings.Contains(err.Error(), "story_id is required") {
		t.Errorf("expected story_id validation first, got %q", err.Error())
	}
}

func TestCreateTaskHandler_ClientError(t *testing.T) {
	clientErr := errors.New("deadline exceeded")
	fc := &fakeFleetClient{createTaskErr: clientErr}
	h := NewCreateTaskHandler(fc)

	_, err := h.Handle(context.Background(), CreateTaskCmd{
		StoryID: "story-1",
		Title:   "valid",
	})
	if err == nil {
		t.Fatal("expected error from client")
	}
	if !strings.Contains(err.Error(), "create_task:") {
		t.Errorf("error should be prefixed with 'create_task:', got %q", err.Error())
	}
	if !errors.Is(err, clientErr) {
		t.Errorf("error should wrap client error; got %q", err.Error())
	}
}

// ---------------------------------------------------------------------------
// ApproveDecisionHandler tests
// ---------------------------------------------------------------------------

func TestApproveDecisionHandler_Success(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewApproveDecisionHandler(fc)

	err := h.Handle(context.Background(), ApproveDecisionCmd{
		StoryID:    "story-5",
		DecisionID: "dec-1",
		Comment:    "Looks good to me",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if fc.adStoryID != "story-5" {
		t.Errorf("client received storyID %q, want %q", fc.adStoryID, "story-5")
	}
	if fc.adDecisionID != "dec-1" {
		t.Errorf("client received decisionID %q, want %q", fc.adDecisionID, "dec-1")
	}
	if fc.adComment != "Looks good to me" {
		t.Errorf("client received comment %q, want %q", fc.adComment, "Looks good to me")
	}
}

func TestApproveDecisionHandler_EmptyStoryID(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewApproveDecisionHandler(fc)

	err := h.Handle(context.Background(), ApproveDecisionCmd{
		StoryID:    "",
		DecisionID: "dec-1",
	})
	if err == nil {
		t.Fatal("expected error for empty story_id")
	}
	if !strings.Contains(err.Error(), "story_id is required") {
		t.Errorf("error message %q does not mention 'story_id is required'", err.Error())
	}
}

func TestApproveDecisionHandler_EmptyDecisionID(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewApproveDecisionHandler(fc)

	err := h.Handle(context.Background(), ApproveDecisionCmd{
		StoryID:    "story-1",
		DecisionID: "",
	})
	if err == nil {
		t.Fatal("expected error for empty decision_id")
	}
	if !strings.Contains(err.Error(), "decision_id is required") {
		t.Errorf("error message %q does not mention 'decision_id is required'", err.Error())
	}
}

func TestApproveDecisionHandler_BothFieldsMissing(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewApproveDecisionHandler(fc)

	err := h.Handle(context.Background(), ApproveDecisionCmd{})
	if err == nil {
		t.Fatal("expected error")
	}
	if !strings.Contains(err.Error(), "story_id is required") {
		t.Errorf("expected story_id validation first, got %q", err.Error())
	}
}

func TestApproveDecisionHandler_CommentOptional(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewApproveDecisionHandler(fc)

	err := h.Handle(context.Background(), ApproveDecisionCmd{
		StoryID:    "story-1",
		DecisionID: "dec-1",
		Comment:    "",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if fc.adComment != "" {
		t.Errorf("client received comment %q, want empty", fc.adComment)
	}
}

func TestApproveDecisionHandler_ClientError(t *testing.T) {
	clientErr := errors.New("not found")
	fc := &fakeFleetClient{approveDecisionErr: clientErr}
	h := NewApproveDecisionHandler(fc)

	err := h.Handle(context.Background(), ApproveDecisionCmd{
		StoryID:    "story-1",
		DecisionID: "dec-1",
	})
	if err == nil {
		t.Fatal("expected error from client")
	}
	if !strings.Contains(err.Error(), "approve_decision:") {
		t.Errorf("error should be prefixed with 'approve_decision:', got %q", err.Error())
	}
	if !errors.Is(err, clientErr) {
		t.Errorf("error should wrap client error; got %q", err.Error())
	}
}

// ---------------------------------------------------------------------------
// RejectDecisionHandler tests
// ---------------------------------------------------------------------------

func TestRejectDecisionHandler_Success(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewRejectDecisionHandler(fc)

	err := h.Handle(context.Background(), RejectDecisionCmd{
		StoryID:    "story-5",
		DecisionID: "dec-2",
		Reason:     "Needs more analysis",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if fc.rdStoryID != "story-5" {
		t.Errorf("client received storyID %q, want %q", fc.rdStoryID, "story-5")
	}
	if fc.rdDecisionID != "dec-2" {
		t.Errorf("client received decisionID %q, want %q", fc.rdDecisionID, "dec-2")
	}
	if fc.rdReason != "Needs more analysis" {
		t.Errorf("client received reason %q, want %q", fc.rdReason, "Needs more analysis")
	}
}

func TestRejectDecisionHandler_EmptyStoryID(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewRejectDecisionHandler(fc)

	err := h.Handle(context.Background(), RejectDecisionCmd{
		StoryID:    "",
		DecisionID: "dec-1",
		Reason:     "Some reason",
	})
	if err == nil {
		t.Fatal("expected error for empty story_id")
	}
	if !strings.Contains(err.Error(), "story_id is required") {
		t.Errorf("error message %q does not mention 'story_id is required'", err.Error())
	}
}

func TestRejectDecisionHandler_EmptyDecisionID(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewRejectDecisionHandler(fc)

	err := h.Handle(context.Background(), RejectDecisionCmd{
		StoryID:    "story-1",
		DecisionID: "",
		Reason:     "Some reason",
	})
	if err == nil {
		t.Fatal("expected error for empty decision_id")
	}
	if !strings.Contains(err.Error(), "decision_id is required") {
		t.Errorf("error message %q does not mention 'decision_id is required'", err.Error())
	}
}

func TestRejectDecisionHandler_EmptyReason(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewRejectDecisionHandler(fc)

	err := h.Handle(context.Background(), RejectDecisionCmd{
		StoryID:    "story-1",
		DecisionID: "dec-1",
		Reason:     "",
	})
	if err == nil {
		t.Fatal("expected error for empty reason")
	}
	if !strings.Contains(err.Error(), "reason is required") {
		t.Errorf("error message %q does not mention 'reason is required'", err.Error())
	}
}

func TestRejectDecisionHandler_ValidationOrder(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewRejectDecisionHandler(fc)

	err := h.Handle(context.Background(), RejectDecisionCmd{})
	if err == nil {
		t.Fatal("expected error")
	}
	if !strings.Contains(err.Error(), "story_id is required") {
		t.Errorf("expected story_id validation first, got %q", err.Error())
	}
}

func TestRejectDecisionHandler_ClientError(t *testing.T) {
	clientErr := errors.New("permission denied")
	fc := &fakeFleetClient{rejectDecisionErr: clientErr}
	h := NewRejectDecisionHandler(fc)

	err := h.Handle(context.Background(), RejectDecisionCmd{
		StoryID:    "story-1",
		DecisionID: "dec-1",
		Reason:     "valid reason",
	})
	if err == nil {
		t.Fatal("expected error from client")
	}
	if !strings.Contains(err.Error(), "reject_decision:") {
		t.Errorf("error should be prefixed with 'reject_decision:', got %q", err.Error())
	}
	if !errors.Is(err, clientErr) {
		t.Errorf("error should wrap client error; got %q", err.Error())
	}
}

// ---------------------------------------------------------------------------
// RenewHandler tests
// ---------------------------------------------------------------------------

func TestRenewHandler_Success(t *testing.T) {
	fc := &fakeFleetClient{
		renewCertPEM: []byte("RENEWED-CERT-PEM"),
		renewCAPEM:   []byte("RENEWED-CA-PEM"),
		renewExpires: "2028-01-01T00:00:00Z",
	}
	credStore := &fakeCredentialStore{}
	cfgStore := &fakeConfigStore{
		loadResult: domain.Config{ServerName: "fleet.example.com"},
	}
	h := NewRenewHandler(fc, credStore, cfgStore)

	result, err := h.Handle(context.Background(), RenewCmd{})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Verify returned result
	if result.ExpiresAt != "2028-01-01T00:00:00Z" {
		t.Errorf("ExpiresAt: got %q, want %q", result.ExpiresAt, "2028-01-01T00:00:00Z")
	}

	// Verify client received CSR
	if len(fc.rnCSRPEM) == 0 {
		t.Fatal("client received empty CSR PEM")
	}
	if !strings.Contains(string(fc.rnCSRPEM), "CERTIFICATE REQUEST") {
		t.Error("CSR PEM does not contain 'CERTIFICATE REQUEST' header")
	}

	// Verify credentials were saved
	if !credStore.saved {
		t.Fatal("credentials were not saved")
	}
	if string(credStore.savedCert) != "RENEWED-CERT-PEM" {
		t.Errorf("saved cert: got %q, want %q", credStore.savedCert, "RENEWED-CERT-PEM")
	}
	if string(credStore.savedCA) != "RENEWED-CA-PEM" {
		t.Errorf("saved CA: got %q, want %q", credStore.savedCA, "RENEWED-CA-PEM")
	}
	if credStore.savedSN != "fleet.example.com" {
		t.Errorf("saved serverName: got %q, want %q", credStore.savedSN, "fleet.example.com")
	}
	// Key should be PEM-encoded EC private key
	if !strings.Contains(string(credStore.savedKey), "EC PRIVATE KEY") {
		t.Error("saved key does not contain 'EC PRIVATE KEY' header")
	}
}

func TestRenewHandler_CSRContainsFleetctlDevice(t *testing.T) {
	fc := &fakeFleetClient{
		renewCertPEM: []byte("CERT"),
		renewCAPEM:   []byte("CA"),
		renewExpires: "2028-01-01",
	}
	credStore := &fakeCredentialStore{}
	cfgStore := &fakeConfigStore{
		loadResult: domain.Config{ServerName: "fleet.example.com"},
	}
	h := NewRenewHandler(fc, credStore, cfgStore)

	_, err := h.Handle(context.Background(), RenewCmd{})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Parse the CSR PEM that was sent to the client.
	block, _ := pem.Decode(fc.rnCSRPEM)
	if block == nil {
		t.Fatal("failed to decode CSR PEM block")
	}

	csr, err := x509.ParseCertificateRequest(block.Bytes)
	if err != nil {
		t.Fatalf("failed to parse CSR DER: %v", err)
	}

	if csr.Subject.CommonName != "fleetctl-device" {
		t.Errorf("CSR CN: got %q, want %q", csr.Subject.CommonName, "fleetctl-device")
	}
	if len(csr.Subject.Organization) == 0 || csr.Subject.Organization[0] != "swe-ai-fleet" {
		t.Errorf("CSR Organization: got %v, want [swe-ai-fleet]", csr.Subject.Organization)
	}
}

func TestRenewHandler_ClientRenewError(t *testing.T) {
	clientErr := errors.New("certificate expired")
	fc := &fakeFleetClient{renewErr: clientErr}
	credStore := &fakeCredentialStore{}
	cfgStore := &fakeConfigStore{
		loadResult: domain.Config{ServerName: "fleet.example.com"},
	}
	h := NewRenewHandler(fc, credStore, cfgStore)

	_, err := h.Handle(context.Background(), RenewCmd{})
	if err == nil {
		t.Fatal("expected error from client renew")
	}
	if !strings.Contains(err.Error(), "server call failed") {
		t.Errorf("error message %q does not mention 'server call failed'", err.Error())
	}
	if !errors.Is(err, clientErr) {
		t.Errorf("error should wrap client error; got %q", err.Error())
	}
	if credStore.saved {
		t.Error("credentials should not be saved when renew fails")
	}
}

func TestRenewHandler_ConfigLoadError(t *testing.T) {
	fc := &fakeFleetClient{
		renewCertPEM: []byte("CERT"),
		renewCAPEM:   []byte("CA"),
		renewExpires: "2028-01-01",
	}
	cfgErr := errors.New("config file not found")
	credStore := &fakeCredentialStore{}
	cfgStore := &fakeConfigStore{loadErr: cfgErr}
	h := NewRenewHandler(fc, credStore, cfgStore)

	_, err := h.Handle(context.Background(), RenewCmd{})
	if err == nil {
		t.Fatal("expected error from config load")
	}
	if !strings.Contains(err.Error(), "failed to load config") {
		t.Errorf("error message %q does not mention 'failed to load config'", err.Error())
	}
	if !errors.Is(err, cfgErr) {
		t.Errorf("error should wrap config error; got %q", err.Error())
	}
	if credStore.saved {
		t.Error("credentials should not be saved when config load fails")
	}
}

func TestRenewHandler_CredStoreSaveError(t *testing.T) {
	fc := &fakeFleetClient{
		renewCertPEM: []byte("CERT"),
		renewCAPEM:   []byte("CA"),
		renewExpires: "2028-01-01",
	}
	saveErr := errors.New("permission denied")
	credStore := &fakeCredentialStore{saveErr: saveErr}
	cfgStore := &fakeConfigStore{
		loadResult: domain.Config{ServerName: "fleet.example.com"},
	}
	h := NewRenewHandler(fc, credStore, cfgStore)

	_, err := h.Handle(context.Background(), RenewCmd{})
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

func TestRenewHandler_GeneratesUniqueKey(t *testing.T) {
	fc := &fakeFleetClient{
		renewCertPEM: []byte("CERT"),
		renewCAPEM:   []byte("CA"),
		renewExpires: "2028-01-01",
	}
	cfgStore := &fakeConfigStore{
		loadResult: domain.Config{ServerName: "fleet.example.com"},
	}

	credStore1 := &fakeCredentialStore{}
	h1 := NewRenewHandler(fc, credStore1, cfgStore)
	_, err := h1.Handle(context.Background(), RenewCmd{})
	if err != nil {
		t.Fatalf("first renew: %v", err)
	}

	credStore2 := &fakeCredentialStore{}
	h2 := NewRenewHandler(fc, credStore2, cfgStore)
	_, err = h2.Handle(context.Background(), RenewCmd{})
	if err != nil {
		t.Fatalf("second renew: %v", err)
	}

	if string(credStore1.savedKey) == string(credStore2.savedKey) {
		t.Error("two renewals produced the same private key PEM")
	}
}

// ---------------------------------------------------------------------------
// CreateBacklogReviewHandler tests
// ---------------------------------------------------------------------------

func TestCreateBacklogReviewHandler_Success(t *testing.T) {
	want := domain.BacklogReview{
		CeremonyID: "cer-br-1",
		Status:     "CREATED",
		CreatedBy:  "alice",
		CreatedAt:  "2026-01-01T00:00:00Z",
		StoryIDs:   []string{"story-1", "story-2"},
	}
	fc := &fakeFleetClient{createBRResult: want}
	h := NewCreateBacklogReviewHandler(fc)

	got, err := h.Handle(context.Background(), CreateBacklogReviewCmd{
		StoryIDs: []string{"story-1", "story-2"},
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got.CeremonyID != want.CeremonyID {
		t.Errorf("CeremonyID: got %q, want %q", got.CeremonyID, want.CeremonyID)
	}
	if got.Status != want.Status {
		t.Errorf("Status: got %q, want %q", got.Status, want.Status)
	}
	if len(got.StoryIDs) != 2 || got.StoryIDs[0] != "story-1" || got.StoryIDs[1] != "story-2" {
		t.Errorf("StoryIDs: got %v, want [story-1 story-2]", got.StoryIDs)
	}
	// Verify delegation
	if len(fc.cbrStoryIDs) != 2 || fc.cbrStoryIDs[0] != "story-1" || fc.cbrStoryIDs[1] != "story-2" {
		t.Errorf("client received storyIDs %v, want [story-1 story-2]", fc.cbrStoryIDs)
	}
	if fc.cbrRequestID == "" {
		t.Error("client received empty requestID")
	}
	if len(fc.cbrRequestID) != 32 {
		t.Errorf("requestID length: got %d, want 32", len(fc.cbrRequestID))
	}
}

func TestCreateBacklogReviewHandler_EmptyStoryIDs(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewCreateBacklogReviewHandler(fc)

	_, err := h.Handle(context.Background(), CreateBacklogReviewCmd{
		StoryIDs: []string{},
	})
	if err == nil {
		t.Fatal("expected error for empty story_ids")
	}
	if !strings.Contains(err.Error(), "at least one story_id is required") {
		t.Errorf("error message %q does not mention 'at least one story_id is required'", err.Error())
	}
}

func TestCreateBacklogReviewHandler_NilStoryIDs(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewCreateBacklogReviewHandler(fc)

	_, err := h.Handle(context.Background(), CreateBacklogReviewCmd{
		StoryIDs: nil,
	})
	if err == nil {
		t.Fatal("expected error for nil story_ids")
	}
	if !strings.Contains(err.Error(), "at least one story_id is required") {
		t.Errorf("error message %q does not mention 'at least one story_id is required'", err.Error())
	}
}

func TestCreateBacklogReviewHandler_ClientError(t *testing.T) {
	clientErr := errors.New("service unavailable")
	fc := &fakeFleetClient{createBRErr: clientErr}
	h := NewCreateBacklogReviewHandler(fc)

	_, err := h.Handle(context.Background(), CreateBacklogReviewCmd{
		StoryIDs: []string{"story-1"},
	})
	if err == nil {
		t.Fatal("expected error from client")
	}
	if !strings.Contains(err.Error(), "create_backlog_review:") {
		t.Errorf("error should be prefixed with 'create_backlog_review:', got %q", err.Error())
	}
	if !errors.Is(err, clientErr) {
		t.Errorf("error should wrap client error; got %q", err.Error())
	}
}

// ---------------------------------------------------------------------------
// StartBacklogReviewHandler tests
// ---------------------------------------------------------------------------

func TestStartBacklogReviewHandler_Success(t *testing.T) {
	wantReview := domain.BacklogReview{
		CeremonyID: "cer-br-1",
		Status:     "IN_PROGRESS",
		StartedAt:  "2026-01-01T00:00:00Z",
	}
	fc := &fakeFleetClient{startBRResult: wantReview, startBRTotal: 5}
	h := NewStartBacklogReviewHandler(fc)

	got, err := h.Handle(context.Background(), StartBacklogReviewCmd{
		CeremonyID: "cer-br-1",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got.Review.CeremonyID != wantReview.CeremonyID {
		t.Errorf("Review.CeremonyID: got %q, want %q", got.Review.CeremonyID, wantReview.CeremonyID)
	}
	if got.Review.Status != wantReview.Status {
		t.Errorf("Review.Status: got %q, want %q", got.Review.Status, wantReview.Status)
	}
	if got.Total != 5 {
		t.Errorf("Total: got %d, want %d", got.Total, 5)
	}
	// Verify delegation
	if fc.sbrCeremonyID != "cer-br-1" {
		t.Errorf("client received ceremonyID %q, want %q", fc.sbrCeremonyID, "cer-br-1")
	}
	if fc.sbrRequestID == "" {
		t.Error("client received empty requestID")
	}
	if len(fc.sbrRequestID) != 32 {
		t.Errorf("requestID length: got %d, want 32", len(fc.sbrRequestID))
	}
}

func TestStartBacklogReviewHandler_EmptyCeremonyID(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewStartBacklogReviewHandler(fc)

	_, err := h.Handle(context.Background(), StartBacklogReviewCmd{
		CeremonyID: "",
	})
	if err == nil {
		t.Fatal("expected error for empty ceremony_id")
	}
	if !strings.Contains(err.Error(), "ceremony_id is required") {
		t.Errorf("error message %q does not mention 'ceremony_id is required'", err.Error())
	}
}

func TestStartBacklogReviewHandler_ClientError(t *testing.T) {
	clientErr := errors.New("ceremony not found")
	fc := &fakeFleetClient{startBRErr: clientErr}
	h := NewStartBacklogReviewHandler(fc)

	_, err := h.Handle(context.Background(), StartBacklogReviewCmd{
		CeremonyID: "cer-1",
	})
	if err == nil {
		t.Fatal("expected error from client")
	}
	if !strings.Contains(err.Error(), "start_backlog_review:") {
		t.Errorf("error should be prefixed with 'start_backlog_review:', got %q", err.Error())
	}
	if !errors.Is(err, clientErr) {
		t.Errorf("error should wrap client error; got %q", err.Error())
	}
}

// ---------------------------------------------------------------------------
// ApproveReviewPlanHandler tests
// ---------------------------------------------------------------------------

func TestApproveReviewPlanHandler_Success(t *testing.T) {
	wantReview := domain.BacklogReview{
		CeremonyID: "cer-br-1",
		Status:     "IN_PROGRESS",
	}
	fc := &fakeFleetClient{approvePlanResult: wantReview, approvePlanID: "plan-42"}
	h := NewApproveReviewPlanHandler(fc)

	got, err := h.Handle(context.Background(), ApproveReviewPlanCmd{
		CeremonyID:  "cer-br-1",
		StoryID:     "story-5",
		PONotes:     "Approved with conditions",
		POConcerns:  "Performance risk",
		PriorityAdj: "HIGH",
		PrioReason:  "Customer demand",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got.Review.CeremonyID != wantReview.CeremonyID {
		t.Errorf("Review.CeremonyID: got %q, want %q", got.Review.CeremonyID, wantReview.CeremonyID)
	}
	if got.PlanID != "plan-42" {
		t.Errorf("PlanID: got %q, want %q", got.PlanID, "plan-42")
	}
	// Verify delegation
	if fc.aprCeremonyID != "cer-br-1" {
		t.Errorf("client received ceremonyID %q, want %q", fc.aprCeremonyID, "cer-br-1")
	}
	if fc.aprStoryID != "story-5" {
		t.Errorf("client received storyID %q, want %q", fc.aprStoryID, "story-5")
	}
	if fc.aprPONotes != "Approved with conditions" {
		t.Errorf("client received poNotes %q, want %q", fc.aprPONotes, "Approved with conditions")
	}
	if fc.aprPOConcerns != "Performance risk" {
		t.Errorf("client received poConcerns %q, want %q", fc.aprPOConcerns, "Performance risk")
	}
	if fc.aprPriorityAdj != "HIGH" {
		t.Errorf("client received priorityAdj %q, want %q", fc.aprPriorityAdj, "HIGH")
	}
	if fc.aprPrioReason != "Customer demand" {
		t.Errorf("client received prioReason %q, want %q", fc.aprPrioReason, "Customer demand")
	}
	if fc.aprRequestID == "" {
		t.Error("client received empty requestID")
	}
	if len(fc.aprRequestID) != 32 {
		t.Errorf("requestID length: got %d, want 32", len(fc.aprRequestID))
	}
}

func TestApproveReviewPlanHandler_EmptyCeremonyID(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewApproveReviewPlanHandler(fc)

	_, err := h.Handle(context.Background(), ApproveReviewPlanCmd{
		CeremonyID: "",
		StoryID:    "story-1",
		PONotes:    "notes",
	})
	if err == nil {
		t.Fatal("expected error for empty ceremony_id")
	}
	if !strings.Contains(err.Error(), "ceremony_id is required") {
		t.Errorf("error message %q does not mention 'ceremony_id is required'", err.Error())
	}
}

func TestApproveReviewPlanHandler_EmptyStoryID(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewApproveReviewPlanHandler(fc)

	_, err := h.Handle(context.Background(), ApproveReviewPlanCmd{
		CeremonyID: "cer-1",
		StoryID:    "",
		PONotes:    "notes",
	})
	if err == nil {
		t.Fatal("expected error for empty story_id")
	}
	if !strings.Contains(err.Error(), "story_id is required") {
		t.Errorf("error message %q does not mention 'story_id is required'", err.Error())
	}
}

func TestApproveReviewPlanHandler_EmptyPONotes(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewApproveReviewPlanHandler(fc)

	_, err := h.Handle(context.Background(), ApproveReviewPlanCmd{
		CeremonyID: "cer-1",
		StoryID:    "story-1",
		PONotes:    "",
	})
	if err == nil {
		t.Fatal("expected error for empty po_notes")
	}
	if !strings.Contains(err.Error(), "po_notes is required") {
		t.Errorf("error message %q does not mention 'po_notes is required'", err.Error())
	}
}

func TestApproveReviewPlanHandler_ValidationOrder(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewApproveReviewPlanHandler(fc)

	_, err := h.Handle(context.Background(), ApproveReviewPlanCmd{})
	if err == nil {
		t.Fatal("expected error")
	}
	if !strings.Contains(err.Error(), "ceremony_id is required") {
		t.Errorf("expected ceremony_id validation first, got %q", err.Error())
	}
}

func TestApproveReviewPlanHandler_ClientError(t *testing.T) {
	clientErr := errors.New("internal server error")
	fc := &fakeFleetClient{approvePlanErr: clientErr}
	h := NewApproveReviewPlanHandler(fc)

	_, err := h.Handle(context.Background(), ApproveReviewPlanCmd{
		CeremonyID: "cer-1",
		StoryID:    "story-1",
		PONotes:    "valid notes",
	})
	if err == nil {
		t.Fatal("expected error from client")
	}
	if !strings.Contains(err.Error(), "approve_review_plan:") {
		t.Errorf("error should be prefixed with 'approve_review_plan:', got %q", err.Error())
	}
	if !errors.Is(err, clientErr) {
		t.Errorf("error should wrap client error; got %q", err.Error())
	}
}

// ---------------------------------------------------------------------------
// RejectReviewPlanHandler tests
// ---------------------------------------------------------------------------

func TestRejectReviewPlanHandler_Success(t *testing.T) {
	want := domain.BacklogReview{
		CeremonyID: "cer-br-1",
		Status:     "IN_PROGRESS",
	}
	fc := &fakeFleetClient{rejectPlanResult: want}
	h := NewRejectReviewPlanHandler(fc)

	got, err := h.Handle(context.Background(), RejectReviewPlanCmd{
		CeremonyID: "cer-br-1",
		StoryID:    "story-5",
		Reason:     "Insufficient detail",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got.CeremonyID != want.CeremonyID {
		t.Errorf("CeremonyID: got %q, want %q", got.CeremonyID, want.CeremonyID)
	}
	if got.Status != want.Status {
		t.Errorf("Status: got %q, want %q", got.Status, want.Status)
	}
	// Verify delegation
	if fc.rprCeremonyID != "cer-br-1" {
		t.Errorf("client received ceremonyID %q, want %q", fc.rprCeremonyID, "cer-br-1")
	}
	if fc.rprStoryID != "story-5" {
		t.Errorf("client received storyID %q, want %q", fc.rprStoryID, "story-5")
	}
	if fc.rprReason != "Insufficient detail" {
		t.Errorf("client received reason %q, want %q", fc.rprReason, "Insufficient detail")
	}
	if fc.rprRequestID == "" {
		t.Error("client received empty requestID")
	}
	if len(fc.rprRequestID) != 32 {
		t.Errorf("requestID length: got %d, want 32", len(fc.rprRequestID))
	}
}

func TestRejectReviewPlanHandler_EmptyCeremonyID(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewRejectReviewPlanHandler(fc)

	_, err := h.Handle(context.Background(), RejectReviewPlanCmd{
		CeremonyID: "",
		StoryID:    "story-1",
		Reason:     "reason",
	})
	if err == nil {
		t.Fatal("expected error for empty ceremony_id")
	}
	if !strings.Contains(err.Error(), "ceremony_id is required") {
		t.Errorf("error message %q does not mention 'ceremony_id is required'", err.Error())
	}
}

func TestRejectReviewPlanHandler_EmptyStoryID(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewRejectReviewPlanHandler(fc)

	_, err := h.Handle(context.Background(), RejectReviewPlanCmd{
		CeremonyID: "cer-1",
		StoryID:    "",
		Reason:     "reason",
	})
	if err == nil {
		t.Fatal("expected error for empty story_id")
	}
	if !strings.Contains(err.Error(), "story_id is required") {
		t.Errorf("error message %q does not mention 'story_id is required'", err.Error())
	}
}

func TestRejectReviewPlanHandler_EmptyReason(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewRejectReviewPlanHandler(fc)

	_, err := h.Handle(context.Background(), RejectReviewPlanCmd{
		CeremonyID: "cer-1",
		StoryID:    "story-1",
		Reason:     "",
	})
	if err == nil {
		t.Fatal("expected error for empty reason")
	}
	if !strings.Contains(err.Error(), "reason is required") {
		t.Errorf("error message %q does not mention 'reason is required'", err.Error())
	}
}

func TestRejectReviewPlanHandler_ValidationOrder(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewRejectReviewPlanHandler(fc)

	_, err := h.Handle(context.Background(), RejectReviewPlanCmd{})
	if err == nil {
		t.Fatal("expected error")
	}
	if !strings.Contains(err.Error(), "ceremony_id is required") {
		t.Errorf("expected ceremony_id validation first, got %q", err.Error())
	}
}

func TestRejectReviewPlanHandler_ClientError(t *testing.T) {
	clientErr := errors.New("story not found")
	fc := &fakeFleetClient{rejectPlanErr: clientErr}
	h := NewRejectReviewPlanHandler(fc)

	_, err := h.Handle(context.Background(), RejectReviewPlanCmd{
		CeremonyID: "cer-1",
		StoryID:    "story-1",
		Reason:     "valid reason",
	})
	if err == nil {
		t.Fatal("expected error from client")
	}
	if !strings.Contains(err.Error(), "reject_review_plan:") {
		t.Errorf("error should be prefixed with 'reject_review_plan:', got %q", err.Error())
	}
	if !errors.Is(err, clientErr) {
		t.Errorf("error should wrap client error; got %q", err.Error())
	}
}

// ---------------------------------------------------------------------------
// CompleteBacklogReviewHandler tests
// ---------------------------------------------------------------------------

func TestCompleteBacklogReviewHandler_Success(t *testing.T) {
	want := domain.BacklogReview{
		CeremonyID:  "cer-br-1",
		Status:      "COMPLETED",
		CompletedAt: "2026-01-02T00:00:00Z",
	}
	fc := &fakeFleetClient{completeBRResult: want}
	h := NewCompleteBacklogReviewHandler(fc)

	got, err := h.Handle(context.Background(), CompleteBacklogReviewCmd{
		CeremonyID: "cer-br-1",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got.CeremonyID != want.CeremonyID {
		t.Errorf("CeremonyID: got %q, want %q", got.CeremonyID, want.CeremonyID)
	}
	if got.Status != want.Status {
		t.Errorf("Status: got %q, want %q", got.Status, want.Status)
	}
	if got.CompletedAt != want.CompletedAt {
		t.Errorf("CompletedAt: got %q, want %q", got.CompletedAt, want.CompletedAt)
	}
	// Verify delegation
	if fc.combrCeremonyID != "cer-br-1" {
		t.Errorf("client received ceremonyID %q, want %q", fc.combrCeremonyID, "cer-br-1")
	}
	if fc.combrRequestID == "" {
		t.Error("client received empty requestID")
	}
	if len(fc.combrRequestID) != 32 {
		t.Errorf("requestID length: got %d, want 32", len(fc.combrRequestID))
	}
}

func TestCompleteBacklogReviewHandler_EmptyCeremonyID(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewCompleteBacklogReviewHandler(fc)

	_, err := h.Handle(context.Background(), CompleteBacklogReviewCmd{
		CeremonyID: "",
	})
	if err == nil {
		t.Fatal("expected error for empty ceremony_id")
	}
	if !strings.Contains(err.Error(), "ceremony_id is required") {
		t.Errorf("error message %q does not mention 'ceremony_id is required'", err.Error())
	}
}

func TestCompleteBacklogReviewHandler_ClientError(t *testing.T) {
	clientErr := errors.New("already completed")
	fc := &fakeFleetClient{completeBRErr: clientErr}
	h := NewCompleteBacklogReviewHandler(fc)

	_, err := h.Handle(context.Background(), CompleteBacklogReviewCmd{
		CeremonyID: "cer-1",
	})
	if err == nil {
		t.Fatal("expected error from client")
	}
	if !strings.Contains(err.Error(), "complete_backlog_review:") {
		t.Errorf("error should be prefixed with 'complete_backlog_review:', got %q", err.Error())
	}
	if !errors.Is(err, clientErr) {
		t.Errorf("error should wrap client error; got %q", err.Error())
	}
}

// ---------------------------------------------------------------------------
// CancelBacklogReviewHandler tests
// ---------------------------------------------------------------------------

func TestCancelBacklogReviewHandler_Success(t *testing.T) {
	want := domain.BacklogReview{
		CeremonyID: "cer-br-1",
		Status:     "CANCELLED",
	}
	fc := &fakeFleetClient{cancelBRResult: want}
	h := NewCancelBacklogReviewHandler(fc)

	got, err := h.Handle(context.Background(), CancelBacklogReviewCmd{
		CeremonyID: "cer-br-1",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got.CeremonyID != want.CeremonyID {
		t.Errorf("CeremonyID: got %q, want %q", got.CeremonyID, want.CeremonyID)
	}
	if got.Status != want.Status {
		t.Errorf("Status: got %q, want %q", got.Status, want.Status)
	}
	// Verify delegation
	if fc.canbrCeremonyID != "cer-br-1" {
		t.Errorf("client received ceremonyID %q, want %q", fc.canbrCeremonyID, "cer-br-1")
	}
	if fc.canbrRequestID == "" {
		t.Error("client received empty requestID")
	}
	if len(fc.canbrRequestID) != 32 {
		t.Errorf("requestID length: got %d, want 32", len(fc.canbrRequestID))
	}
}

func TestCancelBacklogReviewHandler_EmptyCeremonyID(t *testing.T) {
	fc := &fakeFleetClient{}
	h := NewCancelBacklogReviewHandler(fc)

	_, err := h.Handle(context.Background(), CancelBacklogReviewCmd{
		CeremonyID: "",
	})
	if err == nil {
		t.Fatal("expected error for empty ceremony_id")
	}
	if !strings.Contains(err.Error(), "ceremony_id is required") {
		t.Errorf("error message %q does not mention 'ceremony_id is required'", err.Error())
	}
}

func TestCancelBacklogReviewHandler_ClientError(t *testing.T) {
	clientErr := errors.New("ceremony not found")
	fc := &fakeFleetClient{cancelBRErr: clientErr}
	h := NewCancelBacklogReviewHandler(fc)

	_, err := h.Handle(context.Background(), CancelBacklogReviewCmd{
		CeremonyID: "cer-1",
	})
	if err == nil {
		t.Fatal("expected error from client")
	}
	if !strings.Contains(err.Error(), "cancel_backlog_review:") {
		t.Errorf("error should be prefixed with 'cancel_backlog_review:', got %q", err.Error())
	}
	if !errors.Is(err, clientErr) {
		t.Errorf("error should wrap client error; got %q", err.Error())
	}
}
