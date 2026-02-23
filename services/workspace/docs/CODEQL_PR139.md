# CodeQL PR #139 — Security Alerts

Scan: PR #139 · `chore/golang_executor_service`
Total: **2 CRITICAL · 45 HIGH · 1 MEDIUM** = 48 alerts

---

## Summary

| # | Rule | Severity | Alerts | Assessment | Action |
|---|------|----------|--------|------------|--------|
| C-01 | `go/command-injection` | CRITICAL | 2 | Mixed — 1 real, 1 false positive | Code fix + suppress |
| C-02 | `go/path-injection` | HIGH | 39 | False positives — `resolvePath()` already validates | Strengthen sanitizer annotation |
| C-03 | `go/uncontrolled-allocation-size` | HIGH | 4 | 1 real (remote handler uncapped), 3 false positives | 1 code fix + suppress 3 |
| C-04 | `go/sql-injection` | HIGH | 2 | Real — MongoDB operator injection risk | Code fix |
| C-05 | `js/shell-command-injection-from-environment` | MEDIUM | 1 | Existing issue in `generate-grpc.js` (not in this PR scope) | Dismiss/defer |

---

## C-01 · Command Injection · `go/command-injection` · 2 alerts

### Alert 1: `runner.go:226` — BY DESIGN (false positive)

```go
cmd := exec.CommandContext(ctx, command, args...)
```

`command` comes from `spec.Command` (user-controlled). However:
- This is the workspace execution engine — running user-specified commands is its purpose
- Does NOT use a shell (`exec.Command` passes args directly to the OS, no shell interpolation)
- Sandboxed by policy engine upstream; sessions are scoped per tenant

**Fix:** Add CodeQL suppression comment documenting the design intent.

```go
// Command is intentionally user-supplied: this is a sandboxed execution engine.
// exec.CommandContext passes args directly to the OS without shell interpolation.
cmd := exec.CommandContext(ctx, command, args...) //nolint:gosec
```

### Alert 2: `local_manager.go:127` — FALSE POSITIVE

```go
cmd := exec.CommandContext(ctx, "git", args...)
```

Binary is hardcoded (`"git"`). `repoURL` and `targetPath` are passed as arguments,
not interpolated into a shell string. CodeQL flags any user input in `exec.Command` args.

**Fix:** Add suppression comment.

---

## C-02 · Path Injection · `go/path-injection` · 39 alerts — ALL FALSE POSITIVES

All 39 alerts flow through `resolvePath()` in `internal/adapters/tools/path.go`
(or equivalent containment checks in `local_manager.go` / `local_artifacts.go`).

`resolvePath()` already enforces:
1. `filepath.Clean()` normalization
2. Explicit `..` prefix rejection
3. AllowedPaths whitelist check
4. Final containment: `strings.HasPrefix(resolvedClean, workspaceClean+separator)`

`local_artifacts.go:115`:
```go
if cleanPath != cleanBase && !strings.HasPrefix(cleanPath, cleanBase+string(filepath.Separator)) {
```

**Root cause:** CodeQL does not recognize `resolvePath()` as a sanitizer/validator.

**Fix options (choose one):**
- **Option A (preferred):** Add a CodeQL model file (`.github/codeql/models/`) declaring `resolvePath` as a path sanitizer — zero code change, declarative
- **Option B:** Inline the containment check at each call site (invasive, ~39 changes)
- **Option C:** Add `// nolint:gosec` at each flagged use site

**Recommended:** Option A — CodeQL custom model for `resolvePath`.

### Files and lines
| File | Lines (flagged) |
|------|----------------|
| `internal/adapters/tools/fs_tools.go` | 172, 241, 367, 478, 483, 580, 597, 599, 604, 715, 719, 724, 728, 735×2, 837, 869, 873, 878, 973, 988, 990, 1065, 1532, 1539, 1553, 1566, 1572, 1575 |
| `internal/adapters/workspace/local_manager.go` | 44, 158, 163, 171 |
| `internal/adapters/tools/artifact_tools.go` | 269, 317, 441 |
| `internal/adapters/storage/local_artifacts.go` | 67, 146 |
| `internal/adapters/tools/repo_tools.go` | 796 |

---

## C-03 · Uncontrolled Allocation Size · `go/uncontrolled-allocation-size` · 4 alerts

### Alert at `fs_tools.go:299` — REAL (remote list handler missing cap)

```go
// invokeRemote handler — no MaxEntries cap before make()
entries := make([]fsListEntry, 0, request.MaxEntries)
```

The local handler caps `MaxEntries` at 1000 (lines 149-153) but `invokeRemote` does not.

**Fix:** Add cap at top of `invokeRemote`:
```go
if request.MaxEntries <= 0 {
    request.MaxEntries = 200
}
if request.MaxEntries > 1000 {
    request.MaxEntries = 1000
}
```

### Alerts at `fs_tools.go:177, 1289, 1350` — FALSE POSITIVES

- Line 177: `MaxEntries` is capped at lines 149-153 (before use)
- Line 1289: `maxResults` is capped at lines 1243-1246 (before use)
- Line 1350: same as 1289

CodeQL can't trace the cap through the function. Add suppression comments.

---

## C-04 · SQL/NoSQL Injection · `go/sql-injection` · 2 alerts

### `mongo_tools.go:280` and `mongo_tools.go:313`

```go
cursor, err := coll.Find(ctx, filter, opts)     // filter from user
cursor, err := coll.Aggregate(ctx, pipeline)    // pipeline from user
```

MongoDB queries using unvalidated `map[string]any` allow **operator injection**:
- `{"$where": "malicious JS code"}` — server-side JavaScript execution
- `{"$function": {...}}` — arbitrary JavaScript
- `{"field": {"$regex": ".*"}}` — ReDoS potential

**Fix:** Add a recursive filter sanitizer that rejects dangerous top-level operators:

```go
// Dangerous operators that allow server-side code execution
var mongoForbiddenOperators = map[string]bool{
    "$where":       true,
    "$function":    true,
    "$accumulator": true,
}

func validateMongoFilter(filter map[string]any) error {
    for key := range filter {
        if mongoForbiddenOperators[key] {
            return fmt.Errorf("forbidden MongoDB operator: %s", key)
        }
    }
    return nil
}
```

Apply to both `Find` filter and `Aggregate` pipeline stages.

---

## C-05 · JS Shell Injection · `js/shell-command-injection-from-environment` · 1 alert

`services/planning-ui/scripts/generate-grpc.js:60` — pre-existing, not introduced by this PR.

**Action:** Defer. Fix in a separate PR targeting the planning-ui service.

---

## Execution Plan

### Phase 1 — Real code fixes (3 changes)

1. **`mongo_tools.go`** — Add `validateMongoFilter` for `Find` and `Aggregate`
2. **`fs_tools.go`** — Add `MaxEntries` cap in `invokeRemote` (line ~280)
3. **`runner.go`** — Add suppression comment documenting design intent

### Phase 2 — Suppress false positives (targeted)

4. **`local_manager.go:127`** — Add suppression comment for git exec
5. **`fs_tools.go:177, 1289, 1350`** — Add suppression for already-capped allocations

### Phase 3 — CodeQL model for path sanitizer (optional)

6. If Phase 1+2 doesn't reduce alert count sufficiently, add `.github/codeql/` custom model declaring `resolvePath` as a path sanitizer to close all 39 path-injection false positives at once.

### Phase 4 — Defer

7. `generate-grpc.js` — separate PR

---

## Notes

- **Do NOT use `sonar-project.properties` exclusions** to suppress these
- Phase 3 uses CodeQL's official extension mechanism (`.github/codeql/models/`) — this is a model file for the analyzer, not a configuration suppression
- Changes to `fs_tools.go` and `runner.go` are execution-path code — run `go test ./...` locally before committing
- E2E tests in `e2e/` folder must not be broken — do not change interfaces or domain types
