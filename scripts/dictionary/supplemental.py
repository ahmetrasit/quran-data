"""Shared, exact validation for the reviewed supplemental dictionary intake.

The frozen Furuq registry is not extended here. Supplemental IDs belong to the
hash-closed intake registry and must never be inferred from bridge candidates.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = "data/supplemental/registry.v1.json"
SOURCE_NAMES_PATH = "data/supplemental/source-names.v1.json"
TRANSFER_REGISTRY_PATH = ROOT / "data/dictionary/supplemental/registry.v1.json"
ROOT_ID = re.compile(r"root_[0-9]{6}\Z")
HEADWORD_ID = re.compile(r"headword_[0-9]{6}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SOURCE_KEY = re.compile(r"[A-Za-z][A-Za-z0-9_-]*\Z")


def kind_for_id(ident: str) -> str:
    if isinstance(ident, str) and ROOT_ID.fullmatch(ident):
        return "lexical_root"
    if isinstance(ident, str) and HEADWORD_ID.fullmatch(ident):
        return "grammatical_headword"
    raise ValueError(f"Invalid supplemental identity: {ident}")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(data: bytes, name: str) -> dict:
    value = json.loads(data)
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a JSON object")
    return value


def source_phrase(sense: dict, sources: dict[str, dict]) -> str:
    keys = sense.get("sourceKeys")
    if not isinstance(keys, list) or not keys or len(keys) != len(set(keys)):
        raise ValueError(f"Invalid ordered source keys for {sense.get('senseId')}")
    if any(key not in sources for key in keys):
        raise ValueError(f"Unknown source key for {sense.get('senseId')}")
    return "؛ ".join(
        f"{sources[key]['quotationAr']} ({sources[key]['sourceId']}:{key})"
        for key in keys
    )


def binding_refs(connection: sqlite3.Connection, binding: dict) -> list[str]:
    if not isinstance(binding, dict) or not isinstance(binding.get("selector"), dict):
        raise ValueError("Supplemental QAC binding is missing")
    selector = binding["selector"]
    scope = "qacLemma" if "qacLemma" in selector else "qacRef"
    if set(selector) != {"qacRootJoinKey", scope} or not all(
        isinstance(value, str) and value for value in selector.values()
    ):
        raise ValueError(f"Invalid supplemental QAC selector: {selector}")
    column = "lemma_ar" if scope == "qacLemma" else "qac_ref"
    refs = sorted(row[0] for row in connection.execute(
        f"SELECT qac_ref FROM qac_morphemes WHERE root_join_key=? AND {column}=?",
        (selector["qacRootJoinKey"], selector[scope]),
    ))
    if not refs:
        raise ValueError(f"Supplemental QAC selector has no occurrences: {selector}")
    expected = digest(json.dumps(refs, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    if binding.get("selectorRefsSha256") != expected:
        raise ValueError(f"Supplemental QAC selector ref set drift: {selector}")
    return refs


def qac_connection(path: Path | None = None) -> sqlite3.Connection:
    source = path or ROOT / "data/morphology/qac.sqlite.gz"
    connection = sqlite3.connect(":memory:")
    connection.deserialize(gzip.decompress(source.read_bytes()))
    return connection


def expected_occurrence_evidence(connection: sqlite3.Connection, binding: dict) -> dict:
    """Rebuild the export's QAC evidence from the exact reviewed selector."""
    refs = binding_refs(connection, binding)
    connection.row_factory = sqlite3.Row
    marks = ",".join("?" for _ in refs)
    rows = [dict(row) for row in connection.execute(
        f"SELECT * FROM qac_morphemes WHERE qac_ref IN ({marks}) "
        "ORDER BY surah, ayah, word_index, morpheme_index", refs,
    )]
    forms_by_key = {}
    for row in rows:
        key = (row["lemma_ar"], row["stem_ar"], row["pos"], row["morph_features"])
        forms_by_key.setdefault(key, []).append(row)
    forms = []
    form_by_ref = {}
    for index, (key, members) in enumerate(forms_by_key.items(), 1):
        form_id = f"F{index:03d}"
        forms.append({"form_id": form_id, "lemma_ar": key[0], "stem_ar": key[1],
                      "pos": key[2], "measure": members[0]["measure"],
                      "morph_features": key[3], "occurrence_count": len(members)})
        for row in members:
            form_by_ref[row["qac_ref"]] = form_id
    ayah_refs = sorted({(row["surah"], row["ayah"]) for row in rows})
    ayahs = []
    for surah, ayah in ayah_refs:
        words = connection.execute(
            "SELECT surface_ar FROM qac_words WHERE surah=? AND ayah=? ORDER BY word_index",
            (surah, ayah),
        ).fetchall()
        ayahs.append({"ayah_ref": f"{surah}:{ayah}",
                      "surface_ar": " ".join(word[0] for word in words)})
    occurrence_fields = (
        "qac_ref", "qac_word_ref", "surah", "ayah", "word_index", "morpheme_index",
        "surface_ar", "stem_ar", "lemma_ar", "root_raw", "root_ar", "root_join_key",
        "source_pos", "pos", "morpheme_role", "measure", "aspect", "mood", "voice",
        "morph_features",
    )
    occurrences = []
    for row in rows:
        item = {field: row[field] for field in occurrence_fields}
        item["ayah_ref"] = f"{row['surah']}:{row['ayah']}"
        item["form_id"] = form_by_ref[row["qac_ref"]]
        occurrences.append(item)
    return {
        "summary": {"morpheme_count": len(rows),
                    "word_count": len({row["qac_word_ref"] for row in rows}),
                    "ayah_count": len(ayah_refs),
                    "surah_count": len({row["surah"] for row in rows})},
        "forms": forms, "ayahs": ayahs, "occurrences": occurrences,
    }


def load_source_names(read: Callable[[str], bytes]) -> tuple[bytes, dict]:
    raw = read(SOURCE_NAMES_PATH)
    value = json_bytes(raw, SOURCE_NAMES_PATH)
    names = value.get("sources")
    if (value.get("schemaVersion") != "dictionary-supplemental-source-names-v1"
            or not isinstance(names, dict) or not names):
        raise ValueError("Invalid supplemental source-name map")
    codes = set()
    for source_id, record in names.items():
        if (not isinstance(source_id, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", source_id)
                or not isinstance(record, dict)
                or not isinstance(record.get("sourceTitle"), str) or not record["sourceTitle"]
                or not isinstance(record.get("badgeCode"), str)
                or not re.fullmatch(r"[A-Z]{2}", record["badgeCode"])
                or record["badgeCode"] in codes):
            raise ValueError(f"Invalid supplemental source-name row: {source_id}")
        codes.add(record["badgeCode"])
    return raw, names


def validate_intake(value: dict, ident: str, connection: sqlite3.Connection,
                    source_names: dict) -> list[str]:
    kind = kind_for_id(ident)
    if (value.get("schemaVersion") != "dictionary-supplemental-intake-v1"
            or value.get("id") != ident or value.get("kind") != kind
            or not isinstance(value.get("headwordArabic"), str)
            or not value["headwordArabic"].strip()):
        raise ValueError(f"Invalid supplemental intake identity: {ident}")
    if kind == "lexical_root":
        root = value.get("rootArabic")
        if (not isinstance(root, str) or not root.strip() or
                not re.fullmatch(r"[\u0621-\u064a](?: [\u0621-\u064a]){2,3}", root)):
            raise ValueError(f"Supplemental root identity drift: {ident}")
    elif "rootArabic" in value:
        raise ValueError(f"Grammatical headword asserts a root: {ident}")
    binding = value.get("binding")
    selector = binding.get("selector") if isinstance(binding, dict) else None
    if kind == "lexical_root" and isinstance(selector, dict) and root.replace(" ", "") != selector.get("qacRootJoinKey"):
        raise ValueError(f"Supplemental root differs from exact QAC root: {ident}")
    refs = binding_refs(connection, binding)
    snapshot = value.get("sourceSnapshot")
    if (not isinstance(snapshot, dict)
            or not isinstance(snapshot.get("quranDataCommit"), str)
            or not re.fullmatch(r"[0-9a-f]{40}", snapshot["quranDataCommit"])
            or not isinstance(snapshot.get("qacMorphologyGzipSha256"), str)
            or not SHA256.fullmatch(snapshot["qacMorphologyGzipSha256"])):
        raise ValueError(f"Invalid historical supplemental source snapshot: {ident}")
    sources = value.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError(f"Supplemental intake lacks sources: {ident}")
    by_key = {}
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError(f"Invalid supplemental citation: {ident}")
        source_key = source.get("sourceKey")
        quote = source.get("quotationAr")
        if (not isinstance(source_key, str) or not SOURCE_KEY.fullmatch(source_key)
                or source_key in by_key or source.get("sourceType") not in {"lexicon", "grammar", "tafsir"}
                or not isinstance(source.get("sourceId"), str) or not source["sourceId"]
                or not isinstance(source.get("sourceTitle"), str) or not source["sourceTitle"]
                or not isinstance(source.get("author"), str) or not source["author"]
                or not isinstance(source.get("edition"), str) or not source["edition"]
                or not isinstance(source.get("locator"), str) or not source["locator"]
                or not isinstance(quote, str) or not quote or quote != quote.strip()
                or source.get("quotationSha256") != digest(quote.encode("utf-8"))):
            raise ValueError(f"Invalid supplemental source quotation: {ident}/{source_key}")
        if not (isinstance(source.get("sourceUrl"), str) and source["sourceUrl"].startswith("https://")
                or isinstance(source.get("sourceRef"), str) and source["sourceRef"]
                and isinstance(source.get("sourceSha256"), str)
                and SHA256.fullmatch(source["sourceSha256"])):
            raise ValueError(f"Unlocated supplemental citation: {ident}/{source_key}")
        if source["sourceType"] == "lexicon" and (
            source["sourceId"] not in source_names or
            source["sourceTitle"] != source_names[source["sourceId"]]["sourceTitle"]
        ):
            raise ValueError(f"Unknown supplemental lexicon source: {ident}/{source_key}")
        if source["sourceType"] != "lexicon" and source["sourceId"] in source_names:
            raise ValueError(f"Lexicon source is mistyped: {ident}/{source_key}")
        if "parentEntrySha256" in source and (
            source.get("sourceSha256") != source["parentEntrySha256"]
        ):
            raise ValueError(f"Frozen parent-entry hash drift: {ident}/{source_key}")
        by_key[source_key] = source
    analyses = value.get("analyses")
    if not isinstance(analyses, list) or not analyses:
        raise ValueError(f"Supplemental intake lacks ranked analyses: {ident}")
    analysis_ids = set()
    for index, analysis in enumerate(analyses):
        aid = analysis.get("analysisId") if isinstance(analysis, dict) else None
        if (not isinstance(aid, str) or not aid or aid in analysis_ids
                or analysis.get("standing") != ("primary" if index == 0 else "documented_alternative")
                or analysis.get("rootArabic") is not None and not isinstance(analysis["rootArabic"], str)
                or analysis.get("patternAr") is not None and not isinstance(analysis["patternAr"], str)
                or not isinstance(analysis.get("scopeNoteAr"), str) or not analysis["scopeNoteAr"].strip()):
            raise ValueError(f"Invalid supplemental analysis: {ident}/{aid}")
        source_phrase(analysis, by_key)
        analysis_ids.add(aid)
    senses = value.get("senses")
    if not isinstance(senses, list) or not senses:
        raise ValueError(f"Supplemental intake lacks senses: {ident}")
    seen = set()
    declared_ref_sets = []
    for sense in senses:
        sense_id = sense.get("senseId") if isinstance(sense, dict) else None
        pattern = r"B[0-9]{3}" if kind == "lexical_root" else r"S[0-9]{3}"
        if not isinstance(sense_id, str) or not re.fullmatch(pattern, sense_id) or sense_id in seen:
            raise ValueError(f"Invalid or duplicate supplemental sense: {ident}/{sense_id}")
        seen.add(sense_id)
        for field in ("imageAr", "whatIsAr", "whatIsNotAr"):
            if not isinstance(sense.get(field), str) or not sense[field].strip():
                raise ValueError(f"Missing supplemental Arabic sense evidence: {ident}/{sense_id}/{field}")
        source_phrase(sense, by_key)
        claims = sense.get("claims")
        if not isinstance(claims, list) or not claims:
            raise ValueError(f"Supplemental sense has no sourced claim: {ident}/{sense_id}")
        claim_ids = set()
        for claim in claims:
            if (not isinstance(claim, dict) or not isinstance(claim.get("statementAr"), str)
                    or not claim["statementAr"].strip()
                    or not isinstance(claim.get("claimId"), str)
                    or not re.fullmatch(r"bc_[0-9]{3}", claim["claimId"])
                    or claim["claimId"] in claim_ids
                    or not isinstance(claim.get("sourceKeys"), list)
                    or not claim["sourceKeys"]
                    or len(claim["sourceKeys"]) != len(set(claim["sourceKeys"]))
                    or not set(claim["sourceKeys"]) <= set(sense["sourceKeys"])):
                raise ValueError(f"Unsupported supplemental sense claim: {ident}/{sense_id}")
            claim_ids.add(claim["claimId"])
        units = sense.get("lexicalUnits")
        if not isinstance(units, list):
            raise ValueError(f"Missing supplemental lexical-unit roster: {ident}/{sense_id}")
        unit_ids = set()
        for unit in units:
            uid = unit.get("lexicalUnitId") if isinstance(unit, dict) else None
            if (not isinstance(uid, str) or not re.fullmatch(r"lu_[0-9]{3,}", uid)
                    or uid in unit_ids
                    or unit.get("unitKind") not in {"form", "collocation", "lexical_unit", "review"}
                    or unit.get("renderingPolicy") not in {"ordinary", "proper_name"}
                    or not isinstance(unit.get("expressionAr"), str) or not unit["expressionAr"].strip()
                    or not isinstance(unit.get("senseAr"), str) or not unit["senseAr"].strip()):
                raise ValueError(f"Invalid supplemental lexical unit: {ident}/{sense_id}/{uid}")
            source_phrase(unit, by_key)
            if not set(unit["sourceKeys"]) <= set(sense["sourceKeys"]):
                raise ValueError(f"Lexical unit cites outside sense: {ident}/{sense_id}/{uid}")
            unit_ids.add(uid)
        neighbors = sense.get("neighbors")
        if not isinstance(neighbors, list):
            raise ValueError(f"Missing supplemental neighbor roster: {ident}/{sense_id}")
        for neighbor in neighbors:
            if (not isinstance(neighbor, dict)
                    or not re.fullmatch(r"(?:root_[0-9]{6}/B[0-9]{3}|headword_[0-9]{6}/S[0-9]{3})", str(neighbor.get("neighborRef")))
                    or not isinstance(neighbor.get("imageAr"), str) or not neighbor["imageAr"].strip()
                    or not isinstance(neighbor.get("whatIsAr"), str) or not neighbor["whatIsAr"].strip()):
                raise ValueError(f"Invalid supplemental neighbor: {ident}/{sense_id}")
        if "qacMorphemeRefs" in sense:
            sense_refs = sense["qacMorphemeRefs"]
            if (not isinstance(sense_refs, list)
                    or len(sense_refs) != len(set(sense_refs))
                    or not set(sense_refs) <= set(refs)):
                raise ValueError(f"Invalid supplemental sense QAC refs: {ident}/{sense_id}")
            declared_ref_sets.append(set(sense_refs))
    if declared_ref_sets and (len(declared_ref_sets) != len(senses)
                              or set.union(*declared_ref_sets) != set(refs)
                              or sum(map(len, declared_ref_sets)) != len(refs)):
        raise ValueError(f"Supplemental sense QAC refs do not partition binding: {ident}")
    audit = value.get("qacAudit")
    if audit is not None:
        if not isinstance(audit, dict):
            raise ValueError(f"Invalid supplemental QAC audit: {ident}")
        marks = ",".join("?" for _ in refs)
        observed = connection.execute(
            f"SELECT qac_ref, pos FROM qac_morphemes WHERE qac_ref IN ({marks})", refs,
        ).fetchall()
        pos_counts = {}
        for _, pos in observed:
            pos_counts[pos] = pos_counts.get(pos, 0) + 1
        if (audit.get("qacMorphemeRefs") != refs
                or audit.get("qacPosCounts") != pos_counts
                or audit.get("qacNRefs") != sorted(ref for ref, pos in observed if pos == "N")
                or not isinstance(audit.get("observationNote"), str)):
            raise ValueError(f"Supplemental QAC audit differs from source rows: {ident}")
    context = value.get("phraseContext")
    if context is not None:
        if (kind != "grammatical_headword" or not isinstance(context, dict)
                or not isinstance(context.get("statementAr"), str)
                or not context["statementAr"].strip()):
            raise ValueError(f"Invalid supplemental grammatical phrase context: {ident}")
        source_phrase(context, by_key)
    return refs


def load_registry(read: Callable[[str], bytes], *, connection: sqlite3.Connection | None = None
                  ) -> tuple[bytes, dict, dict[str, dict]]:
    raw = read(REGISTRY_PATH)
    _, source_names = load_source_names(read)
    registry = json_bytes(raw, REGISTRY_PATH)
    rows = registry.get("entries")
    if (registry.get("schemaVersion") != "dictionary-supplemental-registry-v1"
            or not isinstance(rows, list) or not rows):
        raise ValueError("Invalid supplemental registry format")
    intakes = {}
    lexical_arabic = set()
    selector_ownership = set()
    own_connection = connection is None
    connection = connection or qac_connection()
    try:
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("Invalid supplemental registry row")
            ident = row.get("id")
            if ident in intakes:
                raise ValueError(f"Unknown or duplicate supplemental ID: {ident}")
            if (row.get("kind") != kind_for_id(ident)
                    or row.get("intakePath") != f"entries/{ident}.json"
                    or not isinstance(row.get("reviewedOn"), str)
                    or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", row["reviewedOn"])):
                raise ValueError(f"Invalid supplemental registry ownership: {ident}")
            path = f"data/supplemental/{row['intakePath']}"
            intake_raw = read(path)
            if row.get("intakeSha256") != digest(intake_raw):
                raise ValueError(f"Supplemental intake hash drift: {ident}")
            intake = json_bytes(intake_raw, path)
            validate_intake(intake, ident, connection, source_names)
            if intake["kind"] == "lexical_root":
                if intake["rootArabic"] in lexical_arabic:
                    raise ValueError(f"Duplicate supplemental Arabic root: {ident}")
                lexical_arabic.add(intake["rootArabic"])
            selector = json.dumps(intake["binding"]["selector"], sort_keys=True, ensure_ascii=False)
            if selector in selector_ownership:
                raise ValueError(f"Duplicate supplemental QAC selector: {ident}")
            selector_ownership.add(selector)
            intakes[ident] = intake
    finally:
        if own_connection:
            connection.close()
    return raw, registry, intakes


def transferred_registry() -> tuple[bytes, dict, dict[str, dict]] | None:
    if not TRANSFER_REGISTRY_PATH.is_file():
        return None
    def read(path: str) -> bytes:
        return (ROOT / "data/dictionary/supplemental" / Path(path).relative_to("data/supplemental")).read_bytes()
    return load_registry(read)


def export_source_path(ident: str) -> str:
    if kind_for_id(ident) == "lexical_root":
        return f"v2/work/entry_creation/{ident}/tr/export/{ident}_entry.json"
    return f"v2/work/entry_creation/headwords/{ident}/tr/export/{ident}_entry.json"


def validate_export_provenance(value: dict, ident: str, registry_sha256: str,
                               intake_sha256: str) -> None:
    """Bind an export to its current intake without rebinding its review snapshot."""
    supplied = value.get("supplementalIntake")
    if (not isinstance(supplied, dict)
            or set(supplied) != {"registryPath", "registrySha256", "intakePath", "intakeSha256"}
            or supplied.get("registryPath") != REGISTRY_PATH
            or not isinstance(supplied.get("registrySha256"), str)
            or not SHA256.fullmatch(supplied["registrySha256"])
            or supplied.get("intakePath") != f"data/supplemental/entries/{ident}.json"
            or supplied.get("intakeSha256") != intake_sha256
            or not SHA256.fullmatch(registry_sha256)
            or not SHA256.fullmatch(intake_sha256)):
        raise ValueError(f"Supplemental export provenance is invalid: {ident}")


def validate_export(value: dict, ident: str, intake: dict, registry_sha256: str,
                    intake_sha256: str, source_names: dict) -> None:
    """Check export identity and all source-owned Arabic/citation fields."""
    kind = kind_for_id(ident)
    validate_export_provenance(value, ident, registry_sha256, intake_sha256)
    if (value.get("generated_by") != "v2/scripts/export_reviewed_supplement.py"
            or value.get("language") != "tr" or value.get("entryKind") != kind):
        raise ValueError(f"Supplemental export identity is invalid: {ident}")
    if (not isinstance(value.get("inputs_sha256"), str)
            or not SHA256.fullmatch(value["inputs_sha256"])):
        raise ValueError(f"Supplemental export input digest is invalid: {ident}")
    occurrence_field = "occurrence_evidence" if kind == "lexical_root" else "occurrenceEvidence"
    with qac_connection() as connection:
        expected_occurrences = expected_occurrence_evidence(connection, intake["binding"])
    if value.get(occurrence_field) != expected_occurrences:
        raise ValueError(f"Supplemental QAC occurrence evidence drift: {ident}")
    sources = {source["sourceKey"]: source for source in intake["sources"]}
    senses = {sense["senseId"]: sense for sense in intake["senses"]}
    if kind == "lexical_root":
        if (value.get("artifact_format") != "dictionary-v2-root-entry-draft-v1"
                or value.get("root_envelope_id") != ident
                or not isinstance(value.get("root_profile"), dict)):
            raise ValueError(f"Invalid supplemental lexical root export: {ident}")
        branches = value.get("branches")
        if not isinstance(branches, list) or len(branches) != len(senses):
            raise ValueError(f"Supplemental root branch roster drift: {ident}")
        seen = set()
        for branch in branches:
            ref = branch.get("branch_ref") if isinstance(branch, dict) else None
            sense_id = ref.split("/")[-1] if isinstance(ref, str) else None
            if ref != f"{ident}/{sense_id}" or sense_id not in senses or sense_id in seen:
                raise ValueError(f"Supplemental root branch identity drift: {ident}/{ref}")
            seen.add(sense_id)
            sense = senses[sense_id]
            expected_arabic = {
                "branch_image_ar": sense["imageAr"],
                "what_is_ar": sense["whatIsAr"],
                "what_is_not_ar": sense["whatIsNotAr"],
                "source_phrase_ar": source_phrase(sense, sources),
            }
            for field, expected in expected_arabic.items():
                if branch.get(field) != expected:
                    raise ValueError(f"Supplemental Arabic evidence drift: {ref}/{field}")
            expected_citations = [sources[key] for key in sense["sourceKeys"]]
            if branch.get("citations") != expected_citations:
                raise ValueError(f"Supplemental typed citation drift: {ref}")
            badges = list(dict.fromkeys(
                source_names[item["sourceId"]]["badgeCode"]
                for item in expected_citations if item["sourceType"] == "lexicon"
            ))
            if branch.get("sources") != badges:
                raise ValueError(f"Supplemental lexicon badge drift: {ref}")
    else:
        if (value.get("artifact_format") != "dictionary-v2-headword-entry-draft-v1"
                or value.get("headwordId") != ident
                or value.get("headwordArabic") != intake["headwordArabic"]
                or value.get("binding") != intake["binding"]
                or "root_envelope_id" in value or "rootIds" in value
                or "root_profile" in value or "occurrence_evidence" in value):
            raise ValueError(f"Invalid grammatical headword export: {ident}")
        exported = value.get("senses")
        if not isinstance(exported, list) or len(exported) != len(senses):
            raise ValueError(f"Supplemental headword sense roster drift: {ident}")
        seen = set()
        for item in exported:
            sense_id = item.get("senseId") if isinstance(item, dict) else None
            if sense_id not in senses or sense_id in seen:
                raise ValueError(f"Supplemental headword sense identity drift: {ident}/{sense_id}")
            seen.add(sense_id)
            sense = senses[sense_id]
            for field, expected in {
                "imageArabic": sense["imageAr"],
                "whatIsArabic": sense["whatIsAr"],
                "whatIsNotArabic": sense["whatIsNotAr"],
                "sourcePhraseArabic": source_phrase(sense, sources),
                "citationKeys": sense["sourceKeys"],
            }.items():
                if item.get(field) != expected:
                    raise ValueError(f"Supplemental headword Arabic/citation drift: {ident}/{sense_id}/{field}")
        referenced = list(dict.fromkeys(
            key for sense in intake["senses"] for key in sense["sourceKeys"]
        ))
        if value.get("citations") != [sources[key] for key in referenced]:
            raise ValueError(f"Supplemental headword citation roster drift: {ident}")
