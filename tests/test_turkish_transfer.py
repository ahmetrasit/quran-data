"""Committed-source selection and regression guards for the Turkish transfer."""

import gzip
import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/dictionary"))
import sync_turkish_entries as sync


def entry(root: str, *, generator: str = "v2/scripts/accept_root_writer.py") -> dict:
    return {
        "artifact_format": "dictionary-v2-root-entry-draft-v1",
        "generated_by": generator,
        "language": "tr",
        "root_envelope_id": root,
        "branches": [{
            "branch_ref": root + "/B001",
            "branch_image_ar": "صورة",
            "what_is_ar": "حد",
            "what_is_not_ar": "غيره",
            "source_phrase_ar": "نص",
            "sources": ["AY"],
        }],
        "occurrence_evidence": {
            "summary": {"morpheme_count": 0, "word_count": 0,
                        "ayah_count": 0, "surah_count": 0},
            "forms": [], "ayahs": [], "occurrences": [],
        },
    }


class TurkishTransferTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name)
        self.source = base / "dictionary"
        self.source.mkdir()
        self.root = base / "quran-data"
        self.bridge = self.root / "data/bridges/qac-furuq-v4-root-map.sqlite.gz"
        self.destination = self.root / "data/dictionary/tr"
        (self.root / "data/bridges").mkdir(parents=True)
        (self.root / "data/bridges/qac-dictionary-root-resolutions.json").write_text(
            json.dumps({"roots": []}), encoding="utf-8")

        database = base / "bridge.sqlite"
        with sqlite3.connect(database) as connection:
            connection.execute("CREATE TABLE qac_to_furuq_mapped (furuq_root_id TEXT)")
            connection.executemany(
                "INSERT INTO qac_to_furuq_mapped VALUES (?)",
                [(root,) for root in ("root_005302", "root_005229", "root_005406")],
            )
        self.bridge.write_bytes(gzip.compress(database.read_bytes()))

        self.write("data/output/root_packets/root_000001.json", {})
        self.write("v2/work/entry_creation/root_000001/tr/output/root_000001_entry.json",
                   entry("root_000001"))
        self.write("v2/work/entry_creation/furuq/root_005302/tr/output/root_005302_entry.json",
                   entry("root_005302"))
        self.write("v2/work/entry_creation/furuq/root_005406/tr/output/root_005406_entry.json",
                   {"branches": [], "root_profile": {}})
        self.write("v2/work/entry_creation/furuq/root_005406/tr/export/root_005406_entry.json",
                   entry("root_005406", generator="v2/scripts/enrich_furuq_writer.py"))
        self.write("v2/work/entry_creation/furuq/root_005229/tr/output/root_005229_entry.json",
                   {"branches": [], "root_profile": {}})
        self.git("init", "-q")
        self.commit()

    def write(self, relative: str, value: dict) -> Path:
        path = self.source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")
        return path

    def git(self, *args: str) -> str:
        return subprocess.check_output(
            ["git", "-C", str(self.source), *args], stderr=subprocess.PIPE,
        ).decode().strip()

    def commit(self):
        self.git("add", "-A")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.com",
                 "commit", "-qm", "fixture")

    def collect(self):
        with patch.object(sync, "ROOT", self.root):
            return sync.collect(self.source, self.bridge)

    def transfer(self, *, check=False):
        with patch.object(sync, "ROOT", self.root):
            return sync.transfer(self.source, self.bridge, self.destination, check=check)

    def test_committed_export_precedes_raw_output_and_dirty_files(self):
        committed_export = self.git(
            "show", "HEAD:v2/work/entry_creation/furuq/root_005406/tr/export/root_005406_entry.json"
        ).encode() + b"\n"
        self.write("v2/work/entry_creation/furuq/root_005406/tr/export/root_005406_entry.json",
                   {"branches": [], "root_profile": {}})
        self.write("v2/work/entry_creation/furuq/root_005229/tr/export/root_005229_entry.json",
                   entry("root_005229", generator="v2/scripts/enrich_furuq_writer.py"))
        (self.source / "data/output/root_packets/root_000001.json").unlink()

        files, manifest = self.collect()
        self.assertEqual(set(files), {
            "root_000001_entry.json", "root_005302_entry.json", "root_005406_entry.json",
        })
        self.assertEqual(files["root_005406_entry.json"], committed_export)
        self.assertEqual(manifest["schemaVersion"], "turkish-dictionary-transfer-v1")
        self.assertEqual(manifest["sourceCommit"], self.git("rev-parse", "HEAD"))
        self.assertEqual(manifest["missingTargetRootIds"], ["root_005229"])
        paths = {row["path"]: row["sourcePath"] for row in manifest["entries"]}
        self.assertEqual(paths["root_005302_entry.json"],
                         "v2/work/entry_creation/furuq/root_005302/tr/output/root_005302_entry.json")
        self.assertEqual(paths["root_005406_entry.json"],
                         "v2/work/entry_creation/furuq/root_005406/tr/export/root_005406_entry.json")
        self.assertEqual(manifest["entries"][-1]["sha256"],
                         hashlib.sha256(committed_export).hexdigest())
        corpus = "".join(f"{row['sha256']}  {row['path']}\n" for row in manifest["entries"])
        self.assertEqual(manifest["sourceCorpusSha256"],
                         hashlib.sha256(corpus.encode()).hexdigest())

    def test_invalid_committed_export_does_not_fall_back_to_output(self):
        self.write("v2/work/entry_creation/furuq/root_005406/tr/output/root_005406_entry.json",
                   entry("root_005406"))
        self.write("v2/work/entry_creation/furuq/root_005406/tr/export/root_005406_entry.json",
                   {"branches": [], "root_profile": {}})
        self.commit()
        with self.assertRaisesRegex(ValueError, "root_005406_entry.json"):
            self.collect()

    def test_check_mode_and_previous_entry_regression_guard(self):
        with self.assertRaisesRegex(ValueError, "Stale Turkish entry transfer"):
            self.transfer(check=True)
        self.assertFalse(self.destination.exists())
        manifest, changed = self.transfer()
        self.assertEqual(len(changed), 4)
        self.assertEqual(manifest["entryCount"], 3)
        self.assertEqual(self.transfer(check=True)[1], [])
        old_entry = self.destination / "root_005229_entry.json"
        old_entry.write_text(json.dumps(entry("root_005229")), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Previously transferred entries require review"):
            self.transfer()
        self.assertTrue(old_entry.exists())
        old_entry.unlink()
        prior_path = self.destination / "MANIFEST.json"
        prior = json.loads(prior_path.read_text(encoding="utf-8"))
        prior["entries"].append({"path": old_entry.name, "sha256": "previously-transferred"})
        prior_path.write_text(json.dumps(prior), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Previously transferred entries require review"):
            self.transfer()


if __name__ == "__main__":
    unittest.main()
