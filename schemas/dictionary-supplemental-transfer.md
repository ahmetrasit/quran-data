# Reviewed supplemental dictionary transfer

The dictionary repository owns `data/supplemental/registry.v1.json`. Each row
owns one `root_...` lexical identity or `headword_...` grammatical identity,
the SHA-256 of its intake JSON, and a review date. The registry is the ID
ledger; no ID range or QAC occurrence target creates a dictionary identity.
The source-name map at `data/supplemental/source-names.v1.json` supplies stable
titles and badge codes for lexicon citations. Grammar and tafsir citations do
not receive lexicon badges.

`scripts/dictionary/sync_turkish_entries.py` reads one committed dictionary
snapshot. It checks the registry, source-name map, every hash-closed intake,
exact QAC selectors and ref-set digests, then the reviewed exports. It copies
source bytes without editing them to `data/dictionary/supplemental/`. It
rejects ID collisions with frozen Furuq roots, Quranic packets, committed
exports, and prior transfer manifests. The frozen Furuq database is unchanged.

Lexical exports come from
`v2/work/entry_creation/<root-id>/tr/export/<root-id>_entry.json` and join the
ordinary `data/dictionary/tr/MANIFEST.json`. Each has
`entryKind: lexical_root`, `root_envelope_id`, `supplementalIntake`, the usual
root profile and branches, and exact `occurrence_evidence`. Its branch Arabic
fields, ordered full typed `citations`, and lexicon-only `sources` badges must
match the reviewed intake. These branches are checked against their intake,
while older branches retain the frozen Furuq evidence check and its four
historical Arabic update records.

Grammatical exports come from
`v2/work/entry_creation/headwords/<headword-id>/tr/export/<headword-id>_entry.json`.
They transfer to `data/dictionary/tr/headwords/` with a separate `MANIFEST.json`
containing source commit, entry paths and SHA-256 hashes, corpus hash, and the
supplemental registry/source-name map hashes. An export has
`entryKind: grammatical_headword`, `headwordId`, Arabic headword, exact selector
binding, headword profile, senses, typed citations, and `occurrenceEvidence`.
It has no root identity. Its exact word/lemma selector remains within the
export; no headword binding bridge is authored.

An export's `supplementalIntake.registrySha256` cites the registry at its
review. A later unrelated registry append need not reseal that export. The
current selected registry row must still own the same ID, kind, intake path,
and exact intake SHA-256; the current registry digest is pinned separately in
both transfer manifests. Changing the selected intake invalidates its export.

Both manifests hash their ordered entries as the UTF-8 concatenation of
`<sha256>  <path>\n` lines. Headword rows are sorted by path. Every exported
QAC occurrence, form, ayah, and summary is independently rebuilt from the
committed morphology rows and must match exactly, preserving raw QAC root and
POS. Source quotations and derived Arabic source phrases must also match the
reviewed intake byte for byte. `sourceSnapshot` in an intake and in existing
word analyses remains historical review provenance; it is not compared with
unrelated current artifact hashes.

Only supplemental lexical roots enter
`qac-dictionary-root-resolutions.json` as `exact_root` when their Arabic
identity equals the QAC root. A headword does not change that root-wide map;
its exact selector can cover a word while the global QAC root remains
`unresolved_identity`. The separate namespace prevents cached clients from
mistaking a grammatical headword for a root ID.
