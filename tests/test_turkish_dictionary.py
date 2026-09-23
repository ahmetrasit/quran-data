import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/dictionary"))
from check_turkish_entries import check, validate_entry


class TurkishEntryTests(unittest.TestCase):
    def entry(self):
        return {"artifact_format": "dictionary-v2-root-entry-draft-v1",
                "generated_by": "v2/scripts/accept_root_writer.py", "language": "tr",
                "root_envelope_id": "root_000001", "branches": [{
                    "branch_ref": "root_000001/B001", "branch_image_ar": "صورة",
                    "what_is_ar": "حد", "what_is_not_ar": "حد", "source_phrase_ar": "نص",
                    "sources": ["AY"]}], "occurrence_evidence": {
                        "summary": {"morpheme_count": 0, "word_count": 0,
                                    "ayah_count": 0, "surah_count": 0},
                        "forms": [], "ayahs": [], "occurrences": []}}

    def test_rejects_empty_and_foreign_branches(self):
        for branches in ([], [{**self.entry()["branches"][0], "branch_ref": "root_000002/B001"}]):
            value = self.entry(); value["branches"] = branches
            with self.assertRaises(ValueError):
                validate_entry(value, "root_000001_entry.json")

    def test_rejects_duplicate_branches_and_whitespace_evidence(self):
        value = self.entry(); value["branches"] *= 2
        with self.assertRaises(ValueError): validate_entry(value, "root_000001_entry.json")
        value = self.entry(); value["branches"][0]["source_phrase_ar"] = " "
        with self.assertRaises(ValueError): validate_entry(value, "root_000001_entry.json")

    def test_rejects_missing_occurrence_evidence_and_wrong_export_marker(self):
        value = self.entry(); del value["occurrence_evidence"]
        with self.assertRaisesRegex(ValueError, "occurrence evidence"):
            validate_entry(value, "root_000001_entry.json")
        value = self.entry()
        with self.assertRaisesRegex(ValueError, "Raw or unrecognized"):
            validate_entry(value, "root_000001_entry.json",
                           expected_generator="v2/scripts/enrich_furuq_writer.py")

    def test_manifest_detects_deleted_entries(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "root_000001_entry.json").write_text(json.dumps(self.entry()))
            (directory / "MANIFEST.json").write_text(json.dumps({"entries": [
                {"path": "root_000002_entry.json", "sha256": "missing"}], "branchCount": 1, "entryCount": 1}))
            with self.assertRaises(ValueError): check(directory)

    def test_wadhar_correction_keeps_matched_count(self):
        import csv
        path = Path(__file__).resolve().parents[1] / "data/bridges/qac-furuq-v4-root-map.tsv"
        with path.open() as handle:
            row = next(r for r in csv.DictReader(handle, delimiter="\t") if r["qac_root_norm"] == "و ذ ر")
        self.assertEqual(row["mapping_status"], "unique")
        self.assertEqual(row["matched_occurrences"], "29")
        self.assertEqual(row["targets"], "و ذ ر=>root_001638=>و ذ ر=>و ذ ر=>source_root_norm:29")

    def test_reader_resolutions_do_not_promote_observational_errors(self):
        base = Path(__file__).resolve().parents[1]
        value = json.loads((base / "data/bridges/qac-dictionary-root-resolutions.json").read_bytes())
        rows = {r["qacRootJoinKey"]: r for r in value["roots"]}
        self.assertEqual(len(rows), 1642)
        self.assertEqual(rows["سمو"]["rootIds"], ["root_000745"])
        self.assertEqual(rows["نوس"]["rootIds"], ["root_000059"])
        self.assertEqual(rows["سهو"]["rootIds"], ["root_003249"])
        self.assertNotIn("root_001251", rows["قول"]["rootIds"])
        self.assertNotIn("root_001315", rows["ءكل"]["rootIds"])
        unresolved = {key for key, row in rows.items()
                      if row["resolution"] == "unresolved_identity"}
        self.assertEqual(unresolved, {"ءدد", "ثبي", "سنه", "قضض", "كيف", "لوت"})
        self.assertEqual(rows["عصو"]["rootIds"], ["root_005713"])
        self.assertEqual(rows["عصو"]["missingEntryRootIds"], [])
        newly_transferred = {
            "root_003789", "root_004482", "root_004706", "root_004914",
            "root_005216", "root_005229", "root_005302", "root_005348",
            "root_005351", "root_005406", "root_005440", "root_005713",
            "root_005748", "root_005754",
        }
        resolved_ids = {root_id for row in rows.values()
                        if row["resolution"] != "unresolved_identity"
                        for root_id in row["rootIds"]}
        self.assertTrue(newly_transferred <= resolved_ids)
        self.assertFalse(any(row["missingEntryRootIds"] for row in rows.values()))
        self.assertTrue(all((base / "data/dictionary/tr" / f"{root_id}_entry.json").is_file()
                            for root_id in newly_transferred))

if __name__ == "__main__": unittest.main()
