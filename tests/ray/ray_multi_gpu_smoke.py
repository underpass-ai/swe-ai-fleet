import os

import ray

ray.init()

@ray.remote(num_gpus=1)
def which_gpu():
    return os.environ.get("CUDA_VISIBLE_DEVICES", "")

print(ray.get([which_gpu.remote() for _ in range(2)]))  # esperado algo como ['0','1']
ray.shutdown()
