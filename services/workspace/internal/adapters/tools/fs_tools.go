package tools

import (
	"bufio"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"
	"unicode/utf8"

	"context"

	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/app"
	"github.com/underpass-ai/swe-ai-fleet/services/workspace/internal/domain"
)

type FSListHandler struct{}

type FSReadHandler struct{}

type FSWriteHandler struct{}

type FSSearchHandler struct{}

func (h *FSListHandler) Name() string {
	return "fs.list"
}

func (h *FSListHandler) Invoke(_ context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		Path       string `json:"path"`
		Recursive  bool   `json:"recursive"`
		MaxEntries int    `json:"max_entries"`
	}{Path: ".", MaxEntries: 200}

	if len(args) > 0 {
		if err := json.Unmarshal(args, &request); err != nil {
			return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeInvalidArgument, Message: "invalid fs.list args", Retryable: false}
		}
	}
	if request.MaxEntries <= 0 {
		request.MaxEntries = 200
	}
	if request.MaxEntries > 1000 {
		request.MaxEntries = 1000
	}

	resolved, pathErr := resolvePath(session, request.Path)
	if pathErr != nil {
		return app.ToolRunResult{}, pathErr
	}

	stat, err := os.Stat(resolved)
	if err != nil {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeExecutionFailed, Message: err.Error(), Retryable: false}
	}

	type entry struct {
		Path     string    `json:"path"`
		Type     string    `json:"type"`
		Size     int64     `json:"size_bytes"`
		Mode     string    `json:"mode"`
		Modified time.Time `json:"modified_at"`
	}

	entries := make([]entry, 0, request.MaxEntries)
	appendEntry := func(path string, info os.FileInfo) {
		rel, relErr := filepath.Rel(session.WorkspacePath, path)
		if relErr != nil {
			rel = info.Name()
		}
		typeName := "file"
		if info.IsDir() {
			typeName = "dir"
		}
		entries = append(entries, entry{
			Path:     rel,
			Type:     typeName,
			Size:     info.Size(),
			Mode:     info.Mode().String(),
			Modified: info.ModTime().UTC(),
		})
	}

	if !stat.IsDir() {
		appendEntry(resolved, stat)
	} else if request.Recursive {
		walkStop := errors.New("stop-walk")
		walkErr := filepath.Walk(resolved, func(path string, info os.FileInfo, walkErr error) error {
			if walkErr != nil {
				return walkErr
			}
			if path != resolved {
				appendEntry(path, info)
			}
			if len(entries) >= request.MaxEntries {
				return walkStop
			}
			return nil
		})
		if walkErr != nil && !errors.Is(walkErr, walkStop) {
			return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeExecutionFailed, Message: walkErr.Error(), Retryable: false}
		}
	} else {
		dirEntries, readErr := os.ReadDir(resolved)
		if readErr != nil {
			return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeExecutionFailed, Message: readErr.Error(), Retryable: false}
		}
		for _, current := range dirEntries {
			if len(entries) >= request.MaxEntries {
				break
			}
			info, infoErr := current.Info()
			if infoErr != nil {
				continue
			}
			appendEntry(filepath.Join(resolved, current.Name()), info)
		}
	}

	return app.ToolRunResult{
		Output: map[string]any{"entries": entries, "count": len(entries)},
		Logs:   []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: fmt.Sprintf("listed %d entries", len(entries))}},
	}, nil
}

func (h *FSReadHandler) Name() string {
	return "fs.read"
}

func (h *FSReadHandler) Invoke(_ context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		Path     string `json:"path"`
		MaxBytes int    `json:"max_bytes"`
	}{MaxBytes: 64 * 1024}

	if err := json.Unmarshal(args, &request); err != nil {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeInvalidArgument, Message: "invalid fs.read args", Retryable: false}
	}
	if request.Path == "" {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeInvalidArgument, Message: "path is required", Retryable: false}
	}
	if request.MaxBytes <= 0 {
		request.MaxBytes = 64 * 1024
	}
	if request.MaxBytes > 1024*1024 {
		request.MaxBytes = 1024 * 1024
	}

	resolved, pathErr := resolvePath(session, request.Path)
	if pathErr != nil {
		return app.ToolRunResult{}, pathErr
	}

	content, err := os.ReadFile(resolved)
	if err != nil {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeExecutionFailed, Message: err.Error(), Retryable: false}
	}
	if len(content) > request.MaxBytes {
		content = content[:request.MaxBytes]
	}

	encoding := "utf8"
	value := string(content)
	if !utf8.Valid(content) {
		encoding = "base64"
		value = base64.StdEncoding.EncodeToString(content)
	}

	return app.ToolRunResult{
		Output: map[string]any{
			"path":       filepath.Clean(request.Path),
			"encoding":   encoding,
			"content":    value,
			"size_bytes": len(content),
		},
		Logs: []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: fmt.Sprintf("read %d bytes", len(content))}},
	}, nil
}

func (h *FSWriteHandler) Name() string {
	return "fs.write"
}

func (h *FSWriteHandler) Invoke(_ context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		Path          string `json:"path"`
		Content       string `json:"content"`
		Encoding      string `json:"encoding"`
		CreateParents bool   `json:"create_parents"`
	}{Encoding: "utf8", CreateParents: true}

	if err := json.Unmarshal(args, &request); err != nil {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeInvalidArgument, Message: "invalid fs.write args", Retryable: false}
	}
	if request.Path == "" {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeInvalidArgument, Message: "path is required", Retryable: false}
	}

	resolved, pathErr := resolvePath(session, request.Path)
	if pathErr != nil {
		return app.ToolRunResult{}, pathErr
	}

	var payload []byte
	switch strings.ToLower(strings.TrimSpace(request.Encoding)) {
	case "", "utf8":
		payload = []byte(request.Content)
	case "base64":
		decoded, err := base64.StdEncoding.DecodeString(request.Content)
		if err != nil {
			return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeInvalidArgument, Message: "invalid base64 content", Retryable: false}
		}
		payload = decoded
	default:
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeInvalidArgument, Message: "encoding must be utf8 or base64", Retryable: false}
	}

	if len(payload) > 1024*1024 {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeInvalidArgument, Message: "content exceeds 1MB limit", Retryable: false}
	}

	if request.CreateParents {
		if err := os.MkdirAll(filepath.Dir(resolved), 0o755); err != nil {
			return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeExecutionFailed, Message: err.Error(), Retryable: false}
		}
	}

	if err := os.WriteFile(resolved, payload, 0o644); err != nil {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeExecutionFailed, Message: err.Error(), Retryable: false}
	}

	hash := sha256.Sum256(payload)
	return app.ToolRunResult{
		Output: map[string]any{
			"path":          filepath.Clean(request.Path),
			"bytes_written": len(payload),
			"sha256":        hex.EncodeToString(hash[:]),
		},
		Logs: []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: fmt.Sprintf("wrote %d bytes", len(payload))}},
	}, nil
}

func (h *FSSearchHandler) Name() string {
	return "fs.search"
}

func (h *FSSearchHandler) Invoke(_ context.Context, session domain.Session, args json.RawMessage) (app.ToolRunResult, *domain.Error) {
	request := struct {
		Path       string `json:"path"`
		Pattern    string `json:"pattern"`
		MaxResults int    `json:"max_results"`
	}{Path: ".", MaxResults: 200}

	if err := json.Unmarshal(args, &request); err != nil {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeInvalidArgument, Message: "invalid fs.search args", Retryable: false}
	}
	if strings.TrimSpace(request.Pattern) == "" {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeInvalidArgument, Message: "pattern is required", Retryable: false}
	}
	if request.MaxResults <= 0 {
		request.MaxResults = 200
	}
	if request.MaxResults > 2000 {
		request.MaxResults = 2000
	}

	resolved, pathErr := resolvePath(session, request.Path)
	if pathErr != nil {
		return app.ToolRunResult{}, pathErr
	}

	re, err := regexp.Compile(request.Pattern)
	if err != nil {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeInvalidArgument, Message: err.Error(), Retryable: false}
	}

	type match struct {
		Path    string `json:"path"`
		Line    int    `json:"line"`
		Snippet string `json:"snippet"`
	}

	results := make([]match, 0, request.MaxResults)
	walkStop := errors.New("search-limit-reached")
	walkErr := filepath.Walk(resolved, func(path string, info os.FileInfo, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if info.IsDir() {
			if info.Name() == ".git" {
				return filepath.SkipDir
			}
			return nil
		}
		if !info.Mode().IsRegular() {
			return nil
		}

		file, openErr := os.Open(path)
		if openErr != nil {
			return nil
		}
		defer file.Close()

		scanner := bufio.NewScanner(file)
		buffer := make([]byte, 0, 64*1024)
		scanner.Buffer(buffer, 2*1024*1024)
		line := 0
		for scanner.Scan() {
			line++
			text := scanner.Text()
			if re.MatchString(text) {
				rel, relErr := filepath.Rel(session.WorkspacePath, path)
				if relErr != nil {
					rel = path
				}
				results = append(results, match{Path: rel, Line: line, Snippet: text})
				if len(results) >= request.MaxResults {
					return walkStop
				}
			}
		}
		return nil
	})
	if walkErr != nil && !errors.Is(walkErr, walkStop) {
		return app.ToolRunResult{}, &domain.Error{Code: app.ErrorCodeExecutionFailed, Message: walkErr.Error(), Retryable: false}
	}

	return app.ToolRunResult{
		Output: map[string]any{"matches": results, "count": len(results)},
		Logs:   []domain.LogLine{{At: time.Now().UTC(), Channel: "stdout", Message: fmt.Sprintf("found %d matches", len(results))}},
	}, nil
}
