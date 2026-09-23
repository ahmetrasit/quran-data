"""Integrity checks for authored, word-scoped dictionary root analyses."""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/bridges/qac-dictionary-word-root-analyses.json"
QAC = ROOT / "data/morphology/qac.sqlite.gz"
RESOLUTIONS = ROOT / "data/bridges/qac-dictionary-root-resolutions.json"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
BRANCH_REF = re.compile(r"(root_\d{6})/(B\d{3})\Z")


class DictionaryWordRootAnalysesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = json.loads(SOURCE.read_text(encoding="utf-8"))
        cls.resolutions = json.loads(RESOLUTIONS.read_text(encoding="utf-8"))
        cls.qac = sqlite3.connect(":memory:")
        cls.qac.deserialize(gzip.decompress(QAC.read_bytes()))
        cls.root_ids = {
            root_id
            for row in cls.resolutions["roots"]
            for root_id in row["rootIds"]
        }

    @classmethod
    def tearDownClass(cls) -> None:
        cls.qac.close()

    def test_source_is_pinned_and_selectors_match_qac(self) -> None:
        self.assertEqual(
            self.source["schemaVersion"], "qac-dictionary-word-root-analyses-v1"
        )
        snapshot = self.source["sourceSnapshot"]
        self.assertRegex(snapshot["qacMorphologyGzipSha256"], HEX64)
        self.assertRegex(snapshot["rootResolutionsSha256"], HEX64)
        self.assertRegex(snapshot["dictionarySourceCommit"], re.compile(r"[0-9a-f]{40}\Z"))

        resolutions_by_key = {
            row["qacRootJoinKey"]: row for row in self.resolutions["roots"]
        }

        seen: set[tuple[str, str, str]] = set()
        for record in self.source["records"]:
            selector = record["selector"]
            self.assertEqual(set(selector), {"qacRootJoinKey", "qacLemma"} if "qacLemma" in selector else {"qacRootJoinKey", "qacRef"})
            scope = "qacLemma" if "qacLemma" in selector else "qacRef"
            key = (selector["qacRootJoinKey"], scope, selector[scope])
            self.assertNotIn(key, seen)
            seen.add(key)
            field = "lemma_ar" if scope == "qacLemma" else "qac_ref"
            refs = sorted(row[0] for row in self.qac.execute(
                f"SELECT qac_ref FROM qac_morphemes WHERE root_join_key=? AND {field}=?",
                (selector["qacRootJoinKey"], selector[scope]),
            ))
            self.assertTrue(refs, key)
            self.assertEqual(
                record["selectorRefsSha256"],
                hashlib.sha256(json.dumps(refs, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest(),
                key,
            )
            baseline = record["baselineResolution"]
            current = resolutions_by_key[selector["qacRootJoinKey"]]
            self.assertEqual(baseline["resolution"], current["resolution"], key)
            self.assertEqual(baseline["rootIds"], current["rootIds"], key)

        self.assertEqual(
            self.qac.execute(
                "SELECT count(*) FROM qac_morphemes WHERE root_join_key=? AND lemma_ar=?",
                ("سمو", "ٱسْم"),
            ).fetchone()[0],
            39,
        )
        self.assertEqual(
            self.qac.execute(
                "SELECT count(*) FROM qac_morphemes WHERE root_join_key=? AND lemma_ar=?",
                ("كيف", "كَيْف"),
            ).fetchone()[0],
            83,
        )

    def test_ranked_evidence_and_dictionary_refs_are_coherent(self) -> None:
        for record in self.source["records"]:
            selector = record["selector"]
            analyses = record["analyses"]
            self.assertTrue(analyses, selector)
            self.assertEqual(
                [item["rank"] for item in analyses],
                list(range(1, len(analyses) + 1)),
                selector,
            )
            self.assertEqual(analyses[0]["standing"], "primary", selector)
            self.assertTrue(
                all(item["standing"] == "documented_alternative" for item in analyses[1:]),
                selector,
            )
            self.assertEqual(
                len({item["rootArabic"] for item in analyses}), len(analyses), selector
            )
            for item in analyses:
                self.assertTrue(item["reasonTr"].strip(), selector)
                self.assertTrue(item["attributionTr"].strip(), selector)
                root_id = item["dictionaryRootId"]
                branch_ref = item["dictionaryBranchRef"]
                if root_id is None:
                    self.assertIsNone(branch_ref, selector)
                else:
                    self.assertIn(root_id, self.root_ids, selector)
                    if branch_ref is not None:
                        match = BRANCH_REF.fullmatch(branch_ref)
                        self.assertIsNotNone(match, branch_ref)
                        self.assertEqual(match.group(1), root_id, branch_ref)
                        entry = json.loads(
                            (ROOT / "data/dictionary/tr" / f"{root_id}_entry.json").read_text(
                                encoding="utf-8"
                            )
                        )
                        self.assertIn(branch_ref, {b["branch_ref"] for b in entry["branches"]})

                self.assertTrue(item["evidence"], selector)
                for evidence in item["evidence"]:
                    self.assertTrue(evidence["sourceTitle"].strip(), selector)
                    self.assertTrue(evidence["noteTr"].strip(), selector)
                    if "sourceUrl" in evidence:
                        self.assertTrue(evidence["sourceUrl"].startswith("https://"))
                    else:
                        self.assertTrue(evidence["sourceRef"].strip())
                        self.assertRegex(evidence["sourceSha256"], HEX64)
                    source_ref = evidence.get("sourceRef", "")
                    if source_ref.endswith("#source_phrase_ar"):
                        evidence_branch = source_ref.removesuffix("#source_phrase_ar")
                        evidence_root, _ = evidence_branch.split("/")
                        entry = json.loads(
                            (ROOT / "data/dictionary/tr" / f"{evidence_root}_entry.json").read_text(
                                encoding="utf-8"
                            )
                        )
                        branch = next(
                            b for b in entry["branches"] if b["branch_ref"] == evidence_branch
                        )
                        self.assertEqual(
                            evidence["sourceSha256"],
                            hashlib.sha256(branch["source_phrase_ar"].encode("utf-8")).hexdigest(),
                            source_ref,
                        )

    def test_competing_accounts_do_not_leak_to_other_lemmas(self) -> None:
        by_key = {
            (record["selector"]["qacRootJoinKey"], record["selector"].get("qacLemma")):
            record
            for record in self.source["records"]
            if "qacLemma" in record["selector"]
        }
        name = by_key[("سمو", "ٱسْم")]
        self.assertEqual(
            [a["rootArabic"] for a in name["analyses"]], ["س م و", "و س م"]
        )
        self.assertNotIn(("سمو", "سَمَآء"), by_key)
        self.assertNotIn("س م م", {a["rootArabic"] for a in name["analyses"]})


if __name__ == "__main__":
    unittest.main()
