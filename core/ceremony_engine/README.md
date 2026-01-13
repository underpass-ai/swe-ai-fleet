# Ceremony Engine

Framework for declarative ceremony execution using YAML-based DSL.

## Overview

The Ceremony Engine provides a framework for defining and executing ceremonies (e.g., Sprint Planning, Daily Standups) using a declarative YAML-based Domain-Specific Language (DSL).

## Key Features

- **Declarative DSL**: Define ceremonies using YAML configuration files
- **Type-safe Domain Model**: Immutable value objects and entities with fail-fast validation
- **Fail-fast Validation**: Comprehensive validation at parse time
- **DDD + Hexagonal Architecture**: Clean separation of concerns

## Structure

```
core/ceremony_engine/
├── domain/              # Domain layer (entities, value objects)
│   ├── entities/        # Aggregate roots
│   └── value_objects/   # Value objects (State, Transition, Step, etc.)
├── infrastructure/      # Infrastructure layer (adapters, mappers)
│   └── yaml_validator.py  # YAML parser and validator
└── tests/               # Unit tests
```

## Usage

```python
from core.ceremony_engine.infrastructure.yaml_validator import CeremonyDefinitionValidator

# Load ceremony definition from YAML file
definition = CeremonyDefinitionValidator.validate_and_parse_from_file(
    "config/ceremonies/dummy_ceremony.yaml"
)

# Access ceremony components
initial_state = definition.get_initial_state()
steps = definition.steps
transitions = definition.transitions
```

## DSL Specification

See `tmp_docs/E0_CEREMONY_ENGINE/E0.1_DSL_YAML_CEREMONIAS.md` for complete DSL specification.

## Example

See `config/ceremonies/dummy_ceremony.yaml` for a minimal working example.

## Testing

```bash
# Run all tests
pytest core/ceremony_engine/tests/

# Run specific test file
pytest core/ceremony_engine/tests/unit/domain/value_objects/test_state.py
```
