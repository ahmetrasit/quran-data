# Root dictionary repair session — 2026-09-23

Companion record: `dictionary/ROOT-DICTIONARY-REPAIR-2026-09-23.md` documents
source entry production and review. This record covers transfer, root mapping,
application integration, and publication. Pending work is explicitly marked.

## Changes already introduced

quran-data commit `c159182b38d3f7becc949a055ba0845489a2a67e` and quran-apps
commit `eea70a4215a64247e0cda90aee8e8d7cdfade0f2` contain the initial repair.

- Audited 1,682 transferred Turkish entries against committed dictionary
  writer outputs and 11,648 Arabic branches against frozen Furuq evidence.
- Strengthened transfer checks for missing/deleted files, byte drift, and
  raw/incomplete writer output. Imported available entries ترق and ذخر;
  verified سهو is included.
- Recorded four explicit source Arabic updates (`root_000086/B011`, B012,
  B014 and `root_001697/B002`) because the dictionary snapshot is newer than
  the released lexicon. The released database remains immutable.
- Corrected occurrence `13:33:13:1` سمّوهم from سمم to سمو and occurrence
  `48:15:8:1` ذرونا from ذور to وذر.
- Introduced source-owned `qac-dictionary-root-resolutions.json`: 1,629 exact
  Arabic identities, seven evidence-bound reviewed aliases, six unresolved
  identities. Withheld 116 observational targets from automatic root lookup.
- KK اسم now resolves primarily to سمو. The observed وسم alternative remains
  research evidence; سمم is available only for its own relevant identity.
- Simplified quran-apps update handling through `npm run data:update` and
  `npm run data:check`, using committed source snapshots and explicit locks.

Full evidence, source hashes and audit commands are in
`data/bridges/ROOT-DICTIONARY-REVIEW.md`, the transfer manifest and Arabic
evidence update file under `data/dictionary/tr/`.

## Gaps discovered by the complete audit

Fourteen missing Turkish entries cover 58 QAC morphemes. Agent-based source
production is underway in dictionary using existing Furuq bundles, one writer
then one independent reviewer per root. User selected GPT-6 Sol at maximum
reasoning, with at most eight active agents. Per-root outcomes and artifacts
are recorded in the dictionary companion document.

Six unresolved identities cover 88 QAC morphemes:

| QAC identity | Example | Count |
| --- | --- | ---: |
| ءدد | إِدًّا, 19:89 | 1 |
| ثبي | ثُبَاتٍ, 4:71 | 1 |
| سنه | يَتَسَنَّهْ, 2:259 | 1 |
| قضض | يَنقَضَّ, 18:77 | 1 |
| كيف | كَيْفَ, e.g. 2:28 | 83 |
| لوت | لَاتَ, 38:3 | 1 |

None of the combined 146 occurrences is tagged PN by QAC. Dictionary branches
still contain proper names: ءلل has divine-name and place-name branches; معن
contains a mixed branch naming معان. The user delegated editorial decisions. These entries will preserve their
source branch roster, use descriptive Turkish name-class/place prose, and keep
original names in injected Arabic evidence fields. No Turkish name spelling or
new lexical name unit is invented; معن/B006 must distinguish ordinary dwelling
from the named place. Empty fallback policies remain explicit noncoverage. لَاتَ at 38:3 is distinct from اللّات at 53:19.

No unresolved identity is automatically equated through weak-letter or
phonetic similarity. In particular, the لوت lookup's ليت candidate has not
been approved. New aliases require branch quotations and evidence hashes.

## Publication checkpoint

- Tafsir evidence generation 5: published to live CDN; all 847 immutable
  objects, activation and two pinned legacy pointers verified.
- TM shell: deployed with production CDN origins; updated installations were
  observed receiving generation 5 and showing only سمو for اسم.
- KK: observed using the corrected shared dictionary evidence for اسم.
- Reader catalog: generation 8 is now activated; generation 9 remains pending a
  refreshed administrator token. Publication retry/Worker storage
  budget fixes are being completed in quran-apps. Do not interpret prepared
  releases or uploaded immutable objects as a completed live activation.

This document will be updated with final source commits, review outcomes,
transfer results and verified activation generations as the session completes.
