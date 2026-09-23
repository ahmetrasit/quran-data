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
- Target rows: 1,652
- `unique`: 1,456 QAC roots
- `split`: 91 QAC roots
- `no_frozen_rooted_surface_match`: 95 QAC roots
- `qac_to_furuq` view rows: 1,747
- `qac_to_furuq_mapped` view rows: 1,649
- `furuq_to_qac` view rows: 1,649

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
bfc0420942c659015f1de26de3214b006d9b761f70f6b09445671fc88bbfe3aa  qac-furuq-v4-root-map.sqlite
5a72dc4eb7ac5ac66b681da2982c0078cc9fcc8381d4594db7e5c01e2047a709  qac-furuq-v4-root-map.sqlite.gz
d31925e58a6030a37ce0fe0756caf17b422b4e015f3a7776215367b77e9a4ef1  qac-furuq-v4-root-map.tsv
d3579d087e9592f814fa44d2ea13427183c23e1a747c6bb9fff84c26615ca537  build_qac_furuq_root_map_db.py
```

September 23 review: corrected the transposed وذر occurrence (48:15:8:1)
and the doubled سمم target for سمّوهم (13:33:13:1). Historical occurrence
disagreements remain in this bridge for audit; dictionary consumers must use
`qac-dictionary-root-resolutions.json` for approved root identities. See
`ROOT-DICTIONARY-REVIEW.md`.
