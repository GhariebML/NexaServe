import os

def find_large_dirs(start_dir, min_size_gb=1.0):
    for root, dirs, files in os.walk(start_dir):
        total_size = 0
        for f in files:
            try:
                fp = os.path.join(root, f)
                total_size += os.path.getsize(fp)
            except Exception:
                pass
        size_gb = total_size / (1024**3)
        if size_gb >= min_size_gb:
            print(f"{size_gb:.2f} GB: {root}")

user_home = r"C:\Users\LAPTOPS HOUSE"
print(f"Scanning large directories in {user_home}...")
for item in os.listdir(user_home):
    full_p = os.path.join(user_home, item)
    if os.path.isdir(full_p) and not item.startswith('.'):
        try:
            total = sum(os.path.getsize(os.path.join(dirpath, f)) for dirpath, _, filenames in os.walk(full_p) for f in filenames)
            gb = total / (1024**3)
            if gb > 1.0:
                print(f"  -> {item}: {gb:.2f} GB")
        except Exception:
            pass
