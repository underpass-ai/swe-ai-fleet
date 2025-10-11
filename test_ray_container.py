#!/usr/bin/env python3
"""
Test Ray container with VLLMAgentJob.
Connects to Ray running in container and executes a simple job.
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import ray  # noqa: E402

print("🔧 Connecting to Ray server at localhost:36379...")

# Connect to Ray in container (direct connection to GCS port)
ray.init(address="localhost:36379", ignore_reinit_error=True)

print("✅ Connected to Ray!")
print(f"   Ray version: {ray.__version__}")
print(f"   Available resources: {ray.available_resources()}")

# Test simple Ray job
@ray.remote
def hello_ray(name):
    return f"Hello from Ray, {name}!"

# Execute
result_ref = hello_ray.remote("Tirso")
result = ray.get(result_ref)

print("\n✅ Ray job executed successfully!")
print(f"   Result: {result}")

# Shutdown
ray.shutdown()

print("\n🎉 Ray container is working perfectly!")

