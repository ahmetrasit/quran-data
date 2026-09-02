# QAC / MASAQ / Word-Analysis Bridge

Artifact: `data/bridges/qac-masaq.sqlite.gz`

Schema version: `qac-masaq-bridge-v1` (SQLite `user_version = 4`)

## Identity Model

- `qac_morpheme_ref` (`S:A:W:M`) is the canonical Arabic occurrence identity.
- `qac_word_ref` (`S:A:W`) is only the parent grouping of QAC morphemes.
- `grammar_ref`, `analysis_ref`, and `masaq_segment_ref` (`S:A:N`) are typed
  source identities. Equal-looking numbers do not imply equal identity.
- Cardinality is many-to-many. A source unit may span several QAC morphemes,
  and one QAC morpheme may anchor several source units.

## Core Tables

`qac_morphemes` contains all canonical QAC units. `link_status` is `linked` or
`no-source-unit`; absence of a source link is valid and must not be filled by
position.

`grammar_units`, `word_analysis_units`, and `masaq_segments` preserve source
identity and source metadata. `word_analysis_units.relation_status` is either
`accepted` or `excluded-source-defect`.

`grammar_qac_edges`, `analysis_grammar_edges`, and `grammar_masaq_edges` retain
the direct evidence-bearing relations. `masaq_qac_paths` materializes the
grammar-mediated MASAQ-to-QAC paths without collapsing distinct grammar paths.
Compound grammar units are not expanded as a Cartesian product: their exact
segment spans are recorded in `reviewed_masaq_qac_decisions`.

`reviewed_decisions` records manual grammar-to-QAC adjudications. Reviewed
grammar-to-MASAQ corrections remain in the source ledger and are identified by
`trace_status = 'reviewed-alignment'`. `reviewed_attachment_decisions` records
namespace redirects, occurrence-level source-defect exclusions, and explicit
approvals for fused or elided QAC carriers.
`attachment_unit_resolutions` accounts for every distinct legacy unit ref in
the promoted `attachments.tsv` corpus. `attachment_endpoint_qac_edges` carries
accepted occurrence-and-role-specific links; `excluded_attachment_endpoints`
keeps quarantined occurrences explicit and ties each one to its review.

Attachment `dep_part`, `head_part`, and preposition metadata select the exact
QAC morpheme within a resolved source span. Explicit QAC pronoun/relative,
preposition, and particle morphemes are preferred. When QAC represents elided
or fused morphology, the edge names the lexical carrier with a typed
`alignment_rule` and `alignment_reviewed_decision_id`; the builder rejects an
endpoint if no valid carrier or matching reviewed approval exists. Carrier
approvals pin the expected four-part QAC target and fail on target drift.

## Consumer Views

- `analysis_qac_edges`: accepted word analysis to QAC morphemes.
- `analysis_masaq_edges`: accepted word analysis to MASAQ segments, including
  trace evidence and group order.
- `accepted_masaq_qac_edges`: accepted MASAQ segment to QAC morphemes, with
  contiguous `target_order` per segment.
- `accepted_grammar_qac_edges`: valid grammar units to QAC morphemes.
- `qac_links`: uniform typed links for `grammar-unit`, `word-analysis`,
  `masaq-segment`, and accepted `attachment-endpoint` namespaces. Attachment
  source refs use `attachment_id#endpoint_role`; use the detailed attachment
  view when role, part, or review provenance is needed.
- `attachment_unit_qac_edges`: exposes the generic unit-level resolution for
  callers that do not have an attachment occurrence and endpoint role.
- `attachment_qac_edges`: maps each accepted attachment occurrence and endpoint
  role through an explicit grammar or MASAQ resolution to exact QAC morphemes.
- `qac_analysis_groups`: derives QAC word grouping while retaining individual
  QAC morpheme and analysis identities.

Consumers must use the accepted views rather than infer joins from source
position, `critical_w`, or the legacy `aligned_qac_word_ref` field.
`masaq_segments.full_surface_ar` is word context and must not be interpreted as
the extent of an individual segment; use the reviewed path edges instead.
