// Package main is the entry point for the fleet-proxy service.
// It reads configuration from environment variables, wires all adapters to the
// application layer, and starts the gRPC server with graceful shutdown.
package main

import (
	"fmt"
	"log/slog"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	proxyv1 "github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/gen/proxyv1"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/adapters/audit"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/adapters/ceremony"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/adapters/eventbus"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/adapters/grpcapi"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/adapters/identitymap"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/adapters/keystore"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/adapters/nats"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/adapters/pki"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/adapters/planning"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/adapters/userclient"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/command"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/ports"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/app/query"
	domainAuth "github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/auth"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/domain/identity"
)

// defaultCertTTL is the default certificate validity duration for enrolled clients.
const defaultCertTTL = 720 * time.Hour // 30 days

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		Level: slog.LevelInfo,
	}))
	slog.SetDefault(logger)

	if err := run(); err != nil {
		slog.Error("fleet-proxy failed", "error", err)
		os.Exit(1)
	}
}

func run() error {
	// --- Configuration from environment ---
	port := envInt("PORT", 8443)
	tlsCertPath := envStr("TLS_CERT_PATH", "")
	tlsKeyPath := envStr("TLS_KEY_PATH", "")
	clientCACertPath := envStr("CLIENT_CA_CERT_PATH", "")
	planningAddr := envStr("PLANNING_SERVICE_ADDR", "localhost:50051")
	ceremonyAddr := envStr("CEREMONY_SERVICE_ADDR", "localhost:50052")
	natsURL := envStr("NATS_URL", "nats://localhost:4222")
	valkeyAddr := envStr("VALKEY_ADDR", "localhost:6379")
	rateLimitRPS := envInt("RATE_LIMIT_RPS", 100)
	caCertPath := envStr("CA_CERT_PATH", "")
	caKeyPath := envStr("CA_KEY_PATH", "")
	userServiceAddr := envStr("USER_SERVICE_ADDR", "")

	// --- Driven adapters (secondary / infrastructure) ---
	planningClient, planErr := planning.NewClient(planningAddr)
	if planErr != nil {
		return fmt.Errorf("create planning client: %w", planErr)
	}
	defer planningClient.Close()
	ceremonyClient := ceremony.NewClient(ceremonyAddr)
	ceremonyClient.Connect()
	eventSubscriber := nats.NewLazySubscriber(natsURL)
	auditLogger := audit.NewLogger()
	identityResolver := identitymap.NewConfigResolver()

	// Internal event bus for RPC trace events.
	internalBus := eventbus.New()
	defer internalBus.Close()

	// Wrap planning client to emit rpc.outbound trace events.
	observablePlanning := planning.NewObservableClient(planningClient, internalBus)

	// Merge NATS domain events + internal RPC trace events into one stream.
	mergedSubscriber := eventbus.NewMerging(eventSubscriber, internalBus)

	// API key store: use static keys from env var when available (dev/E2E),
	// otherwise fall back to Valkey-backed store.
	var apiKeyStore ports.ApiKeyValidator
	if staticKeys := envStr("STATIC_API_KEYS", ""); staticKeys != "" {
		store, storeErr := keystore.NewStaticStore(staticKeys)
		if storeErr != nil {
			return fmt.Errorf("parse STATIC_API_KEYS: %w", storeErr)
		}
		apiKeyStore = store
		// Pre-register identity mappings so enrolled clients pass authz.
		for _, entry := range store.Entries() {
			identityResolver.AddMapping(
				entry.ClientID.String(),
				[]identity.Role{identity.RoleOperator, identity.RoleViewer},
				[]domainAuth.Scope{domainAuth.ScopeWatch, domainAuth.ScopeApprove, domainAuth.ScopeStart},
			)
			slog.Info("registered static identity", "client_id", entry.ClientID.String())
		}
	} else {
		apiKeyStore = keystore.NewValkeyStore(valkeyAddr)
	}

	certIssuer, err := setupCertIssuer(caCertPath, caKeyPath)
	if err != nil {
		return err
	}

	userClient, userCleanup, err := setupUserClient(userServiceAddr)
	if err != nil {
		return err
	}
	if userCleanup != nil {
		defer userCleanup()
	}

	// --- Application layer: command handlers ---
	createProject := command.NewCreateProjectHandler(observablePlanning, auditLogger, userClient)
	createEpic := command.NewCreateEpicHandler(observablePlanning, auditLogger)
	createStory := command.NewCreateStoryHandler(observablePlanning, auditLogger, userClient)
	transitionStory := command.NewTransitionStoryHandler(observablePlanning, auditLogger)
	createTask := command.NewCreateTaskHandler(observablePlanning, auditLogger)
	startCeremony := command.NewStartCeremonyHandler(ceremonyClient, auditLogger)
	startBacklogReview := command.NewStartBacklogReviewHandler(observablePlanning, auditLogger)
	createBacklogReview := command.NewCreateBacklogReviewHandler(observablePlanning, auditLogger)
	approveReviewPlan := command.NewApproveReviewPlanHandler(observablePlanning, auditLogger)
	rejectReviewPlan := command.NewRejectReviewPlanHandler(observablePlanning, auditLogger)
	completeBacklogReview := command.NewCompleteBacklogReviewHandler(observablePlanning, auditLogger)
	cancelBacklogReview := command.NewCancelBacklogReviewHandler(observablePlanning, auditLogger)
	approveDecision := command.NewApproveDecisionHandler(observablePlanning, auditLogger)
	rejectDecision := command.NewRejectDecisionHandler(observablePlanning, auditLogger)
	enrollHandler := command.NewEnrollHandler(apiKeyStore, certIssuer, auditLogger, defaultCertTTL, userClient)
	renewHandler := command.NewRenewHandler(certIssuer, auditLogger, defaultCertTTL)

	// --- Application layer: query handlers ---
	listProjects := query.NewListProjectsHandler(observablePlanning)
	listEpics := query.NewListEpicsHandler(observablePlanning)
	listStories := query.NewListStoriesHandler(observablePlanning)
	listTasks := query.NewListTasksHandler(observablePlanning)
	getCeremony := query.NewGetCeremonyHandler(ceremonyClient)
	listCeremonies := query.NewListCeremoniesHandler(ceremonyClient)
	watchEvents := query.NewWatchEventsHandler(mergedSubscriber)
	getBacklogReview := query.NewGetBacklogReviewHandler(observablePlanning)
	listBacklogReviews := query.NewListBacklogReviewsHandler(observablePlanning)

	// --- gRPC service handlers ---
	commandService := grpcapi.NewFleetCommandService(grpcapi.CommandHandlers{
		CreateProject:         createProject,
		CreateEpic:            createEpic,
		CreateStory:           createStory,
		TransitionStory:       transitionStory,
		CreateTask:            createTask,
		StartCeremony:         startCeremony,
		StartBacklogReview:    startBacklogReview,
		ApproveDecision:       approveDecision,
		RejectDecision:        rejectDecision,
		CreateBacklogReview:   createBacklogReview,
		ApproveReviewPlan:     approveReviewPlan,
		RejectReviewPlan:      rejectReviewPlan,
		CompleteBacklogReview: completeBacklogReview,
		CancelBacklogReview:   cancelBacklogReview,
	})

	queryService := grpcapi.NewFleetQueryService(grpcapi.QueryHandlers{
		ListProjects:       listProjects,
		ListEpics:          listEpics,
		ListStories:        listStories,
		ListTasks:          listTasks,
		GetCeremony:        getCeremony,
		ListCeremonies:     listCeremonies,
		WatchEvents:        watchEvents,
		GetBacklogReview:   getBacklogReview,
		ListBacklogReviews: listBacklogReviews,
	})

	enrollmentService := grpcapi.NewEnrollmentService(enrollHandler, renewHandler)

	// Log handler registration for startup diagnostics.
	slog.Info("application handlers registered",
		"commands", []string{
			"CreateProject", "CreateEpic", "CreateStory", "TransitionStory",
			"CreateTask", "StartCeremony", "StartBacklogReview",
			"CreateBacklogReview", "ApproveReviewPlan", "RejectReviewPlan",
			"CompleteBacklogReview", "CancelBacklogReview",
			"ApproveDecision", "RejectDecision", "Enroll", "Renew",
		},
		"queries", []string{
			"ListProjects", "ListEpics", "ListStories", "ListTasks",
			"GetCeremony", "ListCeremonies", "WatchEvents",
			"GetBacklogReview", "ListBacklogReviews",
		},
	)

	// --- gRPC server ---
	policy := domainAuth.NewAuthorizationPolicy()

	var server *grpcapi.Server

	if tlsCertPath != "" && tlsKeyPath != "" && clientCACertPath != "" {
		slog.Info("starting gRPC server with mTLS",
			"port", port,
			"tls_cert", tlsCertPath,
			"client_ca", clientCACertPath,
		)
		server, err = grpcapi.NewServer(grpcapi.Config{
			Port:             port,
			TLSCertPath:      tlsCertPath,
			TLSKeyPath:       tlsKeyPath,
			ClientCACertPath: clientCACertPath,
			RateLimitRPS:     rateLimitRPS,
		}, policy, identityResolver, auditLogger, internalBus)
	} else {
		slog.Warn("TLS not configured, starting insecure gRPC server (development only)",
			"port", port,
		)
		server, err = grpcapi.NewInsecureServer(port, policy, identityResolver, auditLogger, internalBus)
	}

	if err != nil {
		return fmt.Errorf("create gRPC server: %w", err)
	}

	// Register gRPC services on the server using generated registration functions.
	proxyv1.RegisterFleetCommandServiceServer(server.GRPCServer(), commandService)
	proxyv1.RegisterFleetQueryServiceServer(server.GRPCServer(), queryService)
	proxyv1.RegisterEnrollmentServiceServer(server.GRPCServer(), enrollmentService)

	slog.Info("gRPC services registered",
		"services", []string{
			"fleet.proxy.v1.FleetCommandService",
			"fleet.proxy.v1.FleetQueryService",
			"fleet.proxy.v1.EnrollmentService",
		},
	)

	// --- Graceful shutdown ---
	errCh := make(chan error, 1)
	go func() {
		errCh <- server.Start()
	}()

	slog.Info("fleet-proxy started", "port", port)

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	select {
	case sig := <-sigCh:
		slog.Info("received shutdown signal", "signal", sig)

		// Graceful shutdown with timeout: allow in-flight RPCs to drain
		// before forcing shutdown.
		shutdownDone := make(chan struct{})
		go func() {
			server.Stop()
			close(shutdownDone)
		}()

		shutdownTimeout := 15 * time.Second
		select {
		case <-shutdownDone:
			slog.Info("graceful shutdown completed")
		case <-time.After(shutdownTimeout):
			slog.Warn("graceful shutdown timed out, forcing stop", "timeout", shutdownTimeout)
			server.GRPCServer().Stop()
		}

		if closeErr := mergedSubscriber.Close(); closeErr != nil {
			slog.Warn("error closing event subscriber", "error", closeErr)
		}
		slog.Info("fleet-proxy stopped")
		return nil

	case err := <-errCh:
		return fmt.Errorf("gRPC server error: %w", err)
	}
}

// setupCertIssuer creates a PKI issuer from files or generates an ephemeral
// self-signed CA for development.
func setupCertIssuer(caCertPath, caKeyPath string) (*pki.Issuer, error) {
	if caCertPath != "" && caKeyPath != "" {
		issuer, err := pki.NewIssuer(caCertPath, caKeyPath)
		if err != nil {
			return nil, fmt.Errorf("create PKI issuer: %w", err)
		}
		slog.Info("PKI issuer loaded from files", "ca_cert", caCertPath)
		return issuer, nil
	}
	slog.Warn("CA cert/key not configured, generating ephemeral self-signed CA (development only)")
	caCert, caKey, err := pki.GenerateSelfSignedCA()
	if err != nil {
		return nil, fmt.Errorf("generate self-signed CA: %w", err)
	}
	return pki.NewIssuerFromKeyPair(caCert, caKey), nil
}

// setupUserClient creates a user service client if the address is configured.
// Returns (nil, nil, nil) when no address is set.
func setupUserClient(addr string) (ports.UserClient, func(), error) {
	if addr == "" {
		slog.Warn("USER_SERVICE_ADDR not configured, user identity resolution disabled")
		return nil, nil, nil
	}
	uc, err := userclient.NewClient(addr)
	if err != nil {
		return nil, nil, fmt.Errorf("create user client: %w", err)
	}
	slog.Info("user client connected", "addr", addr)
	return uc, func() { uc.Close() }, nil
}

// envStr reads a string environment variable with a fallback default.
func envStr(key, defaultVal string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return defaultVal
}

// envInt reads an integer environment variable with a fallback default.
func envInt(key string, defaultVal int) int {
	v := os.Getenv(key)
	if v == "" {
		return defaultVal
	}
	n, err := strconv.Atoi(v)
	if err != nil {
		slog.Warn("invalid integer env var, using default",
			"key", key, "value", v, "default", defaultVal)
		return defaultVal
	}
	return n
}
