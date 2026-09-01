# Inter-ayah row-reciprocal TSV v2

Schema ID: `inter-ayah-row-reciprocal-tsv-v2`

The generated files under `data/analysis/inter-ayah/reciprocal/` are a typed,
high-recall traversal projection of the directional three-column review corpus.
Each file is UTF-8 TSV with one header row and fifteen columns in this order:

| Column | Contract |
| --- | --- |
| `record_type` | `directional_review`, `reciprocal_nomination`, `reciprocal_counterevidence`, or `self_reiteration`. |
| `focus_ref` | The single ayah whose generated document contains the record. |
| `target_ref` | The single linked ayah exposed to that focus document. |
| `focus_direction_label` | Original review label for `directional_review`; empty for reciprocal records. |
| `source_direction_label` | Original source-row label in `{strong, medium, weak, no value, contrast, reject}`. It is not a receiving-direction judgment. |
| `source_focus_ref` | Focus ayah of the original directional file. |
| `source_target_ref` | Exact target token in the source row, including an unexpanded range when present. |
| `source_target_component_ref` | Single ayah component represented by this generated record. |
| `relation_scope` | `same_surah` or `cross_surah`. |
| `source_column_order` | `label_target_note` or normalized legacy `target_label_note`. |
| `source_row_role` | `ranked_review` for source lines 1–100; `missing_ayah_suggestion` for the follow-up rows after line 100. |
| `source_note` | Exact third source field, including boundary spaces. |
| `source_file` | Basename of the directional source TSV. |
| `source_line` | One-based source line number. |
| `source_row_sha256` | SHA-256 of the exact UTF-8 source line content, excluding its line terminator. |

## Directionality rules

For a directional source row `A -> B`:

- the `directional_review` record lives in A's document, has `focus_ref=A`,
  `target_ref=B`, and carries the label in `focus_direction_label`;
- the reciprocal record lives in B's document, has `focus_ref=B`,
  `target_ref=A`, leaves `focus_direction_label` empty, and keeps the inherited
  label only as `source_direction_label`;
- labels `strong`, `medium`, `weak`, and `contrast` create
  `reciprocal_nomination`; labels `no value` and `reject` create
  `reciprocal_counterevidence`;
- an existing `B -> A` source row never suppresses the reciprocal record for
  `A -> B` and never changes its provenance or label.

When A and B are the same ayah, the conserved mirror is instead typed
`self_reiteration`. It is not an opposite direction and must not be counted or
presented as reciprocal corroboration. The `directional_review` row remains the
authoritative visible self-citation.

The reciprocal record is evidence that the linked ayah was reviewed in the
source direction. It is a prompt for fresh receiving-side analysis, not a
synthetic reverse verdict.

`source_row_role` preserves the source protocol's two phases. A ranked-review
row and a follow-up missing-ayah suggestion are both review evidence. A
suggestion deliberately expands recall, but is not pre-accepted; its phase and
label likewise cannot veto a fresh receiving-side reading.

## Range and conservation rules

Every target range is expanded into its valid numbered-ayah components. Each
source-row/component occurrence produces exactly one directional and one
mirrored record. Same-surah, cross-surah, self, positive, contrastive, negative,
duplicate, and disagreeing rows all remain visible.

`source_target_ref` remains the scope of the original note. A consumer exposing
one `source_target_component_ref` must retain the full range boundary: the note
nominates contact through a range containing that component and does not imply
that every range-level feature occurs in each constituent ayah. Linguistic
consumers should supply all component texts before assessing a range note.

The generated corpus replaces the parent corpus as the traversal view. A
consumer must not concatenate both, because every parent row is already
represented by a `directional_review` record.

`data/analysis/inter-ayah/reciprocal/MANIFEST.json` binds this contract to the
builder, input corpus, Quran ayah inventory, generated hashes, and exact
conservation counts. Its `documents` object binds every generated filename to
its SHA-256, total record count, directional count, and mirrored count.
