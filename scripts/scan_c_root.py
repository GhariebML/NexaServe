import os

for root, dirs, files in os.walk(r"C:\Users\LAPTOPS HOUSE\.gemini"):
    pass

def get_dir_size(path):
    total = 0
    try:
        for root, _, files in os.walk(path):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except Exception:
                    pass
    except Exception:
        pass
    return total / (1024**3)

print("Checking large root directories on C:...")
try:
    for item in os.listdir("C:\\"):
        full = os.path.join("C:\\", item)
        if os.path.isdir(full) and item not in ('Windows', '$Recycle.Bin', 'System Volume Information'):
            sz = get_dir_size(full)
            if sz > 0.5:
                print(f"C:\\{item} : {sz:.2f} GB")
except Exception as e:
    print(e)
