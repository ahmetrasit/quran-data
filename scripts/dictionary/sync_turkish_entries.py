#!/usr/bin/env python3
"""Transfer accepted dictionary entries from a committed source snapshot."""
import argparse
import gzip
import hashlib
import json
import sqlite3
import subprocess
import tempfile
from pathlib import Path

from check_turkish_entries import ENVELOPE, validate_entry

ROOT = Path(__file__).resolve().parents[2]

def git(source, *args):
    return subprocess.check_output(["git", "-C", str(source), *args])

def committed_paths(source: Path, commit: str, directory: str) -> set[str]:
    return set(git(source, "ls-tree", "-r", "--name-only", commit, "--", directory).decode().splitlines())

def source_path(envelope: str, paths: set[str]) -> str | None:
    filename = envelope + "_entry.json"
    base = f"v2/work/entry_creation/furuq/{envelope}/tr"
    # A reviewed Furuq export supersedes an older accepted output at the same root.
    for path in (f"{base}/export/{filename}",
                 f"v2/work/entry_creation/{envelope}/tr/output/{filename}",
                 f"{base}/output/{filename}"):
        if path in paths:
            return path
    return None

def is_raw_furuq_output(value: object) -> bool:
    return isinstance(value, dict) and set(value) == {"branches", "root_profile"}

def collect(source: Path, bridge: Path):
    commit = git(source, "rev-parse", "HEAD").decode().strip()
    packet_paths = committed_paths(source, commit, "data/output/root_packets")
    packet_envelopes = {
        Path(path).stem for path in packet_paths
        if Path(path).parent.as_posix() == "data/output/root_packets"
        and Path(path).suffix == ".json" and ENVELOPE.fullmatch(Path(path).stem)
    }
    if not packet_envelopes:
        raise ValueError("Dictionary Quranic packet roster is empty")
    components = {root for envelope in packet_envelopes for root in envelope.split("--")}
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "bridge.sqlite"
        db.write_bytes(gzip.decompress(bridge.read_bytes()))
        with sqlite3.connect(db) as connection:
            targets = {r[0] for r in connection.execute("SELECT DISTINCT furuq_root_id FROM qac_to_furuq_mapped")}
    resolutions = json.loads((ROOT / "data/bridges/qac-dictionary-root-resolutions.json").read_bytes())
    targets.update(root_id for row in resolutions["roots"] for root_id in row["rootIds"])
    entry_paths = committed_paths(source, commit, "v2/work/entry_creation")
    missing = []
    files = {}; rows = []; branch_count = 0
    for envelope in sorted(packet_envelopes | (targets - components)):
        filename = envelope + "_entry.json"
        relative = source_path(envelope, entry_paths)
        if relative is None:
            if envelope in packet_envelopes:
                raise ValueError(f"Missing committed dictionary output: {filename}")
            missing.append(envelope)
            continue
        # Git's commit snapshot supplies both roster and bytes; dirty source files
        # cannot change transfer eligibility or acquire the commit's provenance.
        data = git(source, "show", f"{commit}:{relative}")
        value = json.loads(data)
        if relative.endswith(f"/tr/output/{filename}") and "/furuq/" in relative and is_raw_furuq_output(value):
            if envelope in packet_envelopes:
                raise ValueError(f"Raw dictionary output for Quranic packet: {relative}")
            missing.append(envelope)
            continue
        expected_generator = "v2/scripts/enrich_furuq_writer.py" if "/tr/export/" in relative else None
        branch_count += validate_entry(value, filename, expected_generator=expected_generator)
        files[filename] = data
        rows.append({"path": filename, "sourcePath": relative, "sha256": hashlib.sha256(data).hexdigest()})
    corpus_hash = hashlib.sha256("".join(f"{r['sha256']}  {r['path']}\n" for r in rows).encode()).hexdigest()
    manifest = {"schemaVersion": "turkish-dictionary-transfer-v1", "sourceRepository": "dictionary",
                "sourceCommit": commit, "entryCount": len(rows), "branchCount": branch_count,
                "sourceCorpusSha256": corpus_hash, "missingTargetRootIds": missing, "entries": rows}
    return files, manifest

def transfer(source: Path, bridge: Path, destination: Path, *, check: bool = False):
    files, manifest = collect(source, bridge)
    existing = {p.name for p in destination.glob("root_*_entry.json")}
    previous_manifest = destination / "MANIFEST.json"
    if previous_manifest.exists():
        prior = json.loads(previous_manifest.read_bytes())
        existing.update(row["path"] for row in prior["entries"])
    removed = existing - files.keys()
    if removed:
        raise ValueError(f"Previously transferred entries require review: {sorted(removed)}")
    files["MANIFEST.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    changed = []
    for name, data in files.items():
        path = destination / name
        if path.exists() and path.read_bytes() == data:
            continue
        changed.append(name)
        if not check:
            destination.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".tmp")
            temporary.write_bytes(data)
            temporary.replace(path)
    if check and changed:
        raise ValueError(f"Stale Turkish entry transfer: {changed}")
    return manifest, changed

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    manifest, changed = transfer(
        args.source.resolve(), ROOT / "data/bridges/qac-furuq-v4-root-map.sqlite.gz",
        ROOT / "data/dictionary/tr", check=args.check,
    )
    print(f"entries={manifest['entryCount']} branches={manifest['branchCount']} changed={len(changed)}")

if __name__ == "__main__":
    main()
