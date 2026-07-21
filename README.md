# Quran Data

Canonical, consumer-facing Quran data releases.

This repository contains only accepted datasets. Experimental runs, prompts,
packets, reviews, and intermediary files remain in their source repositories.

## Current release

`2026.07.21`

- Quran text
- QAC morphology and indexes
- V4 dictionary and positive handles
- QAC-to-V4 bridge
- completed Furuq database
- reviewed attachment enrichment `final_v3`
- reviewed contextual profiles `final_v3`
- production word analysis for all 6,236 ayahs

Activation, network synthesis, commentary, and encyclopedia entries will be
added only after their canonical output contracts are complete.

See `RELEASE.json` for contents and `manifests/` for coverage and provenance.

## Production roadmap

The current release is complete and unchanged. The ordered plan for promoting
dictionary, activation, image-chain, inter-surah, and commentary data is in
[`ROADMAP.md`](ROADMAP.md). It distinguishes upstream work from artifacts that
belong in this final-only repository.

## Rules

1. One current artifact per dataset contract.
2. Earlier releases live in Git history and tags, not parallel version folders.
3. Every artifact has source provenance and a SHA-256 checksum.
4. No raw experiments or manually edited compiled data.
5. Stable joins use `qac_ref`, `root_id`, `branch_id`, and `ayah_ref`.

SQLite and JSONL payloads are compressed. Use `gzip -dk` for `.gz` and
`zstd -dk` for `.zst` files.
