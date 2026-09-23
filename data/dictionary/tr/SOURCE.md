# Turkish Dictionary Entry Copy Provenance

Updated: 2026-09-23 EDT

Source repository: `../dictionary`
Source commit: `bf756f5d432bd84cf3ff7581c6d46eebb0e62473`

The staged Turkish corpus contains 1,680 reviewed, evidence-enriched writer
outputs: 1,679 Quranic packet envelopes plus `root_003249`. The latter is
stored in the dictionary Furuq workflow but is also the exact QAC/Furuq target
for `س ه و` at 51:11 and 107:5.

- Quranic source: `v2/work/entry_creation/<root-envelope>/tr/output/<root-envelope>_entry.json`
- Added QAC target: `v2/work/entry_creation/furuq/root_003249/tr/output/root_003249_entry.json`
- Destination: `data/dictionary/tr/<root-envelope>_entry.json`

This refresh replaced 27 earlier raw writer responses with accepted,
evidence-enriched output. Seven of those accepted artifacts also retain reviewer
corrections that the older raw copy lacked. The remaining 1,652 Quranic files
matched their source bytes and were left unchanged.

Validation: 1,680 files, 11,643 branches, zero missing Arabic source
phrases or source lists. Source corpus SHA-256 (sorted
`<file-sha256>  <filename>\n` rows): `ab6c5aff50fdc41b162561477ec8c590d48410b1ad107ee3c57e8df0d19e9645`.

The QAC/Furuq bridge still contains one secondary target without an entry:
`و ذ ر -> root_000525` (`ذ و ر`). It is supported by one matched
occurrence in a split mapping and has no V4 branch image or packet. Its root
identity must be reviewed before an entry can be authored.
