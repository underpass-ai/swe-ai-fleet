# SonarCloud Issues — PR #139 (`chore/golang_executor_service`)

> **Total issues**: 333 CODE_SMELL
> **Critical**: 186 · **Major**: 9 · **Minor**: 138
> Source: https://sonarcloud.io/summary/new_code?id=underpass-ai-swe-ai-fleet&pullRequest=139
> All items must be resolved to 0 before merging.

---

## Summary by rule

| Rule | Count | Severity | Description |
|------|------:|----------|-------------|
| `go:S1192` | 115 | CRITICAL | Duplicate string literal — define a named constant |
| `godre:S8193` | 115 | MINOR | Unnecessary `err` variable — inline as `if err := ...; err != nil` |
| `go:S3776` | 62 | CRITICAL | Cognitive complexity > 15 — refactor into smaller functions |
| `godre:S8209` | 19 | MINOR | Consecutive same-type params — group with a struct or reorder |
| `go:S1186` | 9 | MAJOR | Empty function body — add explanatory comment or implement |
| `go:S107` | 5 | MAJOR | >7 function parameters — introduce options/config struct |
| `godre:S8196` | 4 | MINOR | Single-method interface naming — rename to verb form (e.g. `Runner` → `Runnable` or `Run`) |
| `godre:S8239` | 3 | MINOR | Use the existing `ctx` param, not `context.Background()` |
| `godre:S8188` | 1 | MAJOR | Defer `cancel()` immediately after context creation — resource leak |

---

## Task list

### T-01 · Fix resource leak: defer cancel() after context creation
**Rule**: `godre:S8188` · **Severity**: MAJOR · **Count**: 1

- [ ] `internal/adapters/tools/mongo_tools.go:338` — add `defer cancel()` immediately after `context.WithTimeout` / `context.WithDeadline` call

---

### T-02 · Use existing context parameter instead of context.Background()
**Rule**: `godre:S8239` · **Severity**: MINOR · **Count**: 3

- [ ] `internal/adapters/workspace/kubernetes_manager.go:144` — replace `context.Background()` with the received `ctx` parameter
- [ ] `internal/adapters/workspace/kubernetes_manager.go:169` — replace `context.Background()` with the received `ctx` parameter
- [ ] `internal/adapters/workspace/kubernetes_manager.go:222` — replace `context.Background()` with the received `ctx` parameter

---

### T-03 · Add comments to empty function bodies
**Rule**: `go:S1186` · **Severity**: MAJOR · **Count**: 9

- [ ] `internal/adapters/tools/kafka_tools.go:521`
- [ ] `internal/adapters/tools/mongo_tools.go:336`
- [ ] `internal/adapters/tools/mongo_tools.go:342`
- [ ] `internal/adapters/tools/nats_tools.go:368`
- [ ] `internal/adapters/tools/nats_tools.go:393`
- [ ] `internal/adapters/tools/rabbit_tools.go:475`
- [ ] `internal/adapters/tools/rabbit_tools.go:481`
- [ ] `internal/app/service.go:330`
- [ ] `internal/app/service.go:935`

---

### T-04 · Reduce cognitive complexity (refactor large functions)
**Rule**: `go:S3776` · **Severity**: CRITICAL · **Count**: 62

Each function's cognitive complexity must be reduced to ≤ 15 by extracting helper functions or simplifying conditionals.

#### `internal/adapters/tools/swe_runtime_tools.go` (10 functions)
- [ ] Line 142
- [ ] Line 592
- [ ] Line 739
- [ ] Line 941
- [ ] Line 1340
- [ ] Line 2139
- [ ] Line 2270
- [ ] Line 2401
- [ ] Line 2560
- [ ] Line 2760

#### `internal/adapters/policy/static_policy.go` (9 functions)
- [ ] Line 149
- [ ] Line 281
- [ ] Line 319
- [ ] Line 414
- [ ] Line 518
- [ ] Line 589
- [ ] Line 660
- [ ] Line 731
- [ ] Line 769

#### `internal/adapters/tools/repo_analysis_tools.go` (4 functions)
- [ ] Line 508
- [ ] Line 769
- [ ] Line 1039
- [ ] Line 1090

#### `internal/adapters/tools/repo_tools.go` (4 functions)
- [ ] Line 370
- [ ] Line 440
- [ ] Line 702
- [ ] Line 802

#### `internal/adapters/tools/api_benchmark_tools.go` (4 functions)
- [ ] Line 128
- [ ] Line 438
- [ ] Line 480
- [ ] Line 908

#### `internal/adapters/tools/container_tools.go` (4 functions)
- [ ] Line 325
- [ ] Line 416
- [ ] Line 799
- [ ] Line 1270

#### `internal/adapters/tools/image_tools.go` (3 functions)
- [ ] Line 50
- [ ] Line 290
- [ ] Line 570

#### `internal/adapters/tools/fs_tools.go` (3 functions)
- [ ] Line 142
- [ ] Line 776
- [ ] Line 1197

#### `internal/adapters/tools/k8s_delivery_tools.go` (3 functions)
- [ ] Line 87
- [ ] Line 499
- [ ] Line 572

#### `internal/app/service.go` (2 functions)
- [ ] Line 175
- [ ] Line 640

#### `internal/httpapi/server.go` (2 functions)
- [ ] Line 81 — `handleSessionRoutes`
- [ ] Line 165 — `handleInvocationRoutes`

#### `internal/adapters/tools/redis_tools.go` (2 functions)
- [ ] Line 186
- [ ] Line 291

#### `internal/adapters/tools/git_tools.go` (2 functions)
- [ ] Line 140
- [ ] Line 464

#### `internal/adapters/tools/kafka_tools.go` (2 functions)
- [ ] Line 100
- [ ] Line 672

#### `internal/adapters/tools/k8s_tools.go` (2 functions)
- [ ] Line 171
- [ ] Line 347

#### Remaining single-function files
- [ ] `internal/adapters/tools/artifact_tools.go:257`
- [ ] `internal/adapters/tools/language_tool_handlers.go:334`
- [ ] `internal/adapters/tools/runner.go:87`
- [ ] `internal/adapters/tools/toolchain_tools.go:397`
- [ ] `internal/adapters/workspace/local_manager.go:135`
- [ ] `cmd/workspace/main.go:38`

---

### T-05 · Rename single-method interfaces to Go conventions
**Rule**: `godre:S8196` · **Severity**: MINOR · **Count**: 4

- [ ] `internal/adapters/tools/runner.go:35` — rename interface to verb form (e.g. `CommandRunner` → keep or rename to idiomatic Go)
- [ ] `internal/app/types.go:85` — rename interface
- [ ] `internal/app/types.go:89` — rename interface
- [ ] `internal/app/types.go:102` — rename interface

---

### T-06 · Replace too-many-parameters functions with option structs
**Rule**: `go:S107` · **Severity**: MAJOR · **Count**: 5

Functions with > 7 parameters must be refactored to accept a single config/options struct.

- [ ] `internal/adapters/tools/container_tools.go:799`
- [ ] `internal/adapters/tools/container_tools.go:1449`
- [ ] `internal/adapters/tools/fs_tools.go:698`
- [ ] `internal/adapters/tools/fs_tools.go:836`
- [ ] `internal/adapters/tools/language_tool_handlers.go:591`

---

### T-07 · Group consecutive same-type function parameters
**Rule**: `godre:S8209` · **Severity**: MINOR · **Count**: 19

- [ ] `internal/adapters/policy/static_policy.go:899`
- [ ] `internal/adapters/policy/static_policy.go:924`
- [ ] `internal/adapters/tools/artifact_tools.go:484`
- [ ] `internal/adapters/tools/artifact_tools.go:498`
- [ ] `internal/adapters/tools/fs_tools.go:487`
- [ ] `internal/adapters/tools/image_tools.go:946`
- [ ] `internal/adapters/tools/image_tools.go:1057`
- [ ] `internal/adapters/tools/k8s_delivery_tools.go:572`
- [ ] `internal/adapters/tools/k8s_tools.go:384`
- [ ] `internal/adapters/tools/kafka_tools.go:767`
- [ ] `internal/adapters/tools/nats_tools.go:501`
- [ ] `internal/adapters/tools/nats_tools.go:545`
- [ ] `internal/adapters/tools/repo_analysis_tools.go:1044`
- [ ] `internal/adapters/tools/runner.go:68`
- [ ] `internal/adapters/tools/swe_runtime_tools.go:2907`
- [ ] `internal/adapters/tools/swe_runtime_tools.go:3026`
- [ ] `internal/adapters/tools/swe_runtime_tools.go:3104`
- [ ] `internal/adapters/tools/swe_runtime_tools.go:3111`
- [ ] `internal/app/metrics.go:192`

---

### T-08 · Inline unnecessary `err` variable declarations
**Rule**: `godre:S8193` · **Severity**: MINOR · **Count**: 115

Pattern to fix: `err := foo(); if err != nil` → `if err := foo(); err != nil`

#### `internal/adapters/tools/git_tools.go` (11 occurrences)
- [ ] Lines: 111, 147, 201, 255, 315, 371, 431, 470, 588, 649, 709

#### `internal/adapters/tools/language_tool_handlers.go` (14 occurrences)
- [ ] Lines: 137, 162, 184, 205, 227, 251, 273, 295, 317, 341, 422, 455, 494, 536

#### `internal/adapters/tools/swe_runtime_tools.go` (11 occurrences)
- [ ] Lines: 147, 323, 399, 493, 603, 751, 954, 1159, 1288, 1350, 2450

#### `internal/adapters/tools/fs_tools.go` (10 occurrences)
- [ ] Lines: 125, 299, 410, 517, 625, 751, 893, 988, 1100, 1178

#### `internal/adapters/tools/redis_tools.go` (7 occurrences)
- [ ] Lines: 99, 197, 306, 412, 496, 568, 687

#### `internal/adapters/tools/toolchain_tools.go` (6 occurrences)
- [ ] Lines: 94, 140, 225, 275, 328, 404

#### `internal/adapters/tools/repo_analysis_tools.go` (5 occurrences)
- [ ] Lines: 140, 221, 298, 416, 523

#### `internal/adapters/tools/repo_tools.go` (3 occurrences)
- [ ] Lines: 55, 104, 189

#### `internal/adapters/tools/nats_tools.go` (5 occurrences)
- [ ] Lines: 78, 165, 261, 488, 508

#### `internal/adapters/tools/kafka_tools.go` (3 occurrences)
- [ ] Lines: 119, 275, 387

#### `internal/adapters/tools/rabbit_tools.go` (3 occurrences)
- [ ] Lines: 104, 215, 320

#### `internal/adapters/tools/image_tools.go` (4 occurrences)
- [ ] Lines: 68, 304, 489, 927

#### `internal/adapters/tools/k8s_delivery_tools.go` (4 occurrences)
- [ ] Lines: 234, 271, 308, 534

#### `internal/adapters/tools/container_tools.go` (4 occurrences)
- [ ] Lines: 212, 430, 596, 679

#### `internal/adapters/policy/static_policy.go` (9 occurrences)
- [ ] Lines: 161, 226, 337, 432, 533, 604, 675, 746, 784

#### `internal/adapters/tools/mongo_tools.go` (2 occurrences)
- [ ] Lines: 82, 176

#### `internal/adapters/tools/k8s_tools.go` (1 occurrence)
- [ ] Line: 580

#### `internal/adapters/tools/connection_tools.go` (2 occurrences)
- [ ] Lines: 40, 77

#### `internal/adapters/tools/api_benchmark_tools.go` (1 occurrence)
- [ ] Line: 131

#### `internal/adapters/tools/artifact_tools.go` (1 occurrence)
- [ ] Line: 405

#### `internal/httpapi/server.go` (2 occurrences)
- [ ] Lines: 62, 138

#### Test files (fix in test code too)
- [ ] `internal/adapters/tools/git_tools_test.go:54`
- [ ] `internal/adapters/tools/image_tools_test.go:560, 563, 566`
- [ ] `internal/adapters/tools/nats_tools_test.go:222`
- [ ] `internal/adapters/tools/redis_tools_test.go:433`
- [ ] `internal/app/service_schema_test.go:25`

---

### T-09 · Replace duplicate string literals with named constants
**Rule**: `go:S1192` · **Severity**: CRITICAL · **Count**: 115

Each string appearing ≥ 3 times must be extracted to a package-level or file-level constant.
Group by file; define constants at the top of the file (or a dedicated `const.go`).

#### `internal/adapters/tools/catalog_defaults.go` (many literals, highest volume)
- [ ] Lines: 22, 23, 1024, 1044, 1053, 1054, 1078, 1486, 1639, 1640, 1751, 1997, 2073, 2090, 2137
  _(review all repeated schema strings, tool-name strings, and description fragments)_

#### `internal/adapters/tools/swe_runtime_tools.go` (9 occurrences)
- [ ] Lines: 186, 231, 232, 441, 562, 599, 789, 1189, 2763

#### `internal/adapters/tools/fs_tools.go` (7 occurrences)
- [ ] Lines: 303, 586, 593, 713, 719, 857, 919

#### `internal/adapters/tools/container_tools.go` (10 occurrences)
- [ ] Lines: 50, 237, 254, 496, 616, 618, 701, 709, 712, 982

#### `internal/adapters/policy/static_policy.go` (4 occurrences)
- [ ] Lines: 162, 197, 203, 212

#### `internal/adapters/tools/language_tool_handlers.go` (4 occurrences)
- [ ] Lines: 256, 354, 362, 570

#### `internal/adapters/tools/git_tools.go` (3 occurrences)
- [ ] Lines: 264, 598, 602

#### `internal/adapters/tools/image_tools.go` (3 occurrences)
- [ ] Lines: 729, 736, 1039

#### `internal/adapters/tools/k8s_delivery_tools.go` (3 occurrences)
- [ ] Lines: 249, 286, 323

#### `internal/adapters/tools/kafka_tools.go` (3 occurrences)
- [ ] Lines: 132, 163, 752

#### `internal/adapters/tools/nats_tools.go` (2 occurrences)
- [ ] Lines: 91, 105

#### `internal/adapters/tools/rabbit_tools.go` (2 occurrences)
- [ ] Lines: 117, 133

#### `internal/adapters/tools/redis_tools.go` (2 occurrences)
- [ ] Lines: 112, 126

#### `internal/adapters/tools/toolchain_tools.go` (1 occurrence)
- [ ] Line: 197

#### `internal/adapters/tools/repo_analysis_tools.go` (1 occurrence)
- [ ] Line: 196

#### `internal/adapters/tools/repo_tools.go` (1 occurrence)
- [ ] Line: 415

#### `internal/adapters/workspace/kubernetes_manager.go` (1 occurrence)
- [ ] Line: 372

#### `internal/app/service.go` (1 occurrence)
- [ ] Line: 116

#### `internal/httpapi/server.go` (1 occurrence)
- [ ] Line: 50

#### `cmd/workspace/main.go` (1 occurrence)
- [ ] Line: 58

---

## Execution order (recommended)

1. **T-01** — Resource leak (1 change, highest risk) ✅ fix first
2. **T-02** — Wrong context propagation (3 changes, correctness) ✅ fix before T-03
3. **T-03** — Empty bodies (9 changes, comment or implement)
4. **T-05** — Interface naming (4 changes, rename only)
5. **T-06** — Too many parameters → structs (5 refactors)
6. **T-07** — Group same-type params (19 changes, mechanical)
7. **T-04** — Cognitive complexity (62 refactors — most time-consuming)
8. **T-08** — Inline err checks (115 mechanical changes — scripted batch fix)
9. **T-09** — String constants (115 changes — batch then verify compilation)

---

## Notes

- `godre:S8193` and `go:S1192` are **mechanical** and can be addressed with a search-and-replace pass; run `go build ./...` and `go test ./...` after each file.
- `go:S3776` (complexity) requires **reading each function** before splitting — do not blindly refactor; preserve existing tests.
- Test files (`*_test.go`) flagged by `godre:S8193` should also be fixed to maintain consistency.
- After all fixes: push to PR #139, wait for SonarCloud re-analysis and confirm 0 open issues.
