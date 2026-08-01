#!/usr/bin/env python3
"""Build the static inventory consumed by the GitHub Pages browser."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "pages-inventory.json"


def ids_from_audio_manifests(collection: str) -> list[int]:
    base = ROOT / "_audio" / "audio" / collection
    if not base.exists():
        return []
    ids: set[int] = set()
    for manifest in base.glob("S[0-9][0-9][0-9]/manifest.json"):
        try:
            ids.add(int(manifest.parent.name[1:]))
        except ValueError:
            continue
    return sorted(ids)


def ids_from_commentary_dirs(*parts: str) -> list[int]:
    base = ROOT.joinpath(*parts)
    if not base.exists():
        return []
    ids: set[int] = set()
    for directory in base.glob("s[0-9][0-9][0-9]"):
        if not directory.is_dir():
            continue
        try:
            ids.add(int(directory.name[1:]))
        except ValueError:
            continue
    return sorted(ids)


def main() -> None:
    available = {
        "recitation": ids_from_audio_manifests("recitation"),
        "ayah": ids_from_audio_manifests("ayah"),
        "summary": ids_from_audio_manifests("summary"),
        "surah": ids_from_audio_manifests("surah"),
        "ayahText": ids_from_commentary_dirs("data", "commentary", "ayah", "detailed", "tr"),
        "summaryText": ids_from_commentary_dirs("data", "commentary", "ayah", "summary", "tr"),
        "surahText": ids_from_commentary_dirs("data", "commentary", "surah", "detailed", "tr"),
    }
    paths = {
        "quranText": "data/text/quran-uthmani.tsv",
        "audioManifestPattern": "_audio/audio/{collection}/S{surah3}/manifest.json",
        "ayahCommentaryPattern": "data/commentary/ayah/detailed/tr/s{surah3}/{surah}_{ayah}.prose.tr.md",
        "ayahSummaryPattern": "data/commentary/ayah/summary/tr/s{surah3}/{surah}_{ayah}.prose.summary.tr.md",
        "surahCommentaryPattern": "data/commentary/surah/detailed/tr/s{surah3}/{surah}.surah-reading.tr.md",
    }
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    if OUT.exists():
        try:
            current = json.loads(OUT.read_text(encoding="utf-8"))
            if current.get("available") == available and current.get("paths") == paths:
                generated_at = current.get("generatedAt", generated_at)
        except json.JSONDecodeError:
            pass

    inventory = {
        "schemaVersion": 1,
        "generatedAt": generated_at,
        "available": available,
        "paths": paths,
    }
    OUT.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
