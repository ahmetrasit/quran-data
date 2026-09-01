# Inter-Ayah Focus Review Coverage

Verified: 2026-08-31

## Directional corpus

- Expected numbered-ayah documents: 6,236.
- Present `focus_*_cutoff_100.tsv` documents: 6,236.
- Missing documents: 0.
- Rows: 923,267.
- Rows with exactly three tab-separated fields: 923,267.
- Legacy target-first rows: 16. They remain valid directional source records
  and are normalized in the reciprocal projection.
- Short range-target rows: 10. They remain ranges in the source documents.
- The formerly malformed `focus_29_55_cutoff_100.tsv` row has been replaced by
  a schema-clean row.

The directional corpus is complete as a review-output collection. Completeness
does not promote any row to accepted semantic truth.

## Reciprocal projection

The updated per-ayah documents live under [`reciprocal/`](reciprocal/).
[`reciprocal/MANIFEST.json`](reciprocal/MANIFEST.json) is the authoritative
coverage record for row counts, source/output hashes, range expansion, and the
directional/mirrored conservation checks.

Verified generated state:

- Per-ayah TSV documents: 6,236.
- Source-row/target-component occurrences: 923,286.
- `directional_review` records: 923,286.
- Mirrored records: 923,286, comprising 782,282
  `reciprocal_nomination`, 141,001 `reciprocal_counterevidence`, and 3
  `self_reiteration` records.
- Total typed records: 1,846,572.
- Same-surah components: 123,319; cross-surah components: 799,967.
- Ranked-review source rows: 623,600; follow-up missing-ayah suggestions:
  299,667.
- Output TSV corpus SHA-256:
  `7e4a7c5ecbd1d74d5a9ffc5d07c329251c128f2d250262e95318d54e45946ca5`.
- Builder `--check`: passed on 2026-08-31.

Every source-row/target-component occurrence is mirrored, across both same- and
cross-surah scopes. Meaningful labels become discovery nominations; `no value`
and `reject` remain visible as reciprocal counterevidence. Neither form forces
symmetry of interpretation, confidence, explanation, or acceptance. The three
intentional self-links have typed `self_reiteration` twins, which conserve the
rows without pretending that a second direction exists.
