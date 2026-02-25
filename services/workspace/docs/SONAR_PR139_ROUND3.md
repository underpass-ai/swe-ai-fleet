# SonarCloud PR #139 — Round 3 Issues

Scan date: 2026-02-23 (remote branch — does not yet include local commits 4a7c8080 + 121b605f)
Total open: **131 CODE_SMELL** | BUGs: 0 | Vulnerabilities: 0 | Hotspots: 1 (REVIEWED/SAFE)

> **Note:** 115 of the 131 issues (`godre:S8193`) and several `go:S3776`/`go:S107` issues are
> already fixed in local commits not yet pushed. Once pushed, the scan should drop to ~16 real issues.

---

## Summary

| ID | Rule | Severity | Count | Status |
|----|------|----------|-------|--------|
| S3-01 | `godre:S8242` | MAJOR | 1 | New — fix required |
| S3-02 | `go:S1192` | CRITICAL | 4 | Partially new — fix required |
| S3-03 | `go:S3776` | CRITICAL | 5 | Partially fixed locally — verify after push |
| S3-04 | `go:S107` | MAJOR | 6 | Partially fixed locally — verify after push |
| S3-05 | `godre:S8193` | MINOR | 115 | Already fixed locally — resolved by push |

---

## S3-01 · Context in struct field · `godre:S8242` · 1 issue

`context.Context` stored as a struct field instead of passed as a parameter.

| File | Line |
|------|------|
| `internal/adapters/tools/swe_runtime_tools.go` | 1428 |

**Fix:** Find the struct that embeds a `context.Context` field and refactor to pass context as a parameter to the methods that need it.

---

## S3-02 · Duplicate string literals · `go:S1192` · 4 issues

| File | Line | String (inferred) |
|------|------|-------------------|
| `internal/adapters/tools/catalog_defaults.go` | 694 | `"explicit approval required"` (×4) |
| `internal/adapters/tools/container_tools.go` | 80 | string repeated 3+ times |
| `internal/adapters/tools/fs_tools.go` | 633 | string repeated 3+ times |
| `internal/adapters/tools/fs_tools.go` | 760 | string repeated 3+ times |

**Fix:** Read each file at the indicated line, identify the repeated string, add a named constant, replace all occurrences.

---

## S3-03 · Cognitive complexity · `go:S3776` · 5 issues

Functions exceeding complexity 15. Some may already be resolved by local commits (R-04).

| File | Line | Notes |
|------|------|-------|
| `internal/adapters/tools/api_benchmark_tools.go` | 128 | Fixed in R-04 — verify after push |
| `internal/adapters/tools/fs_tools.go` | 1288 | Fixed in R-04 — verify after push |
| `internal/adapters/tools/swe_runtime_tools.go` | 1041 | May be new or line-shifted from R-04 work |
| `internal/adapters/tools/swe_runtime_tools.go` | 1473 | May be new or line-shifted from R-04 work |
| `internal/app/service.go` | 176 | Fixed in R-04 — verify after push |

**Action:** Push first, rescan, then extract remaining helpers from swe_runtime_tools if lines 1041/1473 are still flagged.

---

## S3-04 · Too many parameters · `go:S107` · 6 issues

Functions with more than 7 parameters. Some already fixed in R-03.

| File | Line | Notes |
|------|------|-------|
| `internal/adapters/tools/api_benchmark_tools.go` | 343 | Possibly new — check after push |
| `internal/adapters/tools/container_tools.go` | 589 | R-03 fixed line ~575 → may be resolved |
| `internal/adapters/tools/container_tools.go` | 618 | New or different function |
| `internal/adapters/tools/container_tools.go` | 1030 | New |
| `internal/adapters/tools/image_tools.go` | 587 | R-03 fixed lines ~257, ~501 → may be resolved |
| `internal/adapters/tools/swe_runtime_tools.go` | 998 | New |

**Action:** Push first, rescan, then add options structs for functions still flagged.

---

## S3-05 · Inline `err` into `if` · `godre:S8193` · 115 issues

**Already fixed locally** — all batch agents (A–G) confirmed code is already in the compliant form.
Will be resolved when commits 4a7c8080 and 121b605f are pushed.

Files affected (26 files, 115 locations):
`static_policy.go`, `swe_runtime_tools.go`, `fs_tools.go`, `git_tools.go`,
`language_tool_handlers.go`, `redis_tools.go`, `toolchain_tools.go`,
`repo_analysis_tools.go`, `nats_tools.go`, `container_tools.go`,
`image_tools.go`, `k8s_delivery_tools.go`, `rabbit_tools.go`,
`image_tools_test.go`, `kafka_tools.go`, `repo_tools.go`, `mongo_tools.go`,
`connection_tools.go`, `httpapi/server.go`, `git_tools_test.go`,
`nats_tools_test.go`, `redis_tools_test.go`, `artifact_tools.go`,
`api_benchmark_tools.go`, `k8s_tools.go`, `app/service_schema_test.go`

---

## Recommended execution order

1. **Push** commits 4a7c8080 + 121b605f → wait for CI rescan
2. After rescan, confirm S3-05 (115 issues) is gone
3. **S3-01** (1 issue) — fix `context.Context` struct field in `swe_runtime_tools.go:1428`
4. **S3-02** (4 issues) — add missing string constants in catalog_defaults, container_tools, fs_tools
5. **S3-03** (5 issues) — check which remain after push; extract helpers for any persisting
6. **S3-04** (6 issues) — check which remain after push; add options structs for any persisting
