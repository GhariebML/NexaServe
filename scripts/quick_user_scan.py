import os
import sys

user_dir = r"C:\Users\LAPTOPS HOUSE"
results = []
try:
    items = os.listdir(user_dir)
    for item in items:
        p = os.path.join(user_dir, item)
        if os.path.isdir(p):
            total = 0
            for root, _, files in os.walk(p):
                for f in files:
                    try:
                        total += os.path.getsize(os.path.join(root, f))
                    except Exception:
                        pass
            gb = total / (1024**3)
            results.append((item, gb))
            print(f"Directory {item}: {gb:.2f} GB", flush=True)
except Exception as e:
    print(f"Error: {e}")

results.sort(key=lambda x: x[1], reverse=True)
print("\n--- TOP DIRECTORIES ---", flush=True)
for name, gb in results[:10]:
    print(f"{gb:.2f} GB : {name}", flush=True)
