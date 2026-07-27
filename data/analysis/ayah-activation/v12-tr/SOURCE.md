# Ayah Activation v12-tr Copy Provenance

Copied: 2026-07-27 13:56:18 EDT
Supplemented: 2026-07-27 17:05:41 EDT

Source repository: `/Volumes/OZTURK/_projects/latent_activation`
Source commit: `f47613506937b980f2708aed73eca9ef776deb65`
Destination base: `/Volumes/OZTURK/_projects/quran-data/data/analysis/ayah-activation/v12-tr/s###/`

Initial publication support copy:

- Source base: `_status/v12_cross_run/s###/`
- Copied surahs: 114
- Copied files: 684
- Files copied per surah:
  - `publication.v3.draft.json`
  - `publication_manifest.v3.json`
  - `anchor_map.v3.json`
  - `anchor_occurrences.v3.json`
  - `ayah_roster.v3.json`
  - `linguistic/morphemes.tsv`

Supplemental v12 run copy:

- Source packet pattern: `v12/runs/s###/full_context_packet.json`
- Destination packet pattern: `s###/full_context_packet.json`
- Copied branch inventory packets: 114
- Source control pattern: `v12/runs/s###/full_context_control/`
- Destination control pattern: `s###/full_context_control/`
- Copied full-context control directories: 114
- Copied full-context control files: 178
- Focus run directories copied: 6
  - `s100/focus_100_1/`
  - `s103/focus_103_1/`
  - `s103/focus_103_2/`
  - `s103/focus_103_3/`
  - `s112/focus_112_1/`
  - `s113/focus_113_1/`
- Copied focus-run files: 66
- Excluded path: `s103/focus_103_1/pilot_invalid_prompt_leak/`

Selection rule: copied publication, companion activation data, branch inventories, full-context reader/control artifacts, and the named focus runs needed by downstream ayah-activation workflows. Scripts, prompts, logs, and unrelated interim run-control files were not copied. The known-bad focus prompt-leak run was excluded by name.

Verification on 2026-07-27:

- Destination contained 114 `full_context_packet.json` files.
- Destination contained 114 `full_context_control/` directories with 178 files.
- Destination contained 6 focus directories and 0 `pilot_invalid_prompt_leak` paths.
- Source and destination relative path sets matched for packets, full-context-control files, and included focus files.
