# V4 Positive Handles Schema

Status: draft implementation contract.

V4 owns dictionary-level positive handles. These handles are the stable sides
for Furūq, graph nodes, activation candidates, commentary, rendering, and
dictionary examples.

V4 does not own occurrence rows or occurrence activation.

## Handle Namespaces

Required handle forms:

```text
v4:root:{root_id}
v4:branch:{root_id}:{branch_id}
v4:form:{form_key}
v4:lu:{root_id}:{lexical_unit_id}
v4:collocation:{root_id}:{lexical_unit_id}
v4:construction:{construction_id}
```

Construction handles are reserved until governed construction/frame rows exist.

For `v4:form:{form_key}`, agents should prefer the stored
`corpus_forms.form_key` value from V4. If derivation is unavoidable, derive it
exactly as the builder does:

```text
form_key = root_norm || "||" || quran_stem_ar || "||" || quran_tag
```

where `root_norm` is the space-separated normalized Arabic root,
`quran_stem_ar` is the normalized Quranic stem, and `quran_tag` is the
morphological form tag exposed as `morphological_form_tag` in V4 identity views.
Do not invent a delimiter, transliterate, or derive form keys from English
glosses.

Because `quran_tag` values may contain colons, consumers must parse
`v4:form:{form_key}` by splitting only the namespace prefix (`v4`, `form`) and
treating the rest of the handle as the opaque `form_key`.

## Tables

### `positive_handles`

Required fields:

- `handle` primary key;
- `handle_type`: `root`, `branch`, `form`, `lexical_unit`, `collocation`,
  `construction`;
- `source_table`;
- `source_pk`;
- `root_id`;
- `root_norm`;
- `branch_id`;
- `lexical_unit_id`;
- `form_key`;
- `expression_ar`;
- `morphological_form_tag`;
- `status`: `active`, `needs_review`, `deprecated`, `blocked`;
- `review_status`;
- `created_run_id`;
- `source_checksum`;

### `positive_handle_aliases`

Search keys and continuity keys for lookup.

Required fields:

- `alias_id` primary key;
- `handle`;
- `alias_type`: `root_norm`, `root_join_key`, `quran_stem_ar`,
  `morphological_form_tag`, `form_key`, `source_ref`;
- `alias_value`;
- `source`;
- `confidence`;
- `review_status`.

### `positive_handle_validation_links`

Links to branch-map, grounded-senses, or other validation material.

Required fields:

- `link_id` primary key;
- `handle`;
- `validation_source`;
- `validation_source_key`;
- `relation`: `supports`, `challenges`, `continuity`, `coverage_only`,
  `frame_hint`;
- `evidence_note`;
- `review_status`.

### `positive_handle_conflicts`

Required fields:

- `conflict_id` primary key;
- `handle_a`;
- `handle_b`;
- `conflict_type`: `duplicate`, `root_normalization`, `branch_split`,
  `branch_merge`, `form_ambiguity`, `missing_pass3`;
- `severity`;
- `status`;
- `resolution_note`;

## Lookup Contract

Activation agents should search V4 through:

```text
qac_ref -> qac root_join_key / lemma / POS / measure -> positive_handle_aliases -> positive_handles
```

`root_join_key` is the unspaced `strip_spaces(fold_hamza(root_norm))` value
shared with QAC. Keep the spaced `root_norm` only for display and audit.

The QAC seed is not authoritative by itself. The final activation record must
name governed V4 handles or explicitly record that no governed handle exists.

For positioned form lookup, agents should use the derived QAC-to-V4 bridge in
`_corpus/qac_v4/`. Positive handles expose searchable V4 identities; the bridge
records whether a particular QAC stem morpheme resolves to one usable V4 form
handle or remains ambiguous/unmatched.

## Stop Conditions

Do not promote Furūq or activation candidates if:

- V4 and branch_map are being used as parallel positive authorities;
- a handle cannot be traced to a V4 source row or reserved governed source;
- a QAC occurrence key is used as a V4 positive handle;
- a target-language gloss is used as the positive Arabic sense.
