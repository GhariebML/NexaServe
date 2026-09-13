import os

targets = [
    r"C:\Users\LAPTOPS HOUSE\.ollama",
    r"C:\Users\LAPTOPS HOUSE\.antigravity",
    r"C:\Users\LAPTOPS HOUSE\.gemini",
    r"C:\Users\LAPTOPS HOUSE\.cache",
    r"C:\Users\LAPTOPS HOUSE\AppData\Local",
    r"C:\Users\LAPTOPS HOUSE\AppData\Roaming",
    r"C:\Users\LAPTOPS HOUSE\Deep_Learning_Mastercourse",
    r"C:\Users\LAPTOPS HOUSE\OneDrive",
]

for t in targets:
    if os.path.exists(t):
        total = 0
        for root, _, files in os.walk(t):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except Exception:
                    pass
        print(f"{total / (1024**3):.2f} GB : {t}")
