import importlib
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.e2e


def _load_yaml(path: Path) -> dict[str, Any]:
    # soft import to avoid hard dep for unit jobs
    yaml = importlib.import_module("yaml")
    return yaml.safe_load(path.read_text())


def test_cluster_from_yaml_e2e():
    # This test assumes repo layout with examples/ present.
    example = Path("examples/cluster_from_yaml/input.yaml")
    if not example.exists():
        pytest.skip("example YAML missing; run locally")
    try:
        _ = importlib.import_module("yaml")
    except ModuleNotFoundError:
        pytest.skip("PyYAML not installed; run locally with 'pip install pyyaml'")

    spec = _load_yaml(example)
    # Build a synthetic 'task' for the council from the spec
    apps = spec.get("applications", [])
    app_names = ", ".join(a["name"] for a in apps)
    task = f"deploy cluster {spec.get('cluster_name')} with apps: {app_names}"

    # Import late to avoid import cost when skipped
    from swe_ai_fleet.orchestrator.architect import ArchitectAgent, ArchitectSelector
    from swe_ai_fleet.orchestrator.config import RoleConfig, SystemConfig
    from swe_ai_fleet.orchestrator.council import Agent, PeerCouncil, Tooling
    from swe_ai_fleet.orchestrator.router import Router
    from swe_ai_fleet.tools.validators import kube_lint_stub

    class GenAgent(Agent):
        def generate(self, task, constraints, diversity):
            # Return a fake multi-doc manifest for all apps
            return {
                "content": (
                    f"# plan for: {task}\n"
                    "---\n"
                    "apiVersion: v1\n"
                    "kind: ConfigMap\n"
                    "metadata:\n"
                    "  name: demo"
                )
            }

        def critique(self, proposal, rubric):
            return "ok"

        def revise(self, content, feedback):
            return content

    council = PeerCouncil(agents=[GenAgent()], tooling=Tooling(), rounds=1)
    architect = ArchitectSelector(architect=ArchitectAgent())
    cfg = SystemConfig(
        roles=[RoleConfig(name="devops", replicas=1, model_profile="devops")],
        require_human_approval=True,
    )
    router = Router(config=cfg, councils={"devops": council}, architect=architect)

    res = router.dispatch(role="devops", task=task, constraints={"architect_rubric": {"k": 1}})
    assert "winner" in res and isinstance(res["winner"], str)
    # Validate winner with validators stub
    ok = kube_lint_stub(res["winner"]).get("ok", False)
    assert ok is True
