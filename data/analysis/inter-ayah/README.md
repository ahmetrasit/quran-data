# Inter-ayah focus-review corpora

This directory contains two related contracts:

- The top-level `focus_*_cutoff_100.tsv` files are the directional review
  record. Preserve them for source-direction judgments and provenance.
- [`reciprocal/`](reciprocal/) is the current typed, reciprocal-expanded
  per-ayah traversal projection. It exposes every directional row and mirrors
  every row—including same-surah links and negative counterevidence—from the
  other endpoint.

The reciprocal projection does not promote a relation to semantic truth. A
generated reverse record is either a discovery nomination or explicit
counterevidence inherited from the opposite direction. It must be reassessed
from the receiving ayah, and its source label is not a receiving-direction
judgment.

## Directional source format

Each completed run belongs at:

```text
focus_<surah>_<ayah>_cutoff_100.tsv
```

The Terra High review agent writes this file directly. It is a plain TSV file
with no header. Every line has exactly three tab-separated fields:

```text
strength<TAB>ayah_ref<TAB>short_explanation
```

The first 100 lines are the reviewed candidates in package rank order. Any
later lines are missing-ayah suggestions appended by that same agent after the
fixed follow-up.

The orchestrator does not write the review. Do not add hashes, model or session
details, prompt transcripts, or orchestration metadata to the file.

These are evaluation records, not promoted semantic ground truth. The
`strength` labels describe marginal usefulness in the given order. Suggested
missing ayat are recall hypotheses and must not be inserted automatically into
source networks or future packages.

The complete directional set currently has one file for each of the 6,236
numbered ayahs. Ten source rows name short ayah ranges, and sixteen legacy rows
put the target before the label. The generated reciprocal projection normalizes
those sixteen rows and expands ranges to component ayahs without modifying this
source record.

## Reciprocal projection

Build or verify the updated documents with:

```bash
python3 scripts/analysis/build_reciprocal_inter_ayah.py
python3 scripts/analysis/build_reciprocal_inter_ayah.py --check
```

See [`reciprocal/README.md`](reciprocal/README.md) for its exact derivation and
consumer boundary, and [`reciprocal/MANIFEST.json`](reciprocal/MANIFEST.json)
for deterministic counts and corpus hashes.
