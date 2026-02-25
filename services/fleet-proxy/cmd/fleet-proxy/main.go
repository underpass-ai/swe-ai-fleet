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

	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/adapters/audit"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/adapters/ceremony"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/adapters/grpcapi"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/adapters/identitymap"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/adapters/keystore"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/adapters/nats"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/adapters/pki"
	"github.com/underpass-ai/swe-ai-fleet/services/fleet-proxy/internal/adapters/planning"
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

	// --- Driven adapters (secondary / infrastructure) ---
	planningClient := planning.NewClient(planningAddr)
	ceremonyClient := ceremony.NewClient(ceremonyAddr)
	eventSubscriber := nats.NewLazySubscriber(natsURL)
	auditLogger := audit.NewLogger()
	identityResolver := identitymap.NewConfigResolver()

	// API key store: use static keys from env var when available (dev/E2E),
	// otherwise fall back to Valkey-backed store.
	var apiKeyStore ports.ApiKeyStore
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

	// --- PKI issuer (for enrollment/renewal) ---
	// In production, the CA cert and key paths must be provided.
	// In development, we generate a self-signed CA for testing.
	var certIssuer *pki.Issuer
	if caCertPath != "" && caKeyPath != "" {
		var err error
		certIssuer, err = pki.NewIssuer(caCertPath, caKeyPath)
		if err != nil {
			return fmt.Errorf("create PKI issuer: %w", err)
		}
		slog.Info("PKI issuer loaded from files", "ca_cert", caCertPath)
	} else {
		slog.Warn("CA cert/key not configured, generating ephemeral self-signed CA (development only)")
		caCert, caKey, err := pki.GenerateSelfSignedCA()
		if err != nil {
			return fmt.Errorf("generate self-signed CA: %w", err)
		}
		certIssuer = pki.NewIssuerFromKeyPair(caCert, caKey)
	}

	// --- Application layer: command handlers ---
	createProject := command.NewCreateProjectHandler(planningClient, auditLogger)
	createEpic := command.NewCreateEpicHandler(planningClient, auditLogger)
	createStory := command.NewCreateStoryHandler(planningClient, auditLogger)
	transitionStory := command.NewTransitionStoryHandler(planningClient, auditLogger)
	createTask := command.NewCreateTaskHandler(planningClient, auditLogger)
	startCeremony := command.NewStartCeremonyHandler(ceremonyClient, auditLogger)
	startBacklogReview := command.NewStartBacklogReviewHandler(ceremonyClient, auditLogger)
	approveDecision := command.NewApproveDecisionHandler(planningClient, auditLogger)
	rejectDecision := command.NewRejectDecisionHandler(planningClient, auditLogger)
	enrollHandler := command.NewEnrollHandler(apiKeyStore, certIssuer, auditLogger, defaultCertTTL)
	renewHandler := command.NewRenewHandler(certIssuer, auditLogger, defaultCertTTL)

	// --- Application layer: query handlers ---
	listProjects := query.NewListProjectsHandler(planningClient)
	listEpics := query.NewListEpicsHandler(planningClient)
	listStories := query.NewListStoriesHandler(planningClient)
	listTasks := query.NewListTasksHandler(planningClient)
	getCeremony := query.NewGetCeremonyHandler(ceremonyClient)
	listCeremonies := query.NewListCeremoniesHandler(ceremonyClient)
	watchEvents := query.NewWatchEventsHandler(eventSubscriber)

	// --- gRPC service handlers ---
	commandService := grpcapi.NewFleetCommandService(
		createProject,
		createEpic,
		createStory,
		transitionStory,
		createTask,
		startCeremony,
		startBacklogReview,
		approveDecision,
		rejectDecision,
	)

	queryService := grpcapi.NewFleetQueryService(
		listProjects,
		listEpics,
		listStories,
		listTasks,
		getCeremony,
		listCeremonies,
		watchEvents,
	)

	enrollmentService := grpcapi.NewEnrollmentService(enrollHandler, renewHandler)

	// Log handler registration for startup diagnostics.
	slog.Info("application handlers registered",
		"commands", []string{
			"CreateProject", "CreateEpic", "CreateStory", "TransitionStory",
			"CreateTask", "StartCeremony", "StartBacklogReview",
			"ApproveDecision", "RejectDecision", "Enroll", "Renew",
		},
		"queries", []string{
			"ListProjects", "ListEpics", "ListStories", "ListTasks",
			"GetCeremony", "ListCeremonies", "WatchEvents",
		},
	)

	// --- gRPC server ---
	policy := domainAuth.NewAuthorizationPolicy()

	var server *grpcapi.Server
	var err error

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
		}, policy, identityResolver, auditLogger)
	} else {
		slog.Warn("TLS not configured, starting insecure gRPC server (development only)",
			"port", port,
		)
		server, err = grpcapi.NewInsecureServer(port, policy, identityResolver, auditLogger)
	}

	if err != nil {
		return fmt.Errorf("create gRPC server: %w", err)
	}

	// Register gRPC services on the server.
	grpcapi.RegisterFleetCommandService(server.GRPCServer(), commandService)
	grpcapi.RegisterFleetQueryService(server.GRPCServer(), queryService)
	grpcapi.RegisterEnrollmentService(server.GRPCServer(), enrollmentService)

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
		server.Stop()
		if closeErr := eventSubscriber.Close(); closeErr != nil {
			slog.Warn("error closing event subscriber", "error", closeErr)
		}
		slog.Info("fleet-proxy stopped")
		return nil

	case err := <-errCh:
		return fmt.Errorf("gRPC server error: %w", err)
	}
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
