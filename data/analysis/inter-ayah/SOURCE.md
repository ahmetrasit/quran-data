# Inter-Ayah Focus Review Copy Provenance

Copied: 2026-07-27 17:05:41 EDT

Source repository: `/Volumes/OZTURK/_projects/quran-slm`
Source commit: `9d865a4bba8d74eb7be7694d0559e0ff075946bf`
Source path: `inter-ayah/outputs/`
Destination path: `/Volumes/OZTURK/_projects/quran-data/data/analysis/inter-ayah/`

Copied files: 5,604 focus-ayah TSV review outputs plus the source output README.
Protocol: `focus-ayah-100-card-review-v2`.

Selection rule: copied only existing agent-owned review output files named `focus_*_cutoff_100.tsv` and the output README. Inputs, prompts, generated dossiers, feature arrays, configs, reports, and scripts were not copied.

Status note:

- This is a partial staged import, not a complete formal release corpus.
- 6,236 focus input dossiers exist upstream.
- 5,604 focus TSV outputs existed at final sync time.
- 632 focus outputs are still missing; see `COVERAGE.md`.
- One copied TSV has a known malformed row that the user plans to rerun: `focus_29_55_cutoff_100.tsv:101` has 2 tab-separated fields instead of the expected 3.

Verification on 2026-07-27:

- Destination contained 5,604 `focus_*_cutoff_100.tsv` files after final sync.
- Source and destination SHA-256 checksums matched after normalizing paths.
