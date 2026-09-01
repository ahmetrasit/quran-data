# Inter-Ayah Focus Review Provenance

## Directional source corpus

Initial copy: 2026-07-27 17:05:41 EDT

Source repository: `/Volumes/OZTURK/_projects/quran-slm`

Source commit: `9d865a4bba8d74eb7be7694d0559e0ff075946bf`

Source path: `inter-ayah/outputs/`
Destination path: `data/analysis/inter-ayah/`

The initial staged import contained 5,604 existing agent-owned files named
`focus_*_cutoff_100.tsv` plus the source output README. Inputs, prompts,
generated dossiers, feature arrays, configs, reports, and orchestration logs
were not copied. The protocol was `focus-ayah-100-card-review-v2`.

The repository-side corpus was subsequently completed and refreshed in
`quran-data` commit `82f5ca65ce6f664210d68ac27c63ce47221a18eb`.
The current verified state is 6,236 focus files—one for every numbered ayah—and
923,267 three-field rows. The earlier malformed `focus_29_55_cutoff_100.tsv`
row is no longer present.

The top-level TSVs remain directional agent-review records. They are evaluation
and recall material, not promoted semantic truth.

## Reciprocal projection

`data/analysis/inter-ayah/reciprocal/` is a deterministic projection built from
the complete directional corpus by
`scripts/analysis/build_reciprocal_inter_ayah.py`.

It projects every directional row, normalizes sixteen legacy rows that place
the target before the label, expands each range to its component ayahs, and
mirrors every source-row/component occurrence into the linked ayah. Meaningful
labels become explicit reciprocal nominations; `no value` and `reject` become
explicit reciprocal counterevidence. Same-surah rows, existing reverse rows,
distinct notes, and disagreements are all retained. The three intentional
self-links receive typed `self_reiteration` twins so they cannot be mistaken
for independent reverse evidence.

`reciprocal/MANIFEST.json` binds the builder, Quran text, directional corpus,
generated corpus, per-document counts, and SHA-256 hashes. The verified output
has 6,236 TSV documents and 1,846,572 typed records; its TSV corpus SHA-256 is
`7e4a7c5ecbd1d74d5a9ffc5d07c329251c128f2d250262e95318d54e45946ca5`.
Reciprocal records leave the receiving-direction label empty and carry the
inherited label only in a typed source-direction field; they are not new
target-direction adjudications.
