package storage

import (
	"context"
	"os"
	"path/filepath"
	"testing"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
)

func TestLocalArtifactStore_SaveAndList(t *testing.T) {
	store := NewLocalArtifactStore(t.TempDir())
	ctx := context.Background()

	payloads := []app.ArtifactPayload{
		{Name: "report.txt", ContentType: "text/plain", Data: []byte("hello")},
		{Name: "../unsafe.bin", ContentType: "application/octet-stream", Data: []byte{0x01, 0x02}},
	}

	artifacts, err := store.Save(ctx, "inv-1", payloads)
	if err != nil {
		t.Fatalf("unexpected save error: %v", err)
	}
	if len(artifacts) != 2 {
		t.Fatalf("expected 2 artifacts, got %d", len(artifacts))
	}
	if filepath.Base(artifacts[1].Path) == "../unsafe.bin" {
		t.Fatalf("expected sanitized artifact name, got %s", artifacts[1].Path)
	}

	listed, err := store.List(ctx, "inv-1")
	if err != nil {
		t.Fatalf("unexpected list error: %v", err)
	}
	if len(listed) != 2 {
		t.Fatalf("expected 2 listed artifacts, got %d", len(listed))
	}
}

func TestLocalArtifactStore_EmptyAndMissing(t *testing.T) {
	store := NewLocalArtifactStore(t.TempDir())
	ctx := context.Background()

	artifacts, err := store.Save(ctx, "inv-empty", nil)
	if err != nil {
		t.Fatalf("unexpected save error: %v", err)
	}
	if len(artifacts) != 0 {
		t.Fatalf("expected no artifacts, got %d", len(artifacts))
	}

	listed, err := store.List(ctx, "inv-missing")
	if err != nil {
		t.Fatalf("unexpected list error: %v", err)
	}
	if len(listed) != 0 {
		t.Fatalf("expected empty list for missing invocation, got %d", len(listed))
	}
}

func TestFileSHA256_Error(t *testing.T) {
	_, err := fileSHA256(filepath.Join(t.TempDir(), "missing"))
	if err == nil {
		t.Fatal("expected error for missing file")
	}
}

func TestLocalArtifactStore_ListInvalidFileInfo(t *testing.T) {
	base := t.TempDir()
	store := NewLocalArtifactStore(base)
	ctx := context.Background()

	invocationDir := filepath.Join(base, "inv-bad")
	if err := os.MkdirAll(invocationDir, 0o755); err != nil {
		t.Fatalf("mkdir failed: %v", err)
	}
	if err := os.MkdirAll(filepath.Join(invocationDir, "dir"), 0o755); err != nil {
		t.Fatalf("mkdir failed: %v", err)
	}

	listed, err := store.List(ctx, "inv-bad")
	if err != nil {
		t.Fatalf("unexpected list error: %v", err)
	}
	if len(listed) != 0 {
		t.Fatalf("expected no regular files, got %d", len(listed))
	}
}
