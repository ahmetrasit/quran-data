# Network v3 Channel Output Copy Provenance

Copied: 2026-07-27 13:56:18 EDT
Supplemented: 2026-07-27 17:05:41 EDT

Source repository: `/Volumes/OZTURK/_projects/latent_activation`
Source commit: `f47613506937b980f2708aed73eca9ef776deb65`
Source base: `network/v3/experiments/corpus_neo_adaptive/s###/`
Destination base: `/Volumes/OZTURK/_projects/quran-data/data/analysis/channels/network-v3/s###/`

Generated channel outputs copied:

- Copied eligible surahs: 111
- Excluded by the source workflow: `s103`, `s108`, and `s110`, because those surahs have only three canonical ayahs and cannot satisfy the minimum-span policy documented by `network/v3/README.md`.
- Copied generated output files: 1,443

Files copied per eligible generated-output surah:

- `channel_candidates.jsonl`
- `channel_candidates.tsv`
- `summary.json`
- `families/candidate_graphs.jsonl`
- `families/candidate_similarity_edges.tsv`
- `families/channel_families.jsonl`
- `families/candidate_family_membership.tsv`
- `families/family_branch_inventory.tsv`
- `families/consolidation_summary.json`
- `paths/path_summary.json`
- `paths/path_families/semantic_path_families.jsonl` or `paths/path_families/semantic_path_families.jsonl.gz` for files that would exceed GitHub blob limits
- `paths/path_families/path_similarity_edges.tsv`
- `paths/path_families/path_family_summary.json`

Supplemental review/pericope copy:

- Source review pattern: `network/v3/reviews/s###/reader_a_pilot.md`
- Destination review pattern: `s###/review/reader_a_pilot.md`
- Copied channel review files: 110
- Source pericope path: `network/v3/pericopes/surah_pericopes.jsonl`
- Destination pericope path: `pericopes/surah_pericopes.jsonl`
- Copied pericope files: 1

Selection rule: copied final generated channel-discovery outputs, stage summaries, available first-pass reader reviews, and the pericope ledger. Skipped scripts, prompts, logs, lock files, review queues, review bundles, passage-window helpers, raw sparse path-state files such as `semantic_path_candidates.jsonl`, and rerun or pre-rerun directories.

Verification on 2026-07-27:

- Destination contained 110 `review/reader_a_pilot.md` files.
- Destination pericope checksum matched the source `surah_pericopes.jsonl` checksum.
- Source and destination relative path sets matched for copied review files.
- 20 oversized `semantic_path_families.jsonl` files were stored as `.jsonl.gz` replacements; all compressed replacements are below 100 MB.
