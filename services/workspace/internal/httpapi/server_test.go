package httpapi

import (
	"bytes"
	"encoding/json"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/adapters/audit"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/adapters/policy"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/adapters/storage"
	tooladapter "github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/adapters/tools"
	workspaceadapter "github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/adapters/workspace"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
)

func TestHTTPAPI_EndToEndToolExecutionInWorkspace(t *testing.T) {
	handler, sourcePath := setupHTTPHandler(t)

	createPayload := map[string]any{
		"principal": map[string]any{
			"tenant_id": "tenant-a",
			"actor_id":  "agent-1",
			"roles":     []string{"developer"},
		},
		"source_repo_path":   sourcePath,
		"expires_in_seconds": 3600,
	}
	createResp := doJSONRequest(t, handler, http.MethodPost, "/v1/sessions", createPayload)
	if createResp.StatusCode != http.StatusCreated {
		t.Fatalf("expected 201, got %d body=%s", createResp.StatusCode, createResp.Body.String())
	}

	var createBody map[string]any
	mustDecode(t, createResp.Body.Bytes(), &createBody)
	session := createBody["session"].(map[string]any)
	sessionID := session["id"].(string)
	workspacePath := session["workspace_path"].(string)

	invokePayload := map[string]any{
		"approved": true,
		"args": map[string]any{
			"path":           "notes/result.txt",
			"content":        "workspace ok",
			"create_parents": true,
		},
	}
	invokeResp := doJSONRequest(t, handler, http.MethodPost, "/v1/sessions/"+sessionID+"/tools/fs.write_file/invoke", invokePayload)
	if invokeResp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200, got %d body=%s", invokeResp.StatusCode, invokeResp.Body.String())
	}

	if _, err := os.Stat(filepath.Join(workspacePath, "notes", "result.txt")); err != nil {
		t.Fatalf("expected written file in workspace, got error: %v", err)
	}

	readPayload := map[string]any{"args": map[string]any{"path": "notes/result.txt"}}
	readResp := doJSONRequest(t, handler, http.MethodPost, "/v1/sessions/"+sessionID+"/tools/fs.read_file/invoke", readPayload)
	if readResp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200 on fs.read_file, got %d body=%s", readResp.StatusCode, readResp.Body.String())
	}

	var readBody map[string]any
	mustDecode(t, readResp.Body.Bytes(), &readBody)
	invocation := readBody["invocation"].(map[string]any)
	output := invocation["output"].(map[string]any)
	if output["content"].(string) != "workspace ok" {
		t.Fatalf("unexpected read content: %#v", output)
	}
}

func TestHTTPAPI_ApprovalRequiredAndRouteErrors(t *testing.T) {
	handler, _ := setupHTTPHandler(t)

	createPayload := map[string]any{
		"principal": map[string]any{
			"tenant_id": "tenant-a",
			"actor_id":  "agent-2",
			"roles":     []string{"developer"},
		},
	}
	createResp := doJSONRequest(t, handler, http.MethodPost, "/v1/sessions", createPayload)
	if createResp.StatusCode != http.StatusCreated {
		t.Fatalf("expected 201, got %d", createResp.StatusCode)
	}
	var createBody map[string]any
	mustDecode(t, createResp.Body.Bytes(), &createBody)
	sessionID := createBody["session"].(map[string]any)["id"].(string)

	denyPayload := map[string]any{
		"approved": false,
		"args": map[string]any{
			"path":    "x.txt",
			"content": "denied",
		},
	}
	denyResp := doJSONRequest(t, handler, http.MethodPost, "/v1/sessions/"+sessionID+"/tools/fs.write_file/invoke", denyPayload)
	if denyResp.StatusCode != http.StatusPreconditionRequired {
		t.Fatalf("expected 428, got %d body=%s", denyResp.StatusCode, denyResp.Body.String())
	}

	notFoundResp := doJSONRequest(t, handler, http.MethodGet, "/v1/sessions/"+sessionID+"/unknown", nil)
	if notFoundResp.StatusCode != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", notFoundResp.StatusCode)
	}

	methodResp := doJSONRequest(t, handler, http.MethodGet, "/v1/sessions", nil)
	if methodResp.StatusCode != http.StatusMethodNotAllowed {
		t.Fatalf("expected 405, got %d", methodResp.StatusCode)
	}
}

func TestHTTPAPI_InvocationRoutesAndHealth(t *testing.T) {
	handler, sourcePath := setupHTTPHandler(t)

	healthResp := doJSONRequest(t, handler, http.MethodGet, "/healthz", nil)
	if healthResp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200 healthz, got %d", healthResp.StatusCode)
	}

	createResp := doJSONRequest(t, handler, http.MethodPost, "/v1/sessions", map[string]any{
		"principal": map[string]any{
			"tenant_id": "tenant-a",
			"actor_id":  "agent-3",
			"roles":     []string{"developer"},
		},
		"source_repo_path": sourcePath,
	})
	if createResp.StatusCode != http.StatusCreated {
		t.Fatalf("expected 201 create, got %d body=%s", createResp.StatusCode, createResp.Body.String())
	}

	var createBody map[string]any
	mustDecode(t, createResp.Body.Bytes(), &createBody)
	sessionID := createBody["session"].(map[string]any)["id"].(string)

	invokeResp := doJSONRequest(t, handler, http.MethodPost, "/v1/sessions/"+sessionID+"/tools/fs.read_file/invoke", map[string]any{
		"args": map[string]any{"path": "seed.txt"},
	})
	if invokeResp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200 invoke, got %d body=%s", invokeResp.StatusCode, invokeResp.Body.String())
	}

	var invokeBody map[string]any
	mustDecode(t, invokeResp.Body.Bytes(), &invokeBody)
	invocationID := invokeBody["invocation"].(map[string]any)["id"].(string)

	getResp := doJSONRequest(t, handler, http.MethodGet, "/v1/invocations/"+invocationID, nil)
	if getResp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200 invocation get, got %d", getResp.StatusCode)
	}

	logsResp := doJSONRequest(t, handler, http.MethodGet, "/v1/invocations/"+invocationID+"/logs", nil)
	if logsResp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200 invocation logs, got %d", logsResp.StatusCode)
	}

	artifactsResp := doJSONRequest(t, handler, http.MethodGet, "/v1/invocations/"+invocationID+"/artifacts", nil)
	if artifactsResp.StatusCode != http.StatusOK {
		t.Fatalf("expected 200 invocation artifacts, got %d", artifactsResp.StatusCode)
	}

	malformedResp := doJSONRequest(t, handler, http.MethodPost, "/v1/sessions/"+sessionID+"/tools/fs.read_file/invoke", json.RawMessage(`{"args":`))
	if malformedResp.StatusCode != http.StatusBadRequest {
		t.Fatalf("expected 400 malformed invoke body, got %d", malformedResp.StatusCode)
	}

	invMethodResp := doJSONRequest(t, handler, http.MethodPost, "/v1/invocations/"+invocationID+"/logs", map[string]any{})
	if invMethodResp.StatusCode != http.StatusMethodNotAllowed {
		t.Fatalf("expected 405 invocation logs method, got %d", invMethodResp.StatusCode)
	}

	missingInvResp := doJSONRequest(t, handler, http.MethodGet, "/v1/invocations/missing", nil)
	if missingInvResp.StatusCode != http.StatusNotFound {
		t.Fatalf("expected 404 missing invocation, got %d", missingInvResp.StatusCode)
	}
}

func setupHTTPHandler(t *testing.T) (http.Handler, string) {
	t.Helper()

	workspaceRoot := t.TempDir()
	artifactRoot := t.TempDir()
	sourcePath := t.TempDir()
	if err := os.WriteFile(filepath.Join(sourcePath, "seed.txt"), []byte("seed"), 0o644); err != nil {
		t.Fatalf("write source seed failed: %v", err)
	}

	logger := slog.New(slog.NewTextHandler(os.Stdout, nil))
	workspaceManager := workspaceadapter.NewLocalManager(workspaceRoot)
	catalog := tooladapter.NewCatalog(tooladapter.DefaultCapabilities())
	commandRunner := tooladapter.NewLocalCommandRunner()
	engine := tooladapter.NewEngine(
		tooladapter.NewFSListHandler(commandRunner),
		tooladapter.NewFSReadHandler(commandRunner),
		tooladapter.NewFSWriteHandler(commandRunner),
		tooladapter.NewFSPatchHandler(commandRunner),
		tooladapter.NewFSSearchHandler(commandRunner),
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
	service := app.NewService(workspaceManager, catalog, policyEngine, engine, artifactStore, auditLogger)

	return NewServer(logger, service).Handler(), sourcePath
}

type testResponse struct {
	StatusCode int
	Body       *bytes.Buffer
}

func doJSONRequest(t *testing.T, handler http.Handler, method, path string, payload any) testResponse {
	t.Helper()

	var bodyBytes []byte
	if payload != nil {
		switch typed := payload.(type) {
		case []byte:
			bodyBytes = typed
		case json.RawMessage:
			bodyBytes = []byte(typed)
		default:
			var err error
			bodyBytes, err = json.Marshal(payload)
			if err != nil {
				t.Fatalf("marshal payload failed: %v", err)
			}
		}
	}

	req := httptest.NewRequest(method, path, bytes.NewReader(bodyBytes))
	if payload != nil {
		req.Header.Set("Content-Type", "application/json")
	}

	resp := httptest.NewRecorder()
	handler.ServeHTTP(resp, req)

	buffer := &bytes.Buffer{}
	buffer.Write(resp.Body.Bytes())

	return testResponse{StatusCode: resp.Code, Body: buffer}
}

func mustDecode(t *testing.T, data []byte, destination any) {
	t.Helper()
	if err := json.Unmarshal(data, destination); err != nil {
		t.Fatalf("decode failed: %v body=%s", err, string(data))
	}
}
