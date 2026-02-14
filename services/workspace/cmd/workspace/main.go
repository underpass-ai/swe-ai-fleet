package main

import (
	"context"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/adapters/audit"
	invocationstoreadapter "github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/adapters/invocationstore"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/adapters/policy"
	sessionstoreadapter "github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/adapters/sessionstore"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/adapters/storage"
	tooladapter "github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/adapters/tools"
	workspaceadapter "github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/adapters/workspace"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/httpapi"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
)

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: parseLogLevel(os.Getenv("LOG_LEVEL"))}))

	port := envOrDefault("PORT", "50053")
	workspaceRoot := envOrDefault("WORKSPACE_ROOT", "/tmp/swe-workspaces")
	artifactRoot := envOrDefault("ARTIFACT_ROOT", "/tmp/swe-artifacts")
	workspaceBackend := strings.ToLower(strings.TrimSpace(envOrDefault("WORKSPACE_BACKEND", "local")))

	if err := os.MkdirAll(artifactRoot, 0o755); err != nil {
		logger.Error("failed to create artifact root", "error", err)
		os.Exit(1)
	}

	var kubeConfig *rest.Config
	var kubeClient kubernetes.Interface
	if workspaceBackend == "kubernetes" {
		resolvedConfig, resolvedClient, err := buildKubernetesClient()
		if err != nil {
			logger.Error("failed to initialize kubernetes client", "error", err)
			os.Exit(1)
		}
		kubeConfig = resolvedConfig
		kubeClient = resolvedClient
	}

	sessionStore, err := buildSessionStore(logger)
	if err != nil {
		logger.Error("failed to initialize session store", "error", err)
		os.Exit(1)
	}

	workspaceManager, err := buildWorkspaceManager(workspaceBackend, workspaceRoot, kubeClient, sessionStore)
	if err != nil {
		logger.Error("failed to initialize workspace manager", "error", err)
		os.Exit(1)
	}
	catalog := tooladapter.NewCatalog(tooladapter.DefaultCapabilities())
	commandRunner, err := buildCommandRunner(workspaceBackend, kubeClient, kubeConfig)
	if err != nil {
		logger.Error("failed to initialize command runner", "error", err)
		os.Exit(1)
	}
	engine := tooladapter.NewEngine(
		tooladapter.NewFSListHandler(commandRunner),
		tooladapter.NewFSReadHandler(commandRunner),
		tooladapter.NewFSWriteHandler(commandRunner),
		tooladapter.NewFSPatchHandler(commandRunner),
		tooladapter.NewFSSearchHandler(commandRunner),
		tooladapter.NewConnListProfilesHandler(),
		tooladapter.NewConnDescribeProfileHandler(),
		tooladapter.NewNATSRequestHandler(nil),
		tooladapter.NewNATSSubscribePullHandler(nil),
		tooladapter.NewKafkaConsumeHandler(nil),
		tooladapter.NewKafkaTopicMetadataHandler(nil),
		tooladapter.NewRabbitConsumeHandler(nil),
		tooladapter.NewRabbitQueueInfoHandler(nil),
		tooladapter.NewGitStatusHandler(commandRunner),
		tooladapter.NewGitDiffHandler(commandRunner),
		tooladapter.NewGitApplyPatchHandler(commandRunner),
		tooladapter.NewRepoDetectProjectTypeHandler(commandRunner),
		tooladapter.NewRepoDetectToolchainHandler(commandRunner),
		tooladapter.NewRepoValidateHandler(commandRunner),
		tooladapter.NewRepoBuildHandler(commandRunner),
		tooladapter.NewRepoTestHandler(commandRunner),
		tooladapter.NewRepoRunTestsHandler(commandRunner),
		tooladapter.NewRepoCoverageReportHandler(commandRunner),
		tooladapter.NewRepoStaticAnalysisHandler(commandRunner),
		tooladapter.NewRepoPackageHandler(commandRunner),
		tooladapter.NewSecurityScanSecretsHandler(commandRunner),
		tooladapter.NewCIRunPipelineHandler(commandRunner),
		tooladapter.NewGoModTidyHandler(commandRunner),
		tooladapter.NewGoGenerateHandler(commandRunner),
		tooladapter.NewGoBuildHandler(commandRunner),
		tooladapter.NewGoTestHandler(commandRunner),
		tooladapter.NewRustBuildHandler(commandRunner),
		tooladapter.NewRustTestHandler(commandRunner),
		tooladapter.NewRustClippyHandler(commandRunner),
		tooladapter.NewRustFormatHandler(commandRunner),
		tooladapter.NewNodeInstallHandler(commandRunner),
		tooladapter.NewNodeBuildHandler(commandRunner),
		tooladapter.NewNodeTestHandler(commandRunner),
		tooladapter.NewNodeLintHandler(commandRunner),
		tooladapter.NewNodeTypecheckHandler(commandRunner),
		tooladapter.NewPythonInstallDepsHandler(commandRunner),
		tooladapter.NewPythonValidateHandler(commandRunner),
		tooladapter.NewPythonTestHandler(commandRunner),
		tooladapter.NewCBuildHandler(commandRunner),
		tooladapter.NewCTestHandler(commandRunner),
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

func buildSessionStore(logger *slog.Logger) (app.SessionStore, error) {
	backend := strings.ToLower(strings.TrimSpace(envOrDefault("SESSION_STORE_BACKEND", "memory")))
	switch backend {
	case "", "memory":
		logger.Info("session store initialized", "backend", "memory")
		return app.NewInMemorySessionStore(), nil
	case "valkey":
		address := strings.TrimSpace(os.Getenv("VALKEY_ADDR"))
		if address == "" {
			host := strings.TrimSpace(envOrDefault("VALKEY_HOST", "valkey.swe-ai-fleet.svc.cluster.local"))
			port := strings.TrimSpace(envOrDefault("VALKEY_PORT", "6379"))
			address = fmt.Sprintf("%s:%s", host, port)
		}

		password := os.Getenv("VALKEY_PASSWORD")
		db := parseIntOrDefault(os.Getenv("VALKEY_DB"), 0)
		keyPrefix := envOrDefault("SESSION_STORE_KEY_PREFIX", "workspace:session")
		ttlSeconds := parseIntOrDefault(os.Getenv("SESSION_STORE_TTL_SECONDS"), 86400)

		store, err := sessionstoreadapter.NewValkeyStoreFromAddress(
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
		logger.Info("session store initialized", "backend", "valkey", "address", address, "db", db, "ttl_seconds", ttlSeconds)
		return store, nil
	default:
		return nil, fmt.Errorf("unsupported SESSION_STORE_BACKEND: %s", backend)
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

func parseBoolOrDefault(raw string, fallback bool) bool {
	value := strings.ToLower(strings.TrimSpace(raw))
	switch value {
	case "1", "true", "yes", "on":
		return true
	case "0", "false", "no", "off":
		return false
	case "":
		return fallback
	default:
		return fallback
	}
}

func buildWorkspaceManager(
	backend string,
	workspaceRoot string,
	kubeClient kubernetes.Interface,
	sessionStore app.SessionStore,
) (app.WorkspaceManager, error) {
	switch backend {
	case "", "local":
		if err := os.MkdirAll(workspaceRoot, 0o755); err != nil {
			return nil, fmt.Errorf("create workspace root: %w", err)
		}
		return workspaceadapter.NewLocalManager(workspaceRoot), nil
	case "kubernetes":
		if kubeClient == nil {
			return nil, fmt.Errorf("kubernetes client is required")
		}
		return workspaceadapter.NewKubernetesManager(workspaceadapter.KubernetesManagerConfig{
			Namespace:           envOrDefault("WORKSPACE_K8S_NAMESPACE", "swe-ai-fleet"),
			ServiceAccount:      strings.TrimSpace(os.Getenv("WORKSPACE_K8S_SERVICE_ACCOUNT")),
			PodImage:            envOrDefault("WORKSPACE_K8S_RUNNER_IMAGE", ""),
			InitImage:           envOrDefault("WORKSPACE_K8S_INIT_IMAGE", ""),
			WorkspaceDir:        envOrDefault("WORKSPACE_K8S_WORKDIR", "/workspace/repo"),
			RunnerContainerName: envOrDefault("WORKSPACE_K8S_CONTAINER", "runner"),
			PodNamePrefix:       envOrDefault("WORKSPACE_K8S_POD_PREFIX", "ws"),
			PodReadyTimeout:     time.Duration(parseIntOrDefault(os.Getenv("WORKSPACE_K8S_READY_TIMEOUT_SECONDS"), 120)) * time.Second,
			SessionStore:        sessionStore,
			GitAuthSecretName:   strings.TrimSpace(os.Getenv("WORKSPACE_K8S_GIT_AUTH_SECRET")),
			GitAuthMetadataKey:  envOrDefault("WORKSPACE_K8S_GIT_AUTH_METADATA_KEY", "git_auth_secret"),
			RunAsUser:           int64(parseIntOrDefault(os.Getenv("WORKSPACE_K8S_RUN_AS_USER"), 1000)),
			RunAsGroup:          int64(parseIntOrDefault(os.Getenv("WORKSPACE_K8S_RUN_AS_GROUP"), 1000)),
			FSGroup:             int64(parseIntOrDefault(os.Getenv("WORKSPACE_K8S_FS_GROUP"), 1000)),
			ReadOnlyRootFS:      parseBoolOrDefault(os.Getenv("WORKSPACE_K8S_READ_ONLY_ROOT_FS"), false),
			AutomountSAToken:    parseBoolOrDefault(os.Getenv("WORKSPACE_K8S_AUTOMOUNT_SA_TOKEN"), false),
		}, kubeClient), nil
	default:
		return nil, fmt.Errorf("unsupported WORKSPACE_BACKEND: %s", backend)
	}
}

func buildCommandRunner(
	backend string,
	kubeClient kubernetes.Interface,
	kubeConfig *rest.Config,
) (app.CommandRunner, error) {
	localRunner := tooladapter.NewLocalCommandRunner()
	if backend != "kubernetes" {
		return localRunner, nil
	}
	if kubeClient == nil || kubeConfig == nil {
		return nil, fmt.Errorf("kubernetes runner requires client and rest config")
	}
	k8sRunner := tooladapter.NewK8sCommandRunner(
		kubeClient,
		kubeConfig,
		envOrDefault("WORKSPACE_K8S_NAMESPACE", "swe-ai-fleet"),
	)
	return tooladapter.NewRoutingCommandRunner(localRunner, k8sRunner), nil
}

func buildKubernetesClient() (*rest.Config, kubernetes.Interface, error) {
	kubeConfig, err := resolveKubeConfig()
	if err != nil {
		return nil, nil, err
	}
	clientset, err := kubernetes.NewForConfig(kubeConfig)
	if err != nil {
		return nil, nil, err
	}
	return kubeConfig, clientset, nil
}

func resolveKubeConfig() (*rest.Config, error) {
	if kubeconfig := strings.TrimSpace(os.Getenv("KUBECONFIG")); kubeconfig != "" {
		return clientcmd.BuildConfigFromFlags("", kubeconfig)
	}
	home, homeErr := os.UserHomeDir()
	if homeErr == nil {
		defaultKubeconfig := filepath.Join(home, ".kube", "config")
		if _, err := os.Stat(defaultKubeconfig); err == nil {
			return clientcmd.BuildConfigFromFlags("", defaultKubeconfig)
		}
	}
	return rest.InClusterConfig()
}
