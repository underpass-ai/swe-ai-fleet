# API Changelog - SWE AI Fleet

All notable changes to the API specifications will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial API versioning system
- buf-based validation and breaking change detection
- OCI artifact publishing workflow

## [1.0.0] - 2025-10-30

### Added
- Context Service API (fleet.context.v1)
- Orchestrator Service API (fleet.orchestrator.v1)
- Ray Executor Service API (fleet.ray_executor.v1)
- Planning Service API (fleet.planning.v1)
- StoryCoach Service API (fleet.storycoach.v1)
- Workspace Service API (fleet.workspace.v1)

### Fixed
- Standardized all package names to use `fleet.<service>.v1` convention
- Added `go_package` options to all proto definitions
- Configured buf linting and breaking change detection

[Unreleased]: https://github.com/underpass-ai/swe-ai-fleet/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/underpass-ai/swe-ai-fleet/releases/tag/v1.0.0



