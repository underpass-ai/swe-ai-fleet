# SonarCloud PR #139 — Round 2 Issues

Scan date: 2026-02-23 (after commit 4a7c8080 fixing 333 T-01..T-09 issues)
Total remaining: **196 CODE_SMELL** | BUGs/Vulnerabilities: 0

---

## Summary

| ID | Rule | Severity | Count | Category |
|----|------|----------|-------|----------|
| R-01 | `godre:S8196` | MINOR | 1 | Interface naming (`-er` suffix) |
| R-02 | `godre:S8209` | MINOR | 2 | Group consecutive same-type params |
| R-03 | `go:S107` | MAJOR | 3 | Functions with >7 parameters |
| R-04 | `go:S3776` | CRITICAL | 14 | Cognitive complexity > 15 |
| R-05 | `go:S1192` | CRITICAL | 61 | Duplicate string literals (extract to const) |
| R-06 | `godre:S8193` | MINOR | 115 | Inline `err` declaration into `if` condition |

---

## R-01 · Interface naming · `godre:S8196` · 1 issue

Rename single-method interface to verb/`-er` form.

| File | Line | Details |
|------|------|---------|
| `internal/adapters/tools/runner.go` | 35 | rename interface |

---

## R-02 · Group same-type params · `godre:S8209` · 2 issues

Change `func f(a string, b string)` → `func f(a, b string)`.

| File | Lines |
|------|-------|
| `internal/adapters/tools/k8s_delivery_tools.go` | 601, 623 |

---

## R-03 · Too many parameters · `go:S107` · 3 issues

Introduce a config/options struct to group related parameters.

| File | Lines |
|------|-------|
| `internal/adapters/tools/container_tools.go` | 575 |
| `internal/adapters/tools/image_tools.go` | 257, 501 |

---

## R-04 · Cognitive complexity · `go:S3776` · 14 issues

Extract sub-logic into helper functions to reduce nesting depth below 15.

| File | Lines | Notes |
|------|-------|-------|
| `internal/adapters/tools/api_benchmark_tools.go` | 128 | |
| `internal/adapters/tools/artifact_tools.go` | 281 | complexity 28 |
| `internal/adapters/tools/container_tools.go` | 444, 825 | 2 functions |
| `internal/adapters/tools/fs_tools.go` | 1252 | |
| `internal/adapters/tools/image_tools.go` | 501, 708 | 2 functions |
| `internal/adapters/tools/kafka_tools.go` | 111 | |
| `internal/adapters/tools/redis_tools.go` | 276 | |
| `internal/adapters/tools/swe_runtime_tools.go` | 612, 884, 1000, 1405 | 4 functions |
| `internal/app/service.go` | 176 | |

---

## R-05 · Duplicate string literals · `go:S1192` · 61 issues

Extract string literals appearing 3+ times to named constants.

| File | Lines | Notes |
|------|-------|-------|
| `internal/adapters/policy/static_policy.go` | 206, 212, 221 | 3 issues |
| `internal/adapters/tools/catalog_defaults.go` | 266, 337, 384, 406, 477, 546, 661, 751, 752, 931, 1073 (×14), 1074 (×8) | 22+ issues |
| `internal/adapters/tools/container_tools.go` | 75, 633, 718, 726, 1013 | 5 issues |
| `internal/adapters/tools/fs_tools.go` | 622, 629 (×2), 750, 756, 912 | 6 issues |
| `internal/adapters/tools/k8s_delivery_tools.go` | 271, 308, 345 | 3 issues |
| `internal/adapters/tools/kafka_tools.go` | 779 | 1 issue |
| `internal/adapters/tools/redis_tools.go` | 112, 126 | 2 issues |
| `internal/adapters/tools/swe_runtime_tools.go` | 27, 1254 | 2 issues |
| `internal/adapters/tools/toolchain_tools.go` | 197 | 1 issue |
| `internal/adapters/workspace/kubernetes_manager.go` | 372 (×2) | 2 issues |
| `internal/httpapi/server.go` | 52 | 1 issue |

**Note on catalog_defaults.go:** Lines 1073–1074 account for 22+ issues alone. The `"workspace.tools"` trace name and a span name are likely the culprit — they appear in every capability entry.

---

## R-06 · Inline `err` into `if` · `godre:S8193` · 115 issues

Replace:
```go
err := foo()
if err != nil { ... }
```
With:
```go
if err := foo(); err != nil { ... }
```

Applies to **26 files** (includes test files):

| File | Lines |
|------|-------|
| `internal/adapters/policy/static_policy.go` | 163, 235, 367, 469, 577, 655, 733, 811, 856 |
| `internal/adapters/tools/api_benchmark_tools.go` | 131 |
| `internal/adapters/tools/artifact_tools.go` | 401 |
| `internal/adapters/tools/connection_tools.go` | 40, 77 |
| `internal/adapters/tools/container_tools.go` | 237, 458, 613, 696 |
| `internal/adapters/tools/fs_tools.go` | 141, 335, 446, 553, 661, 788, 948, 1043, 1155, 1233 |
| `internal/adapters/tools/git_tools.go` | 123, 159, 200, 254, 314, 370, 430, 469, 588, 649, 709 |
| `internal/adapters/tools/git_tools_test.go` | 54 |
| `internal/adapters/tools/image_tools.go` | 95, 378, 595, 1039 |
| `internal/adapters/tools/image_tools_test.go` | 560, 563, 566 |
| `internal/adapters/tools/k8s_delivery_tools.go` | 256, 293, 330, 566 |
| `internal/adapters/tools/k8s_tools.go` | 603 |
| `internal/adapters/tools/kafka_tools.go` | 130, 286, 398 |
| `internal/adapters/tools/language_tool_handlers.go` | 148, 173, 195, 216, 238, 262, 284, 306, 328, 352, 444, 468, 507, 549 |
| `internal/adapters/tools/mongo_tools.go` | 82, 176 |
| `internal/adapters/tools/nats_tools.go` | 83, 170, 266, 493, 513 |
| `internal/adapters/tools/nats_tools_test.go` | 222 |
| `internal/adapters/tools/rabbit_tools.go` | 109, 220, 325 |
| `internal/adapters/tools/redis_tools.go` | 99, 197, 291, 389, 473, 545, 664 |
| `internal/adapters/tools/redis_tools_test.go` | 433 |
| `internal/adapters/tools/repo_analysis_tools.go` | 150, 231, 308, 426, 533 |
| `internal/adapters/tools/repo_tools.go` | 68, 117, 202 |
| `internal/adapters/tools/swe_runtime_tools.go` | 160, 343, 419, 513, 623, 778, 1013, 1224, 1353, 1415, 2542 |
| `internal/adapters/tools/toolchain_tools.go` | 94, 140, 225, 275, 328, 404 |
| `internal/app/service_schema_test.go` | 25 |
| `internal/httpapi/server.go` | 64, 150 |

---

## Recommended execution order

1. **R-01** (1 issue) — trivial rename in runner.go
2. **R-02** (2 issues) — trivial param grouping in k8s_delivery_tools.go
3. **R-03** (3 issues) — add option structs in container_tools.go + image_tools.go
4. **R-04** (14 issues) — extract helpers to reduce complexity; tackle largest files first (swe_runtime_tools 4 funcs)
5. **R-05** (61 issues) — extract remaining string constants; catalog_defaults.go is highest volume
6. **R-06** (115 issues) — mechanical inline of `err` into `if`; dispatch in batches of 4-5 files per agent

**R-06 suggested batches:**
- Batch A: `fs_tools.go` (10) + `git_tools.go` (11) + `language_tool_handlers.go` (14)
- Batch B: `swe_runtime_tools.go` (11) + `static_policy.go` (9)
- Batch C: `toolchain_tools.go` (6) + `redis_tools.go` (7) + `repo_analysis_tools.go` (5)
- Batch D: `nats_tools.go` (5) + `k8s_delivery_tools.go` (4) + `image_tools.go` (4) + `container_tools.go` (4)
- Batch E: `rabbit_tools.go` (3) + `kafka_tools.go` (3) + `mongo_tools.go` (2) + `repo_tools.go` (3) + `artifact_tools.go` (1) + `api_benchmark_tools.go` (1) + `connection_tools.go` (2) + `k8s_tools.go` (1)
- Batch F (tests): `git_tools_test.go` (1) + `image_tools_test.go` (3) + `nats_tools_test.go` (1) + `redis_tools_test.go` (1) + `service_schema_test.go` (1)
- Batch G: `httpapi/server.go` (2)
