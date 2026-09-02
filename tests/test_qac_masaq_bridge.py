from __future__ import annotations

import gzip
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.bridges.build_qac_masaq_bridge import (
    BUILDER_VERSION,
    AttachmentEndpoint,
    QacMorpheme,
    ReviewedDecision,
    UnitMapping,
    apply_reviewed_decisions,
    select_attachment_qac_refs,
)


ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "data/bridges/qac-masaq.sqlite.gz"


class QacMasaqBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._directory = tempfile.TemporaryDirectory(prefix="qac-masaq-test-")
        database_path = Path(cls._directory.name) / "bridge.sqlite"
        database_path.write_bytes(gzip.decompress(BRIDGE.read_bytes()))
        cls.database = sqlite3.connect(database_path)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.database.close()
        cls._directory.cleanup()

    def scalar(self, query: str, parameters: tuple[object, ...] = ()) -> object:
        row = self.database.execute(query, parameters).fetchone()
        self.assertIsNotNone(row)
        return row[0]

    def test_integrity_and_release_counts(self) -> None:
        self.assertEqual(self.database.execute("PRAGMA foreign_key_check").fetchall(), [])
        self.assertEqual(self.scalar("PRAGMA user_version"), 4)
        self.assertEqual(
            self.scalar("SELECT value FROM metadata WHERE key = 'builder_version'"),
            BUILDER_VERSION,
        )
        self.assertEqual(self.scalar("SELECT count(*) FROM qac_morphemes"), 128_219)
        self.assertEqual(self.scalar("SELECT count(*) FROM grammar_units"), 95_511)
        self.assertEqual(self.scalar("SELECT count(*) FROM masaq_segments"), 95_511)
        self.assertEqual(self.scalar("SELECT count(*) FROM word_analysis_units"), 95_304)
        self.assertEqual(
            self.scalar(
                "SELECT count(*) FROM word_analysis_units WHERE relation_status = 'accepted'"
            ),
            95_303,
        )

    def test_all_public_edges_are_same_ayah_and_unique(self) -> None:
        self.assertEqual(
            self.scalar(
                """
                SELECT count(*)
                  FROM analysis_qac_edges aq
                  JOIN word_analysis_units wa USING (analysis_ref)
                  JOIN qac_morphemes qm USING (qac_morpheme_ref)
                 WHERE wa.surah != qm.surah OR wa.ayah != qm.ayah
                """
            ),
            0,
        )
        self.assertEqual(
            self.database.execute(
                "SELECT DISTINCT source_namespace FROM qac_links ORDER BY 1"
            ).fetchall(),
            [
                ("attachment-endpoint",),
                ("grammar-unit",),
                ("masaq-segment",),
                ("word-analysis",),
            ],
        )
        self.assertEqual(
            self.scalar(
                """
                SELECT count(*) FROM qac_links
                 WHERE source_namespace = 'attachment-endpoint'
                """
            ),
            self.scalar("SELECT count(*) FROM attachment_qac_edges"),
        )
        self.assertEqual(
            self.scalar(
                """
                SELECT count(*)
                  FROM accepted_masaq_qac_edges mq
                  JOIN masaq_segments ms USING (masaq_segment_ref)
                  JOIN qac_morphemes qm USING (qac_morpheme_ref)
                 WHERE ms.surah != qm.surah OR ms.ayah != qm.ayah
                """
            ),
            0,
        )
        self.assertEqual(
            self.scalar(
                """
                SELECT count(*)
                  FROM attachment_qac_edges aq
                  JOIN qac_morphemes qm USING (qac_morpheme_ref)
                 WHERE aq.attachment_unit_ref NOT LIKE
                       'q:' || qm.surah || ':' || qm.ayah || ':%'
                """
            ),
            0,
        )
        self.assertEqual(
            self.scalar(
                """
                SELECT count(*) FROM (
                  SELECT source_namespace, source_ref, qac_morpheme_ref, count(*) AS n
                    FROM qac_links
                GROUP BY source_namespace, source_ref, qac_morpheme_ref
                  HAVING n > 1
                )
                """
            ),
            0,
        )
        self.assertEqual(
            self.scalar(
                """
                SELECT count(*) FROM (
                  SELECT source_namespace, source_ref, count(*) AS n,
                         min(target_order) AS lo, max(target_order) AS hi,
                         count(DISTINCT target_order) AS distinct_orders
                    FROM qac_links
                GROUP BY source_namespace, source_ref
                  HAVING lo != 1 OR hi != n OR distinct_orders != n
                )
                """
            ),
            0,
        )
        self.assertEqual(
            self.scalar(
                """
                SELECT count(*)
                  FROM word_analysis_units wa
             LEFT JOIN analysis_qac_edges aq USING (analysis_ref)
                 WHERE wa.relation_status = 'accepted' AND aq.analysis_ref IS NULL
                """
            ),
            0,
        )

    def test_masaq_segment_space_is_complete_and_accepted(self) -> None:
        self.assertEqual(
            self.scalar("SELECT count(*) FROM grammar_masaq_edges WHERE accepted = 0"),
            0,
        )
        self.assertEqual(
            self.scalar(
                """
                SELECT count(*)
                  FROM masaq_segments ms
             LEFT JOIN accepted_masaq_qac_edges mq USING (masaq_segment_ref)
                 WHERE mq.masaq_segment_ref IS NULL
                """
            ),
            0,
        )
        self.assertEqual(
            self.scalar(
                """
                WITH per_ayah AS (
                  SELECT surah, ayah, count(*) AS n, min(segment_index) AS lo,
                         max(segment_index) AS hi, count(DISTINCT segment_index) AS d
                    FROM masaq_segments
                GROUP BY surah, ayah
                )
                SELECT count(*) FROM per_ayah
                 WHERE lo != 1 OR hi != n OR d != n
                """
            ),
            0,
        )
        repaired = self.database.execute(
            """
            SELECT masaq_segment_ref, stem_ar, tag, role
             FROM masaq_segments
             WHERE masaq_segment_ref IN ('7:169:45', '17:28:12', '17:28:13')
          ORDER BY surah, ayah, segment_index
            """
        ).fetchall()
        self.assertEqual(
            repaired,
            [
                ("7:169:45", "أ", "INTERROG", "PART_INTERROG"),
                ("17:28:12", "ل", "PREP", "PREP"),
                ("17:28:13", "هم", "PRON", "PREP_OBJ"),
            ],
        )

    def test_known_many_to_many_cases(self) -> None:
        self.assertEqual(
            self.database.execute(
                """
                SELECT analysis_ref FROM analysis_qac_edges
                 WHERE qac_morpheme_ref = '37:130:3:1'
              ORDER BY analysis_ref
                """
            ).fetchall(),
            [("37:130:3",), ("37:130:4",)],
        )
        self.assertEqual(
            self.database.execute(
                """
                SELECT analysis_ref FROM analysis_qac_edges
                 WHERE qac_morpheme_ref = '61:11:4:1'
              ORDER BY analysis_ref
                """
            ).fetchall(),
            [("61:11:6",), ("61:11:7",)],
        )
        self.assertEqual(
            self.database.execute(
                """
                SELECT grammar_ref, qac_morpheme_ref, reviewed_decision_id
                  FROM masaq_qac_paths
                 WHERE masaq_segment_ref = '100:8:3'
              ORDER BY grammar_ref, qac_morpheme_ref
                """
            ).fetchall(),
            [
                ("100:8:2", "100:8:2:1", None),
                ("100:8:3", "100:8:2:2", None),
            ],
        )
        self.assertEqual(
            self.database.execute(
                """
                SELECT masaq_segment_ref, qac_morpheme_ref, target_order
                  FROM accepted_masaq_qac_edges
                  JOIN masaq_segments USING (masaq_segment_ref)
                 WHERE masaq_segment_ref IN (
                   '100:8:1', '100:8:2', '100:8:3',
                   '17:28:12', '17:28:13'
                 )
              ORDER BY surah, ayah, segment_index, target_order
                """
            ).fetchall(),
            [
                ("17:28:12", "17:28:10:1", 1),
                ("17:28:13", "17:28:10:2", 1),
                ("100:8:1", "100:8:1:1", 1),
                ("100:8:2", "100:8:1:2", 1),
                ("100:8:3", "100:8:2:1", 1),
                ("100:8:3", "100:8:2:2", 2),
            ],
        )
        self.assertEqual(
            self.database.execute(
                """
                SELECT analysis_ref, masaq_segment_ref
                  FROM analysis_masaq_edges
                 WHERE analysis_ref IN ('100:8:1', '100:8:2', '100:8:3')
              ORDER BY analysis_ref, masaq_ref_order
                """
            ).fetchall(),
            [
                ("100:8:1", "100:8:1"),
                ("100:8:1", "100:8:2"),
                ("100:8:2", "100:8:3"),
                ("100:8:3", "100:8:3"),
            ],
        )
        self.assertEqual(
            self.database.execute(
                """
                SELECT analysis_ref, qac_morpheme_ref
                  FROM analysis_qac_edges
                 WHERE analysis_ref IN ('19:71:1', '19:71:2')
              ORDER BY analysis_ref, qac_order
                """
            ).fetchall(),
            [
                ("19:71:1", "19:71:1:1"),
                ("19:71:1", "19:71:1:2"),
                ("19:71:2", "19:71:1:1"),
                ("19:71:2", "19:71:1:2"),
            ],
        )

    def test_source_duplicate_is_retained_but_never_public(self) -> None:
        row = self.database.execute(
            """
            SELECT relation_status, exclusion_reason
              FROM word_analysis_units
             WHERE analysis_ref = '17:28:12'
            """
        ).fetchone()
        self.assertEqual(
            row,
            ("excluded-source-defect", "duplicate_qul_cannot_map_to_masaq_lam"),
        )
        self.assertEqual(
            self.scalar(
                """
                SELECT count(*) FROM qac_links
                 WHERE source_namespace IN ('word-analysis', 'grammar-unit')
                   AND source_ref = '17:28:12'
                """
            ),
            0,
        )
        self.assertEqual(
            self.database.execute(
                """
                SELECT masaq_segment_ref FROM grammar_masaq_edges
                 WHERE grammar_ref = '17:28:13'
              ORDER BY masaq_ref_order
                """
            ).fetchall(),
            [("17:28:12",), ("17:28:13",)],
        )

    def test_attachment_endpoints_resolve_or_are_explicitly_excluded(self) -> None:
        self.assertEqual(
            self.scalar("SELECT count(*) FROM attachment_unit_resolutions"),
            74_679,
        )
        self.assertEqual(
            self.scalar(
                """
                SELECT count(*)
                  FROM attachment_unit_resolutions resolution
             LEFT JOIN attachment_qac_edges edge USING (attachment_unit_ref)
                 WHERE edge.attachment_unit_ref IS NULL
                """
            ),
            0,
        )
        self.assertEqual(
            self.scalar(
                """
                SELECT count(*) FROM (
                  SELECT attachment_id, endpoint_role
                    FROM attachment_qac_edges
                GROUP BY attachment_id, endpoint_role
                )
                """
            ),
            129_702,
        )
        self.assertEqual(
            self.scalar(
                """
                SELECT count(*) FROM (
                  SELECT attachment_id, endpoint_role, count(*) AS n,
                         min(target_order) AS lo, max(target_order) AS hi,
                         count(DISTINCT target_order) AS distinct_orders
                    FROM attachment_qac_edges
                GROUP BY attachment_id, endpoint_role
                  HAVING lo != 1 OR hi != n OR distinct_orders != n
                )
                """
            ),
            0,
        )
        self.assertEqual(
            self.database.execute(
                """
                SELECT target_namespace, target_ref, resolution_rule,
                       reviewed_decision_id
                  FROM attachment_unit_resolutions
                 WHERE attachment_unit_ref = 'q:17:28:12'
                """
            ).fetchone(),
            (
                "masaq-segment",
                "17:28:12",
                "reviewed-namespace-redirect",
                "QMA-D001",
            ),
        )
        self.assertEqual(
            self.database.execute(
                """
                SELECT qac_morpheme_ref
                  FROM attachment_qac_edges
                 WHERE attachment_unit_ref = 'q:17:28:12'
              ORDER BY target_order
                """
            ).fetchall(),
            [("17:28:10:1",)],
        )
        self.assertEqual(
            self.database.execute(
                """
                SELECT endpoint_role, qac_morpheme_ref, alignment_rule
                  FROM attachment_qac_edges
                 WHERE attachment_id IN (
                   'ae:v3:s100:008:pass1:attach:a1',
                   'ae:v3:s110:003:pass1:attach:a6'
                 )
              ORDER BY attachment_id, endpoint_role, target_order
                """
            ).fetchall(),
            [
                ("dependent", "100:8:1:3", "explicit-pronominal-morpheme"),
                ("head", "100:8:1:2", "core-particle-morpheme"),
                ("dependent", "110:3:5:2", "explicit-pronominal-morpheme"),
                ("head", "110:3:5:1", "core-particle-morpheme"),
            ],
        )
        self.assertEqual(
            self.database.execute(
                """
                SELECT attachment_id, endpoint_role, attachment_unit_ref,
                       reviewed_decision_id
                  FROM excluded_attachment_endpoints
              ORDER BY attachment_id, endpoint_role
                """
            ).fetchall(),
            [
                (
                    "ae:v3:s004:007:pass1:attach:a16",
                    "dependent",
                    "q:4:7:8",
                    "QMA-D003",
                ),
                (
                    "ae:v3:s004:007:pass1:attach:a16",
                    "head",
                    "q:4:7:8",
                    "QMA-D003",
                ),
            ],
        )
        self.assertEqual(
            self.scalar(
                """
                SELECT count(*) FROM attachment_qac_edges
                 WHERE attachment_id = 'ae:v3:s004:007:pass1:attach:a16'
                """
            ),
            0,
        )
        self.assertEqual(
            self.scalar(
                """
                SELECT count(*) FROM attachment_qac_edges
                 WHERE alignment_rule LIKE '%fallback%'
                """
            ),
            0,
        )
        self.assertEqual(
            self.scalar(
                """
                SELECT count(*) FROM reviewed_attachment_decisions
                 WHERE decision_type = 'approve-fused-carrier'
                """
            ),
            10,
        )
        self.assertEqual(
            self.scalar(
                """
                SELECT count(*) FROM attachment_qac_edges
                 WHERE alignment_rule LIKE 'fused-%-carrier'
                   AND alignment_reviewed_decision_id IS NULL
                """
            ),
            0,
        )

    def test_attachment_parts_select_exact_qac_carriers(self) -> None:
        cases = {
            "ae:v3:s002:234:pass1:attach:a11": (
                "dependent",
                "2:234:17:2",
                "explicit-pronominal-morpheme",
                None,
            ),
            "ae:v3:s005:014:pass1:attach:a9": (
                "preposition",
                "5:14:14:1",
                "fused-preposition-carrier",
                "QMA-D004",
            ),
            "ae:v3:s016:064:pass1:attach:a4": (
                "preposition",
                "16:64:6:1",
                "explicit-preposition-morpheme",
                None,
            ),
            "ae:v3:s054:016:pass1:attach:a5": (
                "dependent",
                "54:16:4:2",
                "fused-suffix-carrier",
                "QMA-D009",
            ),
        }
        for attachment_id, expected in cases.items():
            with self.subTest(attachment_id=attachment_id):
                self.assertEqual(
                    self.database.execute(
                        """
                        SELECT endpoint_role, qac_morpheme_ref, alignment_rule,
                               alignment_reviewed_decision_id
                          FROM attachment_qac_edges
                         WHERE attachment_id = ? AND endpoint_role = ?
                      ORDER BY endpoint_role, target_order
                        """,
                        (attachment_id, expected[0]),
                    ).fetchall(),
                    [expected],
                )
        self.assertEqual(
            self.database.execute(
                """
                SELECT endpoint_role, qac_morpheme_ref
                  FROM attachment_qac_edges
                 WHERE attachment_id = 'ae:v3:s017:028:pass1:attach:a6'
              ORDER BY endpoint_role, target_order
                """
            ).fetchall(),
            [
                ("dependent", "17:28:10:2"),
                ("head", "17:28:9:2"),
                ("preposition", "17:28:10:1"),
            ],
        )

    def test_qac_only_morphemes_remain_explicit(self) -> None:
        self.assertEqual(
            self.scalar(
                "SELECT count(*) FROM qac_morphemes WHERE link_status = 'no-source-unit'"
            ),
            611,
        )

    def test_relative_particle_segment_selects_the_relative_qac_stem(self) -> None:
        endpoint = AttachmentEndpoint(
            attachment_id="fixture",
            endpoint_role="head",
            attachment_unit_ref="q:1:1:1",
            endpoint_part="particle_segment",
            surface_ar="",
            form_tag="",
        )
        candidates = [
            QacMorpheme(
                ref="1:1:1:1",
                word_ref="1:1:1",
                surah=1,
                ayah=1,
                word_index=1,
                morpheme_index=1,
                surface_ar="ma",
                stem_ar="ma",
                pos="REL",
                role="STEM",
            ),
            QacMorpheme(
                ref="1:1:1:2",
                word_ref="1:1:1",
                surah=1,
                ayah=1,
                word_index=1,
                morpheme_index=2,
                surface_ar="li",
                stem_ar="li",
                pos="P",
                role="PREFIX",
            ),
        ]
        selected, rule = select_attachment_qac_refs(endpoint, candidates)
        self.assertEqual([item.ref for item in selected], ["1:1:1:1"])
        self.assertEqual(rule, "core-particle-morpheme")

    def test_reviewed_mapping_may_span_qac_parent_words(self) -> None:
        automatic = UnitMapping(
            grammar_ref="1:1:1",
            qac_refs=("1:1:1:1",),
            qac_word_refs=("1:1:1",),
            rule="normalized-exact",
            rank=0,
            edit_distance=0,
            cost=0,
            source_surface_ar="x",
            target_surface_ar="x",
        )
        morphemes = [
            QacMorpheme(
                ref=f"1:1:{word}:1",
                word_ref=f"1:1:{word}",
                surah=1,
                ayah=1,
                word_index=word,
                morpheme_index=1,
                surface_ar="x",
                stem_ar="x",
                pos="N",
                role="STEM",
            )
            for word in (1, 2)
        ]
        decision = ReviewedDecision(
            decision_id="TEST-D001",
            grammar_ref="1:1:1",
            qac_refs=("1:1:1:1", "1:1:2:1"),
            decision_type="test-cross-word-span",
            reason="regression fixture",
            review_status="accepted",
            reviewed_on="2026-09-02",
        )
        mappings, _audit = apply_reviewed_decisions(
            {automatic.grammar_ref: automatic}, morphemes, [decision]
        )
        self.assertEqual(
            mappings[automatic.grammar_ref].qac_word_refs,
            ("1:1:1", "1:1:2"),
        )


if __name__ == "__main__":
    unittest.main()
