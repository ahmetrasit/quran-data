#!/usr/bin/env python3
"""Resolve dictionary identities without promoting noisy occurrence targets."""
import argparse
import csv
import hashlib
import json
import sqlite3
import sys
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/dictionary"))
from supplemental import transferred_registry

def build(furuq_db):
    bridge = ROOT / "data/bridges/qac-furuq-v4-root-map.tsv"
    aliases_path = ROOT / "data/bridges/qac-dictionary-reviewed-aliases.json"
    aliases = {r["qacRoot"]: r for r in json.loads(aliases_path.read_bytes())["aliases"]}
    by_root = defaultdict(list)
    frozen_ids = set()
    with sqlite3.connect(furuq_db) as connection:
        for root_id, root in connection.execute("SELECT root_id, root_norm FROM roots ORDER BY root_id"):
            by_root[root].append(root_id)
            frozen_ids.add(root_id)
        for alias in aliases.values():
            root_id, branch_id = alias["branchRef"].split("/")
            phrase = connection.execute("SELECT source_phrase_ar FROM branch_images WHERE root_id=? AND branch_id=?", (root_id, branch_id)).fetchone()
            if (root_id not in alias["rootIds"] or not phrase
                    or hashlib.sha256(phrase[0].encode()).hexdigest() != alias["sourcePhraseSha256"]):
                raise ValueError(f"Reviewed alias evidence drift: {alias['qacRoot']}")
    supplement = transferred_registry()
    if supplement:
        _, registry, intakes = supplement
        for row in registry["entries"]:
            root_id = row["id"]
            if row["kind"] != "lexical_root":
                continue
            root = intakes[root_id]["rootArabic"]
            if root_id in frozen_ids or by_root[root]:
                raise ValueError(f"Supplemental root collides with frozen registry: {root_id}/{root}")
            by_root[root].append(root_id)
    available = {root for p in (ROOT / "data/dictionary/tr").glob("root_*_entry.json")
                 for root in p.name.removesuffix("_entry.json").split("--")}
    rows = []
    with bridge.open(newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            root = row["qac_root_norm"]
            alias = aliases.get(root)
            ids = alias["rootIds"] if alias else by_root[root]
            observed = list(dict.fromkeys(target.split("=>")[1] for target in row["targets"].split("|") if target and target.split("=>")[1]))
            rows.append({"qacRoot": root, "qacRootJoinKey": root.replace(" ", ""),
                         "rootIds": ids, "resolution": "reviewed_alias" if alias else "exact_root" if ids else "unresolved_identity",
                         "observedTargetIds": observed, "withheldTargetIds": [i for i in observed if i not in ids],
                         "missingEntryRootIds": [i for i in ids if i not in available]})
    return {"schemaVersion": "qac-dictionary-root-resolutions-v1",
            "policy": "Exact Arabic QAC root identity or an evidence-bound reviewed alias. Occurrence disagreements are discovery evidence only.",
            "bridgeSha256": hashlib.sha256(bridge.read_bytes()).hexdigest(),
            "furuqSha256": hashlib.sha256(furuq_db.read_bytes()).hexdigest(),
            "reviewedAliasesSha256": hashlib.sha256(aliases_path.read_bytes()).hexdigest(),
            "rootCount": len(rows), "counts": dict(Counter(r["resolution"] for r in rows)), "roots": rows}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--furuq-db", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = build(args.furuq_db)
    output = ROOT / "data/bridges/qac-dictionary-root-resolutions.json"
    data = (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode()
    if args.check:
        if output.read_bytes() != data: raise ValueError("Dictionary root resolutions are stale")
    else: output.write_bytes(data)
    print(json.dumps({"roots": result["rootCount"], "counts": result["counts"],
                      "missingEntries": sum(bool(r["missingEntryRootIds"]) for r in result["roots"]),
                      "withheldTargets": sum(len(r["withheldTargetIds"]) for r in result["roots"])}))

if __name__ == "__main__": main()
