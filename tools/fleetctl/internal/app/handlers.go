package app

import (
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/command"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/tools/fleetctl/internal/app/query"
)

// Handlers aggregates all command and query handlers for clean wiring
// into the TUI layer. Each view receives only the handlers it needs.
type Handlers struct {
	// Commands
	Enroll                *command.EnrollHandler
	Renew                 *command.RenewHandler
	CreateProject         *command.CreateProjectHandler
	CreateEpic            *command.CreateEpicHandler
	CreateStory           *command.CreateStoryHandler
	CreateTask            *command.CreateTaskHandler
	TransitionStory       *command.TransitionStoryHandler
	StartCeremony         *command.StartCeremonyHandler
	ApproveDecision       *command.ApproveDecisionHandler
	RejectDecision        *command.RejectDecisionHandler
	CreateBacklogReview   *command.CreateBacklogReviewHandler
	StartBacklogReview    *command.StartBacklogReviewHandler
	ApproveReviewPlan     *command.ApproveReviewPlanHandler
	RejectReviewPlan      *command.RejectReviewPlanHandler
	CompleteBacklogReview *command.CompleteBacklogReviewHandler
	CancelBacklogReview   *command.CancelBacklogReviewHandler

	// Queries
	ListProjects       *query.ListProjectsHandler
	ListEpics          *query.ListEpicsHandler
	ListStories        *query.ListStoriesHandler
	ListTasks          *query.ListTasksHandler
	ListCeremonies     *query.ListCeremoniesHandler
	GetCeremony        *query.GetCeremonyHandler
	WatchEvents        *query.WatchEventsHandler
	GetBacklogReview   *query.GetBacklogReviewHandler
	ListBacklogReviews *query.ListBacklogReviewsHandler
}

// NewHandlers constructs all handlers wired to the given dependencies.
func NewHandlers(client ports.FleetClient, credStore ports.CredentialStore, cfgStore ports.ConfigStore) Handlers {
	return Handlers{
		// Commands
		Enroll:                command.NewEnrollHandler(client, credStore, cfgStore),
		Renew:                 command.NewRenewHandler(client, credStore, cfgStore),
		CreateProject:         command.NewCreateProjectHandler(client),
		CreateEpic:            command.NewCreateEpicHandler(client),
		CreateStory:           command.NewCreateStoryHandler(client),
		CreateTask:            command.NewCreateTaskHandler(client),
		TransitionStory:       command.NewTransitionStoryHandler(client),
		StartCeremony:         command.NewStartCeremonyHandler(client),
		ApproveDecision:       command.NewApproveDecisionHandler(client),
		RejectDecision:        command.NewRejectDecisionHandler(client),
		CreateBacklogReview:   command.NewCreateBacklogReviewHandler(client),
		StartBacklogReview:    command.NewStartBacklogReviewHandler(client),
		ApproveReviewPlan:     command.NewApproveReviewPlanHandler(client),
		RejectReviewPlan:      command.NewRejectReviewPlanHandler(client),
		CompleteBacklogReview: command.NewCompleteBacklogReviewHandler(client),
		CancelBacklogReview:   command.NewCancelBacklogReviewHandler(client),

		// Queries
		ListProjects:       query.NewListProjectsHandler(client),
		ListEpics:          query.NewListEpicsHandler(client),
		ListStories:        query.NewListStoriesHandler(client),
		ListTasks:          query.NewListTasksHandler(client),
		ListCeremonies:     query.NewListCeremoniesHandler(client),
		GetCeremony:        query.NewGetCeremonyHandler(client),
		WatchEvents:        query.NewWatchEventsHandler(client),
		GetBacklogReview:   query.NewGetBacklogReviewHandler(client),
		ListBacklogReviews: query.NewListBacklogReviewsHandler(client),
	}
}
