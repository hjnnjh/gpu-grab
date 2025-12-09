import time
import os

print(f"Task running on GPU: {os.environ.get('CUDA_VISIBLE_DEVICES')}")
time.sleep(10)
print("Task completed")
