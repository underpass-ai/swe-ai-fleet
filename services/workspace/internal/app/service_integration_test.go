package app_test

import (
	"context"
	"encoding/json"
	"log/slog"
	"os"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/adapters/audit"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/adapters/policy"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/adapters/storage"
	tooladapter "github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/adapters/tools"
	workspaceadapter "github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/adapters/workspace"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

func TestService_CreateAndListTools(t *testing.T) {
	svc := setupService(t)
	ctx := context.Background()

	session, err := svc.CreateSession(ctx, app.CreateSessionRequest{
		Principal: domain.Principal{TenantID: "tenant-a", ActorID: "alice", Roles: []string{"developer"}},
	})
	if err != nil {
		t.Fatalf("unexpected error creating session: %v", err)
	}

	tools, listErr := svc.ListTools(ctx, session.ID)
	if listErr != nil {
		t.Fatalf("unexpected list error: %v", listErr)
	}
	if len(tools) == 0 {
		t.Fatal("expected tools to be listed")
	}

	found := false
	for _, tool := range tools {
		if tool.Name == "fs.list" {
			found = true
			break
		}
	}
	if !found {
		t.Fatal("expected fs.list to be available")
	}
}

func TestService_FsWriteRequiresApproval(t *testing.T) {
	svc := setupService(t)
	ctx := context.Background()

	session, err := svc.CreateSession(ctx, app.CreateSessionRequest{
		Principal: domain.Principal{TenantID: "tenant-a", ActorID: "alice", Roles: []string{"developer"}},
	})
	if err != nil {
		t.Fatalf("unexpected error creating session: %v", err)
	}

	invocation, invokeErr := svc.InvokeTool(ctx, session.ID, "fs.write", app.InvokeToolRequest{
		Args: mustJSON(t, map[string]any{"path": "notes/todo.txt", "content": "hello"}),
	})
	if invokeErr == nil {
		t.Fatal("expected approval error")
	}
	if invokeErr.Code != app.ErrorCodeApprovalRequired {
		t.Fatalf("unexpected error code: %s", invokeErr.Code)
	}
	if invocation.Status != domain.InvocationStatusDenied {
		t.Fatalf("expected denied invocation, got %s", invocation.Status)
	}
}

func TestService_FsWriteAndRead(t *testing.T) {
	svc := setupService(t)
	ctx := context.Background()

	session, err := svc.CreateSession(ctx, app.CreateSessionRequest{
		Principal: domain.Principal{TenantID: "tenant-a", ActorID: "alice", Roles: []string{"developer"}},
	})
	if err != nil {
		t.Fatalf("unexpected error creating session: %v", err)
	}

	_, writeErr := svc.InvokeTool(ctx, session.ID, "fs.write", app.InvokeToolRequest{
		Approved: true,
		Args:     mustJSON(t, map[string]any{"path": "notes/todo.txt", "content": "hello world", "create_parents": true}),
	})
	if writeErr != nil {
		t.Fatalf("unexpected fs.write error: %v", writeErr)
	}

	invocation, readErr := svc.InvokeTool(ctx, session.ID, "fs.read", app.InvokeToolRequest{
		Args: mustJSON(t, map[string]any{"path": "notes/todo.txt"}),
	})
	if readErr != nil {
		t.Fatalf("unexpected fs.read error: %v", readErr)
	}

	output, ok := invocation.Output.(map[string]any)
	if !ok {
		t.Fatalf("expected output map, got %T", invocation.Output)
	}
	content, ok := output["content"].(string)
	if !ok {
		t.Fatalf("expected content string in output, got %#v", output["content"])
	}
	if content != "hello world" {
		t.Fatalf("unexpected file content: %q", content)
	}
}

func TestService_PathTraversalDenied(t *testing.T) {
	svc := setupService(t)
	ctx := context.Background()

	session, err := svc.CreateSession(ctx, app.CreateSessionRequest{
		Principal: domain.Principal{TenantID: "tenant-a", ActorID: "alice", Roles: []string{"developer"}},
	})
	if err != nil {
		t.Fatalf("unexpected error creating session: %v", err)
	}

	_, invokeErr := svc.InvokeTool(ctx, session.ID, "fs.read", app.InvokeToolRequest{
		Args: mustJSON(t, map[string]any{"path": "../etc/passwd"}),
	})
	if invokeErr == nil {
		t.Fatal("expected traversal to be denied")
	}
	if invokeErr.Code != app.ErrorCodePolicyDenied {
		t.Fatalf("unexpected error code: %s", invokeErr.Code)
	}
}

func setupService(t *testing.T) *app.Service {
	t.Helper()

	workspaceRoot := t.TempDir()
	artifactRoot := t.TempDir()

	logger := slog.New(slog.NewTextHandler(os.Stdout, nil))
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
	return app.NewService(workspaceManager, catalog, policyEngine, engine, artifactStore, auditLogger)
}

func mustJSON(t *testing.T, payload any) json.RawMessage {
	t.Helper()
	data, err := json.Marshal(payload)
	if err != nil {
		t.Fatalf("marshal payload: %v", err)
	}
	return data
}
