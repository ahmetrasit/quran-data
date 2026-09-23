#!/usr/bin/env python3
"""Check Arabic source evidence in the staged Turkish dictionary corpus."""
import argparse
import json
from pathlib import Path

def check(directory: Path) -> tuple[int, int]:
    paths = sorted(directory.glob("root_*_entry.json"))
    if not paths:
        raise ValueError(f"No Turkish dictionary entries in {directory}")
    branch_count = 0
    for path in paths:
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("artifact_format") != "dictionary-v2-root-entry-draft-v1":
            raise ValueError(f"Raw or unrecognized writer output: {path}")
        if value.get("root_envelope_id") != path.name.removesuffix("_entry.json"):
            raise ValueError(f"Entry identity mismatch: {path}")
        for branch in value.get("branches", []):
            ref = branch.get("branch_ref", path.name)
            if not all(branch.get(field) for field in (
                "branch_image_ar", "what_is_ar", "what_is_not_ar", "source_phrase_ar", "sources"
            )):
                raise ValueError(f"Missing Arabic evidence or sources: {path}: {ref}")
            branch_count += 1
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
