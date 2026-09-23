#!/usr/bin/env python3
"""Check Arabic source evidence in the staged Turkish dictionary corpus."""
import argparse
import hashlib
import json
import re
from pathlib import Path

ENVELOPE = re.compile(r"root_[0-9]{6}(?:--root_[0-9]{6})*")

def validate_entry(value: dict, filename: str) -> int:
    envelope = filename.removesuffix("_entry.json")
    if not ENVELOPE.fullmatch(envelope) or value.get("root_envelope_id") != envelope:
        raise ValueError(f"Entry identity mismatch: {filename}")
    if (value.get("artifact_format") != "dictionary-v2-root-entry-draft-v1"
            or value.get("language") != "tr"):
        raise ValueError(f"Raw or unrecognized writer output: {filename}")
    branches = value.get("branches")
    if not isinstance(branches, list) or not branches:
        raise ValueError(f"Empty or missing branches: {filename}")
    seen = set()
    for branch in branches:
        ref = branch.get("branch_ref", "")
        if (not re.fullmatch(r"root_[0-9]{6}/B[0-9]{3}", ref)
                or ref.split("/")[0] not in envelope.split("--") or ref in seen):
            raise ValueError(f"Invalid or duplicate branch identity: {filename}: {ref}")
        seen.add(ref)
        for field in ("branch_image_ar", "what_is_ar", "what_is_not_ar", "source_phrase_ar"):
            if not isinstance(branch.get(field), str) or not branch[field].strip():
                raise ValueError(f"Missing Arabic evidence: {filename}: {ref}: {field}")
        sources = branch.get("sources")
        if (not isinstance(sources, list) or not sources
                or any(not isinstance(s, str) or not s.strip() for s in sources)):
            raise ValueError(f"Missing source list: {filename}: {ref}")
    return len(branches)

def check(directory: Path) -> tuple[int, int]:
    paths = sorted(directory.glob("root_*_entry.json"))
    if not paths:
        raise ValueError(f"No Turkish dictionary entries in {directory}")
    branch_count = 0
    for path in paths:
        value = json.loads(path.read_text(encoding="utf-8"))
        branch_count += validate_entry(value, path.name)
    manifest_path = directory / "MANIFEST.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected = {row["path"]: row["sha256"] for row in manifest["entries"]}
        actual = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
        if actual != expected or len(expected) != len(manifest["entries"]):
            raise ValueError("Turkish entry manifest does not match corpus filenames/checksums")
        if manifest["branchCount"] != branch_count or manifest["entryCount"] != len(paths):
            raise ValueError("Turkish entry manifest counts do not match corpus")
    return len(paths), branch_count

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "directory", nargs="?", type=Path,
        default=Path(__file__).resolve().parents[2] / "data/dictionary/tr",
    )
    args = parser.parse_args()
    entries, branches = check(args.directory)
    print(f"entries={entries} branches={branches} missing_arabic_sources=0")

if __name__ == "__main__":
    main()
