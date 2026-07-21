# Dataset contracts

- `quran-uthmani.tsv`: `ayah_ref|arabic_text`; `surah:0` records are prefatory
  basmalas and are not part of the canonical 6,236 numbered ayahs.
- SQLite schemas are self-describing. Their source schema notes are included in
  this directory where available.
- Attachment and contextual files retain their source headers unchanged.
- Word-analysis files contain one complete `word-analysis-output-v2` JSON
  object per line, ordered by ayah within each surah.

Canonical join keys are `ayah_ref`, `qac_ref`, `root_id`, and `branch_id`.
