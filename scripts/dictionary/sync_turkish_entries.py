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

from check_turkish_entries import ENVELOPE, SUPPLEMENTAL_GENERATOR, validate_entry, validate_headword
from supplemental import (REGISTRY_PATH, SOURCE_NAMES_PATH, digest,
                          export_source_path, load_registry, load_source_names,
                          validate_export)

ROOT = Path(__file__).resolve().parents[2]

def git(source, *args):
    return subprocess.check_output(["git", "-C", str(source), *args])

def committed_paths(source: Path, commit: str, directory: str) -> set[str]:
    return set(git(source, "ls-tree", "-r", "--name-only", commit, "--", directory).decode().splitlines())

def source_path(envelope: str, paths: set[str], supplemental_ids: set[str]) -> str | None:
    if envelope in supplemental_ids:
        path = export_source_path(envelope)
        return path if path in paths else None
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
    committed_supplemental = committed_paths(source, commit, "data/supplemental")
    supplement = None
    source_names = None
    supplemental_files = {}
    if REGISTRY_PATH in committed_supplemental:
        def committed_read(path: str) -> bytes:
            if path not in committed_supplemental:
                raise ValueError(f"Missing committed supplemental source: {path}")
            return git(source, "show", f"{commit}:{path}")
        registry_bytes, registry, intakes = load_registry(committed_read)
        names_bytes, source_names = load_source_names(committed_read)
        supplemental_files = {REGISTRY_PATH: registry_bytes, SOURCE_NAMES_PATH: names_bytes}
        for row in registry["entries"]:
            path = f"data/supplemental/{row['intakePath']}"
            supplemental_files[path] = committed_read(path)
        supplement = (registry_bytes, registry, intakes, names_bytes)
    elif committed_supplemental:
        raise ValueError("Committed supplemental files have no registry")
    packet_paths = committed_paths(source, commit, "data/output/root_packets")
    packet_envelopes = {
        Path(path).stem for path in packet_paths
        if Path(path).parent.as_posix() == "data/output/root_packets"
        and Path(path).suffix == ".json" and ENVELOPE.fullmatch(Path(path).stem)
    }
    if not packet_envelopes:
        raise ValueError("Dictionary Quranic packet roster is empty")
    components = {root for envelope in packet_envelopes for root in envelope.split("--")}
    supplemental_roots = {row["id"] for row in supplement[1]["entries"]
                          if row["kind"] == "lexical_root"} if supplement else set()
    if supplemental_roots & components:
        raise ValueError("Supplemental root ID collides with Quranic packet roster")
    if supplemental_roots:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "furuq.sqlite"
            with db_path.open("wb") as target:
                subprocess.run(["zstd", "-q", "-dc", str(ROOT / "data/lexicon/furuq.sqlite.zst")],
                               stdout=target, check=True)
            with sqlite3.connect(db_path) as connection:
                frozen_rows = connection.execute("SELECT root_id, root_norm FROM roots").fetchall()
        frozen_ids = {row[0] for row in frozen_rows}
        frozen_norms = {row[1] for row in frozen_rows}
        for ident in supplemental_roots:
            if ident in frozen_ids or supplement[2][ident]["rootArabic"] in frozen_norms:
                raise ValueError(f"Supplemental root collides with frozen Furuq: {ident}")
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "bridge.sqlite"
        db.write_bytes(gzip.decompress(bridge.read_bytes()))
        with sqlite3.connect(db) as connection:
            targets = {r[0] for r in connection.execute("SELECT DISTINCT furuq_root_id FROM qac_to_furuq_mapped")}
    resolutions = json.loads((ROOT / "data/bridges/qac-dictionary-root-resolutions.json").read_bytes())
    targets.update(root_id for row in resolutions["roots"] for root_id in row["rootIds"])
    entry_paths = committed_paths(source, commit, "v2/work/entry_creation")
    if supplement:
        for row in supplement[1]["entries"]:
            ident = row["id"]
            expected = export_source_path(ident)
            name = f"{ident}_entry.json"
            work_base = (f"v2/work/entry_creation/{ident}" if row["kind"] == "lexical_root"
                         else f"v2/work/entry_creation/headwords/{ident}")
            authored_output = f"{work_base}/tr/output/{name}"
            competing = sorted(path for path in entry_paths
                               if Path(path).name == name and path not in {expected, authored_output})
            if competing:
                raise ValueError(f"Supplemental ID collides with committed exports: {ident}: {competing}")
    missing = []
    files = {}; rows = []; branch_count = 0
    for envelope in sorted(packet_envelopes | (targets - components) | supplemental_roots):
        filename = envelope + "_entry.json"
        relative = source_path(envelope, entry_paths, supplemental_roots)
        if relative is None:
            if envelope in packet_envelopes or envelope in supplemental_roots:
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
        expected_generator = (SUPPLEMENTAL_GENERATOR if envelope in supplemental_roots else
                              "v2/scripts/enrich_furuq_writer.py" if "/tr/export/" in relative else None)
        branch_count += validate_entry(value, filename, expected_generator=expected_generator)
        if envelope in supplemental_roots:
            registry_bytes, registry, intakes, _ = supplement
            registry_row = next(row for row in registry["entries"] if row["id"] == envelope)
            validate_export(value, envelope, intakes[envelope], digest(registry_bytes),
                            registry_row["intakeSha256"], source_names)
        files[filename] = data
        rows.append({"path": filename, "sourcePath": relative, "sha256": hashlib.sha256(data).hexdigest()})
    corpus_hash = hashlib.sha256("".join(f"{r['sha256']}  {r['path']}\n" for r in rows).encode()).hexdigest()
    manifest = {"schemaVersion": "turkish-dictionary-transfer-v1", "sourceRepository": "dictionary",
                "sourceCommit": commit, "entryCount": len(rows), "branchCount": branch_count,
                "sourceCorpusSha256": corpus_hash, "missingTargetRootIds": missing, "entries": rows}
    headword_files = {}
    headword_manifest = None
    if supplement:
        registry_bytes, registry, intakes, names_bytes = supplement
        registry_sha = digest(registry_bytes)
        names_sha = digest(names_bytes)
        manifest["supplementalRegistrySha256"] = registry_sha
        manifest["supplementalSourceNamesSha256"] = names_sha
        headword_rows = []
        for row in registry["entries"]:
            ident = row["id"]
            if row["kind"] != "grammatical_headword":
                continue
            path = export_source_path(ident)
            if path not in entry_paths:
                raise ValueError(f"Missing committed grammatical headword export: {path}")
            data = git(source, "show", f"{commit}:{path}")
            filename = f"{ident}_entry.json"
            value = json.loads(data)
            validate_headword(value, filename)
            validate_export(value, ident, intakes[ident], registry_sha,
                            row["intakeSha256"], source_names)
            headword_files[filename] = data
            headword_rows.append({"path": filename, "sourcePath": path, "sha256": digest(data)})
        headword_rows.sort(key=lambda row: row["path"])
        headword_hash = digest("".join(
            f"{row['sha256']}  {row['path']}\n" for row in headword_rows
        ).encode("utf-8"))
        headword_manifest = {
            "schemaVersion": "turkish-dictionary-headword-transfer-v1",
            "sourceRepository": "dictionary", "sourceCommit": commit,
            "supplementalRegistrySha256": registry_sha,
            "supplementalSourceNamesSha256": names_sha,
            "entryCount": len(headword_rows), "sourceCorpusSha256": headword_hash,
            "entries": headword_rows,
        }
    return files, manifest, supplemental_files, headword_files, headword_manifest

def transfer(source: Path, bridge: Path, destination: Path, *, check: bool = False):
    files, manifest, supplemental_files, headword_files, headword_manifest = collect(source, bridge)
    existing = {p.name for p in destination.glob("root_*_entry.json")}
    previous_manifest = destination / "MANIFEST.json"
    if previous_manifest.exists():
        prior = json.loads(previous_manifest.read_bytes())
        existing.update(row["path"] for row in prior["entries"])
        supplemental_roots = {row["id"] for row in
                              json.loads(supplemental_files[REGISTRY_PATH])["entries"]
                              if row["kind"] == "lexical_root"} if supplemental_files else set()
        for row in prior["entries"]:
            ident = row["path"].removesuffix("_entry.json")
            if ident in supplemental_roots and row["sourcePath"] != export_source_path(ident):
                raise ValueError(f"Supplemental root collides with prior transfer: {ident}")
    removed = existing - files.keys()
    if removed:
        raise ValueError(f"Previously transferred entries require review: {sorted(removed)}")
    files["MANIFEST.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    copies = {destination / name: data for name, data in files.items()}
    supplemental_destination = ROOT / "data/dictionary/supplemental"
    existing_supplemental = {
        f"data/supplemental/entries/{path.name}"
        for path in (supplemental_destination / "entries").glob("*.json")
    }
    for name in ("registry.v1.json", "source-names.v1.json"):
        if (supplemental_destination / name).exists():
            existing_supplemental.add(f"data/supplemental/{name}")
    stale_supplemental = existing_supplemental - supplemental_files.keys()
    if stale_supplemental:
        raise ValueError(f"Previously transferred supplemental source requires review: {sorted(stale_supplemental)}")
    for name, data in supplemental_files.items():
        copies[supplemental_destination / Path(name).relative_to("data/supplemental")] = data
    headword_destination = destination / "headwords"
    previous_headwords = headword_destination / "MANIFEST.json"
    if headword_manifest is not None:
        existing_headwords = {p.name for p in headword_destination.glob("headword_*_entry.json")}
        if previous_headwords.exists():
            prior_headwords = json.loads(previous_headwords.read_bytes())["entries"]
            existing_headwords.update(row["path"] for row in prior_headwords)
            for row in prior_headwords:
                ident = row["path"].removesuffix("_entry.json")
                if row["sourcePath"] != export_source_path(ident):
                    raise ValueError(f"Supplemental headword collides with prior transfer: {ident}")
        removed_headwords = existing_headwords - headword_files.keys()
        if removed_headwords:
            raise ValueError(f"Previously transferred headwords require review: {sorted(removed_headwords)}")
        for name, data in headword_files.items():
            copies[headword_destination / name] = data
        copies[previous_headwords] = (json.dumps(headword_manifest, ensure_ascii=False, indent=2) + "\n").encode()
    elif previous_headwords.exists():
        raise ValueError("Committed source removed the supplemental headword registry")
    changed = []
    for path, data in copies.items():
        if path.exists() and path.read_bytes() == data:
            continue
        changed.append(str(path.relative_to(ROOT)))
        if not check:
            path.parent.mkdir(parents=True, exist_ok=True)
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
