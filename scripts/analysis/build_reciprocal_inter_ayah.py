#!/usr/bin/env python3
"""Build the typed row-reciprocal inter-ayah TSV corpus.

The directional three-column corpus remains immutable input. This builder
projects every source row into explicit per-ayah records and mirrors every
source-row/target-component occurrence into the linked ayah's document. A
non-self meaningful source label creates a reciprocal nomination; ``no value``
and ``reject`` create reciprocal counterevidence. A self-link creates a typed
reiteration instead of a fictitious reverse direction. None is a
receiving-direction judgment.

The source corpus is staged in a temporary SQLite database so the complete
projection can be emitted one ayah at a time with bounded memory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = REPO_ROOT / "data" / "analysis" / "inter-ayah"
OUTPUT_DIR = SOURCE_DIR / "reciprocal"
QURAN_TEXT = REPO_ROOT / "data" / "text" / "quran-uthmani.tsv"

LABELS = {"strong", "medium", "weak", "no value", "contrast", "reject"}
MEANINGFUL_LABELS = LABELS - {"no value", "reject"}
FILE_RE = re.compile(r"focus_([1-9][0-9]*)_([1-9][0-9]*)_cutoff_100\.tsv")
AYAH_RE = re.compile(r"([1-9][0-9]*):([1-9][0-9]*)")
RANGE_RE = re.compile(r"([1-9][0-9]*):([1-9][0-9]*)-([1-9][0-9]*)")
TSV_COLUMNS = (
    "record_type",
    "focus_ref",
    "target_ref",
    "focus_direction_label",
    "source_direction_label",
    "source_focus_ref",
    "source_target_ref",
    "source_target_component_ref",
    "relation_scope",
    "source_column_order",
    "source_row_role",
    "source_note",
    "source_file",
    "source_line",
    "source_row_sha256",
)
TSV_HEADER = "\t".join(TSV_COLUMNS)


@dataclass(frozen=True)
class ComponentRow:
    origin_ref: str
    label: str
    target_ref: str
    component_ref: str
    note: str
    source_name: str
    line_number: int
    target_first: bool
    raw_line_sha256: str


@dataclass(frozen=True)
class ProjectionRow:
    record_type: str
    focus_ref: str
    target_ref: str
    focus_direction_label: str
    source_direction_label: str
    source_focus_ref: str
    source_target_ref: str
    source_target_component_ref: str
    relation_scope: str
    source_column_order: str
    source_row_role: str
    source_note: str
    source_file: str
    source_line: int
    source_row_sha256: str

    def line(self) -> str:
        values = (
            self.record_type,
            self.focus_ref,
            self.target_ref,
            self.focus_direction_label,
            self.source_direction_label,
            self.source_focus_ref,
            self.source_target_ref,
            self.source_target_component_ref,
            self.relation_scope,
            self.source_column_order,
            self.source_row_role,
            self.source_note,
            self.source_file,
            str(self.source_line),
            self.source_row_sha256,
        )
        if any("\t" in value or "\n" in value or "\r" in value for value in values):
            raise SystemExit(
                f"Projection value is not TSV-safe at {self.source_file}:"
                f"{self.source_line}"
            )
        return "\t".join(values)


def _ref_key(ref: str) -> tuple[int, int]:
    match = AYAH_RE.fullmatch(ref)
    if match is None:
        raise ValueError(f"Not a single ayah reference: {ref!r}")
    return int(match.group(1)), int(match.group(2))


def _relation_scope(first_ref: str, second_ref: str) -> str:
    return (
        "same_surah"
        if _ref_key(first_ref)[0] == _ref_key(second_ref)[0]
        else "cross_surah"
    )


def _update_corpus_digest(
    digest: Any, name: str, payload: bytes
) -> None:
    name_bytes = name.encode("utf-8")
    digest.update(len(name_bytes).to_bytes(4, "big"))
    digest.update(name_bytes)
    digest.update(len(payload).to_bytes(8, "big"))
    digest.update(payload)


def _load_numbered_ayahs(path: Path) -> set[str]:
    try:
        lines = path.resolve(strict=True).read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise SystemExit(f"Cannot read Quran text {path}: {exc}") from exc

    refs: set[str] = set()
    for line_number, line in enumerate(lines, 1):
        try:
            ref, _arabic = line.split("|", 1)
        except ValueError as exc:
            raise SystemExit(
                f"Malformed Quran text row at {path}:{line_number}"
            ) from exc
        match = re.fullmatch(r"([1-9][0-9]*):([0-9]+)", ref)
        if match is None:
            raise SystemExit(f"Invalid Quran ayah ref at {path}:{line_number}: {ref}")
        if int(match.group(2)) == 0:
            continue
        if ref in refs:
            raise SystemExit(f"Duplicate Quran ayah ref at {path}:{line_number}: {ref}")
        refs.add(ref)
    return refs


def _expected_name(ref: str) -> str:
    surah, ayah = _ref_key(ref)
    return f"focus_{surah}_{ayah}_cutoff_100.tsv"


def _expand_target(
    target_ref: str, valid_refs: set[str], location: str
) -> tuple[str, ...]:
    if AYAH_RE.fullmatch(target_ref):
        if target_ref not in valid_refs:
            raise SystemExit(f"Unknown target ayah at {location}: {target_ref}")
        return (target_ref,)

    match = RANGE_RE.fullmatch(target_ref)
    if match is None:
        raise SystemExit(f"Invalid target ayah or range at {location}: {target_ref}")
    surah, first, last = map(int, match.groups())
    if first > last:
        raise SystemExit(f"Descending target range at {location}: {target_ref}")
    endpoint_refs = (f"{surah}:{first}", f"{surah}:{last}")
    if any(ref not in valid_refs for ref in endpoint_refs):
        raise SystemExit(
            f"Target range has an unknown endpoint at {location}: {target_ref}"
        )
    expanded = tuple(f"{surah}:{ayah}" for ayah in range(first, last + 1))
    unknown = [ref for ref in expanded if ref not in valid_refs]
    if unknown:
        raise SystemExit(
            f"Target range contains unknown ayahs at {location}: "
            + ", ".join(unknown)
        )
    return expanded


def _source_paths(source_dir: Path, valid_refs: set[str]) -> list[Path]:
    paths = sorted(source_dir.glob("focus_*_cutoff_100.tsv"))
    unsafe_paths = [
        path.name for path in paths if path.is_symlink() or not path.is_file()
    ]
    if unsafe_paths:
        raise SystemExit(
            "Directional corpus entries must be regular non-symlink files: "
            + ", ".join(unsafe_paths[:20])
        )
    invalid_names = [path.name for path in paths if not FILE_RE.fullmatch(path.name)]
    if invalid_names:
        raise SystemExit(
            "Malformed directional corpus filenames: " + ", ".join(invalid_names[:20])
        )
    actual_names = {path.name for path in paths}
    expected_names = {_expected_name(ref) for ref in valid_refs}
    if actual_names != expected_names:
        missing = sorted(expected_names - actual_names)[:20]
        extra = sorted(actual_names - expected_names)[:20]
        raise SystemExit(
            "Directional corpus does not cover the numbered Quran exactly; "
            f"missing={missing}, extra={extra}"
        )
    return paths


def _create_stage(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA journal_mode = OFF;
        PRAGMA synchronous = OFF;
        PRAGMA temp_store = FILE;
        CREATE TABLE components (
            component_id INTEGER PRIMARY KEY,
            origin_ref TEXT NOT NULL,
            origin_surah INTEGER NOT NULL,
            origin_ayah INTEGER NOT NULL,
            label TEXT NOT NULL,
            target_ref TEXT NOT NULL,
            component_ref TEXT NOT NULL,
            component_surah INTEGER NOT NULL,
            component_ayah INTEGER NOT NULL,
            note TEXT NOT NULL,
            source_name TEXT NOT NULL,
            source_line INTEGER NOT NULL,
            target_first INTEGER NOT NULL,
            raw_line_sha256 TEXT NOT NULL
        );
        """
    )


def _stage_source_rows(
    connection: sqlite3.Connection,
    source_dir: Path,
    valid_refs: set[str],
) -> tuple[str, dict[str, int | bool]]:
    paths = _source_paths(source_dir, valid_refs)
    source_digest = hashlib.sha256()
    stats: dict[str, int | bool] = {
        "source_file_count": len(paths),
        "source_row_count": 0,
        "source_target_component_count": 0,
        "meaningful_source_row_count": 0,
        "reciprocal_nomination_record_count": 0,
        "reciprocal_counterevidence_record_count": 0,
        "self_reiteration_record_count": 0,
        "same_surah_component_count": 0,
        "cross_surah_component_count": 0,
        "self_component_count": 0,
        "normalized_target_first_row_count": 0,
        "range_source_row_count": 0,
        "range_expanded_component_count": 0,
        "source_note_boundary_space_preserved_count": 0,
        "ranked_review_source_row_count": 0,
        "missing_ayah_suggestion_source_row_count": 0,
    }
    insert_sql = """
        INSERT INTO components (
            origin_ref, origin_surah, origin_ayah, label, target_ref,
            component_ref, component_surah, component_ayah, note, source_name,
            source_line, target_first, raw_line_sha256
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    for path in paths:
        match = FILE_RE.fullmatch(path.name)
        if match is None:
            raise SystemExit(f"Internal filename validation failure: {path.name}")
        origin_surah, origin_ayah = map(int, match.groups())
        origin_ref = f"{origin_surah}:{origin_ayah}"
        try:
            payload = path.read_bytes()
        except OSError as exc:
            raise SystemExit(f"Cannot read directional TSV {path}: {exc}") from exc
        _update_corpus_digest(source_digest, path.name, payload)
        try:
            lines = payload.decode("utf-8").splitlines()
        except UnicodeDecodeError as exc:
            raise SystemExit(f"Directional TSV is not UTF-8: {path}") from exc
        staged: list[tuple[object, ...]] = []
        for line_number, line in enumerate(lines, 1):
            fields = line.split("\t")
            if len(fields) != 3:
                raise SystemExit(
                    f"Expected three TSV fields at {path}:{line_number}; "
                    f"found {len(fields)}"
                )
            first_raw, second_raw, note = fields
            first, second = first_raw.strip(), second_raw.strip()
            if first in LABELS:
                label, target_ref, target_first = first, second, False
            elif second in LABELS:
                target_ref, label, target_first = first, second, True
            else:
                raise SystemExit(
                    f"Cannot identify label and target at {path}:{line_number}"
                )
            expanded_targets = _expand_target(
                target_ref, valid_refs, f"{path}:{line_number}"
            )
            stats["source_row_count"] += 1
            source_row_role = (
                "ranked_review"
                if line_number <= 100
                else "missing_ayah_suggestion"
            )
            stats[f"{source_row_role}_source_row_count"] += 1
            stats["meaningful_source_row_count"] += int(
                label in MEANINGFUL_LABELS
            )
            stats["normalized_target_first_row_count"] += int(target_first)
            stats["source_note_boundary_space_preserved_count"] += int(
                note != note.strip()
            )
            if RANGE_RE.fullmatch(target_ref):
                stats["range_source_row_count"] += 1
                stats["range_expanded_component_count"] += len(expanded_targets)
            raw_line_sha256 = hashlib.sha256(line.encode("utf-8")).hexdigest()
            for component_ref in expanded_targets:
                component_surah, component_ayah = _ref_key(component_ref)
                scope = _relation_scope(origin_ref, component_ref)
                stats["source_target_component_count"] += 1
                stats[f"{scope}_component_count"] += 1
                stats["self_component_count"] += int(origin_ref == component_ref)
                if origin_ref == component_ref:
                    stats["self_reiteration_record_count"] += 1
                elif label in MEANINGFUL_LABELS:
                    stats["reciprocal_nomination_record_count"] += 1
                else:
                    stats["reciprocal_counterevidence_record_count"] += 1
                staged.append(
                    (
                        origin_ref,
                        origin_surah,
                        origin_ayah,
                        label,
                        target_ref,
                        component_ref,
                        component_surah,
                        component_ayah,
                        note,
                        path.name,
                        line_number,
                        int(target_first),
                        raw_line_sha256,
                    )
                )
        connection.executemany(insert_sql, staged)
    connection.commit()
    connection.executescript(
        """
        CREATE INDEX components_by_origin ON components (
            origin_surah, origin_ayah, source_line, component_surah,
            component_ayah, component_id
        );
        CREATE INDEX components_by_target ON components (
            component_surah, component_ayah, origin_surah, origin_ayah,
            source_name, source_line, component_id
        );
        CREATE TABLE meaningful_edges AS
        SELECT
            origin_ref, origin_surah, origin_ayah,
            component_ref, component_surah, component_ayah,
            MAX(label = 'strong')
              + 2 * MAX(label = 'medium')
              + 4 * MAX(label = 'weak')
              + 8 * MAX(label = 'contrast') AS label_mask
        FROM components
        WHERE label IN ('strong', 'medium', 'weak', 'contrast')
        GROUP BY origin_ref, component_ref;
        CREATE UNIQUE INDEX meaningful_edges_pair ON meaningful_edges (
            origin_surah, origin_ayah, component_surah, component_ayah
        );
        """
    )
    meaningful_directed_pair_count = connection.execute(
        "SELECT COUNT(*) FROM meaningful_edges"
    ).fetchone()[0]
    bidirectional_counts = connection.execute(
        """
        SELECT COUNT(*), COALESCE(SUM(a.label_mask != b.label_mask), 0)
        FROM meaningful_edges AS a
        JOIN meaningful_edges AS b
          ON b.origin_surah = a.component_surah
         AND b.origin_ayah = a.component_ayah
         AND b.component_surah = a.origin_surah
         AND b.component_ayah = a.origin_ayah
        WHERE (a.origin_surah < a.component_surah)
           OR (a.origin_surah = a.component_surah
               AND a.origin_ayah < a.component_ayah)
        """
    ).fetchone()
    stats["meaningful_directed_pair_count"] = meaningful_directed_pair_count
    stats["meaningful_bidirectional_pair_count"] = bidirectional_counts[0]
    stats["meaningful_bidirectional_label_disagreement_pair_count"] = (
        bidirectional_counts[1]
    )
    return source_digest.hexdigest(), stats


def _component_from_db(row: tuple[object, ...]) -> ComponentRow:
    return ComponentRow(
        origin_ref=str(row[0]),
        label=str(row[1]),
        target_ref=str(row[2]),
        component_ref=str(row[3]),
        note=str(row[4]),
        source_name=str(row[5]),
        line_number=int(row[6]),
        target_first=bool(row[7]),
        raw_line_sha256=str(row[8]),
    )


def _project_row(
    source_row: ComponentRow,
    *,
    reciprocal: bool,
) -> ProjectionRow:
    if reciprocal:
        if source_row.origin_ref == source_row.component_ref:
            record_type = "self_reiteration"
        else:
            record_type = (
                "reciprocal_nomination"
                if source_row.label in MEANINGFUL_LABELS
                else "reciprocal_counterevidence"
            )
        focus_ref = source_row.component_ref
        target_ref = source_row.origin_ref
        focus_direction_label = ""
    else:
        record_type = "directional_review"
        focus_ref = source_row.origin_ref
        target_ref = source_row.component_ref
        focus_direction_label = source_row.label
    return ProjectionRow(
        record_type=record_type,
        focus_ref=focus_ref,
        target_ref=target_ref,
        focus_direction_label=focus_direction_label,
        source_direction_label=source_row.label,
        source_focus_ref=source_row.origin_ref,
        source_target_ref=source_row.target_ref,
        source_target_component_ref=source_row.component_ref,
        relation_scope=_relation_scope(
            source_row.origin_ref, source_row.component_ref
        ),
        source_column_order=(
            "target_label_note" if source_row.target_first else "label_target_note"
        ),
        source_row_role=(
            "ranked_review"
            if source_row.line_number <= 100
            else "missing_ayah_suggestion"
        ),
        source_note=source_row.note,
        source_file=source_row.source_name,
        source_line=source_row.line_number,
        source_row_sha256=source_row.raw_line_sha256,
    )


def _render_focus(
    connection: sqlite3.Connection, focus_ref: str
) -> tuple[bytes, int, int]:
    focus_surah, focus_ayah = _ref_key(focus_ref)
    selected_columns = """
        origin_ref, label, target_ref, component_ref, note, source_name,
        source_line, target_first, raw_line_sha256
    """
    directional_cursor = connection.execute(
        f"""
        SELECT {selected_columns}
        FROM components
        WHERE origin_surah = ? AND origin_ayah = ?
        ORDER BY source_line, component_surah, component_ayah, component_id
        """,
        (focus_surah, focus_ayah),
    )
    directional = [
        _project_row(_component_from_db(row), reciprocal=False)
        for row in directional_cursor
    ]
    reciprocal_cursor = connection.execute(
        f"""
        SELECT {selected_columns}
        FROM components
        WHERE component_surah = ? AND component_ayah = ?
        ORDER BY origin_surah, origin_ayah, source_name, source_line, component_id
        """,
        (focus_surah, focus_ayah),
    )
    reciprocal = [
        _project_row(_component_from_db(row), reciprocal=True)
        for row in reciprocal_cursor
    ]
    lines = [TSV_HEADER]
    lines.extend(row.line() for row in directional)
    lines.extend(row.line() for row in reciprocal)
    return (
        ("\n".join(lines) + "\n").encode("utf-8"),
        len(directional),
        len(reciprocal),
    )


def _pretty_json(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def _write_if_changed(path: Path, payload: bytes) -> bool:
    if path.is_symlink():
        raise SystemExit(f"Refusing to replace generated symlink: {path}")
    if path.exists() and not path.is_file():
        raise SystemExit(f"Refusing to replace non-file output entry: {path}")
    if path.is_file() and path.read_bytes() == payload:
        return False
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(payload)
            temporary.flush()
            os.fsync(temporary.fileno())
        temporary_path.replace(path)
    except BaseException:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise
    return True


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _manifest(
    source_corpus_sha256: str,
    output_corpus_sha256: str,
    stats: dict[str, int | bool],
    documents: dict[str, dict[str, int | str]],
) -> dict[str, object]:
    builder_path = Path(__file__).resolve()
    return {
        "schema_version": "inter-ayah-reciprocal-manifest-v2",
        "corpus_id": "inter-ayah-row-reciprocal-v2",
        "record_schema": "inter-ayah-row-reciprocal-tsv-v2",
        "record_schema_document": "schemas/inter-ayah-row-reciprocal.md",
        "columns": list(TSV_COLUMNS),
        "builder": str(builder_path.relative_to(REPO_ROOT)),
        "builder_sha256": hashlib.sha256(builder_path.read_bytes()).hexdigest(),
        "source_corpus": str(SOURCE_DIR.relative_to(REPO_ROOT)),
        "source_corpus_sha256": source_corpus_sha256,
        "quran_text": str(QURAN_TEXT.relative_to(REPO_ROOT)),
        "quran_text_sha256": hashlib.sha256(QURAN_TEXT.read_bytes()).hexdigest(),
        "output_corpus": str(OUTPUT_DIR.relative_to(REPO_ROOT)),
        "output_tsv_corpus_sha256": output_corpus_sha256,
        "documents": documents,
        "rules": {
            "every_source_target_component_has_directional_record": True,
            "every_source_target_component_has_mirrored_record": True,
            "same_surah_and_cross_surah_are_mirrored": True,
            "existing_reverse_rows_never_suppress_records": True,
            "non_self_meaningful_labels_create_reciprocal_nominations": sorted(
                MEANINGFUL_LABELS
            ),
            "non_self_negative_labels_create_reciprocal_counterevidence": sorted(
                LABELS - MEANINGFUL_LABELS
            ),
            "self_links_create_typed_reiterations_not_reverse_evidence": True,
            "reciprocal_focus_direction_label_is_empty": True,
            "source_direction_label_is_not_receiving_direction_judgment": True,
            "source_ranges_expand_to_ayah_components": True,
            "source_note_text_is_preserved_exactly": True,
            "directional_records_precede_reciprocal_records": True,
            "parent_and_projection_must_not_be_concatenated": True,
        },
        "counts": stats,
    }


def _allowed_output_names(valid_refs: set[str]) -> set[str]:
    return {_expected_name(ref) for ref in valid_refs} | {
        "MANIFEST.json",
        "README.md",
    }


def _unexpected_output_entries(
    output_dir: Path, valid_refs: set[str]
) -> list[str]:
    if not output_dir.exists():
        return []
    allowed = _allowed_output_names(valid_refs)
    return sorted(path.name for path in output_dir.iterdir() if path.name not in allowed)


def _record_check_problem(problems: list[str], problem: str) -> None:
    if len(problems) < 20:
        problems.append(problem)


def _assert_repo_path_without_symlinks(
    path: Path,
    *,
    label: str,
    allow_missing_leaf: bool = False,
) -> None:
    repo_root = REPO_ROOT.resolve(strict=True)
    absolute = Path(os.path.abspath(path))
    try:
        relative = absolute.relative_to(repo_root)
    except ValueError as exc:
        raise SystemExit(f"{label} must remain inside repository: {path}") from exc
    current = repo_root
    for index, part in enumerate(relative.parts):
        current /= part
        if current.is_symlink():
            raise SystemExit(f"{label} path must not traverse a symlink: {current}")
        if not current.exists():
            is_leaf = index == len(relative.parts) - 1
            if allow_missing_leaf and is_leaf:
                return
            raise SystemExit(f"{label} path does not exist: {current}")
    resolved = absolute.resolve(strict=True)
    if not resolved.is_relative_to(repo_root):
        raise SystemExit(f"{label} resolves outside repository: {path}")


def _resolve_fixed_paths() -> tuple[Path, Path, Path]:
    _assert_repo_path_without_symlinks(
        SOURCE_DIR,
        label="Directional corpus",
    )
    _assert_repo_path_without_symlinks(
        QURAN_TEXT,
        label="Quran text",
    )
    _assert_repo_path_without_symlinks(
        OUTPUT_DIR,
        label="Generated corpus",
        allow_missing_leaf=True,
    )
    source_dir = SOURCE_DIR.resolve(strict=True)
    quran_text = QURAN_TEXT.resolve(strict=True)
    if not source_dir.is_dir():
        raise SystemExit(f"Directional corpus must be a directory: {source_dir}")
    if not quran_text.is_file():
        raise SystemExit(f"Quran text must be a regular file: {quran_text}")
    if OUTPUT_DIR.is_symlink():
        raise SystemExit(f"Generated corpus directory must not be a symlink: {OUTPUT_DIR}")
    output_dir = OUTPUT_DIR
    if output_dir.exists() and not output_dir.is_dir():
        raise SystemExit(f"Generated corpus path must be a directory: {output_dir}")
    if output_dir.parent.resolve(strict=True) != source_dir:
        raise SystemExit("Generated corpus must be the source corpus's reciprocal child")
    if output_dir.name != "reciprocal":
        raise SystemExit("Generated corpus directory must be named reciprocal")
    return source_dir, output_dir, quran_text


def _build_or_check(
    *,
    check: bool,
    output_dir: Path,
    valid_refs: set[str],
    connection: sqlite3.Connection,
    source_corpus_sha256: str,
    stats: dict[str, int | bool],
) -> tuple[dict[str, object], int]:
    if check and not output_dir.is_dir():
        raise SystemExit(f"Generated corpus directory does not exist: {output_dir}")
    if not check:
        output_dir.mkdir(parents=False, exist_ok=True)

    unexpected = _unexpected_output_entries(output_dir, valid_refs)
    if unexpected and not check:
        raise SystemExit(
            "Refusing to delete unexpected generated entries: "
            + ", ".join(unexpected[:20])
        )
    problems = [f"unexpected output entry: {name}" for name in unexpected[:20]]
    expected_names = {_expected_name(ref) for ref in valid_refs}
    if not check:
        unsafe_existing = []
        for name in expected_names | {"MANIFEST.json"}:
            path = output_dir / name
            if path.is_symlink() or (path.exists() and not path.is_file()):
                unsafe_existing.append(name)
        if unsafe_existing:
            raise SystemExit(
                "Generated outputs must be regular non-symlink files before "
                "replacement: " + ", ".join(sorted(unsafe_existing)[:20])
            )
    if check:
        actual_names = {
            path.name for path in output_dir.glob("focus_*_cutoff_100.tsv")
        }
        if actual_names != expected_names:
            _record_check_problem(
                problems,
                f"file set differs: missing={sorted(expected_names - actual_names)[:20]}, "
                f"extra={sorted(actual_names - expected_names)[:20]}",
            )

    output_digest = hashlib.sha256()
    documents: dict[str, dict[str, int | str]] = {}
    directional_count = 0
    reciprocal_count = 0
    changed = 0
    refs_in_digest_order = sorted(valid_refs, key=_expected_name)
    for focus_ref in refs_in_digest_order:
        name = _expected_name(focus_ref)
        payload, focus_directional_count, focus_reciprocal_count = _render_focus(
            connection, focus_ref
        )
        directional_count += focus_directional_count
        reciprocal_count += focus_reciprocal_count
        _update_corpus_digest(output_digest, name, payload)
        documents[name] = {
            "sha256": hashlib.sha256(payload).hexdigest(),
            "record_count": (
                focus_directional_count + focus_reciprocal_count
            ),
            "directional_review_record_count": focus_directional_count,
            "mirrored_record_count": focus_reciprocal_count,
        }
        path = output_dir / name
        if check:
            if path.is_symlink() or not path.is_file() or path.read_bytes() != payload:
                _record_check_problem(problems, f"content differs: {name}")
        else:
            changed += int(_write_if_changed(path, payload))

    source_component_count = int(stats["source_target_component_count"])
    directional_complete = directional_count == source_component_count
    mirrored_complete = reciprocal_count == source_component_count
    if not directional_complete or not mirrored_complete:
        raise SystemExit("Internal error: row-level reciprocal projection is incomplete")
    self_reiteration_count = int(stats["self_reiteration_record_count"])
    stats.update(
        {
            "output_file_count": len(valid_refs),
            "output_record_count": directional_count + reciprocal_count,
            "directional_review_record_count": directional_count,
            "mirrored_record_count": reciprocal_count,
            "reciprocal_record_count": (
                reciprocal_count - self_reiteration_count
            ),
            "directional_component_coverage_complete": directional_complete,
            "row_level_mirror_coverage_complete": mirrored_complete,
        }
    )
    manifest = _manifest(
        source_corpus_sha256,
        output_digest.hexdigest(),
        stats,
        documents,
    )
    manifest_payload = _pretty_json(manifest)
    manifest_path = output_dir / "MANIFEST.json"
    if check:
        if (
            manifest_path.is_symlink()
            or not manifest_path.is_file()
            or manifest_path.read_bytes() != manifest_payload
        ):
            _record_check_problem(problems, "content differs: MANIFEST.json")
        if problems:
            raise SystemExit(
                "Generated corpus check failed:\n- " + "\n- ".join(problems)
            )
    else:
        changed += int(_write_if_changed(manifest_path, manifest_payload))
        _fsync_directory(output_dir)
    return manifest, changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the committed projection instead of writing it",
    )
    args = parser.parse_args()

    source_dir, output_dir, quran_text = _resolve_fixed_paths()
    valid_refs = _load_numbered_ayahs(quran_text)
    with tempfile.TemporaryDirectory(prefix="inter-ayah-reciprocal-") as temporary:
        stage_path = Path(temporary) / "stage.sqlite"
        with sqlite3.connect(stage_path) as connection:
            _create_stage(connection)
            source_corpus_sha256, stats = _stage_source_rows(
                connection, source_dir, valid_refs
            )
            manifest, changed = _build_or_check(
                check=args.check,
                output_dir=output_dir,
                valid_refs=valid_refs,
                connection=connection,
                source_corpus_sha256=source_corpus_sha256,
                stats=stats,
            )
    report = dict(manifest)
    if not args.check:
        report["write_result"] = {"changed_file_count": changed}
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
