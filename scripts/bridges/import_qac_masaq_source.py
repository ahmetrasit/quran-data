#!/usr/bin/env python3
"""Promote the reviewed MASAQ/grammar unit trace used by the QAC bridge."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import re
import subprocess
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_QURAN_ROOTS = (ROOT / "../quran-roots").resolve()
DEFAULT_OUTPUT = ROOT / "data/bridges/qac-masaq/source-units.tsv.gz"
DEFAULT_MANIFEST = ROOT / "data/bridges/qac-masaq/SOURCE.json"
DEFAULT_CORRECTIONS = ROOT / "data/bridges/qac-masaq/reviewed-trace-decisions.tsv"

UPSTREAM_COMMIT = "cc292f6727819620bb4e8eace0048534fab6a614"
UPSTREAM_PATH = "_corpus/sources/frozen/corpus.tsv.gz"
UPSTREAM_SHA256 = "1f01cb96265c5eb79cff5b87aa8abca11436b407b0c8b196eefd6f4cd8f2d59a"

OUTPUT_COLUMNS = (
    "surah",
    "ayah",
    "grammar_ref",
    "grammar_unit_index",
    "surface_ar",
    "grammar",
    "tag",
    "trace_type",
    "trace_status",
    "trace_rule_id",
    "trace_evidence",
    "masaq_refs",
    "masaq_segment_count",
    "alignment_group_id",
    "grammar_order_within_group",
    "masaq_order_within_group",
    "masaq_source_status",
    "masaq_full_surface_ar",
    "masaq_stems",
    "masaq_tags",
    "masaq_roles",
    "masaq_roots_ar",
    "masaq_source_lines",
    "masaq_source_statuses",
)

SOURCE_COLUMNS = {
    "sura": "surah",
    "ayah": "ayah",
    "tsv_word_ref": "grammar_ref",
    "tsv_word_id": "grammar_unit_index",
    "tsv_arabic_uthmani": "surface_ar",
    "tsv_grammar": "grammar",
    "tsv_tag": "tag",
    "trace_type": "trace_type",
    "trace_status": "trace_status",
    "trace_rule_id": "trace_rule_id",
    "trace_evidence": "trace_evidence",
    "masaq_segment_refs": "masaq_refs",
    "masaq_segment_count": "masaq_segment_count",
    "alignment_group_id": "alignment_group_id",
    "tsv_order_within_group": "grammar_order_within_group",
    "masaq_order_within_group": "masaq_order_within_group",
    "masaq_source_status": "masaq_source_status",
    "masaq_joined_arabic": "masaq_full_surface_ar",
    "masaq_joined_stems": "masaq_stems",
    "masaq_joined_tags": "masaq_tags",
    "masaq_joined_roles": "masaq_roles",
    "masaq_joined_roots_arabic": "masaq_roots_ar",
    "masaq_joined_source_lines": "masaq_source_lines",
    "masaq_joined_source_statuses": "masaq_source_statuses",
}

UNIT_REF_RE = re.compile(r"^(\d+):(\d+):(\d+)$")

CORRECTION_FIELDS = (
    "trace_type",
    "trace_status",
    "trace_rule_id",
    "trace_evidence",
    "masaq_refs",
    "masaq_segment_count",
    "alignment_group_id",
    "grammar_order_within_group",
    "masaq_order_within_group",
    "masaq_source_status",
    "masaq_full_surface_ar",
    "masaq_stems",
    "masaq_tags",
    "masaq_roles",
    "masaq_roots_ar",
    "masaq_source_lines",
    "masaq_source_statuses",
)

MASAQ_PARALLEL_FIELDS = (
    "masaq_order_within_group",
    "masaq_full_surface_ar",
    "masaq_stems",
    "masaq_tags",
    "masaq_roles",
    "masaq_roots_ar",
    "masaq_source_lines",
    "masaq_source_statuses",
)
MASAQ_NONEMPTY_FIELDS = {
    "masaq_order_within_group",
    "masaq_full_surface_ar",
    "masaq_stems",
    "masaq_source_lines",
    "masaq_source_statuses",
}
ACCEPTED_TRACE_STATUSES = {
    "exact",
    "approved-rule",
    "approved-exception",
    "reviewed-alignment",
}
REJECTED_TRACE_STATUS = "rejected-source-defect"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def split_masaq_values(
    value: str,
    count: int,
    field: str,
    grammar_ref: str,
    *,
    require_nonempty: bool = False,
) -> tuple[str, ...]:
    if count == 0:
        if value:
            raise SystemExit(f"unexpected {field} without MASAQ refs at {grammar_ref}")
        return ()
    parts = tuple(value.split("|"))
    if len(parts) != count:
        raise SystemExit(
            f"{field} count mismatch at {grammar_ref}: {len(parts)} != {count}"
        )
    if require_nonempty and any(not part for part in parts):
        raise SystemExit(f"empty {field} item at {grammar_ref}")
    return parts


def git_blob(repo: Path) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), "show", f"{UPSTREAM_COMMIT}:{UPSTREAM_PATH}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise SystemExit(f"cannot read pinned Quran Roots source: {detail}")
    if sha256(result.stdout) != UPSTREAM_SHA256:
        raise SystemExit("pinned Quran Roots source checksum mismatch")
    return result.stdout


def load_corrections(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {
            "decision_id",
            "grammar_ref",
            "expected_trace_status",
            *CORRECTION_FIELDS,
            "reason",
            "review_status",
            "reviewed_on",
        }
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            missing = sorted(required - set(reader.fieldnames or ()))
            raise SystemExit(f"trace-correction ledger is missing columns: {missing}")
        rows = list(reader)

    if len({row["decision_id"] for row in rows}) != len(rows):
        raise SystemExit("duplicate trace-correction decision id")
    if len({row["grammar_ref"] for row in rows}) != len(rows):
        raise SystemExit("duplicate trace-correction grammar ref")
    for row in rows:
        if row["review_status"] != "accepted":
            raise SystemExit(f"non-accepted trace decision: {row['decision_id']}")
        if UNIT_REF_RE.fullmatch(row["grammar_ref"]) is None:
            raise SystemExit(f"invalid trace-decision grammar ref: {row['grammar_ref']}")
    return {row["grammar_ref"]: row for row in rows}


def project(
    source_gzip: bytes,
    corrections_path: Path = DEFAULT_CORRECTIONS,
) -> tuple[bytes, dict[str, object]]:
    source_text = gzip.decompress(source_gzip).decode("utf-8")
    reader = csv.DictReader(io.StringIO(source_text), delimiter="\t")
    if reader.fieldnames is None or not set(SOURCE_COLUMNS).issubset(reader.fieldnames):
        missing = sorted(set(SOURCE_COLUMNS) - set(reader.fieldnames or ()))
        raise SystemExit(f"upstream corpus is missing source columns: {missing}")

    corrections = load_corrections(corrections_path)
    applied_corrections: set[str] = set()
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=OUTPUT_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()

    row_count = 0
    ayahs: set[tuple[int, int]] = set()
    grammar_refs: set[str] = set()
    grammar_indices_by_ayah: dict[tuple[int, int], set[int]] = {}
    masaq_refs: set[str] = set()
    masaq_indices_by_ayah: dict[tuple[int, int], set[int]] = {}
    masaq_records: dict[str, tuple[str, ...]] = {}
    masaq_group_positions: dict[str, tuple[str, int]] = {}
    alignment_group_ayahs: dict[str, tuple[int, int]] = {}
    grammar_orders_by_group: dict[str, dict[int, str]] = {}
    masaq_orders_by_group: dict[str, dict[int, str]] = {}
    status_counts: Counter[str] = Counter()
    previous_key = (0, 0, 0)

    for source_row in reader:
        row = {target: source_row[source] for source, target in SOURCE_COLUMNS.items()}
        correction = corrections.get(row["grammar_ref"])
        if correction is not None:
            if row["trace_status"] != correction["expected_trace_status"]:
                raise SystemExit(
                    f"trace-decision preimage drift at {row['grammar_ref']}: "
                    f"{row['trace_status']!r} != {correction['expected_trace_status']!r}"
                )
            for field in CORRECTION_FIELDS:
                row[field] = correction[field]
            applied_corrections.add(row["grammar_ref"])
        match = UNIT_REF_RE.fullmatch(row["grammar_ref"])
        if match is None:
            raise SystemExit(f"invalid grammar ref: {row['grammar_ref']!r}")
        key = tuple(int(part) for part in match.groups())
        if key != (
            int(row["surah"]),
            int(row["ayah"]),
            int(row["grammar_unit_index"]),
        ):
            raise SystemExit(f"grammar ref fields disagree: {row['grammar_ref']}")
        if key <= previous_key:
            raise SystemExit(f"source rows are not strictly ordered at {row['grammar_ref']}")
        previous_key = key
        if row["grammar_ref"] in grammar_refs:
            raise SystemExit(f"duplicate grammar ref: {row['grammar_ref']}")

        try:
            masaq_count = int(row["masaq_segment_count"] or "0")
        except ValueError as error:
            raise SystemExit(
                f"invalid MASAQ segment count at {row['grammar_ref']}: "
                f"{row['masaq_segment_count']!r}"
            ) from error
        if masaq_count < 0:
            raise SystemExit(f"negative MASAQ segment count at {row['grammar_ref']}")
        refs = split_masaq_values(
            row["masaq_refs"],
            masaq_count,
            "masaq_refs",
            row["grammar_ref"],
            require_nonempty=True,
        )
        if len(set(refs)) != len(refs):
            raise SystemExit(f"duplicate MASAQ ref within {row['grammar_ref']}")
        values_by_field = {
            field: split_masaq_values(
                row[field],
                masaq_count,
                field,
                row["grammar_ref"],
                require_nonempty=field in MASAQ_NONEMPTY_FIELDS,
            )
            for field in MASAQ_PARALLEL_FIELDS
        }
        if row["trace_status"] not in ACCEPTED_TRACE_STATUSES | {REJECTED_TRACE_STATUS}:
            raise SystemExit(
                f"unreviewed trace status at {row['grammar_ref']}: "
                f"{row['trace_status']!r}"
            )
        if (masaq_count == 0) != (row["trace_status"] == REJECTED_TRACE_STATUS):
            raise SystemExit(
                f"MASAQ refs/disposition disagree at {row['grammar_ref']}: "
                f"count={masaq_count}, status={row['trace_status']!r}"
            )

        masaq_group_orders = values_by_field["masaq_order_within_group"]
        for order in masaq_group_orders:
            if not order.isdigit() or int(order) <= 0:
                raise SystemExit(
                    f"invalid MASAQ group order at {row['grammar_ref']}: {order!r}"
                )
        if list(map(int, masaq_group_orders)) != sorted(
            {int(order) for order in masaq_group_orders}
        ):
            raise SystemExit(
                f"non-monotonic or duplicate MASAQ group order at "
                f"{row['grammar_ref']}"
            )
        grammar_group_order = row["grammar_order_within_group"]
        if not grammar_group_order.isdigit() or int(grammar_group_order) <= 0:
            raise SystemExit(
                f"invalid grammar group order at {row['grammar_ref']}: "
                f"{grammar_group_order!r}"
            )
        if not row["alignment_group_id"]:
            raise SystemExit(f"empty alignment group id at {row['grammar_ref']}")
        group_id = row["alignment_group_id"]
        group_ayah = alignment_group_ayahs.setdefault(group_id, key[:2])
        if group_ayah != key[:2]:
            raise SystemExit(
                f"cross-ayah alignment group {group_id}: "
                f"{group_ayah[0]}:{group_ayah[1]} != {key[0]}:{key[1]}"
            )
        grammar_order = int(grammar_group_order)
        grammar_orders = grammar_orders_by_group.setdefault(group_id, {})
        previous_grammar = grammar_orders.setdefault(
            grammar_order, row["grammar_ref"]
        )
        if previous_grammar != row["grammar_ref"]:
            raise SystemExit(
                f"duplicate grammar order {grammar_order} in alignment group "
                f"{group_id}: {previous_grammar}, {row['grammar_ref']}"
            )
        for source_line in values_by_field["masaq_source_lines"]:
            if not source_line.isdigit() or int(source_line) <= 0:
                raise SystemExit(
                    f"invalid MASAQ source line at {row['grammar_ref']}: "
                    f"{source_line!r}"
                )

        for index, ref in enumerate(refs):
            ref_match = UNIT_REF_RE.fullmatch(ref)
            if ref_match is None:
                raise SystemExit(f"invalid MASAQ ref at {row['grammar_ref']}: {ref!r}")
            ref_key = tuple(int(part) for part in ref_match.groups())
            if ref_key[:2] != key[:2] or ref_key[2] <= 0:
                raise SystemExit(
                    f"cross-ayah or non-positive MASAQ ref at "
                    f"{row['grammar_ref']}: {ref}"
                )
            record = tuple(
                values_by_field[field][index]
                for field in MASAQ_PARALLEL_FIELDS
                if field != "masaq_order_within_group"
            )
            previous_record = masaq_records.setdefault(ref, record)
            if previous_record != record:
                raise SystemExit(
                    f"conflicting promoted MASAQ metadata for {ref}: "
                    f"{previous_record!r} != {record!r}"
                )
            masaq_refs.add(ref)
            masaq_indices_by_ayah.setdefault(ref_key[:2], set()).add(ref_key[2])
            masaq_order = int(masaq_group_orders[index])
            previous_group_position = masaq_group_positions.setdefault(
                ref, (group_id, masaq_order)
            )
            if previous_group_position != (group_id, masaq_order):
                raise SystemExit(
                    f"conflicting alignment-group position for {ref}: "
                    f"{previous_group_position!r} != {(group_id, masaq_order)!r}"
                )
            masaq_orders = masaq_orders_by_group.setdefault(group_id, {})
            previous_masaq = masaq_orders.setdefault(masaq_order, ref)
            if previous_masaq != ref:
                raise SystemExit(
                    f"duplicate MASAQ order {masaq_order} in alignment group "
                    f"{group_id}: {previous_masaq}, {ref}"
                )

        writer.writerow(row)
        row_count += 1
        grammar_refs.add(row["grammar_ref"])
        grammar_indices_by_ayah.setdefault(key[:2], set()).add(key[2])
        ayahs.add((key[0], key[1]))
        status_counts[row["trace_status"]] += 1

    unapplied = sorted(set(corrections) - applied_corrections)
    if unapplied:
        raise SystemExit(f"trace decisions reference missing source rows: {unapplied}")

    if row_count != 95_511 or len(ayahs) != 6_236 or len(masaq_refs) != 95_511:
        raise SystemExit(
            f"unexpected source coverage: rows={row_count}, ayahs={len(ayahs)}, "
            f"masaq_refs={len(masaq_refs)}"
        )
    if set(masaq_indices_by_ayah) != ayahs:
        raise SystemExit("MASAQ and grammar ayah coverage disagree")
    for ayah_key, indices in grammar_indices_by_ayah.items():
        if indices != set(range(1, len(indices) + 1)):
            raise SystemExit(
                f"non-contiguous grammar unit space at {ayah_key[0]}:{ayah_key[1]}"
            )
    for ayah_key, indices in masaq_indices_by_ayah.items():
        if indices != set(range(1, len(indices) + 1)):
            raise SystemExit(
                f"non-contiguous MASAQ segment space at {ayah_key[0]}:{ayah_key[1]}"
            )
    for group_id, grammar_orders in grammar_orders_by_group.items():
        if set(grammar_orders) != set(range(1, len(grammar_orders) + 1)):
            raise SystemExit(
                f"non-contiguous grammar order in alignment group {group_id}"
            )
        masaq_orders = masaq_orders_by_group.get(group_id, {})
        if masaq_orders and set(masaq_orders) != set(
            range(1, len(masaq_orders) + 1)
        ):
            raise SystemExit(
                f"non-contiguous MASAQ order in alignment group {group_id}"
            )

    tsv = output.getvalue().encode("utf-8")
    compressed = io.BytesIO()
    with gzip.GzipFile(fileobj=compressed, mode="wb", filename="", mtime=0) as handle:
        handle.write(tsv)

    summary: dict[str, object] = {
        "schema": "qac-masaq-source-v1",
        "upstreamRepository": "quran-roots",
        "upstreamCommit": UPSTREAM_COMMIT,
        "upstreamPath": UPSTREAM_PATH,
        "upstreamSha256": UPSTREAM_SHA256,
        "projectionPath": str(DEFAULT_OUTPUT.relative_to(ROOT)),
        "projectionSha256": sha256(compressed.getvalue()),
        "projectionUncompressedSha256": sha256(tsv),
        "grammarUnitCount": row_count,
        "masaqRefCount": len(masaq_refs),
        "ayahCount": len(ayahs),
        "traceStatusCounts": dict(sorted(status_counts.items())),
        "reviewedTraceDecisions": {
            "path": str(corrections_path.resolve().relative_to(ROOT.resolve())),
            "sha256": sha256(corrections_path.read_bytes()),
            "count": len(corrections),
        },
    }
    return compressed.getvalue(), summary


def stable_json(payload: object) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def write_if_changed(path: Path, payload: bytes) -> bool:
    if path.is_file() and path.read_bytes() == payload:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quran-roots", type=Path, default=DEFAULT_QURAN_ROOTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--corrections", type=Path, default=DEFAULT_CORRECTIONS)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    compressed, summary = project(
        git_blob(args.quran_roots.resolve()), args.corrections.resolve()
    )
    summary["projectionPath"] = str(args.output.resolve().relative_to(ROOT.resolve()))
    manifest = stable_json(summary)

    if args.check:
        stale = []
        if not args.output.is_file() or args.output.read_bytes() != compressed:
            stale.append(str(args.output))
        if not args.manifest.is_file() or args.manifest.read_bytes() != manifest:
            stale.append(str(args.manifest))
        if stale:
            raise SystemExit("stale promoted source artifact(s): " + ", ".join(stale))
        print(f"source projection is current: rows={summary['grammarUnitCount']}")
        return 0

    changed = int(write_if_changed(args.output, compressed))
    changed += int(write_if_changed(args.manifest, manifest))
    print(
        f"source projection ready: rows={summary['grammarUnitCount']}, "
        f"masaq_refs={summary['masaqRefCount']}, changed={changed}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
