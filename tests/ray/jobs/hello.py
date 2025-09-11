#!/usr/bin/env python3
import platform
import socket
import time

import ray

ray.init()
print(f"Hello from Ray! host={socket.gethostname()} python={platform.python_version()}")
@ray.remote
def f(x): return x * x
print("sum:", sum(ray.get([f.remote(i) for i in range(10)])))
time.sleep(1)

