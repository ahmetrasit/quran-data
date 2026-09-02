# Quran Data Inventory

Snapshot date: 2026-09-02

This document maps the major datasets currently present in this repository. `RELEASE.json` and `manifests/` remain authoritative for the formal `2026.09.02` release. Items marked staged still need release metadata, checksums, and any documented exception ledgers before a formal release tag.

## Release Payload: 2026.09.02

| Path | What exists | Status | Notes |
| --- | --- | --- | --- |
| `data/text/` | Quran text tables | Released | Formal release payload. |
| `data/morphology/` | QAC morphology database and indexes | Released | Formal release payload. |
| `data/lexicon/` | V4, positive handles, Furuq lexical data | Released | Formal release payload. |
| `data/bridges/` | QAC-to-V4 bridge and QAC-first MASAQ/word-analysis occurrence bridge | Released | The QAC/MASAQ bridge includes explicit many-to-many edges and reviewed exception ledgers. |
| `data/grammar/attachments/` | Reviewed attachment enrichment `final_v3` | Released | Formal release payload. |
| `data/grammar/contextual/` | Reviewed contextual profiles `final_v3` | Released | Formal release payload. |
| `data/analysis/word-analysis/` | Production word analysis for all 6,236 ayahs | Released | Formal release payload. |
| `schemas/` | Public schema notes for released data | Released support | Schema docs, not a data payload. |
| `manifests/` | Release coverage and provenance manifests | Released metadata | Does not yet include July 27 staged imports. |
| `RELEASE.json` | Release manifest for `2026.07.21` | Released metadata | Does not yet include July 27 staged imports. |
| `CHECKSUMS.sha256` | Release checksums | Released metadata | Needs regeneration before promoting staged imports. |

## Staged Imports: 2026-07-27

| Path | What exists | Source | Coverage | Caveats |
| --- | --- | --- | --- | --- |
| `data/dictionary/tr/` | Turkish dictionary entry JSON files and `SOURCE.md` | `../dictionary`, commit `0e4109772b12fd227f99edd5fa41ef4758002227` | 1,679 entry files | Staged, not in `RELEASE.json`; release metadata/checksums pending. |
| `data/translation/glosses/locales/tr/` | Turkish translation gloss JSON files, provenance, and coverage ledger | `../dictionary/v2/gloss_generation/results/tr/`, commit `0e4109772b12fd227f99edd5fa41ef4758002227` | 1,572 reviewed gloss files | 107 Turkish dictionary entry envelopes have no copied gloss result; see `COVERAGE.md`. |
| `data/analysis/ayah-activation/v12-tr/` | V12 Turkish publication support by surah, branch inventories, full-context control/readings, and selected focus runs | `../latent_activation`, commit `f47613506937b980f2708aed73eca9ef776deb65` | 114 surahs; 114 `full_context_packet.json`; 114 `full_context_control/` dirs with 178 files; 6 focus dirs | `s103/focus_103_1/pilot_invalid_prompt_leak/` intentionally excluded. Staged release metadata/checksums pending. |
| `data/analysis/ayah-activation/v12-tr-11ayah/` | V12 Turkish plus/minus-5 reader walks and frozen run metadata | `../latent_activation/v12/runs_11ayah/`, commit `f47613506937b980f2708aed73eca9ef776deb65` | 114 surahs; 114 reader-walk files; 114 `frozen_run.json` files; 232 files total | Staged separately from regular `v12-tr/` so consumers can distinguish wider-window reader evidence. |
| `data/analysis/ayah-activation/v12-cross-run/tr/` | Compact final Turkish cross-run publication findings | `../latent_activation/_status/v12_cross_run/output/tr/`, commit `f47613506937b980f2708aed73eca9ef776deb65` | 114 `*_ayah_findings_publication.json` files | Final publication rows derived upstream from regular and plus/minus-5 V12 reader families; release metadata/checksums pending. |
| `data/analysis/channels/network-v3/` | Network v3 generated channel outputs, path families, review files, and pericopes | `../latent_activation`, commit `f47613506937b980f2708aed73eca9ef776deb65` | 111 eligible generated-output surahs; 110 `review/reader_a_pilot.md` files; 1 pericope JSONL | Generated channel data remains candidate/evaluation material until blind review and adjudication close. The 20 path-family JSONL files that exceeded GitHub blob limits are stored as `.jsonl.gz`; all repository files are now below 100 MB. |
| `data/analysis/inter-ayah/` | Directional focus-ayah 100-card TSV review outputs, provenance, and coverage ledger | Initial copy from `../quran-slm/inter-ayah/outputs/`, commit `9d865a4bba8d74eb7be7694d0559e0ff075946bf`; completed in `quran-data` commit `82f5ca65ce6f664210d68ac27c63ce47221a18eb` | 6,236 of 6,236 focus TSV outputs; 923,267 schema-clean rows | Complete as evaluation records, not promoted semantic truth. |
| `data/analysis/inter-ayah/reciprocal/` | Deterministic reciprocal-expanded per-ayah TSV projection and manifest | Built from the complete directional corpus by `scripts/analysis/build_reciprocal_inter_ayah.py` | 6,236 generated TSV documents; 1,846,572 typed records; exact hashes in `MANIFEST.json` | Mirrored rows are typed as discovery nominations, counterevidence, or self-reiterations, never target-direction judgments. Existing directional disagreements remain visible. |
| `data/bridges/qac-furuq-v4-root-map.sqlite.gz` and `data/bridges/qac-furuq-v4-root-map.tsv` | Root-level QAC-to-furuq_v4 gateway, with bidirectional lookup views | `../latent_activation`, commit `f47613506937b980f2708aed73eca9ef776deb65` | 1,642 QAC roots; 1,647 target rows; 1,448 unique, 92 split, 102 no frozen rooted surface match | Staged, not in `RELEASE.json`; this is the required root identity gateway. Existing `data/bridges/qac-v4.sqlite.gz` remains form-level only. |

## Provenance Files

| Path | Purpose |
| --- | --- |
| `data/dictionary/tr/SOURCE.md` | Turkish dictionary entry copy source, commit, count, and verification. |
| `data/translation/glosses/README.md` | Locale-compatible gloss layout. |
| `data/translation/glosses/locales/tr/SOURCE.md` | Turkish gloss copy source, commit, count, status, and verification. |
| `data/translation/glosses/locales/tr/COVERAGE.md` | Turkish gloss coverage exceptions. |
| `data/analysis/ayah-activation/v12-tr/SOURCE.md` | V12 Turkish activation/publication/support provenance and copied path counts. |
| `data/analysis/ayah-activation/v12-tr-11ayah/SOURCE.md` | V12 plus/minus-5 reader-walk provenance and copied path counts. |
| `data/analysis/ayah-activation/v12-cross-run/SOURCE.md` | V12 cross-run publication provenance and copied file counts. |
| `data/analysis/channels/network-v3/SOURCE.md` | Network v3 generated output, review, and pericope provenance. |
| `data/analysis/inter-ayah/SOURCE.md` | Inter-ayah focus TSV copy provenance and status. |
| `data/analysis/inter-ayah/COVERAGE.md` | Complete directional coverage and reciprocal-projection boundary. |
| `data/analysis/inter-ayah/reciprocal/README.md` | Reciprocal derivation, format, and consumer rules. |
| `data/analysis/inter-ayah/reciprocal/MANIFEST.json` | Deterministic source/output hashes and reciprocal coverage counts. |
| `schemas/inter-ayah-row-reciprocal.md` | Typed directional, reciprocal, self-link, range, and consumer contract. |
| `data/bridges/qac-furuq-v4-root-map-SOURCE.md` | QAC-to-furuq_v4 root gateway provenance, coverage, checksums, and usage boundary. |
| `schemas/qac-furuq-v4-root-map.md` | Root gateway schema and consumer rules. |
| `scripts/bridges/build_qac_furuq_root_map_db.py` | Reproducible builder for `qac-furuq-v4-root-map.sqlite`. |
| `scripts/analysis/build_reciprocal_inter_ayah.py` | Reproducible builder and checker for reciprocal inter-ayah documents. |
| `data/bridges/qac-masaq/README.md` | QAC/MASAQ source promotion, grammar/QAC, segment/QAC, and attachment review ledgers, build commands, and consumption boundary. |
| `schemas/qac-masaq.md` | QAC-first identity model, SQLite tables, accepted views, and cardinality contract. |
| `scripts/bridges/import_qac_masaq_source.py` | Deterministic projection of the pinned source plus reviewed trace corrections. |
| `scripts/bridges/build_qac_masaq_bridge.py` | Deterministic all-Quran graph builder and audit gate. |

## Release Boundary

The staged imports are present in Git history but are not yet a formal quran-data release. Before promoting them, update `RELEASE.json`, `manifests/coverage.json`, `manifests/provenance.json`, and `CHECKSUMS.sha256`, and keep the compressed `.jsonl.gz` replacements for the network-v3 files that would otherwise exceed GitHub's normal 100 MB blob limit.
