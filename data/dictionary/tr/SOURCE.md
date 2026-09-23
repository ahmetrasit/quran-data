# Turkish Dictionary Entry Copy Provenance

Updated: 2026-09-23 EDT

Source repository: `../dictionary`
Source commit: `7daa18787e4826810d651ea5885aa6487187b95e`

The staged Turkish corpus contains 1,696 reviewed, evidence-enriched writer
outputs: 1,679 Quranic packet envelopes plus `root_003249`, `root_002011`, and `root_002765`, plus 14 independently reviewed Furuq exports produced on
September 23. The first of the three earlier additions is
stored in the dictionary Furuq workflow but is also the exact QAC/Furuq target
for `س ه و` at 51:11 and 107:5.

- Quranic source: `v2/work/entry_creation/<root-envelope>/tr/output/<root-envelope>_entry.json`
- Added QAC target: `v2/work/entry_creation/furuq/root_003249/tr/output/root_003249_entry.json`
- New reviewed Furuq sources: `v2/work/entry_creation/furuq/<root>/tr/export/<root>_entry.json`
- Destination: `data/dictionary/tr/<root-envelope>_entry.json`

This refresh replaced 27 earlier raw writer responses with accepted,
evidence-enriched output. Seven of those accepted artifacts also retain reviewer
corrections that the older raw copy lacked. The remaining 1,652 Quranic files
matched their source bytes and were left unchanged.

Validation: 1,696 files, 11,741 branches, zero missing Arabic source
phrases or source lists. Source corpus SHA-256 (sorted
`<file-sha256>  <filename>\n` rows): `861a9f04c2e9c083bd365743935c97af3766d46625868a81071112b3e166bfe4`.

The independent follow-up audit also found accepted entries for `ت ر ق`
(`root_002011`) and `ذ خ ر` (`root_002765`) in the Furuq workflow. They are
now included. The old packet roster alone was not a complete QAC coverage test.

`MANIFEST.json` records the committed source path and SHA-256 of every copied
entry. `scripts/dictionary/sync_turkish_entries.py --source ../dictionary`
repeats the transfer; add `--check` to check it without writing.

See `data/bridges/ROOT-DICTIONARY-REVIEW.md` for the root identity audit,
withheld observational targets, and remaining entry/identity gaps. These
remain staged writer artifacts, not finalized `dictionary/entries/tr` entries.

The 14-entry production batch added 93 branches. All Agent A outputs received
independent Agent B review (5 pass, 9 recorded surgical repairs), then deterministic
Arabic/QAC enrichment. Zero resolved roots now lack entries; the six unresolved
identities remain explicit. The repository-root session log records editorial
decisions, alternative analyses, and exact source/review provenance.
