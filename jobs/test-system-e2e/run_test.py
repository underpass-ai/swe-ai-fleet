#!/usr/bin/env python3
"""
System E2E Test Runner (in-cluster)

This runner:
- Ensures Python deps are available (image provides them)
- Generates gRPC stubs from specs into /app/gen (runtime build phase)
- Sets PYTHONPATH to include /app so tests can `from gen import ...`
- Executes tests/e2e/test_system_e2e.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"


def generate_stubs(specs_root: Path, gen_root: Path) -> None:
    """Generate protobuf Python stubs for orchestrator (and ray executor if present).

    The test imports `from gen import orchestrator_pb2, orchestrator_pb2_grpc`, so we
    generate into `gen_root` and ensure an __init__.py exists.
    """
    print(f"{BLUE}📦 Generating protobuf stubs...{RESET}")

    orchestrator_proto_dir = specs_root / "fleet" / "orchestrator" / "v1"
    ray_exec_proto_dir = specs_root / "fleet" / "ray_executor" / "v1"

    gen_root.mkdir(parents=True, exist_ok=True)

    # Build command with optional ray executor if proto exists
    proto_args = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        f"--proto_path={orchestrator_proto_dir}",
        f"--python_out={gen_root}",
        f"--grpc_python_out={gen_root}",
        f"--pyi_out={gen_root}",
        "orchestrator.proto",
    ]

    ray_proto = ray_exec_proto_dir / "ray_executor.proto"
    if ray_proto.exists():
        proto_args.extend([
            f"--proto_path={ray_exec_proto_dir}",
            str(ray_proto),
        ])

    try:
        subprocess.run(proto_args, check=True, cwd=orchestrator_proto_dir)
    except subprocess.CalledProcessError as exc:
        print(f"{YELLOW}⚠️  Failed to generate stubs: {exc}{RESET}")
        print("   Continuing; tests may fail if stubs are missing.")

    # Fix imports in generated *_grpc.py files to be package-relative
    try:
        import fileinput
        import glob

        for file_path in glob.glob(str(gen_root / "*_grpc.py")):
            with fileinput.FileInput(file_path, inplace=True) as f:
                for line in f:
                    line = line.replace(
                        "import orchestrator_pb2", "from . import orchestrator_pb2"
                    ).replace(
                        "import ray_executor_pb2", "from . import ray_executor_pb2"
                    )
                    print(line, end="")
    except Exception as exc:  # pragma: no cover
        print(f"{YELLOW}⚠️  Failed to adjust grpc imports: {exc}{RESET}")

    # Ensure package init exists
    init_file = gen_root / "__init__.py"
    if not init_file.exists():
        init_file.write_text(
            'from . import orchestrator_pb2, orchestrator_pb2_grpc\n'
            'try:\n'
            '    from . import ray_executor_pb2, ray_executor_pb2_grpc\n'
            'except Exception:\n'
            '    pass\n'
            "__all__ = [\"orchestrator_pb2\", \"orchestrator_pb2_grpc\", \"ray_executor_pb2\", \"ray_executor_pb2_grpc\"]\n"
        )

    print(f"{GREEN}✓ Protobuf stubs ready under {gen_root}{RESET}")


def run_test_script(test_path: Path) -> int:
    """Execute the E2E script directly and return its exit code.

    The migration guide's example accommodates non-pytest scripts; this file
    (`tests/e2e/test_system_e2e.py`) defines an async main and exits with code.
    """
    print()
    print(f"{BLUE}🧪 Running E2E test: {test_path}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")

    result = subprocess.run(
        [
            sys.executable,
            str(test_path),
        ],
        cwd=Path("/app"),
    )

    print(f"{BLUE}{'='*70}{RESET}")
    if result.returncode == 0:
        print(f"{GREEN}✅ Test PASSED!{RESET}")
    else:
        print(f"{RED}❌ Test FAILED with exit code {result.returncode}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")

    return result.returncode


def main() -> None:
    print(f"{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}🚀 System E2E Test Runner{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")

    # Ensure PYTHONPATH has /app so `gen` is importable
    os.environ["PYTHONPATH"] = "/app" + os.pathsep + os.environ.get("PYTHONPATH", "")

    # Display env used by tests
    print(f"{BLUE}Environment:{RESET}")
    print(
        "  ORCHESTRATOR_ADDRESS=",
        os.getenv("ORCHESTRATOR_ADDRESS", "orchestrator.swe-ai-fleet.svc.cluster.local:50055"),
    )
    print(
        "  RAY_EXECUTOR_ADDRESS=",
        os.getenv("RAY_EXECUTOR_ADDRESS", "ray_executor.swe-ai-fleet.svc.cluster.local:50056"),
    )
    print(
        "  NATS_URL=",
        os.getenv("NATS_URL", "nats://nats.swe-ai-fleet.svc.cluster.local:4222"),
    )

    # Generate stubs at runtime from specs packaged into the image
    specs_dir = Path("/app/specs")
    gen_dir = Path("/app/gen")
    generate_stubs(specs_dir, gen_dir)

    # Ensure the test file exists inside image
    test_file = Path("/app/tests/e2e/test_system_e2e.py")
    if not test_file.exists():
        print(f"{RED}❌ Test file not found: {test_file}{RESET}")
        sys.exit(1)

    exit_code = run_test_script(test_file)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()


