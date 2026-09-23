#!/usr/bin/env python3
"""Copy accepted dictionary outputs with a reproducible, checked source manifest."""
import argparse
import gzip
import hashlib
import json
import sqlite3
import subprocess
import tempfile
from pathlib import Path

from check_turkish_entries import validate_entry

ROOT = Path(__file__).resolve().parents[2]

def git(source, *args):
    return subprocess.check_output(["git", "-C", str(source), *args])

def collect(source: Path, bridge: Path):
    commit = git(source, "rev-parse", "HEAD").decode().strip()
    packets = sorted((source / "data/output/root_packets").glob("root_*.json"))
    if not packets:
        raise ValueError("Dictionary Quranic packet roster is empty")
    envelopes = {p.stem for p in packets}
    components = {root for envelope in envelopes for root in envelope.split("--")}
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "bridge.sqlite"
        db.write_bytes(gzip.decompress(bridge.read_bytes()))
        with sqlite3.connect(db) as connection:
            targets = {r[0] for r in connection.execute("SELECT DISTINCT furuq_root_id FROM qac_to_furuq_mapped")}
    resolutions = json.loads((ROOT / "data/bridges/qac-dictionary-root-resolutions.json").read_bytes())
    targets.update(root_id for row in resolutions["roots"] for root_id in row["rootIds"])
    missing = []
    for root_id in sorted(targets - components):
        path = source / "v2/work/entry_creation/furuq" / root_id / "tr/output" / (root_id + "_entry.json")
        if path.exists(): envelopes.add(root_id)
        else: missing.append(root_id)
    files = {}; rows = []; branch_count = 0
    for envelope in sorted(envelopes):
        filename = envelope + "_entry.json"
        relative = Path("v2/work/entry_creation") / envelope / "tr/output" / filename
        if not (source / relative).exists():
            relative = Path("v2/work/entry_creation/furuq") / envelope / "tr/output" / filename
        # Read committed outputs, so uncommitted repairs cannot acquire false provenance.
        data = git(source, "show", f"{commit}:{relative.as_posix()}")
        if (source / relative).read_bytes() != data:
            raise ValueError(f"Commit dictionary output before transferring: {relative}")
        branch_count += validate_entry(json.loads(data), filename)
        files[filename] = data
        rows.append({"path": filename, "sourcePath": relative.as_posix(), "sha256": hashlib.sha256(data).hexdigest()})
    corpus_hash = hashlib.sha256("".join(f"{r['sha256']}  {r['path']}\n" for r in rows).encode()).hexdigest()
    manifest = {"schemaVersion": "turkish-dictionary-transfer-v1", "sourceRepository": "dictionary",
                "sourceCommit": commit, "entryCount": len(rows), "branchCount": branch_count,
                "sourceCorpusSha256": corpus_hash, "missingTargetRootIds": missing, "entries": rows}
    return files, manifest

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    files, manifest = collect(args.source.resolve(), ROOT / "data/bridges/qac-furuq-v4-root-map.sqlite.gz")
    destination = ROOT / "data/dictionary/tr"
    existing = {p.name for p in destination.glob("root_*_entry.json")}
    extra = existing - files.keys()
    if extra:
        raise ValueError(f"Unexpected destination entries require review: {sorted(extra)}")
    files["MANIFEST.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    changed = []
    for name, data in files.items():
        path = destination / name
        if path.exists() and path.read_bytes() == data:
            continue
        changed.append(name)
        if not args.check:
            temporary = path.with_suffix(".tmp")
            temporary.write_bytes(data)
            temporary.replace(path)
    if args.check and changed:
        raise ValueError(f"Stale Turkish entry transfer: {changed}")
    print(f"entries={manifest['entryCount']} branches={manifest['branchCount']} changed={len(changed)}")

if __name__ == "__main__":
    main()
