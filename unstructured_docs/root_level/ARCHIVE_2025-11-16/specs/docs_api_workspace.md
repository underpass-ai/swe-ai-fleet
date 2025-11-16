# Workspace Service API

**Package**: `fleet.workspace.v1`  
**Version**: v1  
**Generated**: 2025-10-31

---

## Full Protocol Definition

<details>
<summary>Click to expand full proto definition</summary>

```protobuf
syntax = "proto3";
package fleet.workspace.v1;

option go_package = "github.com/underpass-ai/swe-ai-fleet/services/workspace/gen/fleet/workspace/v1;workspacev1";

// WorkspaceService manages scoring of containerized agent workspaces
service WorkspaceService {
  rpc ScoreWorkspace (ScoreWorkspaceRequest) returns (ScoreWorkspaceResponse);
}

message ScoreWorkspaceRequest {
  string job_id = 1;
  WorkspaceReport report = 2;
  string rigor_level = 3; // L0, L1, L2, L3
}

message WorkspaceReport {
  string job_id = 1;
  string commit = 2;
  BuildResult build = 3;
  UnitResult unit = 4;
  StaticResult static = 5;
  E2EResult e2e = 6;
  PRResult pr = 7;
  Timings timings = 8;
}

message BuildResult {
  bool ok = 1;
}

message UnitResult {
  bool ok = 1;
  int32 passed = 2;
  int32 failed = 3;
  float coverage = 4;
}

message StaticResult {
  bool ok = 1;
  SonarResult sonar = 2;
}

message SonarResult {
  string project_key = 1;
  string quality_gate = 2; // OK, WARN, ERROR, NONE
  int32 new_critical = 3;
  int32 new_major = 4;
}

message E2EResult {
  bool ok = 1;
  int32 passed = 2;
  int32 failed = 3;
}

message PRResult {
  string url = 1;
}

message Timings {
  int32 total_ms = 1;
}

message ScoreWorkspaceResponse {
  int32 score = 1; // 0-100
  string rigor = 2;
  repeated string reasons = 3; // Human-readable pass/fail reasons per dimension
  string gating_decision = 4; // pass, warn, block
}
```

</details>

---

## Quick Start

```python
from fleet.workspace.v1 import workspace_pb2, workspace_pb2_grpc
```

```go
import "github.com/underpass-ai/swe-ai-fleet/gen/fleet/workspace/v1"
```

---

*This documentation is auto-generated from `specs/fleet/workspace/v1/workspace.proto`*
