import subprocess

sql_file = "infra/postgres/expand-faqs.sql"
with open(sql_file, "rb") as f:
    sql_bytes = f.read()

cmd = ["docker", "exec", "-i", "cs-postgres", "psql", "-U", "postgres", "-d", "customerservice"]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
out, err = p.communicate(input=sql_bytes)
print("STDOUT:", out.decode("utf-8", errors="replace"))
print("STDERR:", err.decode("utf-8", errors="replace"))
print("Return code:", p.returncode)
