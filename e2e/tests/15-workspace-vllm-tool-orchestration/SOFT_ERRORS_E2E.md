# Test 15 - Soft Errors (E2E)

## Approach

Soft errors are now declared **per-tool in `tool_catalog.yaml`** via the
`soft_errors` field. Each entry lists acceptable `(code, message_contains)`
patterns. The generic runner matches these at invocation time.

## Currently declared soft errors

### Write operations on read-only profiles
Tools: `kafka.produce`, `rabbit.publish`, `nats.publish`, `redis.set`, `redis.del`
```yaml
soft_errors:
  - code: policy_denied
    message_contains: "read_only"
```

### NATS request with no responders
Tool: `nats.request`
```yaml
soft_errors:
  - code: execution_failed
    message_contains: "no responders"
```

### RabbitMQ missing queue
Tools: `rabbit.queue_info`, `rabbit.consume`
```yaml
soft_errors:
  - code: execution_failed
    message_contains: "not_found"
```

### Git tools without repository
Tools: all `git.*`
```yaml
soft_errors:
  - code: git_repo_error
  - code: execution_failed
    message_contains: "not a git repository"
```
When matched, the runner sets `git_repo_ready=False` for the remainder of
the run.

### git.push (always expected to fail)
```yaml
soft_errors:
  - code: policy_denied
  - code: execution_failed
  - code: git_repo_error
```
Push targets `upstream` which is not in `allowed_git_remotes`, so policy
denial is the expected path.

## Adding a soft error for a new tool

Add a `soft_errors` list to the tool's entry in `tool_catalog.yaml`:
```yaml
- name: new.tool
  args: {...}
  soft_errors:
    - code: expected_error_code
      message_contains: "substring"
```

## Validation in evidence

In `EVIDENCE_JSON`:
1. Soft-error invocations appear with their original error codes.
2. The test final status is `passed` despite these expected failures.
3. No `error_message` is set for soft-error cases.
