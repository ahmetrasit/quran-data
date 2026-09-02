#!/usr/bin/env python3
"""Build the release-owned QAC/grammar/MASAQ/word-analysis bridge.

QAC morpheme refs (S:A:W:M) are the canonical Arabic occurrence units.  The
other identifiers remain typed source identities and are connected to QAC by
explicit, many-to-many edges.  Surface alignment is evidence for those edges;
it never aliases a three-part source ref to a QAC word ref.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[2]
QAC_PATH = ROOT / "data/morphology/qac.sqlite.gz"
SOURCE_PATH = ROOT / "data/bridges/qac-masaq/source-units.tsv.gz"
SOURCE_MANIFEST_PATH = ROOT / "data/bridges/qac-masaq/SOURCE.json"
TRACE_DECISIONS_PATH = (
    ROOT / "data/bridges/qac-masaq/reviewed-trace-decisions.tsv"
)
DECISIONS_PATH = ROOT / "data/bridges/qac-masaq/reviewed-decisions.tsv"
MASAQ_QAC_DECISIONS_PATH = (
    ROOT / "data/bridges/qac-masaq/reviewed-masaq-qac-decisions.tsv"
)
ATTACHMENT_DECISIONS_PATH = (
    ROOT / "data/bridges/qac-masaq/reviewed-attachment-decisions.tsv"
)
WORD_ANALYSIS_DIR = ROOT / "data/analysis/word-analysis"
ATTACHMENTS_PATH = ROOT / "data/grammar/attachments/attachments.tsv"
RELEASE_MANIFEST_PATH = ROOT / "RELEASE.json"
DEFAULT_OUTPUT = ROOT / "data/bridges/qac-masaq.sqlite.gz"
DEFAULT_AUDIT = ROOT / "data/bridges/qac-masaq-audit.json"

SCHEMA_VERSION = "qac-masaq-bridge-v1"
BUILDER_VERSION = "qac-masaq-bridge-builder-2026-09-02.13"
ARABIC_TAG_RE = re.compile(r"\{\{ar:([^}]*)\}\}")
THREE_PART_REF_RE = re.compile(r"^(\d+):(\d+):(\d+)$")
FOUR_PART_REF_RE = re.compile(r"^(\d+):(\d+):(\d+):(\d+)$")
ATTACHMENT_UNIT_REF_RE = re.compile(r"^q:(\d+):(\d+):(\d+)$")
MAX_SOURCE_UNITS_PER_QAC_WORD = 8
ACCEPTED_MASAQ_TRACE_STATUSES = {
    "exact",
    "approved-rule",
    "approved-exception",
    "reviewed-alignment",
}
EXCLUDED_SOURCE_TRACE_STATUSES = {"rejected-source-defect"}
ATTACHMENT_SUFFIX_PARTS = {
    "pronoun_suffix",
    "object_suffix",
    "possessive_suffix",
}
ATTACHMENT_PARTS = ATTACHMENT_SUFFIX_PARTS | {
    "",
    "whole_word",
    "particle_segment",
    "subject_agreement",
    "preposition",
}
QAC_PRONOMINAL_POS = {"PRON", "REL"}
QAC_PREPOSITION_POS = {"P", "PREP", "PRP"}
ATTACHMENT_CARRIER_RULES = {
    "fused-agreement-carrier",
    "fused-preposition-carrier",
    "fused-suffix-carrier",
}

# These are identity-preserving orthographic folds, not token identity rules.
PRECOMPOSED_FOLD = str.maketrans(
    {
        "ٱ": "ا",
        "أ": "ء",
        "إ": "ء",
        "آ": "ا",
        "ؤ": "ء",
        "ئ": "ء",
        "ى": "ي",
        "ی": "ي",
        "ک": "ك",
    }
)
SIN_SAD_FOLD = str.maketrans({"ص": "س"})
ANNOTATION_CODEPOINTS = set(range(0x06D6, 0x06EE)) | {0x0640}


@dataclass(frozen=True)
class QacMorpheme:
    ref: str
    word_ref: str
    surah: int
    ayah: int
    word_index: int
    morpheme_index: int
    surface_ar: str
    stem_ar: str
    pos: str
    role: str


@dataclass(frozen=True)
class QacWord:
    ref: str
    surah: int
    ayah: int
    word_index: int
    morphemes: tuple[QacMorpheme, ...]

    @property
    def surface_ar(self) -> str:
        return "".join(item.surface_ar for item in self.morphemes)


@dataclass(frozen=True)
class GrammarUnit:
    ref: str
    surah: int
    ayah: int
    unit_index: int
    surface_ar: str
    grammar: str
    tag: str
    trace_type: str
    trace_status: str
    trace_rule_id: str
    trace_evidence: str
    masaq_refs: tuple[str, ...]
    masaq_segment_count: int
    alignment_group_id: str
    grammar_order_within_group: str
    masaq_order_within_group: str
    masaq_source_status: str
    masaq_full_surfaces_ar: tuple[str, ...]
    masaq_stems: tuple[str, ...]
    masaq_tags: tuple[str, ...]
    masaq_roles: tuple[str, ...]
    masaq_roots_ar: tuple[str, ...]
    masaq_source_lines: tuple[str, ...]
    masaq_source_statuses: tuple[str, ...]


@dataclass(frozen=True)
class AnalysisUnit:
    ref: str
    surah: int
    ayah: int
    critical_w: int
    surface_ar: str


@dataclass(frozen=True)
class ReviewedDecision:
    decision_id: str
    grammar_ref: str
    qac_refs: tuple[str, ...]
    decision_type: str
    reason: str
    review_status: str
    reviewed_on: str


@dataclass(frozen=True)
class ReviewedMasaqQacDecision:
    decision_id: str
    grammar_ref: str
    masaq_segment_ref: str
    qac_refs: tuple[str, ...]
    decision_type: str
    reason: str
    review_status: str
    reviewed_on: str


@dataclass(frozen=True)
class ReviewedAttachmentDecision:
    decision_id: str
    attachment_unit_ref: str
    attachment_id: str
    endpoint_role: str
    decision_type: str
    target_namespace: str
    target_ref: str
    reason: str
    review_status: str
    reviewed_on: str


@dataclass(frozen=True)
class MasaqQacPath:
    masaq_segment_ref: str
    qac_morpheme_ref: str
    grammar_ref: str
    alignment_group_id: str
    trace_status: str
    accepted: int
    reviewed_decision_id: str | None


@dataclass(frozen=True)
class AttachmentResolution:
    attachment_unit_ref: str
    target_namespace: str
    target_ref: str
    resolution_rule: str
    reviewed_decision_id: str | None


@dataclass(frozen=True)
class AttachmentEndpoint:
    attachment_id: str
    endpoint_role: str
    attachment_unit_ref: str
    endpoint_part: str
    surface_ar: str
    form_tag: str


@dataclass(frozen=True)
class AttachmentQacEdge:
    attachment_id: str
    endpoint_role: str
    attachment_unit_ref: str
    endpoint_part: str
    surface_ar: str
    form_tag: str
    qac_morpheme_ref: str
    target_order: int
    alignment_rule: str
    alignment_reviewed_decision_id: str | None


@dataclass(frozen=True)
class AttachmentExclusion:
    attachment_id: str
    endpoint_role: str
    attachment_unit_ref: str
    reviewed_decision_id: str


@dataclass(frozen=True)
class SurfaceRelation:
    rank: int
    rule: str
    edit_distance: int
    length_delta: int

    @property
    def cost(self) -> int:
        base = (0, 100, 250, 400, 800, 5000)[self.rank]
        return base + self.edit_distance * 50 + self.length_delta


@dataclass(frozen=True)
class UnitMapping:
    grammar_ref: str
    qac_refs: tuple[str, ...]
    qac_word_refs: tuple[str, ...]
    rule: str
    rank: int
    edit_distance: int
    cost: int
    source_surface_ar: str
    target_surface_ar: str


@dataclass(frozen=True)
class BlockAlignment:
    mappings: tuple[UnitMapping, ...]
    cost: int
    ambiguity_count: int
    uncovered_visible_refs: tuple[str, ...]
    concatenated_edit_distance: int


@dataclass(frozen=True)
class AyahAlignment:
    mappings: tuple[UnitMapping, ...]
    ambiguity_count: int
    block_sizes: tuple[int, ...]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_json(payload: object) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


@lru_cache(maxsize=None)
def normalize_surface(text: str) -> str:
    text = text.translate(PRECOMPOSED_FOLD)
    output: list[str] = []
    for char in unicodedata.normalize("NFKD", text):
        if unicodedata.category(char) in {"Mn", "Me", "Cf"}:
            continue
        if ord(char) in ANNOTATION_CODEPOINTS:
            continue
        if char.isspace() or char in {"|", "ـ"}:
            continue
        output.append(char)
    return "".join(output)


@lru_cache(maxsize=None)
def folded_surface(text: str) -> str:
    value = normalize_surface(text).replace("ء", "ا").replace("ة", "ه")
    return re.sub("ا+", "ا", value)


@lru_cache(maxsize=None)
def consonant_surface(text: str) -> str:
    return normalize_surface(text).replace("ا", "").replace("ء", "")


@lru_cache(maxsize=None)
def weak_consonant_surface(text: str) -> str:
    value = consonant_surface(text)
    return value.replace("و", "").replace("ي", "")


@lru_cache(maxsize=None)
def collapse_doubled_letters(text: str) -> str:
    value = normalize_surface(text)
    return "".join(
        char for index, char in enumerate(value) if index == 0 or char != value[index - 1]
    )


@lru_cache(maxsize=None)
def levenshtein(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    if len(left) > len(right):
        left, right = right, left
    previous = list(range(len(left) + 1))
    for right_index, right_char in enumerate(right, start=1):
        current = [right_index]
        for left_index, left_char in enumerate(left, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[left_index] + 1,
                    previous[left_index - 1] + (left_char != right_char),
                )
            )
        previous = current
    return previous[-1]


@lru_cache(maxsize=None)
def surface_relation(source: str, target: str) -> SurfaceRelation:
    source_norm = normalize_surface(source)
    target_norm = normalize_surface(target)
    if not source_norm or not target_norm:
        return SurfaceRelation(
            5,
            "empty-or-unusable-surface",
            max(len(source_norm), len(target_norm)),
            0,
        )
    delta = abs(len(source_norm) - len(target_norm))
    if source_norm == target_norm:
        return SurfaceRelation(0, "normalized-exact", 0, 0)
    if collapse_doubled_letters(source) == collapse_doubled_letters(target):
        return SurfaceRelation(1, "gemination-fold-exact", 0, delta)
    source_consonants = consonant_surface(source)
    target_consonants = consonant_surface(target)
    if (
        len(source_consonants) >= 2
        and source_consonants == target_consonants
    ):
        return SurfaceRelation(1, "long-vowel-fold-exact", 0, delta)
    if (
        source_norm in target_norm
        or source_norm.startswith(target_norm)
        or source_norm.endswith(target_norm)
    ):
        return SurfaceRelation(1, "normalized-containment", 0, delta)

    source_folded = folded_surface(source)
    target_folded = folded_surface(target)
    folded_delta = abs(len(source_folded) - len(target_folded))
    if source_folded == target_folded:
        return SurfaceRelation(2, "orthographic-fold-exact", 0, folded_delta)
    source_weak = weak_consonant_surface(source)
    target_weak = weak_consonant_surface(target)
    if len(source_weak) >= 2 and source_weak == target_weak:
        return SurfaceRelation(2, "weak-letter-fold-exact", 0, delta)
    if source_norm.translate(SIN_SAD_FOLD) == target_norm.translate(SIN_SAD_FOLD):
        return SurfaceRelation(2, "uthmani-sin-sad-fold-exact", 0, delta)
    if source_folded in target_folded or target_folded in source_folded:
        return SurfaceRelation(3, "orthographic-fold-containment", 0, folded_delta)
    if target_norm in source_norm:
        return SurfaceRelation(3, "normalized-internal-containment", 0, delta)

    if source_consonants and target_consonants and (
        source_consonants == target_consonants
        or source_consonants in target_consonants
        or target_consonants in source_consonants
    ):
        consonant_delta = abs(len(source_consonants) - len(target_consonants))
        return SurfaceRelation(4, "alif-hamza-skeleton", 0, consonant_delta)

    strict_edit = levenshtein(source_norm, target_norm)
    folded_edit = levenshtein(source_folded, target_folded)
    weak_edit = (
        levenshtein(source_weak, target_weak)
        if source_weak and target_weak
        else max(len(source_norm), len(target_norm))
    )
    edit = min(strict_edit, folded_edit, weak_edit + 1)
    return SurfaceRelation(5, "edit-fallback", edit, delta)


def parse_arabic_surface(surface_display: object) -> str:
    match = ARABIC_TAG_RE.search(str(surface_display or ""))
    return match.group(1) if match else ""


def load_qac(path: Path) -> tuple[dict[tuple[int, int], tuple[QacWord, ...]], list[QacMorpheme]]:
    raw = gzip.decompress(path.read_bytes())
    with tempfile.NamedTemporaryFile(suffix=".sqlite") as handle:
        handle.write(raw)
        handle.flush()
        connection = sqlite3.connect(handle.name)
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT qac_ref, qac_word_ref, surah, ayah, word_index,
                   morpheme_index, surface_ar, stem_ar, pos, morpheme_role
              FROM qac_morphemes
          ORDER BY surah, ayah, word_index, morpheme_index
            """
        ).fetchall()
        connection.close()

    all_morphemes = [
        QacMorpheme(
            ref=str(row["qac_ref"]),
            word_ref=str(row["qac_word_ref"]),
            surah=int(row["surah"]),
            ayah=int(row["ayah"]),
            word_index=int(row["word_index"]),
            morpheme_index=int(row["morpheme_index"]),
            surface_ar=str(row["surface_ar"] or ""),
            stem_ar=str(row["stem_ar"] or ""),
            pos=str(row["pos"] or ""),
            role=str(row["morpheme_role"] or ""),
        )
        for row in rows
    ]
    by_word: dict[str, list[QacMorpheme]] = defaultdict(list)
    seen_refs: set[str] = set()
    for item in all_morphemes:
        match = FOUR_PART_REF_RE.fullmatch(item.ref)
        if match is None:
            raise RuntimeError(f"invalid QAC morpheme ref: {item.ref}")
        if item.ref in seen_refs:
            raise RuntimeError(f"duplicate QAC morpheme ref: {item.ref}")
        seen_refs.add(item.ref)
        if tuple(int(part) for part in match.groups()) != (
            item.surah,
            item.ayah,
            item.word_index,
            item.morpheme_index,
        ):
            raise RuntimeError(f"QAC morpheme ref fields disagree: {item.ref}")
        expected_word_ref = f"{item.surah}:{item.ayah}:{item.word_index}"
        if item.word_ref != expected_word_ref:
            raise RuntimeError(
                f"QAC word parent disagrees at {item.ref}: {item.word_ref}"
            )
        by_word[item.word_ref].append(item)

    by_ayah: dict[tuple[int, int], list[QacWord]] = defaultdict(list)
    for word_ref, morphemes in by_word.items():
        first = morphemes[0]
        if [item.morpheme_index for item in morphemes] != list(
            range(1, len(morphemes) + 1)
        ):
            raise RuntimeError(f"non-contiguous QAC morpheme indices at {word_ref}")
        by_ayah[(first.surah, first.ayah)].append(
            QacWord(
                ref=word_ref,
                surah=first.surah,
                ayah=first.ayah,
                word_index=first.word_index,
                morphemes=tuple(morphemes),
            )
        )
    for words in by_ayah.values():
        words.sort(key=lambda item: item.word_index)
        if [item.word_index for item in words] != list(range(1, len(words) + 1)):
            first = words[0]
            raise RuntimeError(
                f"non-contiguous QAC word indices at {first.surah}:{first.ayah}"
            )
    return {key: tuple(value) for key, value in by_ayah.items()}, all_morphemes


def split_source_values(value: str, count: int, field: str, ref: str) -> tuple[str, ...]:
    if count == 0:
        if value:
            raise RuntimeError(f"unexpected {field} without MASAQ refs at {ref}")
        return ()
    parts = tuple(value.split("|"))
    if len(parts) != count:
        raise RuntimeError(
            f"{field} count mismatch at {ref}: {len(parts)} != {count}"
        )
    return parts


def load_source_units(
    path: Path,
) -> tuple[dict[tuple[int, int], tuple[GrammarUnit, ...]], list[GrammarUnit]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {
            "surah",
            "ayah",
            "grammar_ref",
            "grammar_unit_index",
            "surface_ar",
            "trace_status",
            "masaq_refs",
            "masaq_segment_count",
            "alignment_group_id",
            "grammar_order_within_group",
            "masaq_order_within_group",
            "masaq_full_surface_ar",
            "masaq_stems",
            "masaq_tags",
            "masaq_roles",
            "masaq_roots_ar",
            "masaq_source_lines",
            "masaq_source_statuses",
        }
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            missing = sorted(required - set(reader.fieldnames or ()))
            raise RuntimeError(f"source projection is missing columns: {missing}")
        units: list[GrammarUnit] = []
        for row in reader:
            refs = tuple(part for part in row["masaq_refs"].split("|") if part)
            count = int(row["masaq_segment_count"] or "0")
            unit = GrammarUnit(
                ref=row["grammar_ref"],
                surah=int(row["surah"]),
                ayah=int(row["ayah"]),
                unit_index=int(row["grammar_unit_index"]),
                surface_ar=row["surface_ar"],
                grammar=row.get("grammar", ""),
                tag=row.get("tag", ""),
                trace_type=row.get("trace_type", ""),
                trace_status=row.get("trace_status", ""),
                trace_rule_id=row.get("trace_rule_id", ""),
                trace_evidence=row.get("trace_evidence", ""),
                masaq_refs=refs,
                masaq_segment_count=count,
                alignment_group_id=row["alignment_group_id"],
                grammar_order_within_group=row["grammar_order_within_group"],
                masaq_order_within_group=row["masaq_order_within_group"],
                masaq_source_status=row.get("masaq_source_status", ""),
                masaq_full_surfaces_ar=split_source_values(
                    row["masaq_full_surface_ar"],
                    count,
                    "masaq_full_surface_ar",
                    row["grammar_ref"],
                ),
                masaq_stems=split_source_values(
                    row["masaq_stems"], count, "masaq_stems", row["grammar_ref"]
                ),
                masaq_tags=split_source_values(
                    row["masaq_tags"], count, "masaq_tags", row["grammar_ref"]
                ),
                masaq_roles=split_source_values(
                    row["masaq_roles"], count, "masaq_roles", row["grammar_ref"]
                ),
                masaq_roots_ar=split_source_values(
                    row["masaq_roots_ar"], count, "masaq_roots_ar", row["grammar_ref"]
                ),
                masaq_source_lines=split_source_values(
                    row["masaq_source_lines"], count, "masaq_source_lines", row["grammar_ref"]
                ),
                masaq_source_statuses=split_source_values(
                    row["masaq_source_statuses"],
                    count,
                    "masaq_source_statuses",
                    row["grammar_ref"],
                ),
            )
            match = THREE_PART_REF_RE.fullmatch(unit.ref)
            if match is None or tuple(map(int, match.groups())) != (
                unit.surah,
                unit.ayah,
                unit.unit_index,
            ):
                raise RuntimeError(f"invalid grammar unit ref: {unit.ref}")
            if len(refs) != unit.masaq_segment_count:
                raise RuntimeError(f"MASAQ ref count mismatch at {unit.ref}")
            if any(THREE_PART_REF_RE.fullmatch(ref) is None for ref in refs):
                raise RuntimeError(f"invalid MASAQ ref at {unit.ref}")
            units.append(unit)

    if len({item.ref for item in units}) != len(units):
        raise RuntimeError("duplicate grammar unit refs")
    by_ayah: dict[tuple[int, int], list[GrammarUnit]] = defaultdict(list)
    for unit in units:
        by_ayah[(unit.surah, unit.ayah)].append(unit)
    for key, values in by_ayah.items():
        values.sort(key=lambda item: item.unit_index)
        if len({item.unit_index for item in values}) != len(values):
            raise RuntimeError(f"duplicate grammar unit index in {key[0]}:{key[1]}")
    return {key: tuple(value) for key, value in by_ayah.items()}, units


def decompress_zstd(path: Path) -> bytes:
    executable = shutil.which("zstd")
    if executable is None:
        raise RuntimeError("zstd is required to read word-analysis shards")
    result = subprocess.run(
        [executable, "-dc", str(path)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"cannot decompress {path}: {detail}")
    return result.stdout


def word_analysis_source(directory: Path) -> dict[str, Any]:
    paths = sorted(directory.glob("s[0-9][0-9][0-9].jsonl.zst"))
    rows: list[bytes] = []
    shard_hashes: dict[str, str] = {}
    for path in paths:
        digest = sha256_bytes(path.read_bytes())
        shard_hashes[path.stem.removesuffix(".jsonl")] = digest
        rows.append(
            f"{path.name}\t{path.stat().st_size}\t{digest}\n".encode("utf-8")
        )
    return {
        "path": str(directory.relative_to(ROOT)),
        "shardCount": len(paths),
        "fileTreeSha256": sha256_bytes(b"".join(rows)),
        "shardSha256": shard_hashes,
    }


def load_analysis_units(directory: Path) -> list[AnalysisUnit]:
    paths = sorted(directory.glob("s[0-9][0-9][0-9].jsonl.zst"))
    if len(paths) != 114:
        raise RuntimeError(f"expected 114 word-analysis shards, found {len(paths)}")
    units: list[AnalysisUnit] = []
    seen: set[str] = set()
    ayahs: set[tuple[int, int]] = set()
    for path in paths:
        for line in decompress_zstd(path).decode("utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            ayah_ref = str(record.get("ref", ""))
            parts = ayah_ref.split(":")
            if len(parts) != 2 or not all(part.isdigit() for part in parts):
                raise RuntimeError(f"invalid analysis ayah ref: {ayah_ref}")
            surah, ayah = map(int, parts)
            ayahs.add((surah, ayah))
            local_seen: set[int] = set()
            for word in record.get("words") or []:
                critical_w = word.get("critical_w")
                if (
                    not isinstance(critical_w, int)
                    or isinstance(critical_w, bool)
                    or critical_w <= 0
                ):
                    raise RuntimeError(f"invalid critical_w in {ayah_ref}: {critical_w!r}")
                if critical_w in local_seen:
                    raise RuntimeError(f"duplicate critical_w in {ayah_ref}: {critical_w}")
                local_seen.add(critical_w)
                ref = f"{ayah_ref}:{critical_w}"
                if ref in seen:
                    raise RuntimeError(f"duplicate analysis ref: {ref}")
                seen.add(ref)
                units.append(
                    AnalysisUnit(
                        ref=ref,
                        surah=surah,
                        ayah=ayah,
                        critical_w=critical_w,
                        surface_ar=parse_arabic_surface(word.get("surface_display")),
                    )
                )
    if len(ayahs) != 6_236:
        raise RuntimeError(f"expected 6,236 analysis ayahs, found {len(ayahs)}")
    return units


def load_reviewed_decisions(path: Path) -> list[ReviewedDecision]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {
            "decision_id",
            "grammar_ref",
            "qac_morpheme_refs",
            "decision_type",
            "reason",
            "review_status",
            "reviewed_on",
        }
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            missing = sorted(required - set(reader.fieldnames or ()))
            raise RuntimeError(f"reviewed decision ledger is missing columns: {missing}")
        decisions = [
            ReviewedDecision(
                decision_id=row["decision_id"],
                grammar_ref=row["grammar_ref"],
                qac_refs=tuple(
                    part for part in row["qac_morpheme_refs"].split("|") if part
                ),
                decision_type=row["decision_type"],
                reason=row["reason"],
                review_status=row["review_status"],
                reviewed_on=row["reviewed_on"],
            )
            for row in reader
        ]
    if len({item.decision_id for item in decisions}) != len(decisions):
        raise RuntimeError("duplicate reviewed decision id")
    if len({item.grammar_ref for item in decisions}) != len(decisions):
        raise RuntimeError("duplicate reviewed decision grammar ref")
    for item in decisions:
        if item.review_status != "accepted":
            raise RuntimeError(f"non-accepted reviewed decision: {item.decision_id}")
        if THREE_PART_REF_RE.fullmatch(item.grammar_ref) is None or not item.qac_refs:
            raise RuntimeError(f"invalid reviewed decision: {item.decision_id}")
        if any(FOUR_PART_REF_RE.fullmatch(ref) is None for ref in item.qac_refs):
            raise RuntimeError(f"invalid QAC ref in reviewed decision: {item.decision_id}")
    return decisions


def load_reviewed_masaq_qac_decisions(
    path: Path,
) -> list[ReviewedMasaqQacDecision]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {
            "decision_id",
            "grammar_ref",
            "masaq_segment_ref",
            "qac_morpheme_refs",
            "decision_type",
            "reason",
            "review_status",
            "reviewed_on",
        }
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            missing = sorted(required - set(reader.fieldnames or ()))
            raise RuntimeError(
                f"MASAQ/QAC decision ledger is missing columns: {missing}"
            )
        decisions = [
            ReviewedMasaqQacDecision(
                decision_id=row["decision_id"],
                grammar_ref=row["grammar_ref"],
                masaq_segment_ref=row["masaq_segment_ref"],
                qac_refs=tuple(
                    part for part in row["qac_morpheme_refs"].split("|") if part
                ),
                decision_type=row["decision_type"],
                reason=row["reason"],
                review_status=row["review_status"],
                reviewed_on=row["reviewed_on"],
            )
            for row in reader
        ]
    if len({item.decision_id for item in decisions}) != len(decisions):
        raise RuntimeError("duplicate MASAQ/QAC decision id")
    if len({(item.grammar_ref, item.masaq_segment_ref) for item in decisions}) != len(
        decisions
    ):
        raise RuntimeError("duplicate MASAQ/QAC grammar-segment decision")
    for item in decisions:
        if item.review_status != "accepted":
            raise RuntimeError(
                f"non-accepted MASAQ/QAC decision: {item.decision_id}"
            )
        grammar_match = THREE_PART_REF_RE.fullmatch(item.grammar_ref)
        masaq_match = THREE_PART_REF_RE.fullmatch(item.masaq_segment_ref)
        if grammar_match is None or masaq_match is None or not item.qac_refs:
            raise RuntimeError(f"invalid MASAQ/QAC decision: {item.decision_id}")
        ayah = grammar_match.groups()[:2]
        if masaq_match.groups()[:2] != ayah or any(
            (match := FOUR_PART_REF_RE.fullmatch(ref)) is None
            or match.groups()[:2] != ayah
            for ref in item.qac_refs
        ):
            raise RuntimeError(f"cross-ayah MASAQ/QAC decision: {item.decision_id}")
    return decisions


def load_attachment_refs(
    path: Path,
) -> tuple[list[AttachmentEndpoint], set[str], dict[str, Any]]:
    endpoint_fields = (
        (
            "dependent",
            "dep_wid",
            "dep_unit_id",
            "dep_part",
            "dep_surface",
            "dep_form_tag",
        ),
        (
            "head",
            "head_wid",
            "head_unit_id",
            "head_part",
            "head_surface",
            "head_form_tag",
        ),
        (
            "preposition",
            "prep_wid",
            "prep_unit_id",
            None,
            "prep_base",
            None,
        ),
    )
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"unit_id", "sura", "ayah"}
        required.update(
            field
            for descriptor in endpoint_fields
            for field in descriptor[1:]
            if field is not None
        )
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            missing = sorted(required - set(reader.fieldnames or ()))
            raise RuntimeError(f"attachment source is missing columns: {missing}")

        attachment_ids: set[str] = set()
        endpoints: list[AttachmentEndpoint] = []
        attachment_refs: set[str] = set()
        endpoint_occurrences = 0
        row_count = 0
        for row in reader:
            row_count += 1
            attachment_id = row["unit_id"]
            if not attachment_id or attachment_id in attachment_ids:
                raise RuntimeError(f"duplicate or empty attachment id: {attachment_id!r}")
            attachment_ids.add(attachment_id)
            try:
                row_ayah = (int(row["sura"]), int(row["ayah"]))
            except ValueError as error:
                raise RuntimeError(
                    f"invalid attachment position at {attachment_id}"
                ) from error

            for (
                endpoint_role,
                wid_field,
                ref_field,
                part_field,
                surface_field,
                form_tag_field,
            ) in endpoint_fields:
                wid = row[wid_field]
                ref = row[ref_field]
                if bool(wid) != bool(ref):
                    raise RuntimeError(
                        f"attachment endpoint fields disagree at {attachment_id}: "
                        f"{wid_field}={wid!r}, {ref_field}={ref!r}"
                    )
                if not ref:
                    continue
                match = ATTACHMENT_UNIT_REF_RE.fullmatch(ref)
                if match is None:
                    raise RuntimeError(
                        f"invalid attachment endpoint at {attachment_id}: {ref!r}"
                    )
                ref_key = tuple(int(part) for part in match.groups())
                if ref_key[:2] != row_ayah or not wid.isdigit() or int(wid) != ref_key[2]:
                    raise RuntimeError(
                        f"attachment endpoint position mismatch at {attachment_id}: {ref}"
                    )
                attachment_refs.add(ref)
                endpoint_occurrences += 1
                endpoints.append(
                    AttachmentEndpoint(
                        attachment_id=attachment_id,
                        endpoint_role=endpoint_role,
                        attachment_unit_ref=ref,
                        endpoint_part=(
                            "preposition" if part_field is None else row[part_field]
                        ),
                        surface_ar=row[surface_field],
                        form_tag=("" if form_tag_field is None else row[form_tag_field]),
                    )
                )

    if row_count != 58_427:
        raise RuntimeError(f"expected 58,427 attachments, found {row_count}")
    return endpoints, attachment_refs, {
        "path": str(path.relative_to(ROOT)),
        "sha256": sha256_bytes(path.read_bytes()),
        "attachmentCount": row_count,
        "endpointOccurrenceCount": endpoint_occurrences,
        "uniqueEndpointCount": len(attachment_refs),
    }


def load_reviewed_attachment_decisions(
    path: Path,
) -> list[ReviewedAttachmentDecision]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {
            "decision_id",
            "attachment_unit_ref",
            "attachment_id",
            "endpoint_role",
            "decision_type",
            "target_namespace",
            "target_ref",
            "reason",
            "review_status",
            "reviewed_on",
        }
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            missing = sorted(required - set(reader.fieldnames or ()))
            raise RuntimeError(
                f"attachment decision ledger is missing columns: {missing}"
            )
        decisions = [
            ReviewedAttachmentDecision(
                decision_id=row["decision_id"],
                attachment_unit_ref=row["attachment_unit_ref"],
                attachment_id=row["attachment_id"],
                endpoint_role=row["endpoint_role"],
                decision_type=row["decision_type"],
                target_namespace=row["target_namespace"],
                target_ref=row["target_ref"],
                reason=row["reason"],
                review_status=row["review_status"],
                reviewed_on=row["reviewed_on"],
            )
            for row in reader
        ]
    if len({item.decision_id for item in decisions}) != len(decisions):
        raise RuntimeError("duplicate attachment decision id")
    redirects = [
        item for item in decisions if item.decision_type == "namespace-redirect"
    ]
    exclusions = [
        item for item in decisions if item.decision_type == "exclude-source-defect"
    ]
    carrier_approvals = [
        item for item in decisions if item.decision_type == "approve-fused-carrier"
    ]
    if len({item.attachment_unit_ref for item in redirects}) != len(redirects):
        raise RuntimeError("duplicate reviewed attachment redirect")
    occurrence_scopes = {
        (item.attachment_id, item.endpoint_role, item.attachment_unit_ref)
        for item in (*exclusions, *carrier_approvals)
    }
    if len(occurrence_scopes) != len(exclusions) + len(carrier_approvals):
        raise RuntimeError("duplicate reviewed attachment occurrence decision")
    for item in decisions:
        if item.review_status != "accepted":
            raise RuntimeError(
                f"non-accepted attachment decision: {item.decision_id}"
            )
        if item.decision_type == "namespace-redirect":
            source_match = ATTACHMENT_UNIT_REF_RE.fullmatch(
                item.attachment_unit_ref
            )
            target_match = THREE_PART_REF_RE.fullmatch(item.target_ref)
            if (
                source_match is None
                or target_match is None
                or item.attachment_id
                or item.endpoint_role
                or item.target_namespace
                not in {"grammar-unit", "masaq-segment"}
                or source_match.groups()[:2] != target_match.groups()[:2]
            ):
                raise RuntimeError(
                    f"invalid attachment redirect: {item.decision_id}"
                )
        elif item.decision_type == "exclude-source-defect":
            if (
                not item.attachment_id
                or item.endpoint_role
                not in {"", "dependent", "head", "preposition"}
                or item.target_namespace
                or item.target_ref
                or (
                    item.attachment_unit_ref
                    and ATTACHMENT_UNIT_REF_RE.fullmatch(
                        item.attachment_unit_ref
                    )
                    is None
                )
            ):
                raise RuntimeError(
                    f"invalid attachment occurrence decision: {item.decision_id}"
                )
        elif item.decision_type == "approve-fused-carrier":
            source_match = ATTACHMENT_UNIT_REF_RE.fullmatch(
                item.attachment_unit_ref
            )
            target_match = FOUR_PART_REF_RE.fullmatch(item.target_ref)
            if (
                not item.attachment_id
                or item.endpoint_role
                not in {"dependent", "head", "preposition"}
                or source_match is None
                or item.target_namespace != "qac-morpheme"
                or target_match is None
                or source_match.groups()[:2] != target_match.groups()[:2]
            ):
                raise RuntimeError(
                    f"invalid fused-carrier approval: {item.decision_id}"
                )
        else:
            raise RuntimeError(
                f"unknown attachment decision type: {item.decision_id} "
                f"{item.decision_type!r}"
            )
    return decisions


def apply_reviewed_decisions(
    mappings: dict[str, UnitMapping],
    qac_morphemes: Sequence[QacMorpheme],
    decisions: Sequence[ReviewedDecision],
) -> tuple[dict[str, UnitMapping], dict[str, Any]]:
    qac_by_ref = {item.ref: item for item in qac_morphemes}
    result = dict(mappings)
    rows: list[dict[str, Any]] = []
    for decision in decisions:
        automatic = result.get(decision.grammar_ref)
        if automatic is None:
            raise RuntimeError(
                f"reviewed decision references unknown grammar unit: {decision.grammar_ref}"
            )
        missing_qac = [ref for ref in decision.qac_refs if ref not in qac_by_ref]
        if missing_qac:
            raise RuntimeError(
                f"reviewed decision {decision.decision_id} has unknown QAC refs: {missing_qac}"
            )
        grammar_ayah = ":".join(decision.grammar_ref.split(":")[:2])
        if any(":".join(ref.split(":")[:2]) != grammar_ayah for ref in decision.qac_refs):
            raise RuntimeError(f"cross-ayah reviewed decision: {decision.decision_id}")
        qac_words = sorted(
            {qac_by_ref[ref].word_ref for ref in decision.qac_refs},
            key=ref_sort_key,
        )
        target = "".join(qac_by_ref[ref].surface_ar for ref in decision.qac_refs)
        result[decision.grammar_ref] = UnitMapping(
            grammar_ref=automatic.grammar_ref,
            qac_refs=decision.qac_refs,
            qac_word_refs=tuple(qac_words),
            rule=f"reviewed-{decision.decision_type}",
            rank=automatic.rank,
            edit_distance=automatic.edit_distance,
            cost=automatic.cost,
            source_surface_ar=automatic.source_surface_ar,
            target_surface_ar=target,
        )
        rows.append(
            {
                "decisionId": decision.decision_id,
                "grammarRef": decision.grammar_ref,
                "decisionType": decision.decision_type,
                "qacMorphemeRefs": list(decision.qac_refs),
                "automaticQacMorphemeRefs": list(automatic.qac_refs),
                "automaticRule": automatic.rule,
                "changedAutomaticMapping": automatic.qac_refs != decision.qac_refs,
                "reason": decision.reason,
                "reviewedOn": decision.reviewed_on,
            }
        )
    return result, {
        "path": str(DECISIONS_PATH.relative_to(ROOT)),
        "sha256": sha256_bytes(DECISIONS_PATH.read_bytes()),
        "count": len(decisions),
        "decisions": rows,
    }


def build_masaq_qac_paths(
    source_units: Sequence[GrammarUnit],
    mappings: dict[str, UnitMapping],
    qac_morphemes: Sequence[QacMorpheme],
    decisions: Sequence[ReviewedMasaqQacDecision],
) -> tuple[list[MasaqQacPath], dict[str, Any]]:
    source_by_ref = {item.ref: item for item in source_units}
    qac_refs = {item.ref for item in qac_morphemes}
    decision_by_pair = {
        (item.grammar_ref, item.masaq_segment_ref): item for item in decisions
    }
    for decision in decisions:
        source = source_by_ref.get(decision.grammar_ref)
        mapping = mappings.get(decision.grammar_ref)
        if source is None or mapping is None:
            raise RuntimeError(
                f"MASAQ/QAC decision references unknown grammar unit: "
                f"{decision.decision_id}"
            )
        if decision.masaq_segment_ref not in source.masaq_refs:
            raise RuntimeError(
                f"MASAQ/QAC decision references an unrelated segment: "
                f"{decision.decision_id}"
            )
        if len(set(decision.qac_refs)) != len(decision.qac_refs):
            raise RuntimeError(
                f"duplicate QAC ref in MASAQ/QAC decision: {decision.decision_id}"
            )
        if any(ref not in qac_refs or ref not in mapping.qac_refs for ref in decision.qac_refs):
            raise RuntimeError(
                f"MASAQ/QAC decision leaves its grammar span: {decision.decision_id}"
            )

    required_pairs = {
        (unit.ref, masaq_ref)
        for unit in source_units
        if len(unit.masaq_refs) > 1
        for masaq_ref in unit.masaq_refs
    }
    missing_pairs = sorted(required_pairs - set(decision_by_pair))
    if missing_pairs:
        raise RuntimeError(
            f"multi-segment grammar mappings require reviewed MASAQ/QAC spans: "
            f"{missing_pairs}"
        )

    paths: list[MasaqQacPath] = []
    for unit in source_units:
        mapping = mappings[unit.ref]
        accepted = int(unit.trace_status in ACCEPTED_MASAQ_TRACE_STATUSES)
        for masaq_ref in unit.masaq_refs:
            decision = decision_by_pair.get((unit.ref, masaq_ref))
            target_refs = decision.qac_refs if decision else mapping.qac_refs
            for qac_ref in target_refs:
                paths.append(
                    MasaqQacPath(
                        masaq_segment_ref=masaq_ref,
                        qac_morpheme_ref=qac_ref,
                        grammar_ref=unit.ref,
                        alignment_group_id=unit.alignment_group_id,
                        trace_status=unit.trace_status,
                        accepted=accepted,
                        reviewed_decision_id=(decision.decision_id if decision else None),
                    )
                )

    path_keys = {
        (item.masaq_segment_ref, item.qac_morpheme_ref, item.grammar_ref)
        for item in paths
    }
    if len(path_keys) != len(paths):
        raise RuntimeError("duplicate MASAQ/QAC path")
    source_masaq_refs = {ref for unit in source_units for ref in unit.masaq_refs}
    linked_masaq_refs = {
        item.masaq_segment_ref for item in paths if item.accepted
    }
    if linked_masaq_refs != source_masaq_refs:
        missing = sorted(source_masaq_refs - linked_masaq_refs, key=ref_sort_key)
        raise RuntimeError(f"accepted MASAQ segments without QAC paths: {missing[:20]}")

    ordered = sorted(
        paths,
        key=lambda item: (
            ref_sort_key(item.masaq_segment_ref),
            ref_sort_key(item.qac_morpheme_ref),
            ref_sort_key(item.grammar_ref),
        ),
    )
    direct_edges = {
        (item.masaq_segment_ref, item.qac_morpheme_ref)
        for item in ordered
        if item.accepted
    }
    return ordered, {
        "path": str(MASAQ_QAC_DECISIONS_PATH.relative_to(ROOT)),
        "sha256": sha256_bytes(MASAQ_QAC_DECISIONS_PATH.read_bytes()),
        "decisionCount": len(decisions),
        "pathCount": len(ordered),
        "acceptedPathCount": sum(item.accepted for item in ordered),
        "acceptedDirectEdgeCount": len(direct_edges),
    }


def resolve_attachment_units(
    attachment_refs: set[str],
    source_units: Sequence[GrammarUnit],
    mappings: dict[str, UnitMapping],
    masaq_paths: Sequence[MasaqQacPath],
    decisions: Sequence[ReviewedAttachmentDecision],
) -> tuple[list[AttachmentResolution], dict[str, Any]]:
    source_by_ref = {item.ref: item for item in source_units}
    redirect_decisions = [
        item for item in decisions if item.decision_type == "namespace-redirect"
    ]
    decision_by_ref = {
        item.attachment_unit_ref: item for item in redirect_decisions
    }
    unused_decisions = sorted(set(decision_by_ref) - attachment_refs)
    if unused_decisions:
        raise RuntimeError(
            f"attachment decisions reference unused endpoints: {unused_decisions}"
        )

    accepted_masaq_qac: dict[str, set[str]] = defaultdict(set)
    for path in masaq_paths:
        if path.accepted:
            accepted_masaq_qac[path.masaq_segment_ref].add(path.qac_morpheme_ref)

    resolutions: list[AttachmentResolution] = []
    qac_edge_count = 0
    for attachment_ref in sorted(
        attachment_refs,
        key=lambda value: ref_sort_key(value.removeprefix("q:")),
    ):
        decision = decision_by_ref.get(attachment_ref)
        if decision is None:
            target_namespace = "grammar-unit"
            target_ref = attachment_ref.removeprefix("q:")
            resolution_rule = "identity-grammar-unit"
            reviewed_decision_id = None
        else:
            target_namespace = decision.target_namespace
            target_ref = decision.target_ref
            resolution_rule = "reviewed-namespace-redirect"
            reviewed_decision_id = decision.decision_id

        if target_namespace == "grammar-unit":
            source = source_by_ref.get(target_ref)
            if source is None:
                raise RuntimeError(
                    f"attachment endpoint has no grammar unit: {attachment_ref}"
                )
            if source.trace_status in EXCLUDED_SOURCE_TRACE_STATUSES:
                raise RuntimeError(
                    f"attachment endpoint targets an excluded grammar unit without "
                    f"a reviewed redirect: {attachment_ref}"
                )
            target_qac_refs = set(mappings[target_ref].qac_refs)
        elif target_namespace == "masaq-segment":
            target_qac_refs = accepted_masaq_qac.get(target_ref, set())
            if not target_qac_refs:
                raise RuntimeError(
                    f"attachment endpoint has no accepted MASAQ/QAC edge: "
                    f"{attachment_ref} -> {target_ref}"
                )
        else:
            raise RuntimeError(
                f"unsupported attachment target namespace: {target_namespace}"
            )

        attachment_ayah = attachment_ref.removeprefix("q:").split(":")[:2]
        if any(ref.split(":")[:2] != attachment_ayah for ref in target_qac_refs):
            raise RuntimeError(f"cross-ayah attachment resolution: {attachment_ref}")
        qac_edge_count += len(target_qac_refs)
        resolutions.append(
            AttachmentResolution(
                attachment_unit_ref=attachment_ref,
                target_namespace=target_namespace,
                target_ref=target_ref,
                resolution_rule=resolution_rule,
                reviewed_decision_id=reviewed_decision_id,
            )
        )

    return resolutions, {
        "path": str(ATTACHMENT_DECISIONS_PATH.relative_to(ROOT)),
        "sha256": sha256_bytes(ATTACHMENT_DECISIONS_PATH.read_bytes()),
        "decisionCount": len(decisions),
        "redirectDecisionCount": len(redirect_decisions),
        "exclusionDecisionCount": sum(
            item.decision_type == "exclude-source-defect" for item in decisions
        ),
        "carrierApprovalDecisionCount": sum(
            item.decision_type == "approve-fused-carrier" for item in decisions
        ),
        "resolvedEndpointCount": len(resolutions),
        "unitQacEdgeCount": qac_edge_count,
    }


def select_attachment_qac_refs(
    endpoint: AttachmentEndpoint,
    candidates: Sequence[QacMorpheme],
) -> tuple[tuple[QacMorpheme, ...], str]:
    if endpoint.endpoint_part not in ATTACHMENT_PARTS:
        raise RuntimeError(
            f"unsupported attachment endpoint part at {endpoint.attachment_id}: "
            f"{endpoint.endpoint_part!r}"
        )
    ordered = tuple(
        sorted(
            candidates,
            key=lambda item: (
                item.surah,
                item.ayah,
                item.word_index,
                item.morpheme_index,
            ),
        )
    )
    if not ordered:
        raise RuntimeError(
            f"attachment endpoint has no QAC candidates: {endpoint.attachment_id} "
            f"{endpoint.endpoint_role}"
        )
    if endpoint.endpoint_part in {"", "whole_word"}:
        return ordered, "whole-source-unit"

    pronominals = tuple(
        item for item in ordered if item.pos in QAC_PRONOMINAL_POS
    )
    if endpoint.endpoint_part in ATTACHMENT_SUFFIX_PARTS:
        if pronominals:
            return pronominals, "explicit-pronominal-morpheme"
        suffixes = tuple(item for item in ordered if item.role == "SUFFIX")
        if suffixes:
            return suffixes, "explicit-suffix-morpheme"
        carriers = tuple(
            item
            for item in ordered
            if item.role == "STEM" and item.pos not in QAC_PRONOMINAL_POS
        )
        if carriers:
            return carriers, "fused-suffix-carrier"
        raise RuntimeError(
            f"suffix attachment endpoint has no QAC carrier: "
            f"{endpoint.attachment_id} {endpoint.endpoint_role}"
        )

    if endpoint.endpoint_part == "subject_agreement":
        if pronominals:
            return pronominals, "explicit-agreement-morpheme"
        verbs = tuple(item for item in ordered if item.pos == "V")
        if verbs:
            return verbs, "fused-agreement-carrier"
        raise RuntimeError(
            f"agreement attachment endpoint has no QAC carrier: "
            f"{endpoint.attachment_id} {endpoint.endpoint_role}"
        )

    if endpoint.endpoint_part == "particle_segment":
        # The attachment corpus uses particle_segment for relative ma/man, so
        # QAC REL stems are intentional cores here rather than pronoun suffixes.
        core = tuple(
            item
            for item in ordered
            if item.role == "STEM" and item.pos != "PRON"
        )
        if core:
            return core, "core-particle-morpheme"
        non_pronouns = tuple(item for item in ordered if item.pos != "PRON")
        if non_pronouns:
            return non_pronouns, "non-pronoun-particle-morpheme"
        raise RuntimeError(
            f"particle attachment endpoint resolves only to pronouns: "
            f"{endpoint.attachment_id} {endpoint.endpoint_role}"
        )

    particles = tuple(
        item for item in ordered if item.pos in QAC_PREPOSITION_POS
    )
    if particles:
        return particles, "explicit-preposition-morpheme"
    carriers = tuple(
        item
        for item in ordered
        if item.role == "STEM" and item.pos not in QAC_PRONOMINAL_POS
    )
    if carriers:
        return carriers, "fused-preposition-carrier"
    raise RuntimeError(
        f"preposition attachment endpoint has no QAC carrier: "
        f"{endpoint.attachment_id} {endpoint.endpoint_role}"
    )


def build_attachment_qac_edges(
    endpoints: Sequence[AttachmentEndpoint],
    resolutions: Sequence[AttachmentResolution],
    mappings: dict[str, UnitMapping],
    masaq_paths: Sequence[MasaqQacPath],
    qac_morphemes: Sequence[QacMorpheme],
    decisions: Sequence[ReviewedAttachmentDecision],
) -> tuple[list[AttachmentQacEdge], list[AttachmentExclusion], dict[str, Any]]:
    resolution_by_ref = {item.attachment_unit_ref: item for item in resolutions}
    qac_by_ref = {item.ref: item for item in qac_morphemes}
    qac_by_word: dict[str, list[QacMorpheme]] = defaultdict(list)
    for qac in qac_morphemes:
        qac_by_word[qac.word_ref].append(qac)
    accepted_masaq_qac: dict[str, set[str]] = defaultdict(set)
    for path in masaq_paths:
        if path.accepted:
            accepted_masaq_qac[path.masaq_segment_ref].add(path.qac_morpheme_ref)

    endpoint_keys = {
        (item.attachment_id, item.endpoint_role) for item in endpoints
    }
    if len(endpoint_keys) != len(endpoints):
        raise RuntimeError("duplicate attachment endpoint occurrence")
    exclusion_by_endpoint: dict[
        tuple[str, str], ReviewedAttachmentDecision
    ] = {}
    carrier_review_by_endpoint: dict[
        tuple[str, str], ReviewedAttachmentDecision
    ] = {}
    for decision in decisions:
        if decision.decision_type not in {
            "exclude-source-defect",
            "approve-fused-carrier",
        }:
            continue
        matches = [
            endpoint
            for endpoint in endpoints
            if endpoint.attachment_id == decision.attachment_id
            and (
                not decision.endpoint_role
                or endpoint.endpoint_role == decision.endpoint_role
            )
            and (
                not decision.attachment_unit_ref
                or endpoint.attachment_unit_ref == decision.attachment_unit_ref
            )
        ]
        if not matches:
            raise RuntimeError(
                f"attachment occurrence decision matches no endpoint: "
                f"{decision.decision_id}"
            )
        if decision.decision_type == "approve-fused-carrier" and len(matches) != 1:
            raise RuntimeError(
                f"carrier approval must match exactly one endpoint: "
                f"{decision.decision_id}"
            )
        destination = (
            exclusion_by_endpoint
            if decision.decision_type == "exclude-source-defect"
            else carrier_review_by_endpoint
        )
        for endpoint in matches:
            key = (endpoint.attachment_id, endpoint.endpoint_role)
            if key in destination:
                raise RuntimeError(
                    f"overlapping attachment occurrence decisions at {key}: "
                    f"{destination[key].decision_id}, "
                    f"{decision.decision_id}"
                )
            destination[key] = decision
    overlap = set(exclusion_by_endpoint) & set(carrier_review_by_endpoint)
    if overlap:
        raise RuntimeError(
            f"attachment endpoints are both excluded and approved: {sorted(overlap)}"
        )

    edges: list[AttachmentQacEdge] = []
    exclusions: list[AttachmentExclusion] = []
    rule_counts: Counter[str] = Counter()
    part_counts: Counter[str] = Counter()
    multi_target_endpoint_count = 0
    reviewed_carrier_count = 0
    for endpoint in endpoints:
        endpoint_key = (endpoint.attachment_id, endpoint.endpoint_role)
        exclusion = exclusion_by_endpoint.get(endpoint_key)
        if exclusion is not None:
            exclusions.append(
                AttachmentExclusion(
                    attachment_id=endpoint.attachment_id,
                    endpoint_role=endpoint.endpoint_role,
                    attachment_unit_ref=endpoint.attachment_unit_ref,
                    reviewed_decision_id=exclusion.decision_id,
                )
            )
            continue
        resolution = resolution_by_ref[endpoint.attachment_unit_ref]
        if resolution.target_namespace == "grammar-unit":
            candidate_refs = mappings[resolution.target_ref].qac_refs
        else:
            candidate_refs = tuple(accepted_masaq_qac[resolution.target_ref])
        primary_candidates = [qac_by_ref[ref] for ref in candidate_refs]
        parent_candidates = [
            qac
            for word_ref in sorted(
                {item.word_ref for item in primary_candidates}, key=ref_sort_key
            )
            for qac in qac_by_word[word_ref]
        ]
        selection_candidates = primary_candidates
        if endpoint.endpoint_part in ATTACHMENT_SUFFIX_PARTS | {"subject_agreement"}:
            selection_candidates = parent_candidates
        elif endpoint.endpoint_part == "particle_segment" and all(
            item.pos == "PRON" for item in primary_candidates
        ):
            selection_candidates = parent_candidates
        elif endpoint.endpoint_part == "preposition" and not any(
            item.pos in QAC_PREPOSITION_POS for item in primary_candidates
        ):
            selection_candidates = parent_candidates
        selected, rule = select_attachment_qac_refs(
            endpoint, selection_candidates
        )
        carrier_review = carrier_review_by_endpoint.get(endpoint_key)
        if rule in ATTACHMENT_CARRIER_RULES:
            if carrier_review is None:
                raise RuntimeError(
                    f"fused attachment carrier requires reviewed approval: "
                    f"{endpoint.attachment_id} {endpoint.endpoint_role} {rule}"
                )
            selected_refs = tuple(item.ref for item in selected)
            if selected_refs != (carrier_review.target_ref,):
                raise RuntimeError(
                    f"fused-carrier target drift at {carrier_review.decision_id}: "
                    f"{selected_refs!r} != {(carrier_review.target_ref,)!r}"
                )
            reviewed_carrier_count += 1
        elif carrier_review is not None:
            raise RuntimeError(
                f"stale fused-carrier approval no longer selects a carrier: "
                f"{carrier_review.decision_id} ({rule})"
            )
        if len(selected) > 1:
            multi_target_endpoint_count += 1
        rule_counts[rule] += 1
        part_counts[endpoint.endpoint_part or "whole-source-unit"] += 1
        for order, qac in enumerate(selected, start=1):
            edges.append(
                AttachmentQacEdge(
                    attachment_id=endpoint.attachment_id,
                    endpoint_role=endpoint.endpoint_role,
                    attachment_unit_ref=endpoint.attachment_unit_ref,
                    endpoint_part=endpoint.endpoint_part,
                    surface_ar=endpoint.surface_ar,
                    form_tag=endpoint.form_tag,
                    qac_morpheme_ref=qac.ref,
                    target_order=order,
                    alignment_rule=rule,
                    alignment_reviewed_decision_id=(
                        carrier_review.decision_id if carrier_review else None
                    ),
                )
            )

    edge_keys = {
        (item.attachment_id, item.endpoint_role, item.qac_morpheme_ref)
        for item in edges
    }
    if len(edge_keys) != len(edges):
        raise RuntimeError("duplicate attachment/QAC edge")
    linked_endpoint_keys = {
        (item.attachment_id, item.endpoint_role) for item in edges
    }
    accepted_endpoint_keys = endpoint_keys - set(exclusion_by_endpoint)
    if accepted_endpoint_keys != linked_endpoint_keys:
        raise RuntimeError("attachment endpoint/QAC coverage mismatch")
    return edges, exclusions, {
        "endpointCount": len(endpoint_keys),
        "acceptedEndpointCount": len(accepted_endpoint_keys),
        "excludedEndpointCount": len(exclusions),
        "excludedAttachmentCount": len(
            {item.attachment_id for item in exclusions}
        ),
        "excludedEndpoints": [
            {
                "attachmentId": item.attachment_id,
                "endpointRole": item.endpoint_role,
                "attachmentUnitRef": item.attachment_unit_ref,
                "reviewedDecisionId": item.reviewed_decision_id,
            }
            for item in exclusions
        ],
        "edgeCount": len(edges),
        "multiTargetEndpointCount": multi_target_endpoint_count,
        "partCounts": dict(sorted(part_counts.items())),
        "alignmentRuleCounts": dict(sorted(rule_counts.items())),
        "carrierEndpointCount": sum(
            rule_counts[rule] for rule in ATTACHMENT_CARRIER_RULES
        ),
        "reviewedCarrierEndpointCount": reviewed_carrier_count,
        "unreviewedCarrierEndpointCount": 0,
    }


def span_candidates(
    unit: GrammarUnit, word: QacWord
) -> list[tuple[int, int, SurfaceRelation, str]]:
    visible = [item for item in word.morphemes if normalize_surface(item.surface_ar)]
    candidates: list[tuple[int, int, SurfaceRelation, str]] = []
    for start in range(len(visible)):
        for end in range(start, len(visible)):
            target = "".join(item.surface_ar for item in visible[start : end + 1])
            relation = surface_relation(unit.surface_ar, target)
            candidates.append((start, end, relation, target))
    return sorted(
        candidates,
        key=lambda item: (
            item[2].cost,
            item[1] - item[0],
            item[0],
            item[1],
        ),
    )


def align_block(units: Sequence[GrammarUnit], word: QacWord) -> BlockAlignment:
    visible = tuple(
        item for item in word.morphemes if normalize_surface(item.surface_ar)
    )
    if not units or not visible:
        raise RuntimeError(f"cannot align empty source/QAC block at {word.ref}")
    candidates = [span_candidates(unit, word) for unit in units]

    @lru_cache(maxsize=None)
    def solve(
        unit_index: int, previous_start: int, previous_end: int
    ) -> tuple[
        tuple[int, int, int, int],
        tuple[tuple[int, int, SurfaceRelation, str], ...],
        int,
    ] | None:
        if unit_index == len(units):
            trailing_uncovered = max(0, len(visible) - previous_end - 1)
            return (0, trailing_uncovered, 0, 0), (), 1
        best_score: tuple[int, int, int, int] | None = None
        best_path: tuple[tuple[int, int, SurfaceRelation, str], ...] = ()
        ambiguity_count = 0
        for candidate in candidates[unit_index]:
            start, end, relation, _target = candidate
            if start < previous_start or end < previous_end:
                continue
            tail = solve(unit_index + 1, start, end)
            if tail is None:
                continue
            tail_score, tail_path, tail_ambiguity = tail
            overlap = (
                max(0, min(end, previous_end) - max(start, previous_start) + 1)
                if previous_start >= 0
                else 0
            )
            uncovered_gap = (
                start
                if previous_end < 0
                else max(0, start - previous_end - 1)
            )
            evidence_cost = relation.cost - relation.length_delta
            # Endpoint reuse is valid. Prefer evidence quality, then complete
            # QAC coverage, then surface-length fit, and only then less reuse.
            option_score = (
                evidence_cost + tail_score[0],
                uncovered_gap + tail_score[1],
                relation.length_delta + tail_score[2],
                overlap + tail_score[3],
            )
            option_path = (candidate, *tail_path)
            if best_score is None or option_score < best_score:
                best_score = option_score
                best_path = option_path
                ambiguity_count = tail_ambiguity
            elif option_score == best_score:
                ambiguity_count = min(2, ambiguity_count + tail_ambiguity)
                if tuple((part[0], part[1]) for part in option_path) < tuple(
                    (part[0], part[1]) for part in best_path
                ):
                    best_path = option_path
        if best_score is None:
            return None
        return best_score, best_path, ambiguity_count

    solved = solve(0, -1, -1)
    if solved is None:
        raise RuntimeError(f"no monotonic morpheme alignment for {word.ref}")
    relation_score, path, ambiguity_count = solved
    mappings: list[UnitMapping] = []
    covered: set[str] = set()
    for unit, (start, end, relation, target) in zip(units, path, strict=True):
        refs = tuple(item.ref for item in visible[start : end + 1])
        covered.update(refs)
        mappings.append(
            UnitMapping(
                grammar_ref=unit.ref,
                qac_refs=refs,
                qac_word_refs=(word.ref,),
                rule=relation.rule,
                rank=relation.rank,
                edit_distance=relation.edit_distance,
                cost=relation.cost,
                source_surface_ar=unit.surface_ar,
                target_surface_ar=target,
            )
        )

    implicit_suffixes = tuple(
        item.ref
        for item in word.morphemes
        if not normalize_surface(item.surface_ar) and item.role == "SUFFIX"
    )
    unexpected_unalignable = [
        item.ref
        for item in word.morphemes
        if not normalize_surface(item.surface_ar) and item.role != "SUFFIX"
    ]
    if unexpected_unalignable:
        raise RuntimeError(
            f"non-suffix QAC morphemes have no alignable surface at {word.ref}: "
            + ", ".join(unexpected_unalignable)
        )
    if implicit_suffixes:
        last = mappings[-1]
        mappings[-1] = UnitMapping(
            grammar_ref=last.grammar_ref,
            qac_refs=(*last.qac_refs, *implicit_suffixes),
            qac_word_refs=last.qac_word_refs,
            rule=f"{last.rule}+implicit-final-suffix",
            rank=last.rank,
            edit_distance=last.edit_distance,
            cost=last.cost,
            source_surface_ar=last.source_surface_ar,
            target_surface_ar=last.target_surface_ar,
        )
        covered.update(implicit_suffixes)

    uncovered = tuple(item.ref for item in visible if item.ref not in covered)
    source_concat = "".join(item.surface_ar for item in units)
    concat_edit = min(
        levenshtein(normalize_surface(source_concat), normalize_surface(word.surface_ar)),
        levenshtein(folded_surface(source_concat), folded_surface(word.surface_ar)),
    )
    total_cost = (
        relation_score[0]
        + relation_score[2]
        + concat_edit * 15
        + len(uncovered) * 2
    )
    return BlockAlignment(
        mappings=tuple(mappings),
        cost=total_cost,
        ambiguity_count=ambiguity_count,
        uncovered_visible_refs=uncovered,
        concatenated_edit_distance=concat_edit,
    )


def align_ayah(units: Sequence[GrammarUnit], words: Sequence[QacWord]) -> AyahAlignment:
    if len(units) < len(words):
        ref = f"{words[0].surah}:{words[0].ayah}" if words else "unknown"
        raise RuntimeError(f"fewer grammar units than QAC words at {ref}")

    @lru_cache(maxsize=None)
    def block_cost(word_index: int, source_start: int, source_end: int) -> int:
        word = words[word_index]
        block_units = units[source_start:source_end]
        unit_cost = sum(
            surface_relation(unit.surface_ar, word.surface_ar).cost
            for unit in block_units
        )
        for unit in block_units:
            internally_consistent_contexts = [
                context
                for context in unit.masaq_full_surfaces_ar
                if normalize_surface(unit.surface_ar)
                in normalize_surface(context)
                or folded_surface(unit.surface_ar) in folded_surface(context)
            ]
            if internally_consistent_contexts:
                context_cost = min(
                    surface_relation(context, word.surface_ar).cost
                    for context in internally_consistent_contexts
                )
                unit_cost += min(context_cost, 2_000) * 2
        source_concat = "".join(item.surface_ar for item in block_units)
        concat_edit = min(
            levenshtein(
                normalize_surface(source_concat), normalize_surface(word.surface_ar)
            ),
            levenshtein(
                folded_surface(source_concat), folded_surface(word.surface_ar)
            ),
        )
        return unit_cost + concat_edit * 15

    @lru_cache(maxsize=None)
    def solve(
        word_index: int, source_index: int
    ) -> tuple[int, tuple[int, ...], int] | None:
        if word_index == len(words):
            return (0, (), 1) if source_index == len(units) else None
        remaining_words = len(words) - word_index
        remaining_units = len(units) - source_index
        if remaining_units < remaining_words:
            return None
        max_size = min(
            MAX_SOURCE_UNITS_PER_QAC_WORD,
            remaining_units - (remaining_words - 1),
        )
        best_cost: int | None = None
        best_sizes: tuple[int, ...] = ()
        ambiguity_count = 0
        for size in range(1, max_size + 1):
            tail = solve(word_index + 1, source_index + size)
            if tail is None:
                continue
            tail_cost, tail_sizes, tail_ambiguity = tail
            option_cost = block_cost(
                word_index, source_index, source_index + size
            ) + tail_cost
            option_sizes = (size, *tail_sizes)
            if best_cost is None or option_cost < best_cost:
                best_cost = option_cost
                best_sizes = option_sizes
                ambiguity_count = tail_ambiguity
            elif option_cost == best_cost:
                ambiguity_count = min(2, ambiguity_count + tail_ambiguity)
                if option_sizes < best_sizes:
                    best_sizes = option_sizes
        if best_cost is None:
            return None
        return best_cost, best_sizes, ambiguity_count

    solved = solve(0, 0)
    if solved is None:
        ref = f"{words[0].surah}:{words[0].ayah}" if words else "unknown"
        raise RuntimeError(f"cannot partition grammar units over QAC words at {ref}")
    _cost, sizes, partition_ambiguity = solved
    blocks: list[BlockAlignment] = []
    source_index = 0
    for word, size in zip(words, sizes, strict=True):
        blocks.append(align_block(units[source_index : source_index + size], word))
        source_index += size
    ambiguity_count = min(
        2,
        partition_ambiguity
        * max((item.ambiguity_count for item in blocks), default=1),
    )
    return AyahAlignment(
        mappings=tuple(mapping for item in blocks for mapping in item.mappings),
        ambiguity_count=ambiguity_count,
        block_sizes=sizes,
    )


def verify_source_manifest(path: Path, source_path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "qac-masaq-source-v1":
        raise RuntimeError("unsupported QAC/MASAQ source projection schema")
    actual = sha256_bytes(source_path.read_bytes())
    if manifest.get("projectionSha256") != actual:
        raise RuntimeError("source projection checksum does not match SOURCE.json")
    reviewed = manifest.get("reviewedTraceDecisions")
    expected_review_path = str(TRACE_DECISIONS_PATH.relative_to(ROOT))
    if (
        not isinstance(reviewed, dict)
        or reviewed.get("path") != expected_review_path
        or reviewed.get("sha256")
        != sha256_bytes(TRACE_DECISIONS_PATH.read_bytes())
    ):
        raise RuntimeError(
            "reviewed trace decisions do not match the promoted source manifest"
        )
    return manifest


def align_all(
    qac_by_ayah: dict[tuple[int, int], tuple[QacWord, ...]],
    source_by_ayah: dict[tuple[int, int], tuple[GrammarUnit, ...]],
) -> tuple[dict[str, UnitMapping], dict[str, Any]]:
    if set(qac_by_ayah) != set(source_by_ayah):
        missing_qac = sorted(set(source_by_ayah) - set(qac_by_ayah))
        missing_source = sorted(set(qac_by_ayah) - set(source_by_ayah))
        raise RuntimeError(
            f"QAC/source ayah coverage mismatch: no-QAC={missing_qac[:5]}, "
            f"no-source={missing_source[:5]}"
        )

    mappings: dict[str, UnitMapping] = {}
    rule_counts: Counter[str] = Counter()
    rank_counts: Counter[int] = Counter()
    block_size_counts: Counter[int] = Counter()
    ambiguous_ayahs: list[str] = []
    weak_rows: list[dict[str, Any]] = []
    for ayah_index, key in enumerate(sorted(qac_by_ayah), start=1):
        if ayah_index == 1 or ayah_index % 500 == 0:
            print(
                f"aligning ayah {ayah_index}/6236 ({key[0]}:{key[1]})",
                file=sys.stderr,
                flush=True,
            )
        aligned = align_ayah(source_by_ayah[key], qac_by_ayah[key])
        block_size_counts.update(aligned.block_sizes)
        if aligned.ambiguity_count > 1:
            ambiguous_ayahs.append(f"{key[0]}:{key[1]}")
        for mapping in aligned.mappings:
            if mapping.grammar_ref in mappings:
                raise RuntimeError(f"duplicate generated grammar mapping: {mapping.grammar_ref}")
            mappings[mapping.grammar_ref] = mapping
            rule_counts[mapping.rule] += 1
            rank_counts[mapping.rank] += 1
            if mapping.rank >= 4:
                weak_rows.append(
                    {
                        "grammarRef": mapping.grammar_ref,
                        "sourceSurface": mapping.source_surface_ar,
                        "qacWordRefs": list(mapping.qac_word_refs),
                        "qacMorphemeRefs": list(mapping.qac_refs),
                        "targetSurface": mapping.target_surface_ar,
                        "rule": mapping.rule,
                        "rank": mapping.rank,
                        "editDistance": mapping.edit_distance,
                    }
                )
    if set(mappings) != {
        unit.ref for units in source_by_ayah.values() for unit in units
    }:
        raise RuntimeError("generated grammar mapping coverage mismatch")
    return mappings, {
        "ruleCounts": dict(sorted(rule_counts.items())),
        "rankCounts": {str(key): value for key, value in sorted(rank_counts.items())},
        "blockSizeCounts": {str(key): value for key, value in sorted(block_size_counts.items())},
        "ambiguousAyahCount": len(ambiguous_ayahs),
        "ambiguousAyahs": ambiguous_ayahs,
        "weakMappingCount": len(weak_rows),
        "weakMappings": weak_rows,
    }


def validate_analysis_join(
    analysis_units: Sequence[AnalysisUnit],
    source_units: Sequence[GrammarUnit],
) -> tuple[dict[str, GrammarUnit], dict[str, str], dict[str, Any]]:
    source_by_ref = {item.ref: item for item in source_units}
    analysis_by_ref = {item.ref: item for item in analysis_units}
    missing_source = sorted(set(analysis_by_ref) - set(source_by_ref))
    source_only = sorted(set(source_by_ref) - set(analysis_by_ref), key=ref_sort_key)
    if missing_source:
        raise RuntimeError(f"analysis refs missing from grammar source: {missing_source[:20]}")

    relation_counts: Counter[str] = Counter()
    weak: list[dict[str, Any]] = []
    joined: dict[str, GrammarUnit] = {}
    relation_statuses: dict[str, str] = {}
    excluded: list[dict[str, str]] = []
    for analysis in analysis_units:
        source = source_by_ref[analysis.ref]
        relation = surface_relation(analysis.surface_ar, source.surface_ar)
        relation_counts[relation.rule] += 1
        relation_status = (
            "excluded-source-defect"
            if source.trace_status in EXCLUDED_SOURCE_TRACE_STATUSES
            else "accepted"
        )
        relation_statuses[analysis.ref] = relation_status
        if relation_status != "accepted":
            excluded.append(
                {
                    "analysisRef": analysis.ref,
                    "grammarRef": source.ref,
                    "reason": source.trace_evidence,
                }
            )
        elif relation.rank >= 4:
            weak.append(
                {
                    "analysisRef": analysis.ref,
                    "analysisSurface": analysis.surface_ar,
                    "grammarSurface": source.surface_ar,
                    "rule": relation.rule,
                    "rank": relation.rank,
                    "editDistance": relation.edit_distance,
                }
            )
        joined[analysis.ref] = source
    audit = {
        # Kept below as a compatibility field for existing audit consumers.
        "analysisCount": len(analysis_units),
        "acceptedAnalysisCount": sum(
            status == "accepted" for status in relation_statuses.values()
        ),
        "excludedAnalysisCount": len(excluded),
        "excludedAnalyses": excluded,
        "sourceOnlyCount": len(source_only),
        "sourceOnlyRefs": source_only,
        "surfaceRuleCounts": dict(sorted(relation_counts.items())),
        "weakSurfaceCount": len(weak),
        "weakSurfaces": weak,
    }
    return joined, relation_statuses, audit


def ref_sort_key(ref: str) -> tuple[int, ...]:
    return tuple(int(part) for part in ref.split(":"))


def build_audit() -> tuple[dict[str, Any], dict[str, object]]:
    source_manifest = verify_source_manifest(SOURCE_MANIFEST_PATH, SOURCE_PATH)
    release_manifest_bytes = RELEASE_MANIFEST_PATH.read_bytes()
    release_manifest = json.loads(release_manifest_bytes)
    analysis_source = word_analysis_source(WORD_ANALYSIS_DIR)
    if analysis_source["shardCount"] != 114:
        raise RuntimeError(
            f"expected 114 word-analysis shards, found {analysis_source['shardCount']}"
        )
    qac_by_ayah, qac_morphemes = load_qac(QAC_PATH)
    source_by_ayah, source_units = load_source_units(SOURCE_PATH)
    source_by_ref = {item.ref: item for item in source_units}
    analysis_units = load_analysis_units(WORD_ANALYSIS_DIR)
    automatic_mappings, alignment_audit = align_all(qac_by_ayah, source_by_ayah)
    decisions = load_reviewed_decisions(DECISIONS_PATH)
    mappings, review_audit = apply_reviewed_decisions(
        automatic_mappings, qac_morphemes, decisions
    )
    masaq_qac_decisions = load_reviewed_masaq_qac_decisions(
        MASAQ_QAC_DECISIONS_PATH
    )
    masaq_qac_paths, masaq_qac_review_audit = build_masaq_qac_paths(
        source_units,
        mappings,
        qac_morphemes,
        masaq_qac_decisions,
    )
    analysis_join, analysis_statuses, analysis_audit = validate_analysis_join(
        analysis_units, source_units
    )
    attachment_endpoints, attachment_refs, attachment_source_audit = (
        load_attachment_refs(ATTACHMENTS_PATH)
    )
    attachment_decisions = load_reviewed_attachment_decisions(
        ATTACHMENT_DECISIONS_PATH
    )
    attachment_resolutions, attachment_resolution_audit = resolve_attachment_units(
        attachment_refs,
        source_units,
        mappings,
        masaq_qac_paths,
        attachment_decisions,
    )
    (
        attachment_qac_edges,
        attachment_exclusions,
        attachment_mapping_audit,
    ) = build_attachment_qac_edges(
        attachment_endpoints,
        attachment_resolutions,
        mappings,
        masaq_qac_paths,
        qac_morphemes,
        attachment_decisions,
    )

    reviewed_grammar_refs = {item.grammar_ref for item in decisions}
    reviewed_ayahs = {
        ":".join(item.grammar_ref.split(":")[:2]) for item in decisions
    }
    unresolved_weak_refs = sorted(
        {
            item["grammarRef"]
            for item in alignment_audit["weakMappings"]
            if item["grammarRef"] not in reviewed_grammar_refs
        },
        key=ref_sort_key,
    )
    unresolved_ambiguous_ayahs = sorted(
        set(alignment_audit["ambiguousAyahs"]) - reviewed_ayahs,
        key=ref_sort_key,
    )

    masaq_refs = {ref for item in source_units for ref in item.masaq_refs}
    masaq_edge_count = sum(len(item.masaq_refs) for item in source_units)
    trace_counts = Counter(item.trace_status for item in source_units)
    accepted_masaq_edges = sum(
        len(item.masaq_refs)
        for item in source_units
        if item.trace_status in ACCEPTED_MASAQ_TRACE_STATUSES
    )
    unreviewed_trace_refs = sorted(
        (
            item.ref
            for item in source_units
            if item.masaq_refs
            and item.trace_status not in ACCEPTED_MASAQ_TRACE_STATUSES
            and item.trace_status not in EXCLUDED_SOURCE_TRACE_STATUSES
        ),
        key=ref_sort_key,
    )
    accepted_mappings = {
        ref: mapping
        for ref, mapping in mappings.items()
        if source_by_ref[ref].trace_status not in EXCLUDED_SOURCE_TRACE_STATUSES
    }
    mapped_qac_refs = {
        ref for mapping in accepted_mappings.values() for ref in mapping.qac_refs
    }
    qac_refs = {item.ref for item in qac_morphemes}
    unlinked_qac = [item for item in qac_morphemes if item.ref not in mapped_qac_refs]
    unlinked_qac_category_counts = Counter(
        f"{item.role}:{item.pos}" for item in unlinked_qac
    )
    qac_grammar_degrees = Counter(
        ref for mapping in accepted_mappings.values() for ref in mapping.qac_refs
    )
    analysis_qac_edges = sum(
        len(mappings[ref].qac_refs)
        for ref in analysis_join
        if analysis_statuses[ref] == "accepted"
    )

    audit: dict[str, Any] = {
        "schemaVersion": f"{SCHEMA_VERSION}-audit",
        "builderVersion": BUILDER_VERSION,
        "status": "review-required"
        if unresolved_weak_refs
        or unresolved_ambiguous_ayahs
        or analysis_audit["weakSurfaceCount"]
        or unreviewed_trace_refs
        or attachment_mapping_audit["unreviewedCarrierEndpointCount"]
        else "accepted",
        "source": {
            "projectionPath": str(SOURCE_PATH.relative_to(ROOT)),
            "projectionSha256": sha256_bytes(SOURCE_PATH.read_bytes()),
            "qacPath": str(QAC_PATH.relative_to(ROOT)),
            "qacSha256": sha256_bytes(QAC_PATH.read_bytes()),
            "wordAnalysisDirectory": str(WORD_ANALYSIS_DIR.relative_to(ROOT)),
            "wordAnalysisShardCount": analysis_source["shardCount"],
            "wordAnalysisTreeSha256": analysis_source["fileTreeSha256"],
            "releaseManifestPath": str(RELEASE_MANIFEST_PATH.relative_to(ROOT)),
            "releaseManifestSha256": sha256_bytes(release_manifest_bytes),
            "releaseId": release_manifest["release_id"],
            "upstreamCommit": source_manifest["upstreamCommit"],
            "upstreamSha256": source_manifest["upstreamSha256"],
            "reviewedTraceDecisions": source_manifest["reviewedTraceDecisions"],
        },
        "counts": {
            "ayahs": len(qac_by_ayah),
            "qacWords": sum(len(items) for items in qac_by_ayah.values()),
            "qacMorphemes": len(qac_morphemes),
            "qacMorphemesLinked": len(mapped_qac_refs),
            "qacMorphemesUnlinked": len(qac_refs - mapped_qac_refs),
            "grammarUnits": len(source_units),
            "grammarQacEdges": sum(len(item.qac_refs) for item in mappings.values()),
            "wordAnalysisUnits": len(analysis_units),
            "acceptedWordAnalysisUnits": analysis_audit["acceptedAnalysisCount"],
            "excludedWordAnalysisUnits": analysis_audit["excludedAnalysisCount"],
            "analysisQacEdges": analysis_qac_edges,
            "masaqSegments": len(masaq_refs),
            "grammarMasaqEdges": masaq_edge_count,
            "acceptedGrammarMasaqEdges": accepted_masaq_edges,
            "masaqQacPaths": masaq_qac_review_audit["pathCount"],
            "acceptedMasaqQacPaths": masaq_qac_review_audit[
                "acceptedPathCount"
            ],
            "acceptedMasaqQacEdges": masaq_qac_review_audit[
                "acceptedDirectEdgeCount"
            ],
            "attachmentEndpointOccurrences": attachment_source_audit[
                "endpointOccurrenceCount"
            ],
            "acceptedAttachmentEndpointOccurrences": attachment_mapping_audit[
                "acceptedEndpointCount"
            ],
            "excludedAttachmentEndpointOccurrences": attachment_mapping_audit[
                "excludedEndpointCount"
            ],
            "attachmentUnits": attachment_resolution_audit[
                "resolvedEndpointCount"
            ],
            "attachmentUnitQacEdges": attachment_resolution_audit[
                "unitQacEdgeCount"
            ],
            "attachmentQacEdges": attachment_mapping_audit["edgeCount"],
        },
        "traceStatusCounts": dict(sorted(trace_counts.items())),
        "unreviewedTraceRefs": unreviewed_trace_refs,
        "relationCardinality": {
            "qacGrammarDegreeCounts": dict(
                sorted(
                    Counter(qac_grammar_degrees.get(ref, 0) for ref in qac_refs).items()
                )
            ),
            "grammarQacSpanSizeCounts": dict(
                sorted(Counter(len(item.qac_refs) for item in mappings.values()).items())
            ),
        },
        "unlinkedQac": {
            "categoryCounts": dict(sorted(unlinked_qac_category_counts.items())),
            "units": [
                {
                    "qacMorphemeRef": item.ref,
                    "qacWordRef": item.word_ref,
                    "surface": item.surface_ar,
                    "pos": item.pos,
                    "role": item.role,
                }
                for item in unlinked_qac
            ],
        },
        "alignment": alignment_audit,
        "review": {
            **review_audit,
            "unresolvedWeakGrammarRefs": unresolved_weak_refs,
            "unresolvedAmbiguousAyahs": unresolved_ambiguous_ayahs,
        },
        "masaqQacReview": masaq_qac_review_audit,
        "analysisJoin": analysis_audit,
        "attachments": {
            "source": attachment_source_audit,
            "resolution": attachment_resolution_audit,
            "endpointMapping": attachment_mapping_audit,
        },
    }
    context: dict[str, object] = {
        "qacMorphemes": qac_morphemes,
        "sourceUnits": source_units,
        "analysisUnits": analysis_units,
        "mappings": mappings,
        "analysisJoin": analysis_join,
        "analysisStatuses": analysis_statuses,
        "reviewedDecisions": decisions,
        "reviewedMasaqQacDecisions": masaq_qac_decisions,
        "masaqQacPaths": masaq_qac_paths,
        "reviewedAttachmentDecisions": attachment_decisions,
        "attachmentResolutions": attachment_resolutions,
        "attachmentQacEdges": attachment_qac_edges,
        "attachmentExclusions": attachment_exclusions,
        "sourceManifest": source_manifest,
    }
    return audit, context


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA foreign_keys = ON;
        PRAGMA user_version = 4;

        CREATE TABLE metadata (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        ) WITHOUT ROWID;

        CREATE TABLE qac_morphemes (
          qac_morpheme_ref TEXT PRIMARY KEY,
          qac_word_ref TEXT NOT NULL,
          surah INTEGER NOT NULL,
          ayah INTEGER NOT NULL,
          word_index INTEGER NOT NULL,
          morpheme_index INTEGER NOT NULL,
          surface_ar TEXT NOT NULL,
          stem_ar TEXT NOT NULL,
          pos TEXT NOT NULL,
          morpheme_role TEXT NOT NULL,
          grammar_link_count INTEGER NOT NULL,
          link_status TEXT NOT NULL CHECK (link_status IN ('linked', 'no-source-unit'))
        ) WITHOUT ROWID;

        CREATE TABLE grammar_units (
          grammar_ref TEXT PRIMARY KEY,
          surah INTEGER NOT NULL,
          ayah INTEGER NOT NULL,
          grammar_unit_index INTEGER NOT NULL,
          surface_ar TEXT NOT NULL,
          grammar TEXT NOT NULL,
          tag TEXT NOT NULL,
          analysis_disposition TEXT NOT NULL
            CHECK (analysis_disposition IN (
              'released-word-analysis', 'source-only', 'excluded-source-defect'
            )),
          trace_type TEXT NOT NULL,
          trace_status TEXT NOT NULL,
          trace_rule_id TEXT NOT NULL,
          trace_evidence TEXT NOT NULL,
          alignment_group_id TEXT NOT NULL,
          grammar_order_within_group TEXT NOT NULL,
          masaq_order_within_group TEXT NOT NULL,
          masaq_source_status TEXT NOT NULL
        ) WITHOUT ROWID;

        CREATE TABLE word_analysis_units (
          analysis_ref TEXT PRIMARY KEY,
          surah INTEGER NOT NULL,
          ayah INTEGER NOT NULL,
          critical_w INTEGER NOT NULL,
          surface_ar TEXT NOT NULL,
          grammar_ref TEXT NOT NULL UNIQUE,
          relation_status TEXT NOT NULL
            CHECK (relation_status IN ('accepted', 'excluded-source-defect')),
          exclusion_reason TEXT NOT NULL,
          FOREIGN KEY (grammar_ref) REFERENCES grammar_units(grammar_ref)
        ) WITHOUT ROWID;

        CREATE TABLE masaq_segments (
          masaq_segment_ref TEXT PRIMARY KEY,
          surah INTEGER NOT NULL,
          ayah INTEGER NOT NULL,
          segment_index INTEGER NOT NULL,
          full_surface_ar TEXT NOT NULL,
          stem_ar TEXT NOT NULL,
          tag TEXT NOT NULL,
          role TEXT NOT NULL,
          root_ar TEXT NOT NULL,
          source_line INTEGER NOT NULL,
          source_status TEXT NOT NULL
        ) WITHOUT ROWID;

        CREATE TABLE reviewed_decisions (
          decision_id TEXT PRIMARY KEY,
          grammar_ref TEXT NOT NULL UNIQUE,
          qac_morpheme_refs TEXT NOT NULL,
          decision_type TEXT NOT NULL,
          reason TEXT NOT NULL,
          review_status TEXT NOT NULL CHECK (review_status = 'accepted'),
          reviewed_on TEXT NOT NULL,
          FOREIGN KEY (grammar_ref) REFERENCES grammar_units(grammar_ref)
        ) WITHOUT ROWID;

        CREATE TABLE reviewed_masaq_qac_decisions (
          decision_id TEXT PRIMARY KEY,
          grammar_ref TEXT NOT NULL,
          masaq_segment_ref TEXT NOT NULL,
          qac_morpheme_refs TEXT NOT NULL,
          decision_type TEXT NOT NULL,
          reason TEXT NOT NULL,
          review_status TEXT NOT NULL CHECK (review_status = 'accepted'),
          reviewed_on TEXT NOT NULL,
          UNIQUE (grammar_ref, masaq_segment_ref),
          FOREIGN KEY (grammar_ref) REFERENCES grammar_units(grammar_ref),
          FOREIGN KEY (masaq_segment_ref) REFERENCES masaq_segments(masaq_segment_ref)
        ) WITHOUT ROWID;

        CREATE TABLE reviewed_attachment_decisions (
          decision_id TEXT PRIMARY KEY,
          attachment_unit_ref TEXT NOT NULL,
          attachment_id TEXT NOT NULL,
          endpoint_role TEXT NOT NULL
            CHECK (endpoint_role IN ('', 'dependent', 'head', 'preposition')),
          decision_type TEXT NOT NULL
            CHECK (decision_type IN (
              'namespace-redirect', 'exclude-source-defect',
              'approve-fused-carrier'
            )),
          target_namespace TEXT NOT NULL
            CHECK (target_namespace IN (
              '', 'grammar-unit', 'masaq-segment', 'qac-morpheme'
            )),
          target_ref TEXT NOT NULL,
          reason TEXT NOT NULL,
          review_status TEXT NOT NULL CHECK (review_status = 'accepted'),
          reviewed_on TEXT NOT NULL,
          CHECK (
            (decision_type = 'namespace-redirect'
              AND attachment_unit_ref != ''
              AND attachment_id = ''
              AND endpoint_role = ''
              AND target_namespace != ''
              AND target_ref != '')
            OR
            (decision_type = 'exclude-source-defect'
              AND attachment_id != ''
              AND target_namespace = ''
              AND target_ref = '')
            OR
            (decision_type = 'approve-fused-carrier'
              AND attachment_unit_ref != ''
              AND attachment_id != ''
              AND endpoint_role != ''
              AND target_namespace = 'qac-morpheme'
              AND target_ref != '')
          )
        ) WITHOUT ROWID;

        CREATE TABLE attachment_unit_resolutions (
          attachment_unit_ref TEXT PRIMARY KEY,
          target_namespace TEXT NOT NULL
            CHECK (target_namespace IN ('grammar-unit', 'masaq-segment')),
          target_ref TEXT NOT NULL,
          resolution_rule TEXT NOT NULL,
          reviewed_decision_id TEXT,
          FOREIGN KEY (reviewed_decision_id)
            REFERENCES reviewed_attachment_decisions(decision_id)
        ) WITHOUT ROWID;

        CREATE TABLE attachment_endpoint_qac_edges (
          attachment_id TEXT NOT NULL,
          endpoint_role TEXT NOT NULL
            CHECK (endpoint_role IN ('dependent', 'head', 'preposition')),
          attachment_unit_ref TEXT NOT NULL,
          endpoint_part TEXT NOT NULL,
          surface_ar TEXT NOT NULL,
          form_tag TEXT NOT NULL,
          qac_morpheme_ref TEXT NOT NULL,
          target_order INTEGER NOT NULL,
          alignment_rule TEXT NOT NULL,
          alignment_reviewed_decision_id TEXT,
          PRIMARY KEY (attachment_id, endpoint_role, qac_morpheme_ref),
          FOREIGN KEY (attachment_unit_ref)
            REFERENCES attachment_unit_resolutions(attachment_unit_ref),
          FOREIGN KEY (qac_morpheme_ref)
            REFERENCES qac_morphemes(qac_morpheme_ref),
          FOREIGN KEY (alignment_reviewed_decision_id)
            REFERENCES reviewed_attachment_decisions(decision_id)
        ) WITHOUT ROWID;

        CREATE TABLE excluded_attachment_endpoints (
          attachment_id TEXT NOT NULL,
          endpoint_role TEXT NOT NULL
            CHECK (endpoint_role IN ('dependent', 'head', 'preposition')),
          attachment_unit_ref TEXT NOT NULL,
          reviewed_decision_id TEXT NOT NULL,
          PRIMARY KEY (attachment_id, endpoint_role),
          FOREIGN KEY (attachment_unit_ref)
            REFERENCES attachment_unit_resolutions(attachment_unit_ref),
          FOREIGN KEY (reviewed_decision_id)
            REFERENCES reviewed_attachment_decisions(decision_id)
        ) WITHOUT ROWID;

        CREATE TABLE analysis_grammar_edges (
          analysis_ref TEXT NOT NULL,
          grammar_ref TEXT NOT NULL,
          relation_status TEXT NOT NULL
            CHECK (relation_status IN ('accepted', 'excluded-source-defect')),
          evidence_rule TEXT NOT NULL,
          PRIMARY KEY (analysis_ref, grammar_ref),
          FOREIGN KEY (analysis_ref) REFERENCES word_analysis_units(analysis_ref),
          FOREIGN KEY (grammar_ref) REFERENCES grammar_units(grammar_ref)
        ) WITHOUT ROWID;

        CREATE TABLE grammar_masaq_edges (
          grammar_ref TEXT NOT NULL,
          masaq_segment_ref TEXT NOT NULL,
          masaq_ref_order INTEGER NOT NULL,
          alignment_group_id TEXT NOT NULL,
          grammar_order_within_group TEXT NOT NULL,
          masaq_order_within_group TEXT NOT NULL,
          trace_type TEXT NOT NULL,
          trace_status TEXT NOT NULL,
          trace_rule_id TEXT NOT NULL,
          trace_evidence TEXT NOT NULL,
          accepted INTEGER NOT NULL CHECK (accepted IN (0, 1)),
          PRIMARY KEY (grammar_ref, masaq_segment_ref),
          FOREIGN KEY (grammar_ref) REFERENCES grammar_units(grammar_ref),
          FOREIGN KEY (masaq_segment_ref) REFERENCES masaq_segments(masaq_segment_ref)
        ) WITHOUT ROWID;

        CREATE TABLE grammar_qac_edges (
          grammar_ref TEXT NOT NULL,
          qac_morpheme_ref TEXT NOT NULL,
          qac_order INTEGER NOT NULL,
          mapping_group_id TEXT NOT NULL,
          alignment_rule TEXT NOT NULL,
          automatic_alignment_rank INTEGER NOT NULL,
          automatic_edit_distance INTEGER NOT NULL,
          reviewed_decision_id TEXT,
          source_surface_ar TEXT NOT NULL,
          target_surface_ar TEXT NOT NULL,
          PRIMARY KEY (grammar_ref, qac_morpheme_ref),
          FOREIGN KEY (grammar_ref) REFERENCES grammar_units(grammar_ref),
          FOREIGN KEY (qac_morpheme_ref) REFERENCES qac_morphemes(qac_morpheme_ref),
          FOREIGN KEY (reviewed_decision_id) REFERENCES reviewed_decisions(decision_id)
        ) WITHOUT ROWID;

        CREATE TABLE masaq_qac_paths (
          masaq_segment_ref TEXT NOT NULL,
          qac_morpheme_ref TEXT NOT NULL,
          grammar_ref TEXT NOT NULL,
          alignment_group_id TEXT NOT NULL,
          trace_status TEXT NOT NULL,
          accepted INTEGER NOT NULL CHECK (accepted IN (0, 1)),
          reviewed_decision_id TEXT,
          PRIMARY KEY (masaq_segment_ref, qac_morpheme_ref, grammar_ref),
          FOREIGN KEY (masaq_segment_ref) REFERENCES masaq_segments(masaq_segment_ref),
          FOREIGN KEY (qac_morpheme_ref) REFERENCES qac_morphemes(qac_morpheme_ref),
          FOREIGN KEY (grammar_ref) REFERENCES grammar_units(grammar_ref),
          FOREIGN KEY (reviewed_decision_id)
            REFERENCES reviewed_masaq_qac_decisions(decision_id)
        ) WITHOUT ROWID;

        CREATE INDEX idx_qac_morphemes_word
          ON qac_morphemes(qac_word_ref, morpheme_index);
        CREATE INDEX idx_qac_morphemes_position
          ON qac_morphemes(surah, ayah, word_index, morpheme_index);
        CREATE INDEX idx_grammar_units_position
          ON grammar_units(surah, ayah, grammar_unit_index);
        CREATE INDEX idx_word_analysis_position
          ON word_analysis_units(surah, ayah, critical_w);
        CREATE INDEX idx_grammar_masaq_reverse
          ON grammar_masaq_edges(masaq_segment_ref, grammar_ref);
        CREATE INDEX idx_grammar_qac_reverse
          ON grammar_qac_edges(qac_morpheme_ref, grammar_ref);
        CREATE INDEX idx_masaq_qac_reverse
          ON masaq_qac_paths(qac_morpheme_ref, masaq_segment_ref);
        CREATE INDEX idx_attachment_resolution_target
          ON attachment_unit_resolutions(target_namespace, target_ref);
        CREATE INDEX idx_attachment_qac_reverse
          ON attachment_endpoint_qac_edges(qac_morpheme_ref, attachment_id);

        CREATE VIEW accepted_grammar_qac_edges AS
        SELECT gq.*
        FROM grammar_qac_edges gq
        JOIN grammar_units gu USING (grammar_ref)
        WHERE gu.analysis_disposition != 'excluded-source-defect';

        CREATE VIEW analysis_qac_edges AS
        SELECT
          ag.analysis_ref,
          gq.qac_morpheme_ref,
          gq.qac_order,
          ag.grammar_ref,
          gq.mapping_group_id,
          gq.alignment_rule,
          gq.reviewed_decision_id
        FROM analysis_grammar_edges ag
        JOIN grammar_qac_edges gq USING (grammar_ref)
        WHERE ag.relation_status = 'accepted';

        CREATE VIEW analysis_masaq_edges AS
        SELECT
          ag.analysis_ref,
          gm.masaq_segment_ref,
          gm.masaq_ref_order,
          gm.alignment_group_id,
          gm.grammar_order_within_group,
          gm.masaq_order_within_group,
          gm.trace_type,
          gm.trace_status,
          gm.trace_rule_id,
          gm.trace_evidence
        FROM analysis_grammar_edges ag
        JOIN grammar_masaq_edges gm USING (grammar_ref)
        WHERE ag.relation_status = 'accepted' AND gm.accepted = 1;

        CREATE VIEW accepted_masaq_qac_edges AS
        WITH distinct_edges AS (
          SELECT DISTINCT masaq_segment_ref, qac_morpheme_ref
          FROM masaq_qac_paths
          WHERE accepted = 1
        )
        SELECT
          edge.masaq_segment_ref,
          edge.qac_morpheme_ref,
          row_number() OVER (
            PARTITION BY edge.masaq_segment_ref
            ORDER BY qm.surah, qm.ayah, qm.word_index, qm.morpheme_index
          ) AS target_order
        FROM distinct_edges edge
        JOIN qac_morphemes qm USING (qac_morpheme_ref);

        CREATE VIEW qac_links AS
        SELECT
          'grammar-unit' AS source_namespace,
          grammar_ref AS source_ref,
          qac_morpheme_ref,
          mapping_group_id AS link_group_id,
          qac_order AS target_order
        FROM accepted_grammar_qac_edges
        UNION ALL
        SELECT
          'word-analysis' AS source_namespace,
          analysis_ref AS source_ref,
          qac_morpheme_ref,
          'analysis:' || analysis_ref AS link_group_id,
          qac_order AS target_order
        FROM analysis_qac_edges
        UNION ALL
        SELECT
          'masaq-segment' AS source_namespace,
          masaq_segment_ref AS source_ref,
          qac_morpheme_ref,
          'masaq:' || masaq_segment_ref AS link_group_id,
          target_order
        FROM accepted_masaq_qac_edges
        UNION ALL
        SELECT
          'attachment-endpoint' AS source_namespace,
          attachment_id || '#' || endpoint_role AS source_ref,
          qac_morpheme_ref,
          'attachment:' || attachment_id || '#' || endpoint_role AS link_group_id,
          target_order
        FROM attachment_endpoint_qac_edges;

        CREATE VIEW attachment_unit_qac_edges AS
        SELECT
          resolution.attachment_unit_ref,
          resolution.target_namespace,
          resolution.target_ref,
          edge.qac_morpheme_ref,
          edge.qac_order AS target_order,
          resolution.resolution_rule,
          resolution.reviewed_decision_id
        FROM attachment_unit_resolutions resolution
        JOIN accepted_grammar_qac_edges edge
          ON edge.grammar_ref = resolution.target_ref
        WHERE resolution.target_namespace = 'grammar-unit'
        UNION ALL
        SELECT
          resolution.attachment_unit_ref,
          resolution.target_namespace,
          resolution.target_ref,
          edge.qac_morpheme_ref,
          edge.target_order,
          resolution.resolution_rule,
          resolution.reviewed_decision_id
        FROM attachment_unit_resolutions resolution
        JOIN accepted_masaq_qac_edges edge
          ON edge.masaq_segment_ref = resolution.target_ref
        WHERE resolution.target_namespace = 'masaq-segment';

        CREATE VIEW attachment_qac_edges AS
        SELECT
          edge.attachment_id,
          edge.endpoint_role,
          edge.attachment_unit_ref,
          edge.endpoint_part,
          edge.surface_ar,
          edge.form_tag,
          edge.qac_morpheme_ref,
          edge.target_order,
          edge.alignment_rule,
          edge.alignment_reviewed_decision_id,
          resolution.target_namespace,
          resolution.target_ref,
          resolution.resolution_rule,
          resolution.reviewed_decision_id
        FROM attachment_endpoint_qac_edges edge
        JOIN attachment_unit_resolutions resolution USING (attachment_unit_ref);

        CREATE VIEW qac_analysis_groups AS
        SELECT
          qm.qac_word_ref,
          aq.qac_morpheme_ref,
          aq.analysis_ref,
          aq.qac_order,
          aq.mapping_group_id
        FROM analysis_qac_edges aq
        JOIN qac_morphemes qm USING (qac_morpheme_ref);
        """
    )


def build_sqlite(context: dict[str, object], audit: dict[str, Any]) -> bytes:
    qac_morphemes = list(context["qacMorphemes"])
    source_units = list(context["sourceUnits"])
    analysis_units = list(context["analysisUnits"])
    mappings = dict(context["mappings"])
    decisions = list(context["reviewedDecisions"])
    masaq_qac_decisions = list(context["reviewedMasaqQacDecisions"])
    masaq_qac_paths = list(context["masaqQacPaths"])
    attachment_decisions = list(context["reviewedAttachmentDecisions"])
    attachment_resolutions = list(context["attachmentResolutions"])
    attachment_qac_edges = list(context["attachmentQacEdges"])
    attachment_exclusions = list(context["attachmentExclusions"])
    analysis_statuses = dict(context["analysisStatuses"])
    decision_by_grammar = {item.grammar_ref: item for item in decisions}
    source_by_ref = {item.ref: item for item in source_units}
    analysis_refs = {item.ref for item in analysis_units}
    grammar_degrees = Counter(
        qac_ref
        for grammar_ref, mapping in mappings.items()
        if source_by_ref[grammar_ref].trace_status not in EXCLUDED_SOURCE_TRACE_STATUSES
        for qac_ref in mapping.qac_refs
    )

    with tempfile.NamedTemporaryFile(suffix=".sqlite") as handle:
        connection = sqlite3.connect(handle.name)
        connection.execute("PRAGMA page_size = 4096")
        connection.execute("PRAGMA journal_mode = OFF")
        connection.execute("PRAGMA synchronous = OFF")
        create_schema(connection)

        audit_bytes = stable_json(audit)
        metadata = {
            "schema_version": SCHEMA_VERSION,
            "builder_version": BUILDER_VERSION,
            "qac_is_canonical_unit": "true",
            "qac_morpheme_ref_format": "S:A:W:M",
            "source_projection_sha256": str(audit["source"]["projectionSha256"]),
            "qac_sha256": str(audit["source"]["qacSha256"]),
            "quran_roots_commit": str(audit["source"]["upstreamCommit"]),
            "quran_roots_source_sha256": str(audit["source"]["upstreamSha256"]),
            "quran_data_release_id": str(audit["source"]["releaseId"]),
            "quran_data_release_manifest_sha256": str(
                audit["source"]["releaseManifestSha256"]
            ),
            "word_analysis_tree_sha256": str(
                audit["source"]["wordAnalysisTreeSha256"]
            ),
            "reviewed_trace_decisions_sha256": str(
                audit["source"]["reviewedTraceDecisions"]["sha256"]
            ),
            "reviewed_decisions_sha256": str(audit["review"]["sha256"]),
            "reviewed_masaq_qac_decisions_sha256": str(
                audit["masaqQacReview"]["sha256"]
            ),
            "attachments_sha256": str(audit["attachments"]["source"]["sha256"]),
            "reviewed_attachment_decisions_sha256": str(
                audit["attachments"]["resolution"]["sha256"]
            ),
            "audit_sha256": sha256_bytes(audit_bytes),
            **{
                f"count_{key}": str(value)
                for key, value in audit["counts"].items()
            },
        }
        connection.executemany(
            "INSERT INTO metadata(key, value) VALUES (?, ?)",
            sorted(metadata.items()),
        )

        connection.executemany(
            """
            INSERT INTO qac_morphemes (
              qac_morpheme_ref, qac_word_ref, surah, ayah, word_index,
              morpheme_index, surface_ar, stem_ar, pos, morpheme_role,
              grammar_link_count, link_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item.ref,
                    item.word_ref,
                    item.surah,
                    item.ayah,
                    item.word_index,
                    item.morpheme_index,
                    item.surface_ar,
                    item.stem_ar,
                    item.pos,
                    item.role,
                    grammar_degrees.get(item.ref, 0),
                    "linked" if grammar_degrees.get(item.ref, 0) else "no-source-unit",
                )
                for item in sorted(qac_morphemes, key=lambda value: ref_sort_key(value.ref))
            ],
        )
        connection.executemany(
            """
            INSERT INTO grammar_units (
              grammar_ref, surah, ayah, grammar_unit_index, surface_ar,
              grammar, tag, analysis_disposition, trace_type, trace_status,
              trace_rule_id, trace_evidence, alignment_group_id,
              grammar_order_within_group, masaq_order_within_group,
              masaq_source_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item.ref,
                    item.surah,
                    item.ayah,
                    item.unit_index,
                    item.surface_ar,
                    item.grammar,
                    item.tag,
                    (
                        "excluded-source-defect"
                        if item.trace_status in EXCLUDED_SOURCE_TRACE_STATUSES
                        else "released-word-analysis"
                        if item.ref in analysis_refs
                        else "source-only"
                    ),
                    item.trace_type,
                    item.trace_status,
                    item.trace_rule_id,
                    item.trace_evidence,
                    item.alignment_group_id,
                    item.grammar_order_within_group,
                    item.masaq_order_within_group,
                    item.masaq_source_status,
                )
                for item in sorted(source_units, key=lambda value: ref_sort_key(value.ref))
            ],
        )
        connection.executemany(
            """
            INSERT INTO word_analysis_units (
              analysis_ref, surah, ayah, critical_w, surface_ar, grammar_ref,
              relation_status, exclusion_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item.ref,
                    item.surah,
                    item.ayah,
                    item.critical_w,
                    item.surface_ar,
                    item.ref,
                    analysis_statuses[item.ref],
                    (
                        source_by_ref[item.ref].trace_evidence
                        if analysis_statuses[item.ref] != "accepted"
                        else ""
                    ),
                )
                for item in sorted(analysis_units, key=lambda value: ref_sort_key(value.ref))
            ],
        )

        masaq_records: dict[str, tuple[str, str, str, str, str, int, str]] = {}
        for item in source_units:
            values = zip(
                item.masaq_refs,
                item.masaq_full_surfaces_ar,
                item.masaq_stems,
                item.masaq_tags,
                item.masaq_roles,
                item.masaq_roots_ar,
                item.masaq_source_lines,
                item.masaq_source_statuses,
                strict=True,
            )
            for ref, surface, stem, tag, role, root, source_line, status in values:
                try:
                    line_number = int(source_line)
                except ValueError as error:
                    raise RuntimeError(
                        f"invalid MASAQ source line at {item.ref}: {source_line!r}"
                    ) from error
                record = (surface, stem, tag, role, root, line_number, status)
                previous = masaq_records.setdefault(ref, record)
                if previous != record:
                    raise RuntimeError(
                        f"conflicting MASAQ metadata for {ref}: {previous!r} != {record!r}"
                    )
        masaq_refs = sorted(masaq_records, key=ref_sort_key)
        connection.executemany(
            """
            INSERT INTO masaq_segments (
              masaq_segment_ref, surah, ayah, segment_index,
              full_surface_ar, stem_ar, tag, role, root_ar,
              source_line, source_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (ref, *ref_sort_key(ref), *masaq_records[ref])
                for ref in masaq_refs
            ],
        )
        connection.executemany(
            """
            INSERT INTO reviewed_decisions (
              decision_id, grammar_ref, qac_morpheme_refs, decision_type,
              reason, review_status, reviewed_on
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item.decision_id,
                    item.grammar_ref,
                    "|".join(item.qac_refs),
                    item.decision_type,
                    item.reason,
                    item.review_status,
                    item.reviewed_on,
                )
                for item in sorted(decisions, key=lambda value: value.decision_id)
            ],
        )
        connection.executemany(
            """
            INSERT INTO reviewed_masaq_qac_decisions (
              decision_id, grammar_ref, masaq_segment_ref,
              qac_morpheme_refs, decision_type, reason,
              review_status, reviewed_on
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item.decision_id,
                    item.grammar_ref,
                    item.masaq_segment_ref,
                    "|".join(item.qac_refs),
                    item.decision_type,
                    item.reason,
                    item.review_status,
                    item.reviewed_on,
                )
                for item in sorted(
                    masaq_qac_decisions, key=lambda value: value.decision_id
                )
            ],
        )
        connection.executemany(
            """
            INSERT INTO reviewed_attachment_decisions (
              decision_id, attachment_unit_ref, attachment_id, endpoint_role,
              decision_type, target_namespace, target_ref, reason,
              review_status, reviewed_on
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item.decision_id,
                    item.attachment_unit_ref,
                    item.attachment_id,
                    item.endpoint_role,
                    item.decision_type,
                    item.target_namespace,
                    item.target_ref,
                    item.reason,
                    item.review_status,
                    item.reviewed_on,
                )
                for item in sorted(
                    attachment_decisions, key=lambda value: value.decision_id
                )
            ],
        )
        connection.executemany(
            """
            INSERT INTO attachment_unit_resolutions (
              attachment_unit_ref, target_namespace, target_ref,
              resolution_rule, reviewed_decision_id
            ) VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    item.attachment_unit_ref,
                    item.target_namespace,
                    item.target_ref,
                    item.resolution_rule,
                    item.reviewed_decision_id,
                )
                for item in attachment_resolutions
            ],
        )
        connection.executemany(
            """
            INSERT INTO attachment_endpoint_qac_edges (
              attachment_id, endpoint_role, attachment_unit_ref,
              endpoint_part, surface_ar, form_tag, qac_morpheme_ref,
              target_order, alignment_rule, alignment_reviewed_decision_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item.attachment_id,
                    item.endpoint_role,
                    item.attachment_unit_ref,
                    item.endpoint_part,
                    item.surface_ar,
                    item.form_tag,
                    item.qac_morpheme_ref,
                    item.target_order,
                    item.alignment_rule,
                    item.alignment_reviewed_decision_id,
                )
                for item in attachment_qac_edges
            ],
        )
        connection.executemany(
            """
            INSERT INTO excluded_attachment_endpoints (
              attachment_id, endpoint_role, attachment_unit_ref,
              reviewed_decision_id
            ) VALUES (?, ?, ?, ?)
            """,
            [
                (
                    item.attachment_id,
                    item.endpoint_role,
                    item.attachment_unit_ref,
                    item.reviewed_decision_id,
                )
                for item in attachment_exclusions
            ],
        )
        connection.executemany(
            """
            INSERT INTO analysis_grammar_edges (
              analysis_ref, grammar_ref, relation_status, evidence_rule
            ) VALUES (?, ?, ?, ?)
            """,
            [
                (
                    item.ref,
                    item.ref,
                    analysis_statuses[item.ref],
                    surface_relation(item.surface_ar, source.surface_ar).rule,
                )
                for item in sorted(analysis_units, key=lambda value: ref_sort_key(value.ref))
                for source in [source_by_ref[item.ref]]
            ],
        )

        grammar_masaq_rows: list[tuple[object, ...]] = []
        for item in sorted(source_units, key=lambda value: ref_sort_key(value.ref)):
            masaq_orders = [
                part for part in item.masaq_order_within_group.split("|") if part
            ]
            if item.masaq_refs and len(masaq_orders) != len(item.masaq_refs):
                raise RuntimeError(f"MASAQ order count mismatch at {item.ref}")
            for order, (masaq_ref, masaq_group_order) in enumerate(
                zip(item.masaq_refs, masaq_orders, strict=True), start=1
            ):
                grammar_masaq_rows.append(
                    (
                        item.ref,
                        masaq_ref,
                        order,
                        item.alignment_group_id,
                        item.grammar_order_within_group,
                        masaq_group_order,
                        item.trace_type,
                        item.trace_status,
                        item.trace_rule_id,
                        item.trace_evidence,
                        int(item.trace_status in ACCEPTED_MASAQ_TRACE_STATUSES),
                    )
                )
        connection.executemany(
            """
            INSERT INTO grammar_masaq_edges (
              grammar_ref, masaq_segment_ref, masaq_ref_order,
              alignment_group_id, grammar_order_within_group,
              masaq_order_within_group, trace_type, trace_status,
              trace_rule_id, trace_evidence, accepted
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            grammar_masaq_rows,
        )

        grammar_qac_rows: list[tuple[object, ...]] = []
        for grammar_ref in sorted(mappings, key=ref_sort_key):
            mapping = mappings[grammar_ref]
            decision = decision_by_grammar.get(grammar_ref)
            for order, qac_ref in enumerate(mapping.qac_refs, start=1):
                grammar_qac_rows.append(
                    (
                        grammar_ref,
                        qac_ref,
                        order,
                        f"grammar:{grammar_ref}",
                        mapping.rule,
                        mapping.rank,
                        mapping.edit_distance,
                        decision.decision_id if decision else None,
                        mapping.source_surface_ar,
                        mapping.target_surface_ar,
                    )
                )
        connection.executemany(
            """
            INSERT INTO grammar_qac_edges (
              grammar_ref, qac_morpheme_ref, qac_order, mapping_group_id,
              alignment_rule, automatic_alignment_rank,
              automatic_edit_distance, reviewed_decision_id,
              source_surface_ar, target_surface_ar
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            grammar_qac_rows,
        )

        connection.executemany(
            """
            INSERT INTO masaq_qac_paths (
              masaq_segment_ref, qac_morpheme_ref, grammar_ref,
              alignment_group_id, trace_status, accepted,
              reviewed_decision_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    item.masaq_segment_ref,
                    item.qac_morpheme_ref,
                    item.grammar_ref,
                    item.alignment_group_id,
                    item.trace_status,
                    item.accepted,
                    item.reviewed_decision_id,
                )
                for item in masaq_qac_paths
            ],
        )

        foreign_key_issues = connection.execute("PRAGMA foreign_key_check").fetchall()
        if foreign_key_issues:
            raise RuntimeError(f"bridge foreign-key check failed: {foreign_key_issues[:10]}")
        connection.commit()
        connection.execute("VACUUM")
        connection.close()
        handle.seek(0)
        return handle.read()


def deterministic_gzip(data: bytes) -> bytes:
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode="wb", filename="", mtime=0) as handle:
        handle.write(data)
    return output.getvalue()


def write_if_changed(path: Path, data: bytes) -> bool:
    if path.is_file() and path.read_bytes() == data:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--diagnose", action="store_true", help="run alignment and print its audit"
    )
    parser.add_argument(
        "--write", action="store_true", help="write the deterministic bridge and audit"
    )
    parser.add_argument(
        "--check", action="store_true", help="verify that bridge and audit are current"
    )
    parser.add_argument("--audit", type=Path, help="write the complete diagnostic JSON")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if sum((args.diagnose, args.write, args.check)) != 1:
        parser.error("choose exactly one of --diagnose, --write, or --check")
    audit, _context = build_audit()
    audit_path = args.audit or (DEFAULT_AUDIT if not args.diagnose else None)
    audit_bytes = stable_json(audit)
    if args.diagnose:
        if audit_path is not None:
            audit_path.parent.mkdir(parents=True, exist_ok=True)
            audit_path.write_bytes(audit_bytes)
    else:
        if audit["status"] != "accepted":
            raise RuntimeError(
                "bridge audit is not accepted: "
                f"weak={audit['review']['unresolvedWeakGrammarRefs']}, "
                f"ambiguous={audit['review']['unresolvedAmbiguousAyahs']}"
            )
        sqlite_bytes = build_sqlite(_context, audit)
        compressed = deterministic_gzip(sqlite_bytes)
        if args.write:
            changed = int(write_if_changed(args.output, compressed))
            if audit_path is None:
                raise RuntimeError("audit output path is required")
            changed += int(write_if_changed(audit_path, audit_bytes))
            print(
                f"bridge ready: sqlite_sha256={sha256_bytes(sqlite_bytes)}, "
                f"gzip_sha256={sha256_bytes(compressed)}, changed={changed}"
            )
            return 0
        stale: list[str] = []
        if not args.output.is_file() or args.output.read_bytes() != compressed:
            stale.append(str(args.output))
        if (
            audit_path is None
            or not audit_path.is_file()
            or audit_path.read_bytes() != audit_bytes
        ):
            stale.append(str(audit_path or DEFAULT_AUDIT))
        if stale:
            raise RuntimeError("stale bridge artifact(s): " + ", ".join(stale))
        print(
            f"bridge is current: sqlite_sha256={sha256_bytes(sqlite_bytes)}, "
            f"gzip_sha256={sha256_bytes(compressed)}"
        )
        return 0
    print(
        "alignment audit: "
        f"status={audit['status']}, "
        f"grammar_units={audit['counts']['grammarUnits']}, "
        f"weak={audit['alignment']['weakMappingCount']}, "
        f"ambiguous_ayahs={audit['alignment']['ambiguousAyahCount']}, "
        f"analysis_join_weak={audit['analysisJoin']['weakSurfaceCount']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
