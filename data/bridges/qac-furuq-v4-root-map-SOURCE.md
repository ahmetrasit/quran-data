# QAC to furuq_v4 Root Map Provenance

Copied: 2026-07-28 11:30:00 EDT

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
- Target rows: 1,647
- `unique`: 1,448 QAC roots
- `split`: 92 QAC roots
- `no_frozen_rooted_surface_match`: 102 QAC roots
- `qac_to_furuq` view rows: 1,749
- `qac_to_furuq_mapped` view rows: 1,644
- `furuq_to_qac` view rows: 1,644

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
319f5e563e9095c17a84cee1f0b235582ee92db67dcf4aa90b300ca0ffdf77e9  qac-furuq-v4-root-map.sqlite
415d0f14f3f1d6b49fd2fd574d24495090ece1af3f01210998b0bc1eb7b11296  qac-furuq-v4-root-map.sqlite.gz
847c18c635c372a7513b1115de979d91eeededb81101cd97e400d414461e289d  qac-furuq-v4-root-map.tsv
d3579d087e9592f814fa44d2ea13427183c23e1a747c6bb9fff84c26615ca537  build_qac_furuq_root_map_db.py
```
