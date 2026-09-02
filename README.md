# Quran Data

Canonical, consumer-facing Quran data releases.

This repository contains accepted datasets and staged canonical imports. Raw
experiments, prompts, packets, reviews, scripts, logs, and intermediary files
remain in their source repositories.

## Current release

`2026.09.02`

Released in `RELEASE.json`:

- Quran text
- QAC morphology and indexes
- V4 dictionary and positive handles
- QAC-to-V4 bridge
- QAC-first MASAQ, word-analysis, and attachment occurrence bridge
- completed Furuq database
- reviewed attachment enrichment `final_v3`
- reviewed contextual profiles `final_v3`
- production word analysis for all 6,236 ayahs (95,304 source records; 95,303
  accepted reader records after one reviewed duplicate exclusion)

## QAC-first linguistic mapping

The canonical all-Quran mapping artifact is
[`data/bridges/qac-masaq.sqlite.gz`](data/bridges/qac-masaq.sqlite.gz). Use its
`qac_links` view for uniform typed QAC links, `accepted_masaq_qac_edges` for
MASAQ-to-QAC spans, `analysis_qac_edges` for word-analysis links, and
`attachment_qac_edges` for occurrence-and-role-specific attachment links.

See the [bridge guide](data/bridges/qac-masaq/README.md), the
[schema and consumer contract](schemas/qac-masaq.md), and the
[release audit](data/bridges/qac-masaq-audit.json). Only commentary tags with
explicit typed references can participate in this mapping; surface-only tags
remain outside the canonical link graph.

## Staged imports

Copied on 2026-07-27, with per-folder provenance, but not yet folded into a new
`RELEASE.json`, manifest, checksum, and tag set:

- Turkish dictionary entries: `data/dictionary/tr/`, 1,679 entry JSON files
- Turkish translation glosses: `data/translation/glosses/locales/tr/`, 1,572 reviewed gloss JSON files
- Turkish V12 ayah activation/publication support: `data/analysis/ayah-activation/v12-tr/`, 114 surahs plus full-context packets/control directories and 6 focus runs
- Turkish V12 plus/minus-5 reader walks: `data/analysis/ayah-activation/v12-tr-11ayah/`, 114 surahs with reader walks and frozen run metadata
- Turkish V12 cross-run publication findings: `data/analysis/ayah-activation/v12-cross-run/tr/`, 114 final per-surah publication JSON files
- Network v3 generated channel outputs and reviews: `data/analysis/channels/network-v3/`, 111 eligible generated-output surahs, 110 review files, and pericopes; still candidate data pending blind review/adjudication
- Inter-ayah focus review TSVs: `data/analysis/inter-ayah/`, all 6,236 directional outputs staged and schema-clean; reciprocal-expanded consumer documents are under `data/analysis/inter-ayah/reciprocal/`
- QAC-to-furuq_v4 root gateway: `data/bridges/qac-furuq-v4-root-map.sqlite.gz`, plus source TSV and reproducible builder; staged and required for root-level QAC/furuq joins.

See `RELEASE.json` for the formal release payload, `manifests/` for release
coverage and provenance, and `INVENTORY.md` for a path-by-path map of what
exists in this repository. Staged imports carry local `SOURCE.md` files until
the next release metadata is cut.

## Ecosystem status

See [`STATUS.md`](STATUS.md) for the dated cross-repository readiness audit,
latest upstream completion records, verification results, and ordered pending
work. It is an operational snapshot; it does not change the current release
payload.

## Production roadmap

The ordered plan for promoting dictionary, activation, image-chain, inter-surah,
commentary, and app-export data is in [`ROADMAP.md`](ROADMAP.md). It
distinguishes upstream work, staged canonical imports, and artifacts that are
not release-ready.

## Rules

1. One current artifact per dataset contract.
2. Earlier releases live in Git history and tags, not parallel version folders.
3. Every released artifact has source provenance and a SHA-256 checksum.
4. No raw experiments or manually edited compiled data.
5. Stable occurrence joins use `qac_ref`, `branch_id`, and `ayah_ref`.
6. Root-level QAC-to-furuq_v4 joins must use `data/bridges/qac-furuq-v4-root-map.sqlite.gz`; `data/bridges/qac-v4.sqlite.gz` is form-level and must not be used as a root identity gateway.
7. Arabic occurrence joins to MASAQ, word analysis, attachments, and explicitly referenced commentary tags use four-part QAC morpheme refs through `data/bridges/qac-masaq.sqlite.gz`; three-part source refs are never QAC aliases.

SQLite and JSONL payloads are compressed. Use `gzip -dk` for `.gz` and
`zstd -dk` for `.zst` files.
