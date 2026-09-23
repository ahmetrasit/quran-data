# Turkish Dictionary Entry Copy Provenance

Updated: 2026-09-23 EDT

Source repository: `../dictionary`
Source commit: `bf756f5d432bd84cf3ff7581c6d46eebb0e62473`

The staged Turkish corpus contains 1,682 reviewed, evidence-enriched writer
outputs: 1,679 Quranic packet envelopes plus `root_003249`, `root_002011`, and `root_002765`. The first is
stored in the dictionary Furuq workflow but is also the exact QAC/Furuq target
for `س ه و` at 51:11 and 107:5.

- Quranic source: `v2/work/entry_creation/<root-envelope>/tr/output/<root-envelope>_entry.json`
- Added QAC target: `v2/work/entry_creation/furuq/root_003249/tr/output/root_003249_entry.json`
- Destination: `data/dictionary/tr/<root-envelope>_entry.json`

This refresh replaced 27 earlier raw writer responses with accepted,
evidence-enriched output. Seven of those accepted artifacts also retain reviewer
corrections that the older raw copy lacked. The remaining 1,652 Quranic files
matched their source bytes and were left unchanged.

Validation: 1,682 files, 11,648 branches, zero missing Arabic source
phrases or source lists. Source corpus SHA-256 (sorted
`<file-sha256>  <filename>\n` rows): `8996fc0615c3f9867564252c8bf942532e4400a938ba297cce0bb413a27727a4`.

The independent follow-up audit also found accepted entries for `ت ر ق`
(`root_002011`) and `ذ خ ر` (`root_002765`) in the Furuq workflow. They are
now included. The old packet roster alone was not a complete QAC coverage test.

`MANIFEST.json` records the committed source path and SHA-256 of every copied
entry. `scripts/dictionary/sync_turkish_entries.py --source ../dictionary`
repeats the transfer; add `--check` to check it without writing.

See `data/bridges/ROOT-DICTIONARY-REVIEW.md` for the root identity audit,
withheld observational targets, and remaining entry/identity gaps. These
remain staged writer artifacts, not finalized `dictionary/entries/tr` entries.
