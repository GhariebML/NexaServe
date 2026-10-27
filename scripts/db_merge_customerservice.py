"""Merge operational rows from the legacy `customerservice` DB into canonical `nexaserve_final`.

Background: n8n's CS_PG_CRED_01 credential kept writing sessions, messages, tickets and audit logs to
`customerservice` while the dashboard and knowledge base moved to `nexaserve_final`. Both started as
one copy, so the merge is: insert rows that exist only in customerservice; for shared tickets the row
with the newer updated_at wins. nexaserve_final stays authoritative for the knowledge base, admin
users and reference data.

usage:
  python scripts/db_merge_customerservice.py            # dry run: analyse, merge in a transaction, ROLL BACK
  python scripts/db_merge_customerservice.py --commit   # same, then COMMIT
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

import psycopg2
import psycopg2.extras

ROOT = Path(__file__).resolve().parents[1]
SOURCE, TARGET = "customerservice", "nexaserve_final"
# FK-safe order. Knowledge base, admin users and system tables are owned by nexaserve_final.
MERGE_TABLES = ["agents", "ticket_categories", "ticket_tags", "customers", "orders", "conversations",
                "messages", "conversation_summaries", "customer_memory", "tickets", "ticket_events",
                "ticket_tag_assignments", "csat_surveys", "agent_performance", "audit_logs"]
# Shared rows: only these tables are updated in place, newest updated_at wins.
UPDATE_SHARED_BY_UPDATED_AT = {"tickets"}
# No updated_at column; the source is the live operational writer (e.g. n8n escalations set handed_off).
UPDATE_SHARED_FROM_SOURCE = {"conversations"}
# Serial ids that both DBs handed out independently after the split: a "shared" id with different
# content is a different event, so the source row is inserted with a fresh id instead of being dropped.
REINSERT_COLLIDING_SERIAL = {"audit_logs": "id"}


def env_values():
    values = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and not key.startswith("#"):
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def connect(env, db):
    return psycopg2.connect(host="127.0.0.1", port=int(env.get("POSTGRES_PORT", "5432")), dbname=db,
                            user=env["POSTGRES_USER"], password=env["POSTGRES_PASSWORD"])


def columns(cur, table):
    cur.execute("""SELECT column_name FROM information_schema.columns
                   WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position""", (table,))
    return [r[0] for r in cur.fetchall()]


def json_columns(cur, table):
    cur.execute("""SELECT column_name FROM information_schema.columns
                   WHERE table_schema='public' AND table_name=%s AND data_type IN ('json', 'jsonb')""", (table,))
    return {r[0] for r in cur.fetchall()}


def adapt(value, column, json_cols):
    """psycopg2 returns json as dict/list and arrays as list; only json values need wrapping."""
    return psycopg2.extras.Json(value) if column in json_cols and value is not None else value


def primary_key(cur, table):
    cur.execute("""SELECT a.attname FROM pg_index i
                   JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                   WHERE i.indrelid = ('public.' || quote_ident(%s))::regclass AND i.indisprimary
                   ORDER BY array_position(i.indkey, a.attnum)""", (table,))
    return [r[0] for r in cur.fetchall()]


def unique_keys(cur, table):
    """Non-primary unique indexes (column lists, partial predicate ignored -> conservative)."""
    cur.execute("""SELECT array_agg(a.attname ORDER BY array_position(i.indkey, a.attnum)), pg_get_expr(i.indpred, i.indrelid)
                   FROM pg_index i JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                   WHERE i.indrelid = ('public.' || quote_ident(%s))::regclass AND i.indisunique AND NOT i.indisprimary
                   GROUP BY i.indexrelid, i.indpred, i.indrelid""", (table,))
    return [(list(cols), pred) for cols, pred in cur.fetchall()]


def table_exists(cur, table):
    cur.execute("SELECT to_regclass(%s) IS NOT NULL", (f"public.{table}",))
    return cur.fetchone()[0]


def fetch(cur, table, cols, pk):
    cur.execute(f'SELECT {", ".join(f"""\"{c}\"""" for c in cols)} FROM public."{table}"')
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    return {tuple(str(r[k]) for k in pk): r for r in rows}


def comparable(row, cols):
    return {c: (json.dumps(row[c], sort_keys=True, default=str) if isinstance(row[c], (dict, list)) else row[c]) for c in cols}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--commit", action="store_true", help="commit the merge (default: dry run, rolled back)")
    args = parser.parse_args()
    env = env_values()
    src_conn, dst_conn = connect(env, SOURCE), connect(env, TARGET)
    src_conn.set_session(readonly=True, isolation_level="REPEATABLE READ")
    src, dst = src_conn.cursor(), dst_conn.cursor()
    report, blockers = [], []
    try:
        # Serialise with any concurrent merge run; the transaction holds it until commit/rollback.
        dst.execute("SELECT pg_advisory_xact_lock(hashtext('nexaserve-db-merge'))")
        for table in MERGE_TABLES:
            if not table_exists(src, table) or not table_exists(dst, table):
                continue
            src_cols, dst_cols = columns(src, table), columns(dst, table)
            missing_in_target = [c for c in src_cols if c not in dst_cols]
            if missing_in_target:
                blockers.append(f"{table}: source-only columns {missing_in_target}")
                continue
            common = [c for c in src_cols if c in dst_cols]
            json_cols = json_columns(dst, table)
            pk = primary_key(dst, table)
            if not pk:
                blockers.append(f"{table}: no primary key")
                continue
            source_rows, target_rows = fetch(src, table, common, pk), fetch(dst, table, common, pk)
            only_source = [k for k in source_rows if k not in target_rows]
            shared_diff = [k for k in source_rows if k in target_rows
                           and comparable(source_rows[k], common) != comparable(target_rows[k], common)]

            # Unique-key conflicts for rows we are about to insert (e.g. ticket_number, phone_number).
            conflicts = []
            for cols_, pred in unique_keys(dst, table):
                if not all(c in common for c in cols_):
                    continue
                existing = {tuple(str(r[c]) for c in cols_) for r in target_rows.values() if all(r[c] is not None for c in cols_)}
                for k in only_source:
                    value = tuple(str(source_rows[k][c]) for c in cols_)
                    if all(source_rows[k][c] is not None for c in cols_) and value in existing:
                        conflicts.append((cols_, value, k))
            if conflicts:
                blockers.append(f"{table}: {len(conflicts)} unique-key conflicts, e.g. {conflicts[:3]}")

            inserted = 0
            if not conflicts:
                for k in only_source:
                    row = source_rows[k]
                    dst.execute(f'INSERT INTO public."{table}" ({", ".join(f"""\"{c}\"""" for c in common)}) '
                                f'VALUES ({", ".join(["%s"] * len(common))})',
                                [adapt(row[c], c, json_cols) for c in common])
                    inserted += 1

            updated, kept_target, reinserted = 0, 0, 0
            if table in REINSERT_COLLIDING_SERIAL and not conflicts:
                serial = REINSERT_COLLIDING_SERIAL[table]
                insert_cols = [c for c in common if c != serial]
                # Idempotent across runs: skip events already copied under a new id.
                present = {tuple(m.items()) for m in (comparable(r, insert_cols) for r in target_rows.values())}
                for k in shared_diff:
                    row = source_rows[k]
                    if tuple(comparable(row, insert_cols).items()) in present:
                        continue
                    dst.execute(f'INSERT INTO public."{table}" ({", ".join(f"""\"{c}\"""" for c in insert_cols)}) '
                                f'VALUES ({", ".join(["%s"] * len(insert_cols))})',
                                [adapt(row[c], c, json_cols) for c in insert_cols])
                    reinserted += 1
            elif table in UPDATE_SHARED_FROM_SOURCE:
                set_cols = [c for c in common if c not in pk]
                for k in shared_diff:
                    s = source_rows[k]
                    dst.execute(f'UPDATE public."{table}" SET {", ".join(f"""\"{c}\" = %s""" for c in set_cols)} '
                                f'WHERE {" AND ".join(f"""\"{c}\"::text = %s""" for c in pk)}',
                                [adapt(s[c], c, json_cols) for c in set_cols] + list(k))
                    updated += 1
            elif table in UPDATE_SHARED_BY_UPDATED_AT and "updated_at" in common:
                for k in shared_diff:
                    s, t = source_rows[k], target_rows[k]
                    if s["updated_at"] and (t["updated_at"] is None or s["updated_at"] > t["updated_at"]):
                        set_cols = [c for c in common if c not in pk]
                        dst.execute(f'UPDATE public."{table}" SET {", ".join(f"""\"{c}\" = %s""" for c in set_cols)} '
                                    f'WHERE {" AND ".join(f"""\"{c}\"::text = %s""" for c in pk)}',
                                    [adapt(s[c], c, json_cols) for c in set_cols] + list(k))
                        updated += 1
                    else:
                        kept_target += 1
            report.append({"table": table, "source_rows": len(source_rows), "target_rows": len(target_rows),
                           "insert_from_source": inserted if not conflicts else f"blocked ({len(only_source)})",
                           "shared_different": len(shared_diff), "shared_updated_from_source": updated,
                           "shared_reinserted_new_id": reinserted,
                           "shared_target_kept": len(shared_diff) - updated - reinserted})

        # Serial ids: keep sequences ahead of merged rows.
        dst.execute("""SELECT s.schemaname, s.sequencename, d.refobjid::regclass::text, a.attname
                       FROM pg_sequences s
                       JOIN pg_class c ON c.relname = s.sequencename
                       JOIN pg_depend d ON d.objid = c.oid AND d.deptype = 'a'
                       JOIN pg_attribute a ON a.attrelid = d.refobjid AND a.attnum = d.refobjsubid
                       WHERE s.schemaname = 'public'""")
        for schema, seq, table, col in dst.fetchall():
            dst.execute(f'SELECT setval(%s, GREATEST((SELECT COALESCE(MAX("{col}"), 0) FROM {table}), 1))', (f"{schema}.{seq}",))

        print(f"{'table':24} {'source':>7} {'target':>7} {'insert':>9} {'shared≠':>8} {'upd←src':>8} {'new id':>7} {'kept tgt':>8}")
        for r in report:
            print(f"{r['table']:24} {r['source_rows']:>7} {r['target_rows']:>7} {str(r['insert_from_source']):>9} "
                  f"{r['shared_different']:>8} {r['shared_updated_from_source']:>8} {r['shared_reinserted_new_id']:>7} "
                  f"{r['shared_target_kept']:>8}")
        dst.execute("SELECT (SELECT count(*) FROM customers), (SELECT count(*) FROM conversations), "
                    "(SELECT count(*) FROM messages), (SELECT count(*) FROM tickets), (SELECT count(*) FROM audit_logs)")
        print("nexaserve_final after merge: customers=%s conversations=%s messages=%s tickets=%s audit_logs=%s" % dst.fetchone())
        for b in blockers:
            print("BLOCKER:", b)
        if blockers or not args.commit:
            dst_conn.rollback()
            print("\nDRY RUN — rolled back, nothing written." if not blockers else "\nBlockers found — rolled back.")
        else:
            dst_conn.commit()
            print(f"\nCOMMITTED at {datetime.now().isoformat(timespec='seconds')}")
    except Exception:
        dst_conn.rollback()
        raise
    finally:
        src_conn.close()
        dst_conn.close()


if __name__ == "__main__":
    main()
