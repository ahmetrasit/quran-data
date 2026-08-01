#!/usr/bin/env python3
"""Seed ayah/summary reference-chunk responses from already-synthesized
recitation audio, avoiding duplicate paid TTS calls for identical clips.

Every `ayah_reference` chunk in the `ayah` and `summary` commentary
collections (prepare_commentary_chunks.py) is byte-for-byte identical to its
counterpart chunk in the `recitation` collection (prepare_recitation_chunks.py)
-- same ttsText, same voice/prompt/audioConfig, hence the same
`requestSha256` -- because both are built from the same ayah_spoken_label()
+ quran-uthmani.tsv Arabic text. Verified against the real corpus: 1,393/1,393
`ayah` reference chunks and 979/979 `summary` reference chunks match
recitation's byte-for-byte.

Rather than teach synthesize_tts_chunks.py about a cross-collection cache,
this script seeds `responses/<chunkId>.json` in the TARGET collection folder
by copying the matching, already-synthesized response out of the
corresponding `recitation/<surahId>/` folder. synthesize_tts_chunks.py's own
existing idempotency check (`response_matches_chunk`, keyed on
requestSha256/textSha256/promptSha256/voiceSha256/audioConfigSha256 --
UNMODIFIED) then recognizes the seeded response as valid the next time it
runs against the target folder, and materializes wav/mp3/duration locally --
zero API calls, zero extra cost, for those specific chunks.

`synthesize_tts_chunks.py` is never modified by this script and never
imported for anything other than its two small, pure validation helpers
(`load_response`, `response_matches_chunk`) -- reused here so "does this
response still match this chunk" is decided by exactly one piece of logic,
not two copies that could drift apart.

This script only ever writes into `responses/`. It never touches
chunks.jsonl or manifest.json -- the normal synth run still owns updating
those fields (durationSeconds, audioSha256, generatedAt, mp3Sha256) once it
sees the seeded response.

Recitation must already be synthesized for a given ayah before this can
reuse it. Recommended order:

    1. prepare_recitation_chunks.py --all      (+ --besmele once)
    2. synthesize_tts_chunks.py against every recitation/<surahId>/
    3. prepare_commentary_chunks.py ayah/summary --all
    4. reuse_recitation_references.py ayah --all
       reuse_recitation_references.py summary --all
    5. synthesize_tts_chunks.py against every ayah|summary/<surahId>/
       (only pays for chunks step 4 could not seed)

Usage:
    reuse_recitation_references.py ayah S001
    reuse_recitation_references.py summary --all
    reuse_recitation_references.py ayah --all --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tts_common as common  # noqa: E402
from synthesize_tts_chunks import load_response, response_matches_chunk  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]  # .../quran-data


def load_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def atomic_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = dst.with_name(f".{dst.name}.tmp")
    tmp_path.write_bytes(src.read_bytes())
    os.replace(tmp_path, dst)


def _reuse_for_surah_unlocked(
    *, collection: str, surah_id: str, audio_root: Path, dry_run: bool,
) -> dict:
    target_dir = audio_root / collection / surah_id
    recitation_dir = audio_root / "recitation" / surah_id
    target_chunks = load_jsonl(target_dir / "chunks.jsonl")
    recitation_chunks = load_jsonl(recitation_dir / "chunks.jsonl")

    if not target_chunks:
        return {"surahId": surah_id, "status": "no-target-folder"}
    if not recitation_chunks:
        return {"surahId": surah_id, "status": "no-recitation-source-folder"}

    recitation_by_hash = {c["requestSha256"]: c for c in recitation_chunks}

    counts = {"reused": 0, "alreadyDone": 0, "sourceNotSynthesized": 0, "noMatch": 0}
    for chunk in target_chunks:
        if chunk["kind"] != "ayah_reference":
            continue  # only reference chunks can possibly overlap with recitation

        target_response_path = target_dir / chunk["response"]
        existing = load_response(target_response_path)
        if existing and response_matches_chunk(existing, chunk):
            counts["alreadyDone"] += 1  # already synthesized directly, or reused before
            continue

        source_chunk = recitation_by_hash.get(chunk["requestSha256"])
        if source_chunk is None:
            # Should not happen given the verified 100% overlap, but never
            # silently assume -- report it instead of guessing.
            counts["noMatch"] += 1
            continue

        source_response_path = recitation_dir / source_chunk["response"]
        source_response = load_response(source_response_path)
        if not source_response or not response_matches_chunk(source_response, source_chunk):
            counts["sourceNotSynthesized"] += 1  # recitation hasn't generated this one yet
            continue

        counts["reused"] += 1
        if not dry_run:
            atomic_copy(source_response_path, target_response_path)

    return {"surahId": surah_id, "status": "ok", **counts}


def reuse_for_surah(*, collection: str, surah_id: str, audio_root: Path, dry_run: bool) -> dict:
    target_dir = audio_root / collection / surah_id
    if dry_run:
        return _reuse_for_surah_unlocked(
            collection=collection, surah_id=surah_id,
            audio_root=audio_root, dry_run=True,
        )
    with common.CollectionLock(target_dir):
        return _reuse_for_surah_unlocked(
            collection=collection, surah_id=surah_id,
            audio_root=audio_root, dry_run=False,
        )


def discover_surah_ids(collection: str, audio_root: Path) -> list[str]:
    base = audio_root / collection
    if not base.is_dir():
        return []
    return sorted(p.name for p in base.iterdir() if p.is_dir() and p.name.startswith("S"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("collection", choices=["ayah", "summary"])
    parser.add_argument("surah_id", nargs="?", help="e.g. S001; omit when using --all")
    parser.add_argument("--all", action="store_true", help="process every surah folder present")
    parser.add_argument("--audio-root", type=Path, default=REPO_ROOT / "_audio" / "audio")
    parser.add_argument("--dry-run", action="store_true",
                         help="report what would be reused; copy nothing")
    args = parser.parse_args()

    if bool(args.surah_id) == bool(args.all):
        parser.error("pass exactly one of SURAH_ID or --all")

    surah_ids = (
        discover_surah_ids(args.collection, args.audio_root) if args.all else [args.surah_id]
    )
    if not surah_ids:
        print(f"No surah folders found for collection={args.collection!r}", file=sys.stderr)
        return 1

    totals = {"reused": 0, "alreadyDone": 0, "sourceNotSynthesized": 0, "noMatch": 0}
    for surah_id in surah_ids:
        result = reuse_for_surah(
            collection=args.collection, surah_id=surah_id,
            audio_root=args.audio_root, dry_run=args.dry_run,
        )
        print(json.dumps(result, ensure_ascii=False))
        for key in totals:
            totals[key] += result.get(key, 0)

    print(f"TOTAL: {json.dumps(totals)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
