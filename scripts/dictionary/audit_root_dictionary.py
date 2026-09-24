#!/usr/bin/env python3
"""Audit entry identities/evidence and the complete QAC root gateway."""
import argparse
import csv
import gzip
import hashlib
import json
import sqlite3
import tempfile
from supplemental import (digest, load_source_names,
                          qac_connection, transferred_registry, validate_export)
from collections import Counter
from pathlib import Path

from check_turkish_entries import check, check_headwords

ROOT = Path(__file__).resolve().parents[2]

def audit(directory, bridge_path, tsv_path, furuq_db):
    entries, branch_count = check(directory)
    headwords = check_headwords(directory / "headwords")
    roots = set(); branch_refs = set()
    with sqlite3.connect(furuq_db) as connection:
        connection.row_factory = sqlite3.Row
        registry = {r["root_id"]: dict(r) for r in connection.execute("SELECT * FROM roots")}
        branches = {r["root_id"] + "/" + r["branch_id"]: dict(r)
                    for r in connection.execute("SELECT * FROM branch_images")}
    supplement = transferred_registry()
    supplemental_roots = {}
    source_names = {}
    registry_sha = None
    if supplement:
        registry_bytes, supplemental_registry, intakes = supplement
        registry_sha = digest(registry_bytes)
        def read_copied(path):
            return (ROOT / "data/dictionary/supplemental" / Path(path).relative_to("data/supplemental")).read_bytes()
        names_bytes, source_names = load_source_names(read_copied)
        expected_copied = {"registry.v1.json", "source-names.v1.json"} | {
            row["intakePath"] for row in supplemental_registry["entries"]
        }
        copied = {path.relative_to(ROOT / "data/dictionary/supplemental").as_posix()
                  for path in (ROOT / "data/dictionary/supplemental").rglob("*.json")}
        if copied != expected_copied:
            raise ValueError("Copied supplemental source roster differs from registry")
        for row in supplemental_registry["entries"]:
            root_id = row["id"]
            if row["kind"] != "lexical_root":
                continue
            root_ar = intakes[root_id]["rootArabic"]
            if (root_id in registry or
                    any(record["root_norm"] == root_ar for record in registry.values())):
                raise ValueError(f"Supplemental root collides with frozen Furuq: {root_id}/{root_ar}")
            supplemental_roots[root_id] = root_ar
        root_manifest = json.loads((directory / "MANIFEST.json").read_bytes())
        headword_manifest = json.loads((directory / "headwords/MANIFEST.json").read_bytes())
        for manifest in (root_manifest, headword_manifest):
            if (manifest.get("supplementalRegistrySha256") != registry_sha or
                    manifest.get("supplementalSourceNamesSha256") != digest(names_bytes)):
                raise ValueError("Supplemental registry/source-name manifest digest drift")
        if root_manifest.get("sourceCommit") != headword_manifest.get("sourceCommit"):
            raise ValueError("Root and headword transfer source commits differ")
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
        if roots & components or components - (registry.keys() | supplemental_roots.keys()):
            raise ValueError(f"Duplicate or unregistered root: {path}")
        roots.update(components)
        supplemental_component = components & supplemental_roots.keys()
        if supplemental_component:
            if components != supplemental_component or len(components) != 1:
                raise ValueError(f"Supplemental root cannot be merged into a frozen envelope: {path}")
            root_id = next(iter(components))
            row = next(r for r in supplemental_registry["entries"] if r["id"] == root_id)
            validate_export(value, root_id, intakes[root_id], registry_sha,
                            row["intakeSha256"], source_names)
        for branch in value["branches"]:
            ref = branch["branch_ref"]
            if supplemental_component:
                branch_refs.add(ref)
                continue
            original = branches.get(ref)
            if original is None:
                raise ValueError(f"Unregistered branch: {ref}")
            for key in ("branch_image_ar", "what_is_ar", "what_is_not_ar", "source_phrase_ar"):
                if branch[key] != original[key]:
                    raise ValueError(f"Arabic evidence differs from frozen registry: {ref}: {key}")
            branch_refs.add(ref)
    if supplement:
        if set(supplemental_roots) - roots:
            raise ValueError("Reviewed supplemental roots lack transferred entries")
        headword_ids = set()
        for path in sorted((directory / "headwords").glob("headword_*_entry.json")):
            value = json.loads(path.read_bytes())
            ident = value["headwordId"]
            if ident in headword_ids or ident not in intakes or intakes[ident]["kind"] != "grammatical_headword":
                raise ValueError(f"Unknown or duplicate grammatical headword: {ident}")
            headword_ids.add(ident)
            row = next(r for r in supplemental_registry["entries"] if r["id"] == ident)
            validate_export(value, ident, intakes[ident], registry_sha,
                            row["intakeSha256"], source_names)
        if headword_ids != {ident for ident in intakes if intakes[ident]["kind"] == "grammatical_headword"}:
            raise ValueError("Reviewed supplemental headword roster is incomplete")
        with qac_connection() as qac:
            refs = set()
            for ident in headword_ids:
                selector = intakes[ident]["binding"]["selector"]
                column = "lemma_ar" if "qacLemma" in selector else "qac_ref"
                target = selector.get("qacLemma", selector.get("qacRef"))
                selected = {row[0] for row in qac.execute(
                    f"SELECT qac_ref FROM qac_morphemes WHERE root_join_key=? AND {column}=?",
                    (selector["qacRootJoinKey"], target),
                )}
                if refs & selected:
                    raise ValueError("Grammatical headword selectors overlap")
                refs.update(selected)
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
            "headwordCount": headwords, "supplementalRootCount": len(supplemental_roots),
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
