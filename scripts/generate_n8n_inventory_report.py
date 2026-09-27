"""Generate a read-only inventory of live n8n workflow records."""
import json
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sql = """SELECT json_agg(json_build_object('id',id,'name',name,'active',active,'version',\"versionId\",'version_counter',\"versionCounter\",'updated_at',\"updatedAt\") ORDER BY name,id) FROM workflow_entity"""
raw = subprocess.check_output(
    ["docker", "exec", "cs-postgres", "psql", "-U", "postgres", "-d", "n8n", "-Atc", sql],
    text=True,
    encoding="utf-8",
)
items = json.loads(raw)
counts = Counter(item["name"] for item in items)
used_by = {
    "CSWF000000000001": "Webhook entry; invokes session, intent, 04A/04B/04C, 06, 05",
    "CSWF000000000002": "Called by Master 01",
    "CSWF000000000003": "Called by Master 01",
    "CSWF000000000004": "Master 01 order route",
    "CSWF000000000005": "Master 01 FAQ route",
    "CSWF000000000006": "Master 01 human escalation route",
    "RWLCadRzOPjTHXVo": "Agent bridge; caller linkage not confirmed in live execution sample",
    "CSWF000000000007": "Called by Master 01 after response assembly",
    "F7kjakLJXmzBDsvS": "Called by Master 01 after response assembly",
    "CSWF000000000008": "Global error handling; retained as active",
}
lines = [
    "# n8n Workflow Inventory",
    "",
    "Live PostgreSQL snapshot at 2026-09-27 22:55 Africa/Cairo. 38 workflow records exist; 17 are active. Duplicate names are retained as records. No workflow was deleted or archived.",
    "",
    "| Workflow ID | Name | Active | Purpose / used by | Current version | Duplicate? | Required? | Safe to archive? |",
    "|---|---|---:|---|---|---|---|---|",
]
for item in items:
    name = item["name"].replace("|", "\\|").replace("\n", " ")
    active = bool(item["active"])
    usage = used_by.get(item["id"], "Caller not established by the active core workflow graph; automation/analytics support record")
    required = "Core" if item["id"] in used_by else "Unverified"
    duplicate = "Yes (same-name record exists)" if counts[item["name"]] > 1 else "No"
    safe = "No (active; usage not disproven)" if active else "Review only; no archive action taken"
    version = f"{item['version']} (counter {item['version_counter']})"
    lines.append(f"| `{item['id']}` | {name} | {'Yes' if active else 'No'} | {usage} | `{version}` | {duplicate} | {required} | {safe} |")
lines += [
    "",
    "## Notes",
    "",
    "- The active 01/02/03/04A/04B/04C/04D/05/06 records are the production customer-service path; the live 6124 trace confirms 01→02→03→04B→06→05→webhook response.",
    "- Repeated analytics, CSAT, automation, agent-management, and KB-admin workflow names have inactive and/or historical entries. Their exact producer/caller graph is not proven from the customer-service execution sample, so none is marked safe for automatic archival.",
    "- `Current version` is the live `versionId` plus n8n `versionCounter`, not a semantic release number.",
]
(ROOT / "docs" / "n8n_workflow_inventory.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Wrote live inventory for {len(items)} workflows ({sum(bool(x['active']) for x in items)} active).")
