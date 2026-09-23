#!/usr/bin/env python3
"""Audit entry identities/evidence and the complete QAC root gateway."""
import argparse
import csv
import gzip
import hashlib
import json
import sqlite3
import tempfile
from collections import Counter
from pathlib import Path

from check_turkish_entries import check

ROOT = Path(__file__).resolve().parents[2]

def audit(directory, bridge_path, tsv_path, furuq_db):
    entries, branch_count = check(directory)
    roots = set(); branch_refs = set()
    with sqlite3.connect(furuq_db) as connection:
        connection.row_factory = sqlite3.Row
        registry = {r["root_id"]: dict(r) for r in connection.execute("SELECT * FROM roots")}
        branches = {r["root_id"] + "/" + r["branch_id"]: dict(r)
                    for r in connection.execute("SELECT * FROM branch_images")}
    updates = json.loads((directory / "ARABIC-EVIDENCE-UPDATES.json").read_bytes())
    database_sha = hashlib.sha256(furuq_db.read_bytes()).hexdigest()
    if database_sha == updates["releasedFuruqSha256"]:
        for update in updates["updates"]:
            current = branches.get(update["branchRef"])
            previous = update["released"]
            if (previous is None and current is not None) or (previous is not None and
                    (current is None or any(current[k] != v for k, v in previous.items()))):
                raise ValueError(f"Released evidence baseline drift: {update['branchRef']}")
            branches[update["branchRef"]] = update["dictionary"]
    elif database_sha != updates["sourceDecompressedSha256"]:
        raise ValueError("Unrecognized Arabic evidence snapshot")
    for path in sorted(directory.glob("root_*_entry.json")):
        value = json.loads(path.read_bytes())
        components = set(value["root_envelope_id"].split("--"))
        if roots & components or components - registry.keys():
            raise ValueError(f"Duplicate or unregistered root: {path}")
        roots.update(components)
        for branch in value["branches"]:
            ref = branch["branch_ref"]
            original = branches.get(ref)
            if original is None:
                raise ValueError(f"Unregistered branch: {ref}")
            for key in ("branch_image_ar", "what_is_ar", "what_is_not_ar", "source_phrase_ar"):
                if branch[key] != original[key]:
                    raise ValueError(f"Arabic evidence differs from frozen registry: {ref}: {key}")
            branch_refs.add(ref)
    with tempfile.TemporaryDirectory() as temporary:
        db = Path(temporary) / "bridge.sqlite"
        db.write_bytes(gzip.decompress(bridge_path.read_bytes()))
        with sqlite3.connect(db) as connection:
            connection.row_factory = sqlite3.Row
            mapped = [dict(r) for r in connection.execute("SELECT * FROM qac_to_furuq_mapped")]
            root_rows = {r["qac_root_norm"]: dict(r) for r in connection.execute("SELECT * FROM qac_root_map")}
            with tsv_path.open(newline="") as handle:
                tsv = list(csv.DictReader(handle, delimiter="\t"))
            if len(tsv) != len(root_rows):
                raise ValueError("TSV/database root roster mismatch")
            for row in tsv:
                stored = root_rows[row["qac_root_norm"]]
                for key, value in row.items():
                    if str(stored["targets_raw" if key == "targets" else key]) != value:
                        raise ValueError(f"TSV/database mismatch: {row['qac_root_norm']}: {key}")
            missing = sorted({r["furuq_root_id"] for r in mapped} - roots)
            if missing:
                raise ValueError(f"Mapped roots without dictionary entries: {missing}")
            for row in mapped:
                if registry[row["furuq_root_id"]]["root_norm"] != row["furuq_root_norm"]:
                    raise ValueError(f"Bridge root identity mismatch: {row}")
            # Unmapped records stay visible; they are not missing-entry records.
            unmapped = [dict(r) for r in connection.execute(
                "SELECT qac_root_norm, unmapped_reason FROM qac_to_furuq WHERE has_furuq_root=0 ORDER BY qac_root_norm")]
    return {"entryCount": entries, "branchCount": branch_count, "componentRootCount": len(roots),
            "missingArabicEvidenceCount": 0, "missingMappedEntryCount": 0,
            "qacRootCount": len(root_rows), "mappingStatuses": dict(Counter(r["mapping_status"] for r in root_rows.values())),
            "unmappedRecords": unmapped}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--furuq-db", type=Path, required=True, help="Decompressed data/lexicon/furuq.sqlite.zst")
    args = parser.parse_args()
    result = audit(ROOT / "data/dictionary/tr", ROOT / "data/bridges/qac-furuq-v4-root-map.sqlite.gz",
                   ROOT / "data/bridges/qac-furuq-v4-root-map.tsv", args.furuq_db)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
