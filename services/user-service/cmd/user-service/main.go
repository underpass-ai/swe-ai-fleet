// Package main is the entry point for the user-service.
// It reads configuration from environment variables, initializes DuckDB,
// wires all adapters to the application layer, and starts the gRPC server
// with graceful shutdown.
package main

import (
	"database/sql"
	"fmt"
	"log/slog"
	"os"
	"os/signal"
	"strconv"
	"syscall"

	_ "github.com/marcboeker/go-duckdb"

	"github.com/underpass-ai/swe-ai-fleet/services/user-service/internal/adapters/duckdb"
	"github.com/underpass-ai/swe-ai-fleet/services/user-service/internal/adapters/grpcapi"
	"github.com/underpass-ai/swe-ai-fleet/services/user-service/internal/app/command"
	"github.com/underpass-ai/swe-ai-fleet/services/user-service/internal/app/query"
)

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		Level: slog.LevelInfo,
	}))
	slog.SetDefault(logger)

	if err := run(); err != nil {
		slog.Error("user-service failed", "error", err)
		os.Exit(1)
	}
}

func run() error {
	port := envInt("PORT", 50058)
	duckdbPath := envStr("DUCKDB_PATH", "/data/user-service.duckdb")

	// --- DuckDB ---
	db, err := sql.Open("duckdb", duckdbPath)
	if err != nil {
		return fmt.Errorf("open duckdb %s: %w", duckdbPath, err)
	}
	defer db.Close()

	if err := duckdb.EnsureSchema(db); err != nil {
		return fmt.Errorf("ensure schema: %w", err)
	}
	slog.Info("DuckDB initialized", "path", duckdbPath)

	// --- Driven adapters ---
	store := duckdb.NewStore(db)

	// --- Application layer: command handlers ---
	createUser := command.NewCreateUserHandler(store)
	updateUser := command.NewUpdateUserHandler(store)

	// --- Application layer: query handlers ---
	getUser := query.NewGetUserHandler(store)
	getUserByClientID := query.NewGetUserByClientIDHandler(store)
	listUsers := query.NewListUsersHandler(store)

	// --- gRPC service ---
	userService := grpcapi.NewUserServiceServer(
		createUser,
		updateUser,
		getUser,
		getUserByClientID,
		listUsers,
	)

	server := grpcapi.NewInsecureServer(port)
	grpcapi.RegisterUserService(server.GRPCServer(), userService)

	slog.Info("gRPC services registered", "services", []string{"fleet.user.v1.UserService"})

	// --- Graceful shutdown ---
	errCh := make(chan error, 1)
	go func() {
		errCh <- server.Start()
	}()

	slog.Info("user-service started", "port", port)

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	select {
	case sig := <-sigCh:
		slog.Info("received shutdown signal", "signal", sig)
		server.Stop()
		slog.Info("user-service stopped")
		return nil

	case err := <-errCh:
		return fmt.Errorf("gRPC server error: %w", err)
	}
}

func envStr(key, defaultVal string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return defaultVal
}

func envInt(key string, defaultVal int) int {
	v := os.Getenv(key)
	if v == "" {
		return defaultVal
	}
	n, err := strconv.Atoi(v)
	if err != nil {
		slog.Warn("invalid integer env var, using default", "key", key, "value", v, "default", defaultVal)
		return defaultVal
	}
	return n
}
