package tools

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

func TestFSWriteReadListSearchFlow(t *testing.T) {
	root := t.TempDir()
	session := domain.Session{WorkspacePath: root, AllowedPaths: []string{"."}}
	ctx := context.Background()

	write := &FSWriteHandler{}
	read := &FSReadHandler{}
	list := &FSListHandler{}
	search := &FSSearchHandler{}

	_, err := write.Invoke(ctx, session, mustJSON(t, map[string]any{
		"path":           "notes/todo.txt",
		"content":        "hola\nTODO: test",
		"create_parents": true,
	}))
	if err != nil {
		t.Fatalf("unexpected write error: %v", err)
	}

	readResult, err := read.Invoke(ctx, session, mustJSON(t, map[string]any{"path": "notes/todo.txt"}))
	if err != nil {
		t.Fatalf("unexpected read error: %v", err)
	}
	readOutput := readResult.Output.(map[string]any)
	if readOutput["encoding"] != "utf8" {
		t.Fatalf("unexpected encoding: %#v", readOutput)
	}

	listResult, err := list.Invoke(ctx, session, mustJSON(t, map[string]any{"path": ".", "recursive": true}))
	if err != nil {
		t.Fatalf("unexpected list error: %v", err)
	}
	if listResult.Output.(map[string]any)["count"].(int) < 1 {
		t.Fatalf("expected at least one entry, got %#v", listResult.Output)
	}

	searchResult, err := search.Invoke(ctx, session, mustJSON(t, map[string]any{"path": ".", "pattern": "TODO"}))
	if err != nil {
		t.Fatalf("unexpected search error: %v", err)
	}
	if searchResult.Output.(map[string]any)["count"].(int) < 1 {
		t.Fatalf("expected at least one match, got %#v", searchResult.Output)
	}
}

func TestFSReadBinaryAndValidationErrors(t *testing.T) {
	root := t.TempDir()
	session := domain.Session{WorkspacePath: root, AllowedPaths: []string{"."}}
	ctx := context.Background()

	if err := os.WriteFile(filepath.Join(root, "bin.dat"), []byte{0xff, 0xfe, 0xfd}, 0o644); err != nil {
		t.Fatalf("write binary file failed: %v", err)
	}

	read := &FSReadHandler{}
	result, err := read.Invoke(ctx, session, mustJSON(t, map[string]any{"path": "bin.dat"}))
	if err != nil {
		t.Fatalf("unexpected read error: %v", err)
	}
	output := result.Output.(map[string]any)
	if output["encoding"] != "base64" {
		t.Fatalf("expected base64 encoding, got %#v", output["encoding"])
	}
	if _, decodeErr := base64.StdEncoding.DecodeString(output["content"].(string)); decodeErr != nil {
		t.Fatalf("expected valid base64 content: %v", decodeErr)
	}

	_, err = read.Invoke(ctx, session, mustJSON(t, map[string]any{}))
	if err == nil || err.Code != app.ErrorCodeInvalidArgument {
		t.Fatalf("expected missing path error, got: %#v", err)
	}

	search := &FSSearchHandler{}
	_, err = search.Invoke(ctx, session, mustJSON(t, map[string]any{"pattern": "["}))
	if err == nil || err.Code != app.ErrorCodeInvalidArgument {
		t.Fatalf("expected invalid regex error, got: %#v", err)
	}
}

func TestFSWriteValidationAndTraversal(t *testing.T) {
	session := domain.Session{WorkspacePath: t.TempDir(), AllowedPaths: []string{"."}}
	ctx := context.Background()
	write := &FSWriteHandler{}

	_, err := write.Invoke(ctx, session, json.RawMessage(`{"path":"x","content":"%%%","encoding":"base64"}`))
	if err == nil || err.Code != app.ErrorCodeInvalidArgument {
		t.Fatalf("expected invalid base64 error, got: %#v", err)
	}

	_, err = write.Invoke(ctx, session, mustJSON(t, map[string]any{"path": "x", "content": "a", "encoding": "unknown"}))
	if err == nil || err.Code != app.ErrorCodeInvalidArgument {
		t.Fatalf("expected invalid encoding error, got: %#v", err)
	}

	_, err = write.Invoke(ctx, session, mustJSON(t, map[string]any{"path": "../x", "content": "a"}))
	if err == nil || err.Code != app.ErrorCodePolicyDenied {
		t.Fatalf("expected policy denial, got: %#v", err)
	}

	large := make([]byte, 1024*1024+1)
	_, err = write.Invoke(ctx, session, mustJSON(t, map[string]any{"path": "big.txt", "content": string(large)}))
	if err == nil || err.Code != app.ErrorCodeInvalidArgument {
		t.Fatalf("expected content size error, got: %#v", err)
	}
}

func mustJSON(t *testing.T, payload any) json.RawMessage {
	t.Helper()
	data, err := json.Marshal(payload)
	if err != nil {
		t.Fatalf("marshal failed: %v", err)
	}
	return data
}
