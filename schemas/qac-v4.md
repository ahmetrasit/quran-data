# QAC to V4 Bridge Schema

Status: v0 implementation contract.

This schema describes a derived lookup database. It is not a source morphology
schema, dictionary schema, or activation schema.

## Tables

### `qac_v4_form_bridge`

One row per rooted QAC stem morpheme.

Required fields:

- `bridge_id` primary key;
- `qac_ref`;
- `qac_word_ref`;
- `surah`;
- `ayah`;
- `word_index`;
- `morpheme_index`;
- `root_join_key`;
- `qac_root_ar`;
- `qac_stem_ar`;
- `qac_lemma_ar`;
- `qac_pos`;
- `qac_measure`;
- `qac_aspect`;
- `qac_voice`;
- `stem_norm_keys`;
- `lemma_norm_keys`;
- `match_status`: `unique`, `ambiguous`, `unmatched`, `no_v4_forms`;
- `match_basis`;
- `selected_v4_form_handle`;
- `selected_v4_form_key`;
- `selected_v4_morphological_form_tag`;
- `candidate_count`;
- `top_candidate_count`;
- `downstream_usable`;
- `confidence`: `high`, `medium`, `low`, `none`;
- `review_status`;
- `ambiguity_reason`;
- `source_run_id`;
- `schema_version`.

### `qac_v4_form_candidates`

Candidate V4 form handles for each bridge row.

Required fields:

- `candidate_id` primary key;
- `bridge_id`;
- `qac_ref`;
- `v4_form_handle`;
- `v4_form_key`;
- `v4_root_norm`;
- `v4_quran_stem_ar`;
- `v4_morphological_form_tag`;
- `match_basis`;
- `matched_key`;
- `tag_compatibility`: `compatible`, `unknown`, `incompatible`;
- `score`;
- `rank`;
- `selection_status`: `selected`, `top_ambiguous`, `candidate`;
- `review_status`.

### `qac_v4_normalization_variants`

Audit table for the normalized QAC keys used during matching.

Required fields:

- `variant_id` primary key;
- `qac_ref`;
- `variant_source`: `stem`, `lemma`;
- `normalization_method`;
- `normalized_value`.

### `build_metadata`

Required fields:

- `key` primary key;
- `value`.

## Matching Contract

The builder must:

1. Read QAC rows from `qac_morphemes`.
2. Restrict bridge rows to rooted `STEM` morphemes.
3. Read governed V4 form handles from `positive_handles`.
4. Enrich V4 form handles with V4 `corpus_forms` metadata where available.
5. Match only inside the same `root_join_key`.
6. Normalize Quranic vocalization and orthographic marks into explicit variants.
7. Preserve all candidates and never hide ambiguity.
8. Select a form handle only when the top candidate is unique.

Recommended match basis priority:

```text
stem_to_v4_sample_surface
stem_to_v4_stem
lemma_to_v4_sample_surface
lemma_to_v4_stem
```

V4 `sample_surfaces` may be used only as form-identity evidence. They do not
license occurrence senses and do not replace QAC as the occurrence source.

## Downstream Rule

Activation may consume form handles from this bridge only when:

```text
match_status = unique
AND downstream_usable = 1
```

`downstream_usable=1` additionally requires an active V4 form handle,
tag-compatible QAC/V4 morphology, one selected top candidate, and stem-based
match evidence. Lemma-only matches and unknown/incompatible tag matches must
remain review candidates, not activation-ready form mappings.

Ambiguous and unmatched rows are still valuable: they preserve the exact
failure mode that a review agent or future bridge improvement must resolve.

## Audit Requirement

Every build must be followed by `_corpus/qac_v4/scripts/audit_qac_v4_bridge.py`.
The audit must cover both QAC completeness and QAC-to-V4 mapping coverage before
the bridge is used by activation agents.
