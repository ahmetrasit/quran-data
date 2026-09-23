# QAC to furuq_v4 Root Map Provenance

Copied: 2026-07-28 11:30:00 EDT
Coverage refreshed in quran-data commit `464a991fc` on 2026-07-29.

Source repository: `/Volumes/OZTURK/_projects/latent_activation`
Source commit: `f47613506937b980f2708aed73eca9ef776deb65`

Source artifacts:

- `_status/v12_cross_run/audits/qac-furuq-v4-root-map.sqlite`
- `_status/v12_cross_run/audits/frozen-qac-root-authoritative-map.tsv`
- `_status/v12_cross_run/scripts/build_qac_furuq_root_map_db.py`

Destination artifacts:

- `data/bridges/qac-furuq-v4-root-map.sqlite.gz`
- `data/bridges/qac-furuq-v4-root-map.tsv`
- `scripts/bridges/build_qac_furuq_root_map_db.py`

Purpose:

This is the root-level gateway for QAC root keys and furuq_v4 root ids. Use it
for QAC-root-to-furuq joins and reverse furuq-root-to-QAC joins. Do not use
`data/bridges/qac-v4.sqlite.gz` for root identity resolution; that bridge is
form-level.

Coverage:

- QAC root rows: 1,642
- Target rows: 1,654
- `unique`: 1,455 QAC roots
- `split`: 92 QAC roots
- `no_frozen_rooted_surface_match`: 95 QAC roots
- `qac_to_furuq` view rows: 1,749
- `qac_to_furuq_mapped` view rows: 1,651
- `furuq_to_qac` view rows: 1,651

Unmapped notes:

- `qac_to_furuq` includes all QAC roots and exposes `has_furuq_root` plus
  `unmapped_reason`.
- `qac_to_furuq_mapped` contains mapped targets only.
- Split mappings preserve all targets and mark the dominant target with
  `is_dominant=1`.

Verification:

- Builder compiled with `python3 -m py_compile`.
- The SQLite DB was rebuilt with `SOURCE_DATE_EPOCH=1785252600`.
- All nonblank `furuq_root_id` values validate against `resources/furuq_v4.sqlite`.
- Target occurrence sums match `matched_occurrences`.
- `git diff --check` passed in the source repository after builder changes.

Checksums:

```text
8caeb501326c0d2db7af199d84e9d1508815f225ac994d18197ae3b0a4e3266b  qac-furuq-v4-root-map.sqlite
3c99051a8d9ff0f6d8611b0421ed91525e3457f6f99320591b6a35a9baa61d63  qac-furuq-v4-root-map.sqlite.gz
ed99768f5eb29850339d472bdc2d776957a526eb65ce7c8095ea5448f62be843  qac-furuq-v4-root-map.tsv
d3579d087e9592f814fa44d2ea13427183c23e1a747c6bb9fff84c26615ca537  build_qac_furuq_root_map_db.py
```
