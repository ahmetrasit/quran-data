# Reciprocal-expanded inter-ayah documents

This directory is the typed, per-ayah traversal view of the directional
focus-review corpus in the parent directory. It contains one generated TSV for
each of the Quran's 6,236 numbered ayahs plus `MANIFEST.json`.

Use this projection—not a concatenation of it with the parent corpus—when a
consumer needs row-level discovery from either endpoint. Use the parent files
only when their original three-column shape or exact source order is itself the
object of study.

The projection is high-recall review material. It neither accepts a relation
nor forces two directions to have the same meaning, confidence, explanation,
or final judgment.

## Record model

Every file has a header and the typed columns specified in
[`schemas/inter-ayah-row-reciprocal.md`](../../../../schemas/inter-ayah-row-reciprocal.md).
It contains four record types:

- `directional_review` projects an authored source row into the source ayah's
  own document. `focus_direction_label` contains that direction's actual
  review label.
- `reciprocal_nomination` mirrors a source row labelled `strong`, `medium`,
  `weak`, or `contrast` into every target-component ayah's document.
- `reciprocal_counterevidence` mirrors a source row labelled `no value` or
  `reject`. Negative evidence stays visible; it does not disappear merely
  because it does not nominate a positive relation.
- `self_reiteration` conserves the generated twin of an intentional source row
  that points to its own focus ayah. It is not an opposite direction and must
  not be treated as independent corroboration.

For reciprocal records and self-reiterations, `focus_direction_label` is empty.
The inherited label is kept only in `source_direction_label`, beside explicit
source and target provenance. On a genuine reciprocal record it describes what
the other direction's review said and is never a judgment from the receiving
ayah. On a self-reiteration it only traces the conserved source row.

## Derivation and conservation

For every source row and every component of its target reference, the builder
emits exactly:

1. one `directional_review` record in the source ayah's document; and
2. one mirrored record in the target ayah's document—normally a reciprocal
   record, or `self_reiteration` when both endpoints are the same ayah.

This happens even when a reverse row already exists. Distinct rows, labels,
notes, and disagreements therefore remain distinct rather than being collapsed
at the ayah-pair level. Same-surah and cross-surah rows are both mirrored. A
short source range expands to one component record per ayah in both directions,
while `source_target_ref` preserves the exact original range.

The original note remains range-scoped. An expanded component is a discovery
handle, not a claim that every feature described across the range appears in
that ayah. Linguistic consumers must retain this boundary and inspect all range
components before assigning a feature to one component.

`source_note` preserves the source note field exactly after UTF-8 decoding,
including leading or trailing spaces. `source_row_sha256`, source
filename, and source line make every generated record traceable to its exact
three-column row.

`source_row_role` also preserves the source protocol phase: lines 1–100 are
`ranked_review`, while later follow-up additions are
`missing_ayah_suggestion`. Both remain visible. A suggestion is a high-recall
invitation to fresh analysis, not an accepted relation and not a veto.

## Rebuild and verification

From the repository root:

```bash
python3 scripts/analysis/build_reciprocal_inter_ayah.py
python3 scripts/analysis/build_reciprocal_inter_ayah.py --check
```

`MANIFEST.json` records the schema, rules, source and output corpus hashes,
per-document hashes and counts, exact corpus counts, range expansion, and
row-level conservation checks. Do not edit the generated TSVs or manifest
manually.
