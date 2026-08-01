#!/usr/bin/env python3
"""Summarize the spending ledger (_audio/ledger/*.jsonl).

Reads every dated ledger file synthesize_tts_chunks.py has written and
prints totals broken down by event type and, optionally, filtered to one
collection or surah. See _audio/ledger/README.md for the schema this reads.

Usage:
    ledger_summary.py
    ledger_summary.py --collection ayah
    ledger_summary.py --surah S100
    ledger_summary.py --collection ayah --surah S100
"""
from __future__ import annotations

import argparse
import glob
import json
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]  # .../quran-data
DEFAULT_LEDGER_DIR = REPO_ROOT / "_audio" / "ledger"


def load_entries(ledger_dir: Path, *, collection: str | None, surah: str | None):
    for path in sorted(glob.glob(str(ledger_dir / "*.jsonl"))):
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                entry = json.loads(line)
                if collection and entry.get("collection") != collection:
                    continue
                if surah and entry.get("surahId") != surah:
                    continue
                yield entry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ledger-dir", type=Path, default=DEFAULT_LEDGER_DIR)
    parser.add_argument("--collection", choices=["recitation", "ayah", "summary", "surah"])
    parser.add_argument("--surah", help="e.g. S100")
    args = parser.parse_args()

    by_event = defaultdict(lambda: {"count": 0, "durationSeconds": 0.0, "billedUsd": 0.0})
    by_collection = defaultdict(lambda: {"count": 0, "billedUsd": 0.0})
    total_billed = 0.0
    total_duration = 0.0
    n = 0

    for entry in load_entries(args.ledger_dir, collection=args.collection, surah=args.surah):
        n += 1
        event = entry.get("event", "?")
        billed = entry.get("billedTotalUsd", 0.0) or 0.0
        duration = entry.get("durationSeconds") or 0.0

        by_event[event]["count"] += 1
        by_event[event]["durationSeconds"] += duration
        by_event[event]["billedUsd"] += billed

        coll = entry.get("collection", "?")
        by_collection[coll]["count"] += 1
        by_collection[coll]["billedUsd"] += billed

        total_billed += billed
        total_duration += duration

    if n == 0:
        print("No ledger entries match.")
        return 0

    print(f"{n} ledger entries" + (f" (collection={args.collection})" if args.collection else "")
          + (f" (surah={args.surah})" if args.surah else ""))
    print()
    print("By event:")
    for event, stats in sorted(by_event.items()):
        hrs = stats["durationSeconds"] / 3600
        print(f"  {event:<12} count={stats['count']:<6} audio={hrs:.2f}hr  billed=${stats['billedUsd']:.4f}")
    print()
    print("By collection:")
    for coll, stats in sorted(by_collection.items()):
        print(f"  {coll:<12} count={stats['count']:<6} billed=${stats['billedUsd']:.4f}")
    print()
    print(f"TOTAL billed: ${total_billed:.4f}")
    print(f"TOTAL audio generated or reused: {total_duration/3600:.2f} hr")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
