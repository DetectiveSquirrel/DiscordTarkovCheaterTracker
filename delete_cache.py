import os
import shutil

for root, dirs, files in os.walk("."):
    for dir in dirs:
        if dir == "__pycache__":
            pycache_path = os.path.join(root, dir)
            shutil.rmtree(pycache_path)
            print(f"Deleted {pycache_path}")
