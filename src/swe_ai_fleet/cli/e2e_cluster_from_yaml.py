from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Any

import yaml

from swe_ai_fleet.orchestrator.architect import ArchitectAgent, ArchitectSelector
from swe_ai_fleet.orchestrator.council import Agent, PeerCouncil, Tooling

# ---------- Domain DTOs ----------


@dataclass(frozen=True)
class AppSpec:
    name: str
    image: str
    replicas: int = 1
    persistent_volume: bool = False


@dataclass(frozen=True)
class ClusterSpec:
    cluster_name: str
    nodes: int
    applications: list[AppSpec]


# ---------- Simple YAML Manifest generator (K8s) ----------


def render_deployment(app: AppSpec, namespace: str = "default") -> str:
    # Minimal K8s Deployment manifest; intentionally simple for the PoC.
    container_name = app.name
    return f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {app.name}
  namespace: {namespace}
  labels:
    app: {app.name}
spec:
  replicas: {app.replicas}
  selector:
    matchLabels:
      app: {app.name}
  template:
    metadata:
      labels:
        app: {app.name}
    spec:
      containers:
        - name: {container_name}
          image: {app.image}
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 8080
          readinessProbe:
            httpGet:
              path: /
              port: 8080
            initialDelaySeconds: 3
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /healthz
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 10
"""


def render_service(app: AppSpec, namespace: str = "default") -> str:
    return f"""apiVersion: v1
kind: Service
metadata:
  name: {app.name}
  namespace: {namespace}
spec:
  type: ClusterIP
  selector:
    app: {app.name}
  ports:
    - name: http
      port: 80
      targetPort: 8080
"""


# ---------- Mock Developer Agents (diversity via minor variations) ----------


class DevAgentA(Agent):
    def generate(self, task: str, constraints: dict[str, Any], diversity: bool) -> dict[str, Any]:
        spec: ClusterSpec = constraints["cluster_spec"]
        manifests = []
        for app in spec.applications:
            manifests.append(render_deployment(app))
            manifests.append(render_service(app))
        return {"author": "DevA", "content": "\n---\n".join(manifests)}

    def critique(self, proposal: str, rubric: dict[str, Any]) -> str:
        # Minimal heuristic critique.
        notes = []
        if "livenessProbe" not in proposal:
            notes.append("Add livenessProbe for containers.")
        if "readinessProbe" not in proposal:
            notes.append("Add readinessProbe for containers.")
        return "\n".join(notes) or "OK"

    def revise(self, content: str, feedback: str) -> str:
        return content  # Keep simple; real impl would patch YAML per feedback.


class DevAgentB(DevAgentA):
    def generate(self, task: str, constraints: dict[str, Any], diversity: bool) -> dict[str, Any]:
        # Variation: use NodePort for the first service.
        spec: ClusterSpec = constraints["cluster_spec"]
        manifests = []
        for idx, app in enumerate(spec.applications):
            manifests.append(render_deployment(app))
            if idx == 0:
                svc = render_service(app).replace("type: ClusterIP", "type: NodePort")
                manifests.append(svc)
            else:
                manifests.append(render_service(app))
        return {"author": "DevB", "content": "\n---\n".join(manifests)}


class DevAgentC(DevAgentA):
    def generate(self, task: str, constraints: dict[str, Any], diversity: bool) -> dict[str, Any]:
        # Variation: change port mapping to 8081 target on services (minor diff)
        spec: ClusterSpec = constraints["cluster_spec"]
        manifests = []
        for app in spec.applications:
            manifests.append(render_deployment(app))
            svc = render_service(app).replace("targetPort: 8080", "targetPort: 8081")
            manifests.append(svc)
        return {"author": "DevC", "content": "\n---\n".join(manifests)}


# ---------- Architect ----------


class SimpleArchitect(ArchitectAgent):
    # Uses tool telemetry default selection (highest OK signals); could call a strong LLM later.
    pass


# ---------- CLI ----------


def parse_cluster_spec(path: str) -> ClusterSpec:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    apps = [AppSpec(**a) for a in data.get("applications", [])]
    return ClusterSpec(
        cluster_name=data["cluster_name"], nodes=int(data["nodes"]), applications=apps
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="[Legacy PoC] SWE AI Fleet E2E: cluster-from-yaml")
    parser.add_argument("--spec", required=True, help="Path to YAML spec (cluster/apps)")
    parser.add_argument("--dry-run", action="store_true", help="Perform only dry-run validations")
    args = parser.parse_args()

    cluster_spec = parse_cluster_spec(args.spec)

    agents: list[Agent] = [DevAgentA(), DevAgentB(), DevAgentC()]
    tooling = Tooling()
    council = PeerCouncil(agents=agents, tooling=tooling, rounds=1)
    architect = SimpleArchitect()
    selector = ArchitectSelector(architect=architect)

    constraints: dict[str, Any] = {
        "rubric": {"k8s": "basic-probes, service-exposure minimal"},
        "architect_rubric": {"k": 3},
        "cluster_spec": cluster_spec,
    }

    ranked = council.deliberate(
        task="Generate K8s manifests for applications", constraints=constraints
    )
    decision = selector.choose(ranked, rubric=constraints["architect_rubric"])

    print("# SWE AI Fleet E2E Result")
    print("Winner manifest (truncated to 1500 chars):\n")
    winner = decision["winner"]
    print(winner[:1500] + ("..." if len(winner) > 1500 else ""))

    if args.dry_run:
        # In a later step we will perform `kubectl apply --dry-run=server` here.
        print("\n(DRY-RUN) Skipping kubectl apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
