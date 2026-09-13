import os
import shutil

for drive in ['C', 'D', 'E']:
    try:
        total, used, free = shutil.disk_usage(f"{drive}:\\")
        print(f"Drive {drive}: Total: {total/(1024**3):.1f} GB, Used: {used/(1024**3):.1f} GB, Free: {free/(1024**3):.2f} GB")
    except Exception as e:
        print(f"Drive {drive}: {e}")
