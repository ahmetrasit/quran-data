# Root dictionary review — 2026-09-23

**Later session update:** all 14 missing Turkish entries were independently
reviewed and transferred. The current corpus contains 1,696 entries and 11,741
branches, with zero missing resolved entries. Six identities remain deliberately
unresolved after source adjudication; see the repository-root
`ROOT-DICTIONARY-REPAIR-2026-09-23.md`. The diagnosis below records the initial
audit before that production batch.

The September entry repair was correct but did not close the mapping issue.
All 1,682 transferred entries match their committed dictionary writer outputs.
All 11,648 branch images, Arabic inclusion/exclusion boundaries, and source
phrases match the frozen Furuq branch registry. The transfer manifest now
detects removed files, changed bytes, and incomplete/raw entry regressions.

The dictionary's frozen Furuq snapshot is newer than quran-data's released
lexicon. Four consumed branches differ: `root_000086/B011`, `B012`, `B014`
and `root_001697/B002`. `../dictionary/tr/ARABIC-EVIDENCE-UPDATES.json`
preserves both versions and exact source snapshot hashes. The audit applies
these explicit updates when checking against the released lexicon. The
released database itself remains immutable; its root identities are identical.

## Why unrelated roots appeared

The historical bridge aggregates frozen/MASAQ occurrence matches. A root
disagreement for one word therefore became a candidate for every word sharing
the QAC root. These are observations, not adjudicated root equivalences.
The problem affects unique mappings as well as split mappings.

- `13:33:13:1`, `سَمُّوهُمْ`, QAC lemma `سَمَّىٰ`: one frozen row assigned
  `س م م / root_000743`. Furuq `root_000745/B005` explicitly contains naming
  and `سميت فلانا زيدا`. The occurrence belongs to `س م و`; the bridge count
  moves from the unrelated سمم target to سمو without changing matched totals.
- `48:15:8:1`, `ذَرُونَا`, QAC lemma `يَذَرَ`: the frozen word is numbered
  `48:15:9` and transposes the root to `ذ و ر / root_000525`. Furuq
  `root_001638/B003` explicitly contains `ذره أي دعه وهو يذره`. Its five
  dictionary sources support وذر. The stray target's sole dictionary route
  is to ذرو, with no branch images. Move this one matched occurrence to
  `root_001638`; no new ذور entry should be authored to accommodate it.
- Other observed disagreements include `ق و ل -> ق ل ل` (قل),
  `ء ك ل -> ك ل ل` (كل), `د ع و -> د ع ع`, and `و ج د -> ج د د`.
  They are no longer automatically published as dictionary identities.

The original occurrence evidence is in the latent_activation source snapshot
`f47613506937b980f2708aed73eca9ef776deb65`, under
`_status/v12_cross_run/audits/frozen-qac-root-bridge-occurrences.tsv`.
The dictionary source commit is recorded in `../dictionary/tr/MANIFEST.json`.

## Dictionary resolution policy

`qac-dictionary-root-resolutions.json` covers all 1,642 QAC roots:

- 1,629 use exact Arabic root identity, preserving composite registry roots.
- 7 use reviewed aliases with exact branch-evidence hashes in
  `qac-dictionary-reviewed-aliases.json` (including ناس -> ءنس).
- 6 have no reviewed identity: ءدد, ثبي, سنه, قضض, كيف, لوت.
- 14 resolved roots still lack Turkish entries. Their exact IDs are listed
  in `missingEntryRootIds`; they must not fall back to unrelated entries.
- 116 observational targets are withheld from automatic dictionary lookup.
  This is a conservative publication policy, not a claim that every withheld
  historical/etymological alternative is linguistically impossible.

اسم resolves to سمو. The observed وسم alternative is retained for research,
but the supplied branch evidence for وسم describes a physical identifying
mark; it does not authorize making it a primary dictionary identity for
every سمو word (including سماء). سمم remains available for its own QAC root.

These explicit gaps supersede the earlier two-item missing-target diagnosis.
The frozen lexicon's wider root classification and the remaining missing
entry authoring require separate editorial work; this audit does not mark
them as resolved or fabricate source material.

## Repeatable checks

Decompress the committed `data/lexicon/furuq.sqlite.zst` into a temporary file.
Then run, using that file as `<furuq.sqlite>`:

```sh
python3 scripts/bridges/build_dictionary_root_resolutions.py --furuq-db <furuq.sqlite>
python3 scripts/dictionary/sync_turkish_entries.py --source ../dictionary
python3 scripts/bridges/build_dictionary_root_resolutions.py --furuq-db <furuq.sqlite>
python3 scripts/dictionary/check_turkish_entries.py
python3 scripts/dictionary/audit_root_dictionary.py --furuq-db <furuq.sqlite>
python3 scripts/dictionary/sync_turkish_entries.py --source ../dictionary --check
python3 -m unittest discover -s tests -p test_turkish_dictionary.py
```

The second resolution build refreshes entry availability after transfer.
Use `--check` with the resolution builder to detect a stale generated map.

## Supplemental intake checkpoint — 2026-09-24

The source repository now has a separate reviewed supplemental intake path for
the four missing lexical roots and two grammatical headwords. Transfer and
resolution scripts read the committed source registry and exact exports; no
frozen Furuq row or occurrence-derived alias is modified. The copied registry
and intakes remain hash-closed. Supplemental root Arabic evidence is checked
against those intakes, while older branch evidence continues to be checked
against frozen Furuq and its explicit historical updates. The grammatical
headwords live in a separate manifest and do not become root resolutions.

The counts above describe the accepted pre-supplement corpus. After the six
entries pass their independent review and committed transfer, rerun the listed
checks and record the resulting counts and source commit here. The four exact
lexical identities may then replace their unresolved root-map rows; كيف and
لوت remain unresolved at root level while their exact grammatical selectors
can cover their respective words.

## Reviewed six-entry transfer — 2026-09-24

Dictionary commit `e553f0afe23f32c422561bcd3ee7e65f0b503b2b` supplied
four lexical entries (`root_900001`–`root_900004`) and two grammatical
headwords (`headword_000001`–`headword_000002`). The committed sync copied
the registry, its six hash-closed intakes, source-name map, and exact exports.
The root corpus has **1,700 entries / 11,756 branches**; its component-root
roster has **1,711** IDs. The separate grammatical manifest has **two**
entries. The frozen Furuq source remains unchanged.

The 1,642-row root resolution map now has **1,633 exact roots, seven reviewed
aliases, and two unresolved root identities** (`كيف`, `لوت`). The four new
exact identities each select their dedicated supplemental root; no observed
target became an alias. The exact grammatical selectors cover 83 instances of
`كَيْفَ` and the one `لَاتَ` at 38:3:8:2, without giving either a root-wide
identity. Four scoped primary analyses now link to their reviewed B001 branch;
their competing analyses remain selector-limited. The older historical
`sourceSnapshot` and source-ref digest were retained.

The full dictionary audit, `sync --check`, root-resolution `--check`, focused
Turkish dictionary tests, and scoped word-analysis tests passed after transfer.
The audit reports zero missing Arabic evidence and zero missing mapped entries.
