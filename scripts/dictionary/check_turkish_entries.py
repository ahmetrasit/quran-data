#!/usr/bin/env python3
"""Check Arabic source evidence in the staged Turkish dictionary corpus."""
import argparse
import hashlib
import json
import re
from pathlib import Path

ENVELOPE = re.compile(r"root_[0-9]{6}(?:--root_[0-9]{6})*")
GENERATORS = {
    "v2/scripts/accept_root_writer.py",
    "v2/scripts/enrich_furuq_writer.py",
    "v2/scripts/export_reviewed_supplement.py",
}
SUPPLEMENTAL_GENERATOR = "v2/scripts/export_reviewed_supplement.py"

def validate_entry(value: dict, filename: str, *, expected_generator: str | None = None) -> int:
    envelope = filename.removesuffix("_entry.json")
    if (not isinstance(value, dict) or not ENVELOPE.fullmatch(envelope)
            or value.get("root_envelope_id") != envelope):
        raise ValueError(f"Entry identity mismatch: {filename}")
    if (value.get("artifact_format") != "dictionary-v2-root-entry-draft-v1"
            or value.get("language") != "tr"
            or value.get("generated_by") not in GENERATORS
            or (expected_generator is not None and value.get("generated_by") != expected_generator)):
        raise ValueError(f"Raw or unrecognized writer output: {filename}")
    if value["generated_by"] == SUPPLEMENTAL_GENERATOR:
        if (value.get("entryKind") != "lexical_root" or
                not isinstance(value.get("supplementalIntake"), dict) or
                not isinstance(value.get("inputs_sha256"), str) or
                not re.fullmatch(r"[0-9a-f]{64}", value["inputs_sha256"])):
            raise ValueError(f"Unbound supplemental root export: {filename}")
    branches = value.get("branches")
    if not isinstance(branches, list) or not branches:
        raise ValueError(f"Empty or missing branches: {filename}")
    seen = set()
    for branch in branches:
        if not isinstance(branch, dict):
            raise ValueError(f"Invalid branch: {filename}")
        ref = branch.get("branch_ref", "")
        if (not re.fullmatch(r"root_[0-9]{6}/B[0-9]{3}", ref)
                or ref.split("/")[0] not in envelope.split("--") or ref in seen):
            raise ValueError(f"Invalid or duplicate branch identity: {filename}: {ref}")
        seen.add(ref)
        for field in ("branch_image_ar", "what_is_ar", "what_is_not_ar", "source_phrase_ar"):
            if not isinstance(branch.get(field), str) or not branch[field].strip():
                raise ValueError(f"Missing Arabic evidence: {filename}: {ref}: {field}")
        sources = branch.get("sources")
        if (not isinstance(sources, list)
                or (not sources and value["generated_by"] != SUPPLEMENTAL_GENERATOR)
                or any(not isinstance(s, str) or not s.strip() for s in sources)):
            raise ValueError(f"Missing source list: {filename}: {ref}")
        if value["generated_by"] == SUPPLEMENTAL_GENERATOR:
            citations = branch.get("citations")
            if not isinstance(citations, list) or not citations:
                raise ValueError(f"Missing typed supplemental citations: {filename}: {ref}")
    occurrence = value.get("occurrence_evidence")
    if (not isinstance(occurrence, dict)
            or not isinstance(occurrence.get("summary"), dict)
            or any(not isinstance(occurrence.get(field), list)
                   for field in ("forms", "ayahs", "occurrences"))
            or any(type(occurrence["summary"].get(field)) is not int
                   or occurrence["summary"][field] < 0
                   for field in ("morpheme_count", "word_count", "ayah_count", "surah_count"))):
        raise ValueError(f"Missing or incomplete occurrence evidence: {filename}")
    return len(branches)


def validate_headword(value: dict, filename: str) -> None:
    ident = filename.removesuffix("_entry.json")
    if (not re.fullmatch(r"headword_[0-9]{6}_entry\.json", filename)
            or not isinstance(value, dict)
            or value.get("artifact_format") != "dictionary-v2-headword-entry-draft-v1"
            or value.get("generated_by") != SUPPLEMENTAL_GENERATOR
            or value.get("entryKind") != "grammatical_headword"
            or value.get("headwordId") != ident
            or value.get("language") != "tr"
            or not isinstance(value.get("headwordArabic"), str)
            or not value["headwordArabic"].strip()
            or not isinstance(value.get("inputs_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", value["inputs_sha256"])
            or not isinstance(value.get("supplementalIntake"), dict)
            or not isinstance(value.get("binding"), dict)
            or not isinstance(value.get("headwordProfile"), dict)
            or not isinstance(value.get("senses"), list) or not value["senses"]
            or not isinstance(value.get("citations"), list) or not value["citations"]
            or not isinstance(value.get("occurrenceEvidence"), dict)):
        raise ValueError(f"Invalid reviewed grammatical headword: {filename}")
    seen = set()
    for sense in value["senses"]:
        sense_id = sense.get("senseId") if isinstance(sense, dict) else None
        if (not isinstance(sense_id, str) or not re.fullmatch(r"S[0-9]{3}", sense_id)
                or sense_id in seen or not isinstance(sense.get("sourcePhraseArabic"), str)
                or not sense["sourcePhraseArabic"].strip()):
            raise ValueError(f"Invalid headword sense: {filename}/{sense_id}")
        seen.add(sense_id)


def check_headwords(directory: Path) -> int:
    paths = sorted(directory.glob("headword_*_entry.json"))
    manifest_path = directory / "MANIFEST.json"
    if not manifest_path.exists() and not paths:
        return 0
    if not manifest_path.exists():
        raise ValueError("Headword transfer lacks a manifest")
    manifest = json.loads(manifest_path.read_bytes())
    if manifest.get("schemaVersion") != "turkish-dictionary-headword-transfer-v1":
        raise ValueError("Invalid headword manifest")
    for path in paths:
        validate_headword(json.loads(path.read_bytes()), path.name)
    expected = {row["path"]: row["sha256"] for row in manifest["entries"]}
    actual = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    ordered = manifest["entries"]
    corpus_hash = hashlib.sha256("".join(
        f"{row['sha256']}  {row['path']}\n" for row in ordered
    ).encode("utf-8")).hexdigest()
    if (actual != expected or len(expected) != len(manifest["entries"])
            or manifest.get("entryCount") != len(paths)
            or [row["path"] for row in ordered] != sorted(expected)
            or manifest.get("sourceCorpusSha256") != corpus_hash):
        raise ValueError("Headword transfer manifest does not match entries")
    return len(paths)

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
    headwords = check_headwords(args.directory / "headwords")
    print(f"entries={entries} branches={branches} headwords={headwords} missing_arabic_sources=0")

if __name__ == "__main__":
    main()
