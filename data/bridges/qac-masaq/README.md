# QAC / MASAQ / Word-Analysis Bridge

This directory owns the reviewed inputs for
`data/bridges/qac-masaq.sqlite.gz`. The SQLite artifact makes the four-part QAC
morpheme reference (`S:A:W:M`) the canonical Arabic occurrence key. Grammar
units, MASAQ segments, released word-analysis records, and attachment aliases
retain separate typed identities and connect to QAC through explicit edges.

## Consumer Entry Points

- Use `qac_links` for a uniform inverse or forward lookup across the
  `grammar-unit`, `masaq-segment`, `word-analysis`, and `attachment-endpoint`
  namespaces.
- Use `accepted_masaq_qac_edges` for direct MASAQ-to-QAC spans and
  `analysis_qac_edges` for released word-analysis-to-QAC spans.
- Use `attachment_qac_edges`, not the generic unit projection, when attachment
  occurrence, endpoint role, part, carrier rule, or review provenance matters.
- Use `excluded_attachment_endpoints` and `word_analysis_units.relation_status`
  when auditing complete accepted-plus-excluded source accounting.

For example, a canonical QAC unit can be resolved to every linked source unit
without assuming one-to-one cardinality:

```sql
SELECT source_namespace, source_ref, link_group_id, target_order
FROM qac_links
WHERE qac_morpheme_ref = ?
ORDER BY source_namespace, source_ref, target_order;
```

Consumers must verify the artifact checksum, `PRAGMA user_version = 4`, and the
release metadata before querying it. See `schemas/qac-masaq.md` for the complete
table/view contract and `data/bridges/qac-masaq-audit.json` for release counts.
Surface-only commentary tags are intentionally not mapped by this artifact.

## Inputs

- `source-units.tsv.gz` is a deterministic projection of the pinned Quran Roots
  frozen corpus recorded in `SOURCE.json`.
- `reviewed-trace-decisions.tsv` repairs the legacy grammar-to-MASAQ trace. It
  promotes the formerly dropped source segments, accepts two reviewed surface
  variants, and quarantines the duplicated `17:28:12` analysis record.
- `reviewed-decisions.tsv` adjudicates ambiguous or weak grammar-to-QAC spans.
- `reviewed-masaq-qac-decisions.tsv` resolves compound grammar spans to exact
  MASAQ/QAC segment edges instead of emitting a Cartesian product.
- `reviewed-attachment-decisions.tsv` redirects the two attachment unit refs
  affected by the quarantined upstream duplicate and excludes one attachment
  record whose claimed Arabic word does not occur in its cited ayah. It also
  approves the ten occurrence-specific carriers where attachment morphology is
  fused or elided in QAC.
- QAC and word-analysis inputs come from this quran-data repository. Consumers
  must not read `study` or `word_analysis` as an alternative production source.
- The promoted `data/grammar/attachments/attachments.tsv` file is validated in
  full. Every accepted endpoint occurrence has one or more exact QAC edges;
  reviewed source defects remain explicitly accounted for as exclusions.

Generated files are not hand-edited. Rebuild and verify from the repository
root:

```sh
python3 scripts/bridges/import_qac_masaq_source.py
python3 scripts/bridges/build_qac_masaq_bridge.py --write
python3 scripts/bridges/import_qac_masaq_source.py --check
python3 scripts/bridges/build_qac_masaq_bridge.py --check
python3 -m unittest tests.test_qac_masaq_bridge
```

The bridge intentionally does not force every QAC morpheme to have a MASAQ or
analysis counterpart. QAC-only morphology is retained with
`link_status = 'no-source-unit'`. Conversely, every accepted word-analysis
record has at least one explicit QAC edge. The source duplicate `17:28:12` is
retained with `relation_status = 'excluded-source-defect'` and is absent from
all grammar and word-analysis public link views. Its attachment use as the
preposition in `lahum`, and the adjacent pronoun endpoint carried by the repaired
compound row, are preserved through reviewed MASAQ-namespace redirects. The
invalid 4:7 attachment is retained only in the reviewed exclusion ledger and
`excluded_attachment_endpoints`; it never appears in the public QAC edge view.
