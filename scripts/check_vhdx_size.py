import os

path = r'C:\Users\LAPTOPS HOUSE\AppData\Local\Docker\wsl\main\ext4.vhdx'
if os.path.exists(path):
    size_gb = os.path.getsize(path) / (1024**3)
    print(f"VHDX Size: {size_gb:.2f} GB")
else:
    print("Path does not exist")
