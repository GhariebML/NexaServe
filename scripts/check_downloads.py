import os
import shutil

p = os.path.expanduser("~/Downloads")
if os.path.exists(p):
    total = sum(os.path.getsize(os.path.join(root, f)) for root, _, files in os.walk(p) for f in files)
    print(f"Downloads folder: {total / (1024**3):.2f} GB")
else:
    print("Downloads not found")
