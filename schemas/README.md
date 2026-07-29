# Dataset contracts

Root-level QAC-to-furuq_v4 joins must use
`data/bridges/qac-furuq-v4-root-map.sqlite.gz`; see
`schemas/qac-furuq-v4-root-map.md`. The older `qac-v4` bridge is form-level and
must not be used for root identity resolution.

- `quran-uthmani.tsv`: `ayah_ref|arabic_text`; `surah:0` records are prefatory
  basmalas and are not part of the canonical 6,236 numbered ayahs.
- SQLite schemas are self-describing. Their source schema notes are included in
  this directory where available.
- Attachment and contextual files retain their source headers unchanged.
- Word-analysis files contain one complete `word-analysis-output-v2` JSON
  object per line, ordered by ayah within each surah.

Canonical occurrence join keys are `ayah_ref`, `qac_ref`, and `branch_id`.
Canonical root-level QAC/furuq_v4 joins go through the QAC-to-furuq_v4 root
gateway, not through raw root string equality.
