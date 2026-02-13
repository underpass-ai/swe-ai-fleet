package main

import (
	"context"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/adapters/audit"
	invocationstoreadapter "github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/adapters/invocationstore"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/adapters/policy"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/adapters/storage"
	tooladapter "github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/adapters/tools"
	workspaceadapter "github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/adapters/workspace"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/httpapi"
)

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: parseLogLevel(os.Getenv("LOG_LEVEL"))}))

	port := envOrDefault("PORT", "50053")
	workspaceRoot := envOrDefault("WORKSPACE_ROOT", "/tmp/swe-workspaces")
	artifactRoot := envOrDefault("ARTIFACT_ROOT", "/tmp/swe-artifacts")

	if err := os.MkdirAll(workspaceRoot, 0o755); err != nil {
		logger.Error("failed to create workspace root", "error", err)
		os.Exit(1)
	}
	if err := os.MkdirAll(artifactRoot, 0o755); err != nil {
		logger.Error("failed to create artifact root", "error", err)
		os.Exit(1)
	}

	workspaceManager := workspaceadapter.NewLocalManager(workspaceRoot)
	catalog := tooladapter.NewCatalog(tooladapter.DefaultCapabilities())
	commandRunner := tooladapter.NewLocalCommandRunner()
	engine := tooladapter.NewEngine(
		&tooladapter.FSListHandler{},
		&tooladapter.FSReadHandler{},
		&tooladapter.FSWriteHandler{},
		&tooladapter.FSSearchHandler{},
		tooladapter.NewGitStatusHandler(commandRunner),
		tooladapter.NewGitDiffHandler(commandRunner),
		tooladapter.NewGitApplyPatchHandler(commandRunner),
		tooladapter.NewRepoRunTestsHandler(commandRunner),
	)
	artifactStore := storage.NewLocalArtifactStore(artifactRoot)
	policyEngine := policy.NewStaticPolicy()
	auditLogger := audit.NewLoggerAudit(logger)
	invocationStore, err := buildInvocationStore(logger)
	if err != nil {
		logger.Error("failed to initialize invocation store", "error", err)
		os.Exit(1)
	}

	service := app.NewService(workspaceManager, catalog, policyEngine, engine, artifactStore, auditLogger, invocationStore)
	server := httpapi.NewServer(logger, service)

	httpServer := &http.Server{
		Addr:              ":" + port,
		Handler:           server.Handler(),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       30 * time.Second,
		WriteTimeout:      120 * time.Second,
		IdleTimeout:       120 * time.Second,
	}

	go func() {
		logger.Info("workspace service listening", "port", port, "workspace_root", workspaceRoot)
		if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Error("http server failed", "error", err)
			os.Exit(1)
		}
	}()

	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
	<-stop

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	_ = httpServer.Shutdown(ctx)
	logger.Info("workspace service stopped")
}

func envOrDefault(key, fallback string) string {
	value := os.Getenv(key)
	if value == "" {
		return fallback
	}
	return value
}

func parseLogLevel(raw string) slog.Level {
	switch raw {
	case "debug", "DEBUG":
		return slog.LevelDebug
	case "warn", "WARN":
		return slog.LevelWarn
	case "error", "ERROR":
		return slog.LevelError
	default:
		return slog.LevelInfo
	}
}

func buildInvocationStore(logger *slog.Logger) (app.InvocationStore, error) {
	backend := strings.ToLower(strings.TrimSpace(envOrDefault("INVOCATION_STORE_BACKEND", "memory")))
	switch backend {
	case "", "memory":
		logger.Info("invocation store initialized", "backend", "memory")
		return app.NewInMemoryInvocationStore(), nil
	case "valkey":
		address := strings.TrimSpace(os.Getenv("VALKEY_ADDR"))
		if address == "" {
			host := strings.TrimSpace(envOrDefault("VALKEY_HOST", "valkey.swe-ai-fleet.svc.cluster.local"))
			port := strings.TrimSpace(envOrDefault("VALKEY_PORT", "6379"))
			address = fmt.Sprintf("%s:%s", host, port)
		}

		password := os.Getenv("VALKEY_PASSWORD")
		db := parseIntOrDefault(os.Getenv("VALKEY_DB"), 0)
		keyPrefix := envOrDefault("INVOCATION_STORE_KEY_PREFIX", "workspace:invocation")
		ttlSeconds := parseIntOrDefault(os.Getenv("INVOCATION_STORE_TTL_SECONDS"), 86400)

		store, err := invocationstoreadapter.NewValkeyStoreFromAddress(
			context.Background(),
			address,
			password,
			db,
			keyPrefix,
			time.Duration(ttlSeconds)*time.Second,
		)
		if err != nil {
			return nil, err
		}
		logger.Info("invocation store initialized", "backend", "valkey", "address", address, "db", db, "ttl_seconds", ttlSeconds)
		return store, nil
	default:
		return nil, fmt.Errorf("unsupported INVOCATION_STORE_BACKEND: %s", backend)
	}
}

func parseIntOrDefault(raw string, fallback int) int {
	value := strings.TrimSpace(raw)
	if value == "" {
		return fallback
	}
	parsed, err := strconv.Atoi(value)
	if err != nil {
		return fallback
	}
	return parsed
}
