import ray, torch, os
ray.init()

@ray.remote(num_gpus=2)
def torch_probe():
    return dict(
        visible=os.environ.get("CUDA_VISIBLE_DEVICES", ""),
        cuda_is_available=torch.cuda.is_available(),
        device_count=torch.cuda.device_count(),
        name=torch.cuda.get_device_name(0) if torch.cuda.is_available() else "N/A",
    )

print(ray.get(torch_probe.remote()))
ray.shutdown()

