"""Data-level backup of a PostgreSQL database without pg_dump (e.g. while Docker's CLI is unavailable).

Writes every public table as CSV (COPY ... WITH CSV HEADER) plus schema.json describing columns,
constraints, indexes and sequence positions, and a SHA-256 manifest. Restore = recreate the schema
(infra/postgres/schema.sql + deployment/migrations) and COPY each CSV back in FK order.

usage: python scripts/csv_db_backup.py DBNAME OUT_DIR
"""
import hashlib
import json
import sys
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parents[1]


def env_values():
    values = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and not key.startswith("#"):
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def main(dbname: str, out_dir: Path) -> None:
    env = env_values()
    out_dir.mkdir(parents=True, exist_ok=False)
    conn = psycopg2.connect(host="127.0.0.1", port=int(env.get("POSTGRES_PORT", "5432")), dbname=dbname,
                            user=env["POSTGRES_USER"], password=env["POSTGRES_PASSWORD"])
    conn.set_session(readonly=True, isolation_level="REPEATABLE READ")  # one consistent snapshot
    cur = conn.cursor()
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
    tables = [r[0] for r in cur.fetchall()]
    schema = {"database": dbname, "tables": {}}
    for table in tables:
        cur.execute("""SELECT column_name, data_type, udt_name, is_nullable, column_default
                       FROM information_schema.columns WHERE table_schema='public' AND table_name=%s
                       ORDER BY ordinal_position""", (table,))
        columns = [dict(zip(("name", "data_type", "udt", "nullable", "default"), r)) for r in cur.fetchall()]
        cur.execute("""SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
                       WHERE conrelid = ('public.' || quote_ident(%s))::regclass ORDER BY conname""", (table,))
        constraints = dict(cur.fetchall())
        cur.execute("SELECT indexname, indexdef FROM pg_indexes WHERE schemaname='public' AND tablename=%s ORDER BY 1", (table,))
        indexes = dict(cur.fetchall())
        path = out_dir / f"{table}.csv"
        with path.open("w", encoding="utf-8", newline="") as fh:
            cur.copy_expert(f'COPY public."{table}" TO STDOUT WITH (FORMAT csv, HEADER true)', fh)
        cur.execute(f'SELECT count(*) FROM public."{table}"')
        schema["tables"][table] = {"rows": cur.fetchone()[0], "columns": columns,
                                   "constraints": constraints, "indexes": indexes}
    cur.execute("""SELECT sequencename, last_value FROM pg_sequences WHERE schemaname='public' ORDER BY 1""")
    schema["sequences"] = dict(cur.fetchall())
    conn.close()
    (out_dir / "schema.json").write_text(json.dumps(schema, indent=2, default=str), encoding="utf-8")
    manifest = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}" for p in sorted(out_dir.iterdir())]
    (out_dir / "SHA256SUMS").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    total = sum(t["rows"] for t in schema["tables"].values())
    print(f"{dbname}: {len(tables)} tables, {total} rows -> {out_dir}")


if __name__ == "__main__":
    main(sys.argv[1], Path(sys.argv[2]))
