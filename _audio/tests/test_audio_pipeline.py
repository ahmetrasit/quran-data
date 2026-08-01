import json
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import run_tts_batch as batch  # noqa: E402
import prepare_commentary_chunks as commentary  # noqa: E402
import synthesize_tts_chunks as synth  # noqa: E402
import tts_common as common  # noqa: E402


class AudioPipelineTest(unittest.TestCase):
    def build_collection(self, root: Path) -> Path:
        collection = root / "audio" / "ayah" / "S001"
        sections = [
            {
                "title": "Fâtiha birinci ayet",
                "kind": "ayah_detailed",
                "grades": [],
                "paragraphs": [
                    {
                        "kind": "ayah_reference",
                        "text": "بِسْمِ اللَّهِ",
                        "ttsText": "Fâtiha birinci ayet. بِسْمِ اللَّهِ",
                    },
                    {"kind": "paragraph", "text": "Kısa bir açıklama."},
                ],
            }
        ]
        with common.CollectionLock(collection):
            common.write_collection(
                out_dir=collection,
                surah_id="S001",
                collection="ayah",
                source="test.md",
                sources=["test.md"],
                sections=sections,
            )
        return collection

    def test_reference_and_commentary_prompts_are_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            collection = self.build_collection(Path(directory).resolve())
            chunks = synth.load_jsonl(collection / "chunks.jsonl")
            requests = [
                synth.strict_json_loads((collection / chunk["request"]).read_text())
                for chunk in chunks
            ]

            self.assertEqual(requests[0]["input"]["prompt"], common.RECITATION_PROMPT)
            self.assertEqual(requests[1]["input"]["prompt"], common.COMMENTARY_PROMPT)
            self.assertNotEqual(chunks[0]["promptSha256"], chunks[1]["promptSha256"])
            self.assertEqual(len(synth.preflight_collection(collection)["remoteChunks"]), 2)

    def test_collection_lock_blocks_only_the_same_collection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            first = root / "audio" / "ayah" / "S001"
            second = root / "audio" / "ayah" / "S002"
            second.mkdir(parents=True)
            with common.CollectionLock(first):
                with self.assertRaises(RuntimeError):
                    with synth.CollectionLock(first):
                        pass
                with synth.CollectionLock(second):
                    pass

    def test_parallel_ledger_appends_remain_valid_jsonl(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger_dir = Path(directory).resolve() / "ledger"

            def append(index: int) -> None:
                synth.append_ledger_entry(
                    ledger_dir,
                    {"event": "test", "attemptId": str(index)},
                )

            with ThreadPoolExecutor(max_workers=8) as executor:
                list(executor.map(append, range(40)))

            path = next(ledger_dir.glob("*.jsonl"))
            entries = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual(len(entries), 40)
            self.assertEqual({entry["attemptId"] for entry in entries}, {str(i) for i in range(40)})

    def test_parallel_budget_reserves_provider_maximum_for_inflight_calls(self):
        maximum = synth.maximum_single_request_cost()

        self.assertEqual(
            synth.affordable_pool_slots(
                Decimal("0"), maximum * 3, 50, 0, 10
            ),
            3,
        )
        self.assertEqual(
            synth.affordable_pool_slots(
                Decimal("0"), maximum * 3, 50, 2, 10
            ),
            1,
        )
        self.assertEqual(
            synth.affordable_pool_slots(
                maximum * 3, maximum * 3, 50, 0, 10
            ),
            0,
        )

    def test_batch_plan_is_offline_and_revalidates_request_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            collection = self.build_collection(Path(directory).resolve())
            first = batch.build_plan(
                [collection],
                workers=2,
                limit=1,
                force=False,
                reconcile_unknown=False,
                project_id=synth.DEFAULT_PROJECT_ID,
            )
            batch.revalidate_plan(first, workers=2)

            request_path = collection / "requests" / "sec-001-p-001.json"
            request_path.write_bytes(request_path.read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "changed after planning"):
                batch.revalidate_plan(first, workers=2)

    def test_surah_title_is_attached_to_first_prose_request(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory).resolve() / "12.surah-reading.tr.md"
            source.write_text("# Başlık\n\nİlk paragraf.\n\nİkinci paragraf.\n", encoding="utf-8")
            sections = commentary._build_surah_section(
                surah_number=12,
                surah_name="Yûsuf",
                surah_reading_path=source,
            )

            paragraphs = sections[0]["paragraphs"]
            self.assertEqual(len(paragraphs), 2)
            self.assertEqual(paragraphs[0]["kind"], "paragraph")
            self.assertEqual(paragraphs[0]["text"], "İlk paragraf.")
            self.assertEqual(paragraphs[0]["ttsText"], "Başlık. İlk paragraf.")
            self.assertNotIn("ttsText", paragraphs[1])

    def test_confirmed_provider_rejection_is_split_without_changing_text(self):
        text = "Birinci cümle açıklamayı kurar. İkinci cümle sürdürür. Üçüncü cümle tamamlar."

        parts = commentary._split_near_midpoint_at_sentence(text)

        self.assertEqual(len(parts), 2)
        self.assertEqual(" ".join(parts), text)


if __name__ == "__main__":
    unittest.main()
