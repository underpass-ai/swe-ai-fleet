#!/usr/bin/env python3
import os
import subprocess

import ray

ray.init()

@ray.remote(num_gpus=1)
def gpu_task():
    vis = os.environ.get("CUDA_VISIBLE_DEVICES","")
    cmd = ["nvidia-smi", "-i", vis or "0",
           "--query-gpu=index,name,uuid,memory.total",
           "--format=csv,noheader"]
    out = subprocess.check_output(cmd, text=True)
    return {"visible": vis, "nvidia_smi": out.strip()}

print(ray.get(gpu_task.remote()))

