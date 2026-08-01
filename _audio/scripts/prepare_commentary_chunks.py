#!/usr/bin/env python3
"""Prepare TTS request chunks for the three commentary collections.

This is "Group 2" of the audio pipeline: it turns prose_generation's staged
Turkish commentary (imported into `data/commentary/`) into the
request/manifest shape `synthesize_tts_chunks.py` sends to Google TTS. It
never calls the network itself -- see tts_common.py's module docstring for
why preparation and synthesis are deliberately separate scripts.

Three collections, three different source shapes:

  ayah     data/commentary/ayah/detailed/tr/sNNN/{S}_{A}.prose.tr.md
           Full per-ayah commentary. One audio SECTION per ayah, containing:
             1. an "ayah_reference" paragraph = spoken surah+ordinal label
                followed by the canonical Arabic ayah text (from
                quran-uthmani.tsv) -- e.g. "Fatiha birinci ayet. بسم..."
             2. one "paragraph" per blank-line-separated prose paragraph in
                the source file, with {ar,tr,gloss} spans converted for
                speech.
           Only *.prose.tr.md is used -- evidence/friction/index/findings
           files are the evidence apparatus COMMENTARY_SPEC.md explicitly
           keeps out of reader-facing prose ("the prose must be readable end
           to end with the evidence surface closed"), so they are excluded
           from audio for the same reason. This matches the S001 precedent.

  summary  data/commentary/ayah/summary/tr/sNNN/{S}_{A}.prose.summary.tr.md
           Same per-ayah section shape as `ayah`, just a shorter source
           text. Some summary files also carry {ar,tr,gloss} spans (verified
           in s087-s092) even though the earliest examples (s001, s103)
           happen not to -- the span conversion always runs regardless.

  surah    data/commentary/surah/detailed/tr/sNNN/{S}.surah-reading.tr.md
           One audio SECTION for the whole surah (not one per ayah -- this
           tier is a continuous essay, not ayah-anchored). First paragraph
           is a spoken "section_title" (the file's `# Heading` if present,
           else a synthesized "<name> Suresi Okumasi" fallback -- headings
           are inconsistently present across the corpus, confirmed absent in
           e.g. s019 and s100). No Arabic/ayah_reference lead here: a
           surah-reading essay is not anchored to one ayah's Arabic text.

Usage:
    prepare_commentary_chunks.py ayah 1
    prepare_commentary_chunks.py summary 100 --dry-run
    prepare_commentary_chunks.py surah --all

Output lands at `_audio/audio/<collection>/<surahId>/` by default -- see
--out-root to redirect (used by this script's own self-tests).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import tts_common as common

REPO_ROOT = Path(__file__).resolve().parents[2]  # .../quran-data


def default_paths(repo_root: Path) -> dict[str, Path]:
    return {
        "commentary_root": repo_root / "data" / "commentary",
        "quran_text": repo_root / "data" / "text" / "quran-uthmani.tsv",
        "surah_names": repo_root / "_audio" / "audio" / "recitation" / "surah-names.tr.tsv",
        "out_root": repo_root / "_audio" / "audio",
    }


# ---------------------------------------------------------------------------
# Source discovery
# ---------------------------------------------------------------------------

_AYAH_FILENAME_RE = re.compile(r"^(\d+)_(\d+)\.")


def _find_ayah_files(directory: Path, surah_number: int, suffix: str) -> list[tuple[int, Path]]:
    """Return [(ayah_number, path), ...] sorted, for files 'N_A.<suffix>'."""
    if not directory.is_dir():
        return []
    found = []
    for path in directory.glob(f"{surah_number}_*.{suffix}"):
        match = _AYAH_FILENAME_RE.match(path.name)
        if not match:
            continue
        file_surah, file_ayah = int(match.group(1)), int(match.group(2))
        if file_surah != surah_number:
            # Defensive: a stray '11_3....' file should never end up under a
            # glob scoped to surah 1's own directory, but never silently
            # accept a mismatch if it somehow does.
            raise ValueError(
                f"{path} is in the surah {surah_number} directory but its "
                f"filename says surah {file_surah}"
            )
        found.append((file_ayah, path))
    return sorted(found)


def discover_surahs(commentary_root: Path, collection: str) -> list[int]:
    """List every surah number that has source material for `collection`."""
    if collection == "ayah":
        base = commentary_root / "ayah" / "detailed" / "tr"
        pattern = "*.prose.tr.md"
    elif collection == "summary":
        base = commentary_root / "ayah" / "summary" / "tr"
        pattern = "*.prose.summary.tr.md"
    elif collection == "surah":
        base = commentary_root / "surah" / "detailed" / "tr"
        pattern = "*.surah-reading.tr.md"
    else:
        raise ValueError(collection)
    if not base.is_dir():
        return []
    numbers = set()
    for surah_dir in base.glob("s*"):
        if not surah_dir.is_dir():
            continue
        if any(surah_dir.glob(pattern)):
            numbers.add(int(surah_dir.name.lstrip("s")))
    return sorted(numbers)


# ---------------------------------------------------------------------------
# Section builders -- one per collection shape.
# ---------------------------------------------------------------------------

def _build_ayah_style_sections(
    *, surah_number: int, surah_name: str, ayah_files: list[tuple[int, Path]],
    quran_text: dict[str, str], collection: str,
) -> list[dict]:
    sections = []
    for ayah_number, path in ayah_files:
        ayah_ref = f"{surah_number}:{ayah_number}"
        arabic = quran_text.get(ayah_ref)
        if arabic is None:
            raise ValueError(
                f"No Quran text for {ayah_ref} in quran-uthmani.tsv, needed by {path}"
            )
        spoken_label = common.ayah_spoken_label(surah_name, ayah_number)
        raw_text = path.read_text(encoding="utf-8")
        converted = common.convert_gloss_spans(raw_text, source_label=str(path))
        body_paragraphs = common.split_paragraphs(converted)
        if not body_paragraphs:
            raise ValueError(f"{path} produced zero paragraphs after cleaning")
        paragraphs = [{
            "kind": "ayah_reference",
            "text": arabic,
            "ttsText": f"{spoken_label}. {arabic}",
        }]
        paragraphs += [{"kind": "paragraph", "text": p} for p in body_paragraphs]
        sections.append({
            "title": spoken_label,
            "kind": f"{collection}_detailed" if collection == "ayah" else "ayah_summary",
            "grades": [],
            "paragraphs": paragraphs,
        })
    return sections


def _build_surah_section(
    *, surah_number: int, surah_name: str, surah_reading_path: Path,
) -> list[dict]:
    raw_text = surah_reading_path.read_text(encoding="utf-8")
    converted = common.convert_gloss_spans(raw_text, source_label=str(surah_reading_path))
    heading, rest = common.extract_heading(converted)
    title = heading if heading else f"{surah_name} Suresi Okuması"
    body_paragraphs = common.split_paragraphs(rest)
    if not body_paragraphs:
        raise ValueError(f"{surah_reading_path} produced zero body paragraphs after cleaning")
    paragraphs = [{
        "kind": "section_title",
        "text": title,
        "ttsText": common.sentence_punctuate(title),
    }]
    paragraphs += [{"kind": "paragraph", "text": p} for p in body_paragraphs]
    return [{
        "title": title,
        "kind": "surah_reading",
        "grades": [],
        "paragraphs": paragraphs,
    }]


# ---------------------------------------------------------------------------
# Per-surah orchestration
# ---------------------------------------------------------------------------

def process_one(
    *, surah_number: int, collection: str, commentary_root: Path,
    quran_text: dict[str, str], surah_names: dict[int, str], out_root: Path,
    dry_run: bool,
) -> dict | None:
    surah_name = surah_names.get(surah_number)
    if surah_name is None:
        raise ValueError(
            f"No Turkish name for surah {surah_number} in surah-names.tr.tsv"
        )
    surah_id = common.normalize_surah_id(surah_number)

    if collection == "ayah":
        src_dir = commentary_root / "ayah" / "detailed" / "tr" / f"s{surah_number:03d}"
        ayah_files = _find_ayah_files(src_dir, surah_number, "prose.tr.md")
        if not ayah_files:
            return None
        sections = _build_ayah_style_sections(
            surah_number=surah_number, surah_name=surah_name, ayah_files=ayah_files,
            quran_text=quran_text, collection="ayah",
        )
        sources = [str(p.relative_to(REPO_ROOT)) for _, p in ayah_files]
        extra = {
            "sourceDirectory": str(src_dir.relative_to(REPO_ROOT)),
            "arabicTextSource": "data/text/quran-uthmani.tsv",
            "inlineGlossConversion": "{ar, tr, gloss} -> Arabic (gloss); transliteration omitted",
            "titleHandling": (
                "Ayah reference is a standalone first ttsText: Turkish surah "
                "name and spelled-out ordinal label followed by canonical "
                "Arabic text; analysis prose follows without a label."
            ),
        }
    elif collection == "summary":
        src_dir = commentary_root / "ayah" / "summary" / "tr" / f"s{surah_number:03d}"
        ayah_files = _find_ayah_files(src_dir, surah_number, "prose.summary.tr.md")
        if not ayah_files:
            return None
        sections = _build_ayah_style_sections(
            surah_number=surah_number, surah_name=surah_name, ayah_files=ayah_files,
            quran_text=quran_text, collection="summary",
        )
        sources = [str(p.relative_to(REPO_ROOT)) for _, p in ayah_files]
        extra = {
            "sourceDirectory": str(src_dir.relative_to(REPO_ROOT)),
            "arabicTextSource": "data/text/quran-uthmani.tsv",
            "inlineGlossConversion": "{ar, tr, gloss} -> Arabic (gloss); transliteration omitted",
            "titleHandling": (
                "Ayah reference is a standalone first ttsText: Turkish surah "
                "name and spelled-out ordinal label followed by canonical "
                "Arabic text; compact summary prose follows without a label."
            ),
        }
    elif collection == "surah":
        src_file = (
            commentary_root / "surah" / "detailed" / "tr" / f"s{surah_number:03d}"
            / f"{surah_number}.surah-reading.tr.md"
        )
        if not src_file.is_file():
            return None
        sections = _build_surah_section(
            surah_number=surah_number, surah_name=surah_name, surah_reading_path=src_file,
        )
        sources = [str(src_file.relative_to(REPO_ROOT))]
        extra = {
            "sourceDirectory": str(src_file.parent.relative_to(REPO_ROOT)),
            "titleHandling": (
                "First chunk of the (single) section is a spoken title: the "
                "source file's leading '# Heading' when present, else a "
                "synthesized '<name> Suresi Okumasi' fallback. No per-ayah "
                "Arabic reference -- this tier is a continuous surah-wide "
                "essay, not anchored to one ayah."
            ),
        }
    else:
        raise ValueError(collection)

    if dry_run:
        total_paragraphs = sum(len(s["paragraphs"]) for s in sections)
        print(json.dumps({
            "surahId": surah_id,
            "collection": collection,
            "sectionCount": len(sections),
            "paragraphCount": total_paragraphs,
            "sample": {
                "firstSectionTitle": sections[0]["title"],
                "firstTtsText": (sections[0]["paragraphs"][0].get("ttsText")
                                  or sections[0]["paragraphs"][0]["text"])[:160],
            },
        }, ensure_ascii=False, indent=2))
        return {"outDir": None, "chunkCount": total_paragraphs, "sectionCount": len(sections)}

    out_dir = out_root / collection / surah_id
    common.check_generation_lock(out_dir)
    result = common.write_collection(
        out_dir=out_dir,
        surah_id=surah_id,
        collection=collection,
        source=sources[0],
        sources=sources,
        sections=sections,
        extra_manifest_fields=extra,
    )
    print(json.dumps(result, ensure_ascii=False))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("collection", choices=["ayah", "summary", "surah"])
    parser.add_argument("surah_number", type=int, nargs="?",
                         help="1-114; omit when using --all")
    parser.add_argument("--all", action="store_true",
                         help="process every surah with source material for this collection")
    parser.add_argument("--commentary-root", type=Path, default=None)
    parser.add_argument("--quran-text", type=Path, default=None)
    parser.add_argument("--surah-names", type=Path, default=None)
    parser.add_argument("--out-root", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true",
                         help="parse and report chunk counts; write nothing to disk")
    args = parser.parse_args()

    if bool(args.surah_number) == bool(args.all):
        parser.error("pass exactly one of SURAH_NUMBER or --all")

    paths = default_paths(REPO_ROOT)
    commentary_root = args.commentary_root or paths["commentary_root"]
    quran_text_path = args.quran_text or paths["quran_text"]
    surah_names_path = args.surah_names or paths["surah_names"]
    out_root = args.out_root or paths["out_root"]

    quran_text = common.load_quran_text(quran_text_path)
    surah_names = common.load_surah_names(surah_names_path)

    surah_numbers = (
        discover_surahs(commentary_root, args.collection)
        if args.all else [args.surah_number]
    )
    if not surah_numbers:
        print(f"No source material found for collection={args.collection!r}", file=sys.stderr)
        return 1

    processed, skipped, failed = [], [], []
    for surah_number in surah_numbers:
        try:
            result = process_one(
                surah_number=surah_number, collection=args.collection,
                commentary_root=commentary_root, quran_text=quran_text,
                surah_names=surah_names, out_root=out_root, dry_run=args.dry_run,
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
        if skipped:
            print(f"skipped (no source material): {skipped}", file=sys.stderr)

    if failed:
        return 1
    if not processed and not args.dry_run:
        print(f"No surahs processed for surah_number={args.surah_number}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
