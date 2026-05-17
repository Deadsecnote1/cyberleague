#!/usr/bin/env python3
"""Sync workflow entity connections and history after node renames."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

WF_ID = Path(__file__).resolve().parents[1] / ".workflow_id"
DB = Path.home() / ".n8n" / "database.sqlite"
ROOT = "/home/thanushiyan/Desktop/buildathon_cursor"

def fix_connections(connections: dict, nodes: list) -> dict:
    """Rebuild connections using current node names."""
    name_map = {
        "Start Scan": "Scan from CSV",
        "Load Targets (CSV)": "Load Vulnerable Targets",
    }
    fixed = {}
    for key, value in connections.items():
        new_key = name_map.get(key, key)
        new_main = []
        for outputs in value.get("main", []):
            new_outputs = []
            for link in outputs:
                new_link = {**link, "node": name_map.get(link["node"], link["node"])}
                new_outputs.append(new_link)
            new_main.append(new_outputs)
        fixed[new_key] = {"main": new_main}
    return fixed


def main() -> None:
    wf_id = WF_ID.read_text().strip()
    conn = sqlite3.connect(DB)
    nodes = json.loads(conn.execute("SELECT nodes FROM workflow_entity WHERE id=?", (wf_id,)).fetchone()[0])
    connections = json.loads(
        conn.execute("SELECT connections FROM workflow_entity WHERE id=?", (wf_id,)).fetchone()[0]
    )

    for node in nodes:
        if node["name"] == "Loop Targets":
            node["parameters"] = {"batchSize": 1, "options": {}}

    connections = fix_connections(connections, nodes)

    if "Scan from CSV" not in connections:
        connections["Scan from CSV"] = connections.pop("Start Scan", {"main": [[]]})
    if "Load Vulnerable Targets" not in connections.get("Scan from CSV", {}).get("main", [[]])[0]:
        connections["Scan from CSV"] = {
            "main": [[{"node": "Load Vulnerable Targets", "type": "main", "index": 0}]]
        }
        connections["Load Vulnerable Targets"] = {
            "main": [[{"node": "Parse Target List", "type": "main", "index": 0}]]
        }

    trigger_count = sum(1 for n in nodes if "Trigger" in n.get("type", ""))

    conn.execute(
        """UPDATE workflow_entity
           SET nodes=?, connections=?, updatedAt=datetime('now'),
               versionCounter=versionCounter+1, triggerCount=?
           WHERE id=?""",
        (json.dumps(nodes), json.dumps(connections), trigger_count, wf_id),
    )

    hist = conn.execute(
        "SELECT versionId FROM workflow_history WHERE workflowId=? ORDER BY createdAt DESC LIMIT 1",
        (wf_id,),
    ).fetchone()
    if hist:
        conn.execute(
            "UPDATE workflow_history SET nodes=?, connections=? WHERE workflowId=? AND versionId=?",
            (json.dumps(nodes), json.dumps(connections), wf_id, hist[0]),
        )

    conn.commit()
    print("synced", wf_id)
    print("triggers:", [n["name"] for n in nodes if "Trigger" in n["type"]])


if __name__ == "__main__":
    main()
