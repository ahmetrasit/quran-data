#!/usr/bin/env python3
"""Prepare TTS request chunks for the standalone "recitation" collection.

This is "Group 1" of the audio pipeline. It is the counterpart to the
"ayah_reference" lead paragraph already embedded inside each ayah in the
`ayah` commentary collection (see prepare_commentary_chunks.py) -- but here
it stands alone, one short audio file per ayah, with no commentary prose
attached: just the spoken surah name, ayah ordinal, and the canonical Arabic
ayah text. Source data is exactly two files, no prose_generation commentary
involved at all:

  data/text/quran-uthmani.tsv                    canonical Arabic text
  _audio/audio/recitation/surah-names.tr.tsv      Turkish surah names

Each ayah becomes its own SECTION with exactly one paragraph:

    kind: "ayah_reference"
    text:    "<arabic ayah text>"                       (display/audit)
    ttsText: "<name> <ordinal> ayet. <arabic ayah text>"  (spoken)

The `sectionTitle` (and therefore the "S001.md" clean-text heading) uses the
digit form "<name> <number>" rather than the spelled-out ordinal, e.g.
"Fatiha 1" -- matching the original recitation spec literally ("<surah name>
<ayah number>: <arabic>") for the human-readable/audit label, while the
*spoken* ttsText still uses the spelled-out ordinal ("... birinci ayet...")
because digits do not reliably read naturally aloud. This is a deliberate
split between the display and speech forms; see ayah_spoken_label() and its
docstring in tts_common.py.

Basmalah handling. `quran-uthmani.tsv` carries an explicit ':0' row (the
basmalah) before every surah except al-Fatiha (whose own 1:1 *is* the
basmalah -- there is no separate 1:0 row) and at-Tawbah (which has none at
all) -- 112 rows in total. All 112 share exactly one identical Arabic string
(verified). Per-ayah sections therefore SKIP ':0' rows entirely -- see
build_recitation_sections() -- rather than generating 112 near-duplicate
TTS requests that differ only by which surah name is prefixed to identical
Arabic. Instead there is exactly one shared, surah-agnostic basmalah clip,
built by --besmele into `_audio/audio/recitation/besmele/`. Playback/app
assembly is expected to prepend that one clip before every surah's own
recitation, except S001 and S009. This script does not splice it into each
surah's own folder -- see build_besmele_section().

Usage:
    prepare_recitation_chunks.py 1
    prepare_recitation_chunks.py 9 --dry-run
    prepare_recitation_chunks.py --all
    prepare_recitation_chunks.py --besmele
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import tts_common as common

REPO_ROOT = Path(__file__).resolve().parents[2]  # .../quran-data


def default_paths(repo_root: Path) -> dict[str, Path]:
    return {
        "quran_text": repo_root / "data" / "text" / "quran-uthmani.tsv",
        "surah_names": repo_root / "_audio" / "audio" / "recitation" / "surah-names.tr.tsv",
        "out_root": repo_root / "_audio" / "audio" / "recitation",
    }


def build_recitation_sections(
    *, surah_number: int, surah_name: str, quran_text: dict[str, str],
) -> list[dict]:
    refs = common.surah_ayah_refs(quran_text, surah_number)
    refs = [(ayah_number, ref) for ayah_number, ref in refs if ayah_number != 0]
    if not refs:
        return []
    sections = []
    for ayah_number, ref in refs:
        arabic = quran_text[ref]
        spoken_label = common.ayah_spoken_label(surah_name, ayah_number)
        display_label = f"{surah_name} {ayah_number}"
        sections.append({
            "title": display_label,
            "kind": "recitation",
            "grades": [],
            "paragraphs": [{
                "kind": "ayah_reference",
                "text": arabic,
                "ttsText": f"{spoken_label}. {arabic}",
            }],
        })
    return sections


def build_besmele_section(quran_text: dict[str, str]) -> list[dict]:
    """The single shared, surah-agnostic basmalah clip.

    All 112 ':0' rows in quran-uthmani.tsv (every surah except al-Fatiha and
    at-Tawbah) were verified to carry the exact same Arabic string, so one
    recitation covers every placement -- no surah name is prefixed here,
    unlike the per-ayah sections, because this clip is meant to be reused as
    a generic lead-in rather than regenerated per surah.
    """
    basmalah_texts = {text for ref, text in quran_text.items() if ref.endswith(":0")}
    if not basmalah_texts:
        raise ValueError("No ':0' basmalah rows found in quran-uthmani.tsv")
    if len(basmalah_texts) != 1:
        raise ValueError(
            f"Expected exactly one shared basmalah text across all ':0' rows, "
            f"found {len(basmalah_texts)}: {basmalah_texts}"
        )
    arabic = next(iter(basmalah_texts))
    return [{
        "title": "Besmele",
        "kind": "recitation",
        "grades": [],
        "paragraphs": [{
            "kind": "besmele_reference",
            "text": arabic,
            "ttsText": f"Besmele. {arabic}",
        }],
    }]


def process_one(
    *, surah_number: int, quran_text: dict[str, str], surah_names: dict[int, str],
    out_root: Path, quran_text_relpath: str, dry_run: bool,
) -> dict | None:
    surah_name = surah_names.get(surah_number)
    if surah_name is None:
        raise ValueError(
            f"No Turkish name for surah {surah_number} in surah-names.tr.tsv"
        )
    sections = build_recitation_sections(
        surah_number=surah_number, surah_name=surah_name, quran_text=quran_text,
    )
    if not sections:
        return None
    surah_id = common.normalize_surah_id(surah_number)

    if dry_run:
        print(json.dumps({
            "surahId": surah_id,
            "collection": "recitation",
            "sectionCount": len(sections),
            "sample": {
                "firstTitle": sections[0]["title"],
                "firstTtsText": sections[0]["paragraphs"][0]["ttsText"],
                "lastTitle": sections[-1]["title"],
                "lastTtsText": sections[-1]["paragraphs"][0]["ttsText"],
            },
        }, ensure_ascii=False, indent=2))
        return {"outDir": None, "chunkCount": len(sections), "sectionCount": len(sections)}

    out_dir = out_root / surah_id
    with common.CollectionLock(out_dir):
        result = common.write_collection(
            out_dir=out_dir,
            surah_id=surah_id,
            collection="recitation",
            source=quran_text_relpath,
            sources=[quran_text_relpath],
            sections=sections,
            extra_manifest_fields={
                "arabicTextSource": quran_text_relpath,
                "titleHandling": (
                    "Each section is exactly one ayah_reference paragraph: "
                    "sectionTitle uses the digit form '<name> <number>' (or "
                    "'<name> besmele' for the ayah-0 basmalah row); ttsText "
                    "speaks the surah name and spelled-out ordinal ayet label "
                    "followed by the canonical Arabic text. No commentary prose."
                ),
            },
        )
    print(json.dumps(result, ensure_ascii=False))
    return result


def process_besmele(
    *, quran_text: dict[str, str], out_root: Path, quran_text_relpath: str, dry_run: bool,
) -> dict:
    sections = build_besmele_section(quran_text)
    surah_id = "besmele"

    if dry_run:
        print(json.dumps({
            "surahId": surah_id,
            "collection": "recitation",
            "sectionCount": len(sections),
            "sample": {"ttsText": sections[0]["paragraphs"][0]["ttsText"]},
        }, ensure_ascii=False, indent=2))
        return {"outDir": None, "chunkCount": 1, "sectionCount": 1}

    out_dir = out_root / surah_id
    with common.CollectionLock(out_dir):
        result = common.write_collection(
            out_dir=out_dir,
            surah_id=surah_id,
            collection="recitation",
            source=quran_text_relpath,
            sources=[quran_text_relpath],
            sections=sections,
            extra_manifest_fields={
                "arabicTextSource": quran_text_relpath,
                "titleHandling": (
                    "Single shared, surah-agnostic basmalah clip -- not tied to "
                    "any one surah name. All 112 ':0' rows in quran-uthmani.tsv "
                    "share one identical Arabic string, so this one recitation "
                    "covers every placement."
                ),
                "reuseNote": (
                    "Playback/app assembly should prepend this clip before every "
                    "surah's own recitation except S001 (al-Fatiha, whose own "
                    "ayah 1 IS the basmalah) and S009 (at-Tawbah, which has no "
                    "basmalah at all). This script does not concatenate it into "
                    "each surah's own folder -- per-surah recitation sections "
                    "(build_recitation_sections) skip ':0' rows entirely."
                ),
            },
        )
    print(json.dumps(result, ensure_ascii=False))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("surah_number", type=int, nargs="?",
                         help="1-114; omit when using --all or --besmele")
    parser.add_argument("--all", action="store_true", help="process every surah, 1-114")
    parser.add_argument("--besmele", action="store_true",
                         help="generate only the single shared generic basmalah clip "
                              "(_audio/audio/recitation/besmele/), reused before every "
                              "surah except S001 and S009")
    parser.add_argument("--quran-text", type=Path, default=None)
    parser.add_argument("--surah-names", type=Path, default=None)
    parser.add_argument("--out-root", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true",
                         help="parse and report chunk counts; write nothing to disk")
    args = parser.parse_args()

    mode_count = sum([bool(args.surah_number), args.all, args.besmele])
    if mode_count != 1:
        parser.error("pass exactly one of SURAH_NUMBER, --all, or --besmele")

    paths = default_paths(REPO_ROOT)
    quran_text_path = args.quran_text or paths["quran_text"]
    surah_names_path = args.surah_names or paths["surah_names"]
    out_root = args.out_root or paths["out_root"]
    quran_text_relpath = str(quran_text_path.resolve().relative_to(REPO_ROOT))

    quran_text = common.load_quran_text(quran_text_path)

    if args.besmele:
        process_besmele(
            quran_text=quran_text, out_root=out_root,
            quran_text_relpath=quran_text_relpath, dry_run=args.dry_run,
        )
        return 0

    surah_names = common.load_surah_names(surah_names_path)

    surah_numbers = (
        sorted({int(ref.split(":")[0]) for ref in quran_text})
        if args.all else [args.surah_number]
    )

    processed, skipped, failed = [], [], []
    for surah_number in surah_numbers:
        try:
            result = process_one(
                surah_number=surah_number, quran_text=quran_text, surah_names=surah_names,
                out_root=out_root, quran_text_relpath=quran_text_relpath, dry_run=args.dry_run,
            )
        except Exception as error:  # noqa: BLE001 -- surface every failure, keep going under --all
            failed.append((surah_number, str(error)))
            print(f"S{surah_number:03d}: FAILED: {error}", file=sys.stderr)
            continue
        if result is None:
            skipped.append(surah_number)
        else:
            processed.append(surah_number)

    if args.all:
        print(
            f"processed={len(processed)} skipped={len(skipped)} failed={len(failed)}",
            file=sys.stderr,
        )

    if failed:
        return 1
    if not processed and not args.dry_run:
        print(f"No surahs processed for surah_number={args.surah_number}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
