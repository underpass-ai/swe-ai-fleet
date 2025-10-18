# API Definitions - SWE AI Fleet

This directory contains all Protocol Buffer API definitions for SWE AI Fleet microservices.

## Directory Structure

```
specs/
├── fleet/                      # All service APIs
│   ├── context/v1/
│   ├── orchestrator/v1/
│   ├── ray_executor/v1/
│   ├── planning/v1/
│   ├── storycoach/v1/
│   └── workspace/v1/
├── buf.yaml                   # Buf configuration
├── buf.gen.yaml              # Code generation config
├── VERSION                   # Current API version
└── README.md                 # This file
```

## Version

Current API version: **v1.0.0**

## Namespace Convention

All services use `fleet.<service>.v<major>`:

- `fleet.context.v1`
- `fleet.orchestrator.v1`
- `fleet.ray_executor.v1`
- `fleet.planning.v1`
- `fleet.storycoach.v1`
- `fleet.workspace.v1`

## Usage

```bash
# Validate
cd specs && buf lint

# Check breaking changes
buf breaking --against '.git#branch=main'

# Generate code
buf generate
```

## Documentation

- [API Versioning Strategy](../docs/API_VERSIONING_STRATEGY.md)
- [Tooling Setup](../docs/TOOLING_SETUP.md)
