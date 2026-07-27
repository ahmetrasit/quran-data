# Quran Data

Canonical, consumer-facing Quran data releases.

This repository contains accepted datasets and staged canonical imports. Raw
experiments, prompts, packets, reviews, scripts, logs, and intermediary files
remain in their source repositories.

## Current release

`2026.07.21`

Released in `RELEASE.json`:

- Quran text
- QAC morphology and indexes
- V4 dictionary and positive handles
- QAC-to-V4 bridge
- completed Furuq database
- reviewed attachment enrichment `final_v3`
- reviewed contextual profiles `final_v3`
- production word analysis for all 6,236 ayahs

## Staged imports

Copied on 2026-07-27, with per-folder provenance, but not yet folded into a new
`RELEASE.json`, manifest, checksum, and tag set:

- Turkish dictionary entries: `data/dictionary/tr/`, 1,679 entry JSON files
- Turkish translation glosses: `data/translation/glosses/locales/tr/`, 1,572 reviewed gloss JSON files
- Turkish V12 ayah activation/publication support: `data/analysis/ayah-activation/v12-tr/`, 114 surahs plus full-context packets/control directories and 6 focus runs
- Network v3 generated channel outputs and reviews: `data/analysis/channels/network-v3/`, 111 eligible generated-output surahs, 110 review files, and pericopes; still candidate data pending blind review/adjudication
- Inter-ayah focus review TSVs: `data/analysis/inter-ayah/`, 5,604 of 6,236 focus outputs staged; 632 missing and `focus_29_55_cutoff_100.tsv` needs rerun

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
5. Stable joins use `qac_ref`, `root_id`, `branch_id`, and `ayah_ref`.

SQLite and JSONL payloads are compressed. Use `gzip -dk` for `.gz` and
`zstd -dk` for `.zst` files.
