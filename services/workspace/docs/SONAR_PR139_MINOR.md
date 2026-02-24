# SonarCloud PR #139 — MINOR Issues (godre:S8193)

Scan date: 2026-02-23
Rule: **`godre:S8193`** — Inline `err` declaration into `if` condition
Total: **115 issues** across **26 files**

---

## Status

> **All 115 issues are already fixed in local commits `4a7c8080` and `121b605f`.**
> SonarCloud still shows them because the remote branch has not yet been updated.
>
> **Action required: push the 3 pending commits.**
>
> ```
> f91817cc  docs: add Round 3 SonarCloud planning document for PR#139
> 121b605f  fix(workspace): resolve remaining 196 SonarCloud CODE_SMELL issues (Round 2)
> 4a7c8080  fix(workspace): resolve 333 SonarCloud CODE_SMELL issues on PR#139
> ```
>
> Once CI rescans, all 115 MINOR issues will be resolved automatically.

---

## Pattern

Replace:
```go
err := foo()
if err != nil { ... }
```
With:
```go
if err := foo(); err != nil { ... }
```

---

## Issues by file (115 total)

| File | Lines | Count |
|------|-------|-------|
| `internal/adapters/tools/language_tool_handlers.go` | 148, 173, 195, 216, 238, 262, 284, 306, 328, 352, 444, 468, 507, 549 | 14 |
| `internal/adapters/tools/git_tools.go` | 123, 159, 200, 254, 314, 370, 430, 469, 588, 649, 709 | 11 |
| `internal/adapters/tools/swe_runtime_tools.go` | 160, 343, 419, 513, 623, 778, 1013, 1224, 1353, 1415, 2542 | 11 |
| `internal/adapters/tools/fs_tools.go` | 141, 335, 446, 553, 661, 788, 948, 1043, 1155, 1233 | 10 |
| `internal/adapters/policy/static_policy.go` | 163, 235, 367, 469, 577, 655, 733, 811, 856 | 9 |
| `internal/adapters/tools/redis_tools.go` | 99, 197, 291, 389, 473, 545, 664 | 7 |
| `internal/adapters/tools/toolchain_tools.go` | 94, 140, 225, 275, 328, 404 | 6 |
| `internal/adapters/tools/nats_tools.go` | 83, 170, 266, 493, 513 | 5 |
| `internal/adapters/tools/repo_analysis_tools.go` | 150, 231, 308, 426, 533 | 5 |
| `internal/adapters/tools/container_tools.go` | 237, 458, 613, 696 | 4 |
| `internal/adapters/tools/image_tools.go` | 95, 378, 595, 1039 | 4 |
| `internal/adapters/tools/k8s_delivery_tools.go` | 256, 293, 330, 566 | 4 |
| `internal/adapters/tools/image_tools_test.go` | 560, 563, 566 | 3 |
| `internal/adapters/tools/kafka_tools.go` | 130, 286, 398 | 3 |
| `internal/adapters/tools/rabbit_tools.go` | 109, 220, 325 | 3 |
| `internal/adapters/tools/repo_tools.go` | 68, 117, 202 | 3 |
| `internal/adapters/tools/connection_tools.go` | 40, 77 | 2 |
| `internal/adapters/tools/mongo_tools.go` | 82, 176 | 2 |
| `internal/httpapi/server.go` | 64, 150 | 2 |
| `internal/adapters/tools/api_benchmark_tools.go` | 131 | 1 |
| `internal/adapters/tools/artifact_tools.go` | 401 | 1 |
| `internal/adapters/tools/git_tools_test.go` | 54 | 1 |
| `internal/adapters/tools/k8s_tools.go` | 603 | 1 |
| `internal/adapters/tools/nats_tools_test.go` | 222 | 1 |
| `internal/adapters/tools/redis_tools_test.go` | 433 | 1 |
| `internal/app/service_schema_test.go` | 25 | 1 |
| **Total** | | **115** |

---

## Batch plan (if manual fixes are needed after rescan)

If any issues remain after pushing, apply fixes in these batches:

| Batch | Files | Issues |
|-------|-------|--------|
| A | `fs_tools.go` (10) + `git_tools.go` (11) + `language_tool_handlers.go` (14) | 35 |
| B | `swe_runtime_tools.go` (11) + `static_policy.go` (9) | 20 |
| C | `toolchain_tools.go` (6) + `redis_tools.go` (7) + `repo_analysis_tools.go` (5) | 18 |
| D | `nats_tools.go` (5) + `k8s_delivery_tools.go` (4) + `image_tools.go` (4) + `container_tools.go` (4) | 17 |
| E | `rabbit_tools.go` (3) + `kafka_tools.go` (3) + `mongo_tools.go` (2) + `repo_tools.go` (3) + `artifact_tools.go` (1) + `api_benchmark_tools.go` (1) + `connection_tools.go` (2) + `k8s_tools.go` (1) | 16 |
| F | `git_tools_test.go` (1) + `image_tools_test.go` (3) + `nats_tools_test.go` (1) + `redis_tools_test.go` (1) + `service_schema_test.go` (1) | 7 |
| G | `httpapi/server.go` (2) | 2 |

---

## Recommended execution order

1. **Push** commits `4a7c8080` + `121b605f` + `f91817cc` → wait for CI rescan
2. **Verify** all 115 MINOR issues are closed on SonarCloud
3. If any remain, apply batch fixes A–G above
