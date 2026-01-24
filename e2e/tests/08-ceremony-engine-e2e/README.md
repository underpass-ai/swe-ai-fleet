## E2E Test: Ceremony Engine (E0)

This E2E test runs the `core/ceremony_engine` against multiple YAML-defined
ceremonies and verifies that:
- steps execute successfully with the built-in step handlers
- transitions happen according to guards
- the ceremony reaches a terminal state

### Ceremony Inputs
- `CEREMONY_NAMES` (comma-separated list)
  - Default: `dummy_ceremony,e2e_aggregation,e2e_human_gate,e2e_multi_step`
- `CEREMONIES_DIR`
  - Default: `/app/config/ceremonies`

### Usage
```
make build
make deploy
make logs
```
