package main

import (
	"bytes"
	"log/slog"
	"os"
	"reflect"
	"testing"
)

func TestEnvOrDefault(t *testing.T) {
	const key = "WORKSPACE_TEST_ENV_OR_DEFAULT"
	_ = os.Unsetenv(key)
	if value := envOrDefault(key, "fallback"); value != "fallback" {
		t.Fatalf("expected fallback, got %s", value)
	}

	if err := os.Setenv(key, "configured"); err != nil {
		t.Fatalf("setenv failed: %v", err)
	}
	t.Cleanup(func() { _ = os.Unsetenv(key) })
	if value := envOrDefault(key, "fallback"); value != "configured" {
		t.Fatalf("expected configured value, got %s", value)
	}
}

func TestParseLogLevel(t *testing.T) {
	if got := parseLogLevel("debug"); got != slog.LevelDebug {
		t.Fatalf("expected debug, got %v", got)
	}
	if got := parseLogLevel("WARN"); got != slog.LevelWarn {
		t.Fatalf("expected warn, got %v", got)
	}
	if got := parseLogLevel("ERROR"); got != slog.LevelError {
		t.Fatalf("expected error, got %v", got)
	}
	if got := parseLogLevel("unknown"); got != slog.LevelInfo {
		t.Fatalf("expected info fallback, got %v", got)
	}
}

func TestParseIntOrDefault(t *testing.T) {
	if got := parseIntOrDefault("42", 9); got != 42 {
		t.Fatalf("expected 42, got %d", got)
	}
	if got := parseIntOrDefault("  ", 9); got != 9 {
		t.Fatalf("expected fallback 9, got %d", got)
	}
	if got := parseIntOrDefault("bad", 9); got != 9 {
		t.Fatalf("expected fallback for invalid input, got %d", got)
	}
}

func TestParseStringMapEnv(t *testing.T) {
	parsed, err := parseStringMapEnv(`{"toolchains":"registry.example.com/runner/toolchains:v1","fat":"registry.example.com/runner/fat:v1"}`)
	if err != nil {
		t.Fatalf("unexpected parse error: %v", err)
	}
	expected := map[string]string{
		"toolchains": "registry.example.com/runner/toolchains:v1",
		"fat":        "registry.example.com/runner/fat:v1",
	}
	if !reflect.DeepEqual(expected, parsed) {
		t.Fatalf("unexpected parsed map: %#v", parsed)
	}

	empty, err := parseStringMapEnv("  ")
	if err != nil {
		t.Fatalf("unexpected empty parse error: %v", err)
	}
	if empty != nil {
		t.Fatalf("expected nil map for empty input, got %#v", empty)
	}
}

func TestParseStringMapEnvRejectsInvalidJSON(t *testing.T) {
	_, err := parseStringMapEnv(`{"toolchains":`)
	if err == nil {
		t.Fatal("expected parse error")
	}
}

func TestBuildInvocationStoreMemoryAndUnsupported(t *testing.T) {
	var logs bytes.Buffer
	logger := slog.New(slog.NewTextHandler(&logs, nil))

	const backendKey = "INVOCATION_STORE_BACKEND"
	_ = os.Unsetenv(backendKey)
	store, err := buildInvocationStore(logger)
	if err != nil {
		t.Fatalf("unexpected memory store error: %v", err)
	}
	if store == nil {
		t.Fatal("expected non-nil memory store")
	}

	if err := os.Setenv(backendKey, "unknown-backend"); err != nil {
		t.Fatalf("setenv failed: %v", err)
	}
	t.Cleanup(func() { _ = os.Unsetenv(backendKey) })

	_, err = buildInvocationStore(logger)
	if err == nil {
		t.Fatal("expected unsupported backend error")
	}
}
