#!/usr/bin/env python3
"""Shared helpers for every TTS *preparation* script under `_audio/scripts/`.

This module has no network code and never calls Google TTS. It only builds
the on-disk request/manifest shape that `synthesize_tts_chunks.py` consumes.
That separation is deliberate: preparation is cheap, deterministic, and safe
to re-run; synthesis costs money and talks to a remote API. Keeping them in
different files means re-running a prep script after fixing a typo never
re-triggers billed audio generation by accident.

Two collection families read this module:

- `prepare_recitation_chunks.py`  -> collection "recitation"
- `prepare_commentary_chunks.py`  -> collections "ayah", "summary", "surah"

Both end up calling `write_collection()`, which writes the same on-disk shape
`synthesize_tts_chunks.py` already knows how to consume (this shape was
reverse-engineered from the hand-built `quran-data/_audio/audio/ayah/S001`
pilot -- see `_audio/README.md` for the full provenance story):

    <out_dir>/
      <surahId>.md          human-readable clean-text copy (audit only)
      chunks.jsonl           canonical paragraph-level text -> audio mapping
      manifest.json           app/agent-facing summary of the same chunks
      requests/<chunkId>.json  one Google TTS request body per paragraph
      responses/               filled in later, by synthesize_tts_chunks.py
      originals/{wav,mp3}/     filled in later, by synthesize_tts_chunks.py
      sections/{wav,mp3}/      filled in later, by synthesize_tts_chunks.py

Voice and audio config are identical across every collection. Commentary
uses the conversational narrator prompt; canonical Quran reference chunks
use a strict prompt that forbids additions, repetition, translation, and
continuation. Recitation and commentary-reference requests still match each
other exactly, so synthesized reference audio remains reusable.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import fcntl
from pathlib import Path

# ---------------------------------------------------------------------------
# Voice, prompts, and audio config.
# Copied verbatim from latent_activation/_audio/tts-generation-spec.md and
# from the fields already recorded in the shipped S001 pilot manifest.
# ---------------------------------------------------------------------------

COMMENTARY_PROMPT = (
    "Speak as a warm, conversational Turkish narrator addressing one curious "
    "listener. Sound like a thoughtful person sharing a discovery as it becomes "
    "clear, with natural human cadence, varied sentence energy, and quiet "
    "curiosity. Let short reveal sentences land, then slow slightly for "
    "explanation. Use clear Istanbul Turkish diction and natural pauses. Avoid "
    "sermon, classroom lecture, documentary-announcer delivery, exaggerated "
    "drama, and a repeated rhetorical rise-and-fall. Do not give every section "
    "the same cadence. Pronounce Arabic Quranic words naturally as Arabic, then "
    "return smoothly to Turkish."
)

RECITATION_PROMPT = (
    "Read only the exact text in the text field. The text field is the complete "
    "script. Do not repeat, add, explain, translate, paraphrase, or continue it. "
    "Stop immediately after the final Arabic word. Say the Turkish label once, "
    "then recite the Arabic Quran text once, with a short natural pause after "
    "the label."
)

# Backward-compatible name for commentary callers. New request generation
# chooses a prompt explicitly for every paragraph kind.
PROMPT = COMMENTARY_PROMPT

AUDIO_CONFIG = {
    "audioEncoding": "LINEAR16",
    "pitch": 0,
    "speakingRate": 1,
}

VOICE = {
    "languageCode": "tr-TR",
    "modelName": "gemini-3.1-flash-tts-preview",
    "name": "Rasalgethi",
}

# The inline-gloss-span rule from COMMENTARY_SPEC.md SS "Arabic lexical items":
# authored prose carries `{ar:..., tr:..., gloss:...}` so one source can render
# for both reading (transliteration first) and listening (Arabic surface form)
# editions. For TTS we speak the Arabic surface form plus the Turkish gloss in
# parentheses, and drop the transliteration -- it exists only to help a reader
# who cannot see Arabic script; it is redundant once the Arabic is spoken aloud.
GLOSS_SPAN_RE = re.compile(r"\{ar:(.*?),\s*tr:(.*?),\s*gloss:(.*?)\}")

# Anything that still looks like an unconverted span after GLOSS_SPAN_RE has
# run means the source used a shape this regex didn't anticipate (extra
# whitespace, reordered fields, a typo). Per this project's own rule --
# "never silently repair; report gaps instead" (COMMENTARY_SPEC.md) -- that
# must fail loudly rather than ship literal `{ar:...}` markup into an audio
# script.
STRAY_SPAN_RE = re.compile(r"\{\s*(ar|tr|gloss)\s*:")


def convert_gloss_spans(text: str, *, source_label: str = "<text>") -> str:
    """Convert `{ar:X, tr:Y, gloss:Z}` -> `X (Z)` for spoken delivery.

    When the span is followed by a plain space -- the ordinary "prose keeps
    going" case, ~91% of occurrences in the real corpus -- a comma is
    inserted before that space, giving a deliberate TTS pause after every
    Arabic-plus-gloss insertion: `X (Z), `.

    That comma is deliberately NOT inserted when the span is followed by
    anything else, because ~9% of spans in the real corpus have a Turkish
    suffix or existing punctuation glued directly onto the closing brace,
    e.g. `{ar:نَصْرُ, tr:nasru, gloss:yardım}dur.` (-> must stay `yardım)dur.`,
    the suffix "-dur" attaches to the gloss word itself) or
    `{ar:فِى, tr:fî, gloss:içinde}'dir.` (apostrophe-suffix, same reason), or
    a span already followed by its own ',' / '.' / ':' / ';' in the source.
    Blindly appending a comma in those cases would either break the Turkish
    suffix attachment (inserting a word-breaking comma+space mid-word) or
    double up punctuation (", ,", ", ."). Only the unambiguous plain-space
    case gets the inserted comma; every other case is left exactly as the
    source had it.

    Raises ValueError if a `{ar:...}`-shaped span survives conversion, since
    that would otherwise speak raw markup aloud.
    """
    def repl(match: re.Match) -> str:
        ar = match.group(1).strip()
        gloss = match.group(3).strip()
        converted = f"{ar} ({gloss})"
        following = text[match.end():match.end() + 1]
        if following == " ":
            return f"{converted},"  # the untouched space after the match completes ", "
        return converted

    converted = GLOSS_SPAN_RE.sub(repl, text)
    stray = STRAY_SPAN_RE.search(converted)
    if stray:
        raise ValueError(
            f"Unconverted gloss span in {source_label} near: "
            f"{converted[max(0, stray.start() - 20): stray.start() + 40]!r}"
        )
    return converted


# ---------------------------------------------------------------------------
# Turkish ordinal numbers (1..999 is enough headroom; the longest surah,
# al-Baqara, has 286 ayahs). Hand-verified rule, not a general vowel-harmony
# algorithm: Turkish ordinal suffixes are irregular enough (dort -> dorduncu,
# bir -> birinci) that a lookup table for the ~19 base words is safer than a
# generated suffix. Only the LAST word of a compound cardinal number takes the
# ordinal suffix; every earlier word stays in plain cardinal form. E.g. 286 =
# "iki yuz seksen altı" (cardinal) -> "iki yuz seksen altıncı" (ordinal): only
# "altı" -> "altıncı" changes.
# ---------------------------------------------------------------------------

_UNITS = {1: "bir", 2: "iki", 3: "üç", 4: "dört", 5: "beş",
          6: "altı", 7: "yedi", 8: "sekiz", 9: "dokuz"}
_TENS = {1: "on", 2: "yirmi", 3: "otuz", 4: "kırk", 5: "elli",
         6: "altmış", 7: "yetmiş", 8: "seksen", 9: "doksan"}
_ORDINAL_SUFFIX = {
    "bir": "birinci", "iki": "ikinci", "üç": "üçüncü", "dört": "dördüncü",
    "beş": "beşinci", "altı": "altıncı", "yedi": "yedinci", "sekiz": "sekizinci",
    "dokuz": "dokuzuncu", "on": "onuncu", "yirmi": "yirminci", "otuz": "otuzuncu",
    "kırk": "kırkıncı", "elli": "ellinci", "altmış": "altmışıncı",
    "yetmiş": "yetmişinci", "seksen": "sekseninci", "doksan": "doksanıncı",
    "yüz": "yüzüncü",
}


def turkish_cardinal_components(n: int) -> list[str]:
    """Break n (1..999) into its spoken cardinal-number word components."""
    if not 1 <= n <= 999:
        raise ValueError(f"turkish_cardinal_components only supports 1..999, got {n}")
    components: list[str] = []
    hundreds, remainder = divmod(n, 100)
    if hundreds == 1:
        components.append("yüz")
    elif hundreds > 1:
        components.append(_UNITS[hundreds])
        components.append("yüz")
    tens, ones = divmod(remainder, 10)
    if tens:
        components.append(_TENS[tens])
    if ones:
        components.append(_UNITS[ones])
    return components


def turkish_ordinal(n: int) -> str:
    """1 -> 'birinci', 11 -> 'on birinci', 286 -> 'iki yuz seksen altıncı'."""
    components = turkish_cardinal_components(n)
    components[-1] = _ORDINAL_SUFFIX[components[-1]]
    return " ".join(components)


# ---------------------------------------------------------------------------
# Text plumbing shared by every collection.
# ---------------------------------------------------------------------------

def normalize_surah_id(surah_number: int) -> str:
    return f"S{surah_number:03d}"


def sentence_punctuate(text: str) -> str:
    text = text.strip()
    if text.endswith((".", "!", "?", ":", ";", "؛", "؟")):
        return text
    return f"{text}."


def extract_heading(markdown_text: str) -> tuple[str | None, str]:
    """If the text opens with a `# Heading` line, return (heading, rest).

    Otherwise return (None, markdown_text) unchanged. Only surah-reading
    files sometimes carry a title heading (confirmed inconsistent across the
    corpus: e.g. s001 has one, s019/s100 do not) -- callers must supply a
    fallback title when this returns None.
    """
    stripped = markdown_text.lstrip("﻿ \n\t")
    match = re.match(r"^#\s+(.+?)\s*(?:\n|$)", stripped)
    if not match:
        return None, markdown_text
    heading = match.group(1).strip()
    rest = stripped[match.end():]
    return heading, rest


def split_paragraphs(markdown_text: str) -> list[str]:
    """Split on blank-line-separated blocks; collapse internal whitespace.

    Source commentary paragraphs are already single logical lines, but this
    defensively collapses any soft-wrapped newlines so a paragraph never
    ships to TTS with a stray line break in the middle of a sentence.
    """
    normalized = markdown_text.replace("\r\n", "\n").replace("﻿", "")
    blocks = re.split(r"\n\s*\n", normalized.strip())
    paragraphs = []
    for block in blocks:
        block = re.sub(r"\s+", " ", block.strip())
        if block:
            paragraphs.append(block)
    return paragraphs


def ayah_spoken_label(surah_name: str, ayah_number: int) -> str:
    """'<name> <ordinal> ayet', or '<name> besmele' for the prefatory ayah 0.

    `quran-uthmani.tsv` carries an explicit `S:0` row for the basmalah before
    every surah except al-Fatiha (which has no separate 1:0 row -- its own
    1:1 *is* the basmalah) and at-Tawbah (which has none at all). There is no
    natural ordinal for "ayah zero", so the ayah_number == 0 branch here
    labels it distinctly rather than speaking a nonsensical ordinal.

    NOTE: `prepare_recitation_chunks.py` no longer calls this with
    ayah_number == 0 -- all 112 ':0' rows share one identical Arabic string,
    so recitation generates a single shared, surah-agnostic basmalah clip
    (build_besmele_section()) instead of 112 near-duplicate per-surah
    requests. The ayah_number == 0 branch below is kept for any other caller
    that needs a per-surah-labelled basmalah reference (e.g. if a future
    commentary tier ever covers the basmalah as its own ayah) and mirrors
    the explicit 1:1 <-> 1:0 boundary mapping STATUS.md already documents
    for the reader-facing side.
    """
    if ayah_number == 0:
        return f"{surah_name} besmele"
    return f"{surah_name} {turkish_ordinal(ayah_number)} ayet"


# ---------------------------------------------------------------------------
# Quran text / surah name lookups.
# ---------------------------------------------------------------------------

def load_quran_text(path: Path) -> dict[str, str]:
    """Parse `quran-uthmani.tsv` ('S:A|text' rows, pipe- not tab-delimited)."""
    text_by_ref: dict[str, str] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n").rstrip("\r")
            if not line or "|" not in line:
                continue
            ref, _, arabic = line.partition("|")
            text_by_ref[ref.strip()] = arabic.lstrip("﻿").strip()
    return text_by_ref


def surah_ayah_refs(quran_text: dict[str, str], surah_number: int) -> list[tuple[int, str]]:
    """[(ayah_number, ref), ...] for one surah, ascending, '0' (basmalah) first."""
    prefix = f"{surah_number}:"
    refs = []
    for ref in quran_text:
        if ref.startswith(prefix) and ref[len(prefix):].isdigit():
            refs.append((int(ref[len(prefix):]), ref))
    return sorted(refs)


def load_surah_names(path: Path) -> dict[int, str]:
    """Parse the `surah_number<TAB>name_tr` lookup table."""
    names: dict[int, str] = {}
    with path.open(encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    if not lines:
        raise ValueError(f"{path} is empty")
    for line in lines[1:]:  # skip header
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 2:
            raise ValueError(f"{path}: malformed row {line!r}")
        names[int(parts[0])] = parts[1].strip()
    return names


# ---------------------------------------------------------------------------
# JSON / hashing / atomic-write plumbing.
# Ported unchanged from latent_activation/_audio/scripts/prepare_tts_chunks.py
# so the hashes this module writes match what synthesize_tts_chunks.py
# recomputes when it validates a request file before calling the API.
# ---------------------------------------------------------------------------

def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(text, encoding="utf-8")
    os.replace(tmp_path, path)


def stable_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def prompt_for_kind(kind: str) -> tuple[str, str]:
    if kind in {"ayah_reference", "besmele_reference"}:
        return "recitation", RECITATION_PROMPT
    return "commentary", COMMENTARY_PROMPT


def build_request(text: str, *, prompt: str = COMMENTARY_PROMPT) -> dict:
    return {"audioConfig": AUDIO_CONFIG, "input": {"prompt": prompt, "text": text}, "voice": VOICE}


def request_hash(request: dict) -> str:
    return sha256_text(stable_json(request))


def cleanup_unreferenced_files(groups: list[tuple[Path, list[Path]]]) -> None:
    """Delete stale files left over from a previous prep run for this surah.

    Without this, shrinking a source (fewer paragraphs on a re-run) would
    leave orphaned request/audio files that chunks.jsonl no longer points to.
    """
    for directory, referenced in groups:
        if not directory.exists():
            continue
        referenced_resolved = {p.resolve() for p in referenced}
        for path in directory.glob("*"):
            if path.is_file() and path.resolve() not in referenced_resolved:
                path.unlink()


# ---------------------------------------------------------------------------
# The shared collection writer. Both prepare_recitation_chunks.py and
# prepare_commentary_chunks.py build a `sections` list and hand it to this
# function; it does not know or care which collection it is writing.
# ---------------------------------------------------------------------------

def write_clean_markdown(path: Path, sections: list[dict]) -> None:
    lines = []
    for index, section in enumerate(sections, start=1):
        heading_level = "#" if index == 1 else "##"
        lines.append(f"{heading_level} {section['title']}")
        lines.append("")
        for paragraph in section["paragraphs"]:
            if paragraph["kind"] == "section_title":
                continue  # already shown as the heading above
            lines.append(paragraph["text"])
            lines.append("")
    atomic_write_text(path, "\n".join(lines).rstrip() + "\n")


def write_collection(
    *,
    out_dir: Path,
    surah_id: str,
    collection: str,
    source: str,
    sources: list[str],
    sections: list[dict],
    extra_manifest_fields: dict | None = None,
) -> dict:
    """Write <surahId>.md, chunks.jsonl, manifest.json, and requests/*.json.

    `sections` shape (built by the caller):
        [{"title": str, "kind": str, "grades": list,
          "paragraphs": [{"kind": str, "text": str, "ttsText": str?}, ...]},
         ...]
    `ttsText` defaults to `text` when omitted (the common case -- only the
    ayah_reference and section_title paragraph kinds set it explicitly, to
    prepend a spoken label ahead of the same text shown for reading).

    Does not touch the network. Safe to re-run any number of times; it
    overwrites deterministically and prunes orphaned files from prior runs.
    """
    requests_dir = out_dir / "requests"
    responses_dir = out_dir / "responses"
    originals_wav_dir = out_dir / "originals" / "wav"
    originals_mp3_dir = out_dir / "originals" / "mp3"
    sections_wav_dir = out_dir / "sections" / "wav"
    sections_mp3_dir = out_dir / "sections" / "mp3"
    for directory in (requests_dir, responses_dir, originals_wav_dir,
                      originals_mp3_dir, sections_wav_dir, sections_mp3_dir):
        directory.mkdir(parents=True, exist_ok=True)

    write_clean_markdown(out_dir / f"{surah_id}.md", sections)

    chunks = []
    prompts = {
        "commentary": COMMENTARY_PROMPT,
        "recitation": RECITATION_PROMPT,
    }
    prompt_hashes = {name: sha256_text(prompt) for name, prompt in prompts.items()}
    voice_hash = sha256_text(stable_json(VOICE))
    audio_config_hash = sha256_text(stable_json(AUDIO_CONFIG))

    for section_index, section in enumerate(sections, start=1):
        section_chunks = []
        for paragraph_index, paragraph in enumerate(section["paragraphs"], start=1):
            chunk_id = f"sec-{section_index:03d}-p-{paragraph_index:03d}"
            tts_text = paragraph.get("ttsText") or paragraph["text"]
            prompt_kind, prompt = prompt_for_kind(paragraph["kind"])
            request = build_request(tts_text, prompt=prompt)
            request_sha256 = request_hash(request)
            atomic_write_text(
                requests_dir / f"{chunk_id}.json",
                json.dumps(request, ensure_ascii=False, indent=2) + "\n",
            )
            record = {
                "surahId": surah_id,
                "sourceKind": collection,
                "source": source,
                "chunkId": chunk_id,
                "sectionIndex": section_index,
                "paragraphIndex": paragraph_index,
                "kind": paragraph["kind"],
                "publicationKind": section.get("kind", collection),
                "grades": list(section.get("grades", [])),
                "sectionTitle": section["title"],
                "text": paragraph["text"],
                "ttsText": tts_text,
                "ttsCharCount": len(tts_text),
                "promptKind": prompt_kind,
                "promptCharCount": len(prompt),
                "request": f"requests/{chunk_id}.json",
                "response": f"responses/{chunk_id}.json",
                "wav": f"originals/wav/{chunk_id}.wav",
                "mp3": f"originals/mp3/{chunk_id}.mp3",
                "durationSeconds": None,
                "charCount": len(paragraph["text"]),
                "wordCount": len(paragraph["text"].split()),
                "textSha256": sha256_text(paragraph["text"]),
                "promptSha256": prompt_hashes[prompt_kind],
                "voiceSha256": voice_hash,
                "audioConfigSha256": audio_config_hash,
                "requestSha256": request_sha256,
            }
            chunks.append(record)
            section_chunks.append(record)
        section["chunks"] = section_chunks

    atomic_write_text(
        out_dir / "chunks.jsonl",
        "".join(json.dumps(chunk, ensure_ascii=False) + "\n" for chunk in chunks),
    )

    manifest = {
        "source": source,
        "sources": sources,
        "sourceKind": collection,
        "surahId": surah_id,
        "collection": collection,
        "cleanMarkdown": f"{surah_id}.md",
        "chunksJsonl": "chunks.jsonl",
        "prompt": COMMENTARY_PROMPT,
        "promptSha256": prompt_hashes["commentary"],
        "prompts": prompts,
        "promptSha256ByKind": prompt_hashes,
        "voice": VOICE,
        "audioConfig": AUDIO_CONFIG,
        "chunkCount": len(chunks),
    }
    manifest.update(extra_manifest_fields or {})
    manifest["sections"] = [
        {
            "sectionIndex": index,
            "title": section["title"],
            "kind": section.get("kind", collection),
            "grades": list(section.get("grades", [])),
            "wav": f"sections/wav/sec-{index:03d}.wav",
            "mp3": f"sections/mp3/sec-{index:03d}.mp3",
            "durationSeconds": None,
            "paragraphs": [
                {
                    key: chunk[key]
                    for key in ("paragraphIndex", "kind", "chunkId", "text",
                                "ttsText", "ttsCharCount", "promptKind",
                                "promptCharCount", "request", "response", "wav",
                                "mp3", "durationSeconds")
                }
                for chunk in section["chunks"]
            ],
        }
        for index, section in enumerate(sections, start=1)
    ]
    atomic_write_text(
        out_dir / "manifest.json",
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    )

    cleanup_unreferenced_files([
        (requests_dir, [out_dir / chunk["request"] for chunk in chunks]),
        (responses_dir, [out_dir / chunk["response"] for chunk in chunks]),
        (originals_wav_dir, [out_dir / chunk["wav"] for chunk in chunks]),
        (originals_mp3_dir, [out_dir / chunk["mp3"] for chunk in chunks]),
        (sections_wav_dir, [out_dir / s["wav"] for s in manifest["sections"]]),
        (sections_mp3_dir, [out_dir / s["mp3"] for s in manifest["sections"]]),
    ])

    return {"outDir": str(out_dir), "chunkCount": len(chunks), "sectionCount": len(sections)}


class CollectionLock:
    """Exclusive non-blocking lock shared by prepare, reuse, and synthesis."""

    def __init__(self, out_dir: Path):
        self.path = out_dir / ".tts-generation.lock"
        self.handle = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.is_symlink():
            raise ValueError(f"Refusing symlinked collection lock: {self.path}")
        self.handle = self.path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            self.handle.close()
            self.handle = None
            raise RuntimeError(
                f"Another TTS process holds the collection lock: {self.path}"
            ) from error
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.handle is not None:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
            self.handle.close()
            self.handle = None


if __name__ == "__main__":
    # Manual self-check for the ordinal function -- run `python3 tts_common.py`
    # after editing it. Not a substitute for the pytest-style checks a cold
    # agent should still run against real corpus data (see _audio/README.md).
    samples = [1, 2, 3, 4, 6, 7, 9, 10, 11, 19, 20, 26, 30, 40, 50, 60, 70, 80,
               90, 99, 100, 101, 111, 150, 200, 219, 286]
    for n in samples:
        print(f"{n:>3} -> {turkish_ordinal(n)}")
