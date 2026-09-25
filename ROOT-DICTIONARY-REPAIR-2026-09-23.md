# Root dictionary repair session — 2026-09-23

Companion record: `dictionary/ROOT-DICTIONARY-REPAIR-2026-09-23.md` documents
source entry production and review. This record covers transfer, root mapping,
application integration, and publication. Pending work is explicitly marked.

## Changes already introduced

History traced again on September 24: commit `dfca1fdd051e9c765653218bebbe997b9e360111`
(July 28, “new qac t ofuruq root mapping for split roots”) already contains
the problematic `س م و` bridge row with targets سمو (190), وسم (2), and سمم
(1). Commit `464a991fc6b27db8d79c046883adf2326f46ed46` (July 29) retains
that row. These are occurrence observations; interpreting every target as a
root identity propagated one erroneous سمم occurrence to unrelated words such
as اسم. The original frozen occurrence evidence predates this bridge import;
this trace identifies its entry into quran-data, not its first upstream creation.

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


## Independent identity adjudication (2026-09-23)

Controller decision: preserve all six unresolved root identities. The review
rejected two initially proposed aliases after finding competing derivations.
The evidence and rejected alternatives are retained below for future lexical
headword work.

# Independent root-identity review — 2026-09-23

## Recommendation

**Do not add either proposed single-target reviewed alias.** Keep QAC `ث ب ي` at 4:71:7:1 and `س ن ه` at 2:259:42:1 as `unresolved_identity` in the root-resolution file. The proposed dictionary branches are meaningful *interpretive and lexical candidates*, but the evidence does not establish either as the unique root identity of the QAC key. A form-level link or a dedicated dictionary packet can preserve the useful associations without silently replacing the QAC analysis.

The [bridge schema](quran-data/schemas/qac-furuq-v4-root-map.md) says published dictionary resolution uses exact root identity or a reviewed, source-bound alias; observed occurrence targets do not prove lexical equivalence. The [builder](quran-data/scripts/bridges/build_dictionary_root_resolutions.py) exposes an approved alias as `resolution: reviewed_alias` for every token of that QAC root. The decision is therefore stronger than finding a source that discusses the word under a nearby heading.

## `ث ب ي` — 4:71:7:1 `ثُبَاتٍ`

**Reject `root_000209` (`ث و ب`)/B001 as a sole root alias.** The [QAC root page](https://corpus.quran.com/qurandictionary.jsp?q=vby) assigns the verse's noun to `ث ب ي`. `root_000209` is a valid lexical association: its B001 includes `اجتماع الناس`, lexical unit `lu_007` gives `الثبة` as a group, and the frozen Mufradat entry under the *exact* `ثوب` route says `الثبة: الجماعة الثائب بعضهم إلى بعض` and quotes `فانفروا ثبات ... [النساء/71]`. The entry has SHA-256 `0a93118a17e1f50149c9679d4c36d3f4580f32593fc8bb24109bcb496cd6128c`; the proposed [B001 source phrase](../dictionary/public/agent/root/root_000209/branch/root_000209--B001.source.json) hashes to `03948b05175bb51a1b882a93502c669fc8685681530496a406217d6e78f549d1`. B001's source phrase mentions `ثبة الحوض`, while the exact verse and group noun occur in the longer Mufradat entry and the branch lexical unit.

There is substantive morphological disagreement. [Lisān al-ʿArab, `ثبا`](https://islamweb.net/ar/library/content/122/975/%D8%AB%D8%A8%D8%A7) places the group noun with `أصلها ثبي`, reports the alternative `ثبو`, and distinguishes the basin noun's derivation from medial `و` in `ثاب يثوب`. [Lisān al-ʿArab, `ثوب`](https://www.islamweb.net/ar/library/content/122/1095/%D8%AB%D9%88%D8%A8) preserves both the `ثاب` account and the weak-final `ثبية` account for the verse. [Al-Qurṭubī on 4:71](https://islamweb.net/ar/library/content/48/1083/%D9%82%D9%88%D9%84%D9%87-%D8%AA%D8%B9%D8%A7%D9%84%D9%89-%D9%8A%D8%A7-%D8%A3%D9%8A%D9%87%D8%A7-%D8%A7%D9%84%D8%B0%D9%8A%D9%86-%D8%A2%D9%85%D9%86%D9%88%D8%A7-%D8%AE%D8%B0%D9%88%D8%A7-%D8%AD%D8%B0%D8%B1%D9%83%D9%85-%D9%81%D8%A7%D9%86%D9%81%D8%B1%D9%88%D8%A7-%D8%AB%D8%A8%D8%A7%D8%AA-%D8%A3%D9%88-%D8%A7%D9%86%D9%81%D8%B1%D9%88%D8%A7-%D8%AC%D9%85%D9%8A%D8%B9%D8%A7) reports al-Naḥḥās distinguishing `ثبة الجماعة` (`ثُبَيّة` in diminutive) from `ثبة الحوض` (`ثُوَيبة`), while allowing a relationship as another opinion. This is a genuine difference in which radical was lost, not simply two spellings of one root. The dictionary contains no exact `ث ب ي` card or branch in its alias shard. `root_000212` (`ث ي ب`) is the married-person sense; `root_000192` (`ث ب ت`) is firmness. Neither replaces the missing group root.

**Recommended representation:** retain the gap; separately link the exact noun `ثُبَاتٍ` to `root_000209/B001` as a source-attributed Mufradat interpretation if a form-level link is available. Mark `ث ب ي`/`ث ب و` as the competing weak-final analysis for a later dictionary headword or packet review.

## `س ن ه` — 2:259:42:1 `يَتَسَنَّهْ`

**Reject `root_000750` (`س ن ن`)/B005 as a sole root alias.** The [QAC root page](https://corpus.quran.com/qurandictionary.jsp?q=snh) assigns this form V verb to `س ن ه`. The frozen Ṣiḥāḥ entry routed into `root_000751` under broad `سنأ` says `لم يتسن: لم يتغير` from `حمأ مسنون` and replaces one of two nūns with yāʾ. That is a real `س ن ن` derivation, supported by the change sense of [`root_000750/B005`](../dictionary/public/agent/root/root_000750/branch/root_000750--B005.source.json), whose source phrase hashes to `e766c1be25dbf74c3528761c569b593cc2d49a9cda9e36cef7e85cef80baef1e`. But B005 itself quotes `حمأ مسنون`, not `يتسنه`. The frozen Mufradat continuation routed under `سنا` also quotes `لم يتسنه` and calls final `ه` `هاء الاستراحة`, supporting a nonradical-hāʾ reading; its entry SHA-256 is `9a7faf22a7a4902cd33eec772db8197296a13afd7fd0a1e2c4efac01ed752dbc`.

The frozen ʿAyn entry **directly supports QAC's radical `ه`**. Its internal subsection reads `# سنه السنة نقصانها حذف الهاء وتصغيرها سنيهة ... وقال الله عز وجل لم يتسنه ... ومن جعل حذف السنة واوا قرأ لم يتسن ... وإثبات الهاء أصوب`. The entry is available in `the frozen Furuq database`, `dictionary_entries` at `source_id='ayn'`, `source_entry_id='1638'`, `source_ref` ending `sha=39345c43483e0061`, full entry SHA-256 `39345c43483e0061899d66b98f99b436f06af49da2a3d4915d757d680fc970c9`. It is an overbroad source entry indexed under `صهم` and duplicated on unrelated root routes, so **the route labels do not establish `صهم` as this word's root**; the clearly marked `# سنه` subsection is the relevant source evidence.

[Al-Ṭabarī on 2:259](https://islamweb.net/ar/library/content/50/765/%D8%A7%D9%84%D9%82%D9%88%D9%84-%D9%81%D9%8A-%D8%AA%D8%A3%D9%88%D9%8A%D9%84-%D9%82%D9%88%D9%84%D9%87-%D8%AA%D8%B9%D8%A7%D9%84%D9%89-%D9%81%D8%A7%D9%86%D8%B8%D8%B1-%D8%A5%D9%84%D9%89-%D8%B7%D8%B9%D8%A7%D9%85%D9%83-%D9%88%D8%B4%D8%B1%D8%A7%D8%A8%D9%83-%D9%84%D9%85-%D9%8A%D8%AA%D8%B3%D9%86%D9%87-) explicitly lays out the two readings and derivations: hāʾ as a stop letter with `س ن و` or `س ن ن` analyses, and hāʾ as the third radical from `س ن ه`; he favors the original-hāʾ analysis. [Lisān al-ʿArab, `سنه`](https://www.islamweb.net/ar/library/content/122/4033/%D8%B3%D9%86%D9%87) likewise records the original-hāʾ, weak-final-wāw, and doubled-nūn accounts. The shared gloss “did not change” is insufficient to decide the root. `root_000751/B008` covers the year/period sense under `س ن و` but does not itself attest this verbal form. No exact `س ن ه` dictionary card appears in its alias shard.

**Recommended representation:** retain the gap and record `س ن ن`/B005 as one etymological explanation. Preserve the original-hāʾ interpretation as the best direct match to the QAC key, with a dedicated `س ن ه` lexical packet or an explicitly attributed form-level link when supported.

## Provenance and scope

I inspected cards, `routes.min.json`, branch selection and selected branch sources for `root_000192`, `root_000209`, `root_000212`, `root_000750`, and `root_000751`; QAC morpheme rows in `the September 23 QAC gap audit`; and the scoped frozen dictionary entries named above. The SHA-256 values for both proposed branch phrases match the current UTF-8 `source_phrase_ar` values. They prove the branch anchors have not drifted; they do not resolve the competing derivations. The historical occurrence bridge's `ث ب ت` and `س ن ن` targets are observations only under its own consumer rule.


## Completed source transfer — 2026-09-23

Dictionary production commit `ee70049ad` contains all 14 reviewed entries;
`7daa18787` completes the editorial evidence log. The transfer manifest pins
the latter source commit. All 14 exports were transferred: **1,696 entries,
11,741 branches, zero missing Arabic evidence, zero missing resolved entries**.
Independent review outcomes: **5 pass, 9 surgical repair, 0 unresolved editorial
reviews, 0 missing writer outputs, 0 outputs awaiting review**. No alias was
added: the six unresolved identities still cover 88 QAC morphemes.

The new transfer supports committed `tr/export` artifacts while retaining legacy
enriched outputs. It reads the committed Git tree, skips unexported raw drafts,
and rejects regression/removal of previously transferred entries. Source paths,
commit and exact checksums remain in manifest schema v1. Nine dictionary and
transfer tests pass. All 11,741 branches pass the released-lexicon Arabic audit
with the four previously recorded evidence overlays.

وشي B010/B011 remain explicitly qualified documentary branches: disputed mixed
speech vs lightness, and unspecified relation to sound. The user authorized
controller curation; its original response, four changed paths, exact source
phrases, hashes and rationale are preserved in the dictionary editorial folder.
A fresh first independent review then corrected only B005 wording. No positive
meaning was invented for the uncertain documentary branches.

The full six-identity audit follows. Its proposed alternatives were rejected as
root-wide aliases after independent review; these records support future exact
headword or explicitly attributed form-level work.

# Editorial review of six QAC root gaps — 2026-09-23

## Decision

**Add no new root-level reviewed aliases. Keep all six QAC keys unresolved.** The proposed `ث ب ي → ث و ب` and `س ن ه → س ن ن` links are legitimate lexical or etymological associations for individual words, but primary sources also support other radicals. The existing reviewed-alias schema publishes a single dictionary root identity for the QAC root, so it cannot represent these alternatives honestly. A source-attributed form-level link or a dedicated dictionary packet would preserve the associations without replacing the QAC analysis.

The QAC tokens below come from `the September 23 QAC gap audit`. Dictionary lookup followed `../dictionary/AGENTS.md` and `public/agent/START_HERE.md`: alias and form shards, then each candidate card, `routes.min.json`, `branches.select.min.json`, selected branch sources, and scoped frozen source text where the compact branch omitted a decisive phrase. Dictionary file links resolve from this report in `.scratch/`. Branch hashes are SHA-256 of the exact UTF-8 `source_phrase_ar` in the named `.source.json` file; they use the same rule as the existing reviewed-alias file.

| QAC key and token | Decision | Candidate root IDs actually inspected |
|---|---|---|
| `ء د د`, `19:89:4:1` إِدًّا | unresolved | `root_000021` |
| `ث ب ي`, `4:71:7:1` ثُبَاتٍ | unresolved; ثوب is one lexical explanation | `root_000192`, `root_000209`, `root_000212` |
| `س ن ه`, `2:259:42:1` يَتَسَنَّهْ | unresolved; ه / و / ن analyses compete | `root_000750`, `root_000751` |
| `ق ض ض`, `18:77:17:1` يَنقَضَّ | unresolved | `root_001543` |
| `ك ي ف`, 83 occurrences of كَيْفَ | unresolved | none returned by exact root or form lookup |
| `ل و ت`, `38:3:8:2` لَاتَ | unresolved | `root_001389` |

## Rejected root alias proposals

The branch hashes below document the proposed links and their evidence; **neither is approved as a root alias**. The frozen source text was checked against independent accounts of the same forms before making the final decision.

### `ثبي`: ثوب explains the form, but does not establish root identity

- The QAC noun denotes groups in `فَانْفِرُوا ثُبَاتٍ أَوِ انْفِرُوا جَمِيعًا`; see the [QAC verse](https://corpus.quran.com/grammar.jsp?chapter=4&verse=71). Exact `ث ب ي` and normalized `ثبات` form lookup did not return the correct root. A targeted frozen-source phrase search after compact lookup found the verse under `ث و ب`.
- [`root_000209/B001`](../dictionary/public/agent/root/root_000209/branch/root_000209--B001.source.json) includes `اجتماع الناس` and `جماعات يثاب إليها` in its `what_is_ar` (`sourcePhraseSha256 = 03948b05175bb51a1b882a93502c669fc8685681530496a406217d6e78f549d1`). Its lexical unit `lu_007` is `الثبة`, glossed `الجماعة التي يثوب بعضها إلى بعض`, linked to B001. The frozen Mufradat `ثوب` entry (`entry_text_sha256 = 0a93118a17e1f50149c9679d4c36d3f4580f32593fc8bb24109bcb496cd6128c`) explicitly says `الثبة: الجماعة الثائب بعضهم إلى بعض` and cites `فانفروا ثبات أو انفروا جميعا [النساء/71]`. Its route is exact to `root_000209`.
- The same broad Mufradat entry is also routed as a **weak-medial variant** to `root_000212` (`ث ي ب`), but that packet's sole B001 and lexical unit are `الثيب`, the previously married woman, and its `what_is_not_ar` excludes `ثبة الحوض` and general return. The historical observed `root_000192` (`ث ب ت`) B001 is firmness (`ثبت الشيء يثبت ثباتا وثبوتا`; `sourcePhraseSha256 = 1e7e7921a56ad61e6f0034d8baa4810838e6729129f80d098d235aa111a894f6`), a different `ثبات` sense.
- [Lisān al-ʿArab, ثبا](https://islamweb.net/ar/library/content/122/975/%D8%AB%D8%A8%D8%A7) states `أصلها ثبي` for the group noun and reports a possible final و. It distinguishes the basin noun's medial و from `ثاب يثوب`. [Al-Qurṭubī on 4:71](https://islamweb.net/ar/library/content/48/1083/%D9%82%D9%88%D9%84%D9%87-%D8%AA%D8%B9%D8%A7%D9%84%D9%89-%D9%8A%D8%A7-%D8%A3%D9%8A%D9%87%D8%A7-%D8%A7%D9%84%D8%B0%D9%8A%D9%86-%D8%A2%D9%85%D9%86%D9%88%D8%A7-%D8%AE%D8%B0%D9%88%D8%A7-%D8%AD%D8%B0%D8%B1%D9%83%D9%85-%D9%81%D8%A7%D9%86%D9%81%D8%B1%D9%88%D8%A7-%D8%AB%D8%A8%D8%A7%D8%AA-%D8%A3%D9%88-%D8%A7%D9%86%D9%81%D8%B1%D9%88%D8%A7-%D8%AC%D9%85%D9%8A%D8%B9%D8%A7) reports al-Naḥḥās distinguishing `ثُبَيّة` for a group from `ثُوَيبة` for a basin, while recording a proposed relationship as another opinion. These are competing accounts of which radical is missing. Mufradat's `ثوب` placement does not justify replacing QAC `ث ب ي` with a sole `ث و ب` identity. Retain the root gap; `root_000209/B001` can be recorded as a source-attributed link for this form if the consumer supports that distinction.

### `سنه`: the final ه has competing analyses

- [`root_000750/B005`](../dictionary/public/agent/root/root_000750/branch/root_000750--B005.source.json) gives `الحمأ المسنون المتغير المنتن` and `حمإ مسنون أي متغير`. Its branch image is `حَمَأ مسنون وصورة مملسة`, and its inclusion boundary explicitly includes change (`التغيير`). It was the proposed branch anchor for the doubled-ن analysis, though its compact source omits the verb `يتسنه`.
- In the frozen `sihah` entry attached to `root_000751` (`entry_text_sha256 = e8c760f77da3477e330325fa462c60bc7126a42f7394722e0235af7010509676`, route headword `سنأ`), the source says: `لم يتسن : لم يتغير، من ... حمأ مسنون ... فأبدل من إحدى النونات ياء`. The **two nuns** identify the etymological root `س ن ن`, despite that source entry's broad `سنأ` heading and its placement in the `س ن و` packet. The source reference begins `sihah:...:heading%3A5377:...:sha=e8c760f77da3477e`.
- In the frozen `mufradat` entry attached to `root_000751` (`entry_text_sha256 = 9a7faf22a7a4902cd33eec772db8197296a13afd7fd0a1e2c4efac01ed752dbc`), the source explicitly cites `لم يتسنه [البقرة/259]`, says `لم يتغير`, and calls the final `ه` `للاستراحة`. Thus the written `ه` is not necessarily a lexical radical **in this analysis**. The source reference begins `mufradat:...:heading%3A739:...:sha=9a7faf22a7a4902c`.
- The frozen ʿAyn entry directly supports QAC's `س ن ه`. Its marked `# سنه` subsection says `السنة نقصانها حذف الهاء ... وقال الله عز وجل لم يتسنه ... وإثبات الهاء أصوب`. The entry is `dictionary_entries` `source_id='ayn'`, `source_entry_id='1638'`, full `entry_text_sha256 = 39345c43483e0061899d66b98f99b436f06af49da2a3d4915d757d680fc970c9`, with `source_ref` ending `sha=39345c43483e0061`. This oversized source entry is indexed under `صهم` and duplicated on unrelated routes `root_000497`, `root_000717`, `root_000953`, and `root_001575`; those IDs are **not identity candidates**. The internal `# سنه` section, not the route label, is relevant.
- [Al-Ṭabarī on 2:259](https://islamweb.net/ar/library/content/50/765/%D8%A7%D9%84%D9%82%D9%88%D9%84-%D9%81%D9%8A-%D8%AA%D8%A3%D9%88%D9%8A%D9%84-%D9%82%D9%88%D9%84%D9%87-%D8%AA%D8%B9%D8%A7%D9%84%D9%89-%D9%81%D8%A7%D9%86%D8%B8%D8%B1-%D8%A5%D9%84%D9%89-%D8%B7%D8%B9%D8%A7%D9%85%D9%83-%D9%88%D8%B4%D8%B1%D8%A7%D8%A8%D9%83-%D9%84%D9%85-%D9%8A%D8%AA%D8%B3%D9%86%D9%87-) explicitly distinguishes a nonradical stop ه with و or doubled ن derivation from a radical ه reading, and favors the original-ه account. The shared gloss “did not change” cannot resolve the competing roots. `root_000751/B008` (`sourcePhraseSha256 = 8dfd6f23bfd2cb87b75b6c2377869b09bac79b4535d8700c9096e64128979fe4`) covers a year and staying one year under `س ن و` but does not directly attest this change/decay verb. Retain `س ن ه` unresolved; preserve `س ن ن/B005` as one attributed etymological explanation.

## Other unresolved identities

### `ءدد` — 19:89 إِدًّا

The QAC token is an adjective meaning “atrocious”; see the [QAC word context](https://corpus.quran.com/wordbyword.jsp?chapter=19&verse=89). Exact `ء د د` has no dictionary alias or card. The form lookup after folding `إِدّ` to `اد` and the nearby `ء د ا` weak-final alias recall `root_000021` (`ء د ي`) only as a **candidate**. Its route's `ء د ا` sources are weak-final variants of `أدى`, and its card/branches cover conveying, payment, equipment, aid, and unrelated idioms. For example, [`root_000021/B004`](../dictionary/public/agent/root/root_000021/branch/root_000021--B004.source.json) contains `الأداة الآلة` (`sourcePhraseSha256 = 5da7745bb0e492f9aa1f224cec9d1f61bbcf22f8ad43d86a4c4d6a2e41309cd7`). None attests the doubled-dāl adjective `إِدّ`. The shared unvoweled letters are insufficient for an alias.

### `قضض` — 18:77 يَنقَضَّ

The QAC identifies a form VII verb from `ق ض ض`, “collapse,” with `ن` as the form prefix; see its [morphology page](https://corpus.quran.com/wordmorphology.jsp?location=(18:77:17)). Exact `ق ض ض` has no dictionary card. The consonant-only form lookup `ينقض` and historical observation return `root_001543` (`ن ق ض`). Its [`B001`](../dictionary/public/agent/root/root_001543/branch/root_001543--B001.source.json) says `نقضت الحبل والبناء` and covers undoing a constructed thing (`sourcePhraseSha256 = 5cdac16e7f72adf1e6e1c426d312d5b8e38ca3ec496c224031d210d000935bc3`). This is a semantic neighbor, but there the `ن` is a radical and the `ض` is not doubled. A phrase hit for `يريد أن ينقض` in the frozen Maqayis `نقض` entry refers to a poet wanting to undo another's composition (`يريد أن ينقض ما أربه صاحبه`), not the verse's wall. No selected branch source attests `انقضّ الجدار` as this root. Keep the identities separate.

### `كيف` — 83 interrogative tokens

All 83 gap rows have lemma `كَيْف`, surface `كَيْفَ`, and QAC `POS:INTG`; the [QAC word analysis](https://corpus.quran.com/wordbyword.jsp?chapter=2&verse=28) calls it an interrogative noun. Exact `ك ي ف` alias and normalized `كيف` form lookup return no dictionary candidate. There is no branch evidence for assigning its 83 tokens to a nearby consonantal root. This needs a lexical/functional headword or explicit no-dictionary handling, not an alias.

### `لوت` — 38:3 لَاتَ

The target is `38:3:8:2` (`وَلَاتَ حِينَ مَنَاصٍ`), **not** the proper noun `اللَّات` at 53:19; [QAC distinguishes the latter](https://corpus.quran.com/wordmorphology.jsp?location=(53:19:2)). Exact `ل و ت` is absent. Weak-letter normalization of `ل و ت` and lexical lookup of `لات` recall only `root_001389` (`ل ي ت`) as a candidate. [`root_001389/B001`](../dictionary/public/agent/root/root_001389/branch/root_001389--B001.source.json) is the wishing particle `لَيْت` (`sourcePhraseSha256 = 833696b26bb4d52153a86601252f9e6b3e5b6a579530b4960c55933f8b3819bb`); [`B002`](../dictionary/public/agent/root/root_001389/branch/root_001389--B002.source.json) is `لاته يليته نقصه` (`sourcePhraseSha256 = 630c4ff23dbe359916495e9d618e8e3d913c0e21894c7eb4c63704173498e327`); `B003` is turning someone away. None of its selected branches contains the verse's negation/time construction. Its frozen Sihah entry **does** quote `ولات حين مناص` and reports `شبهوا لات بليس` and the analysis `هي لا، والتاء إنما زيدت في حين` (`entry_text_sha256 = 9ae3775a58b8ad0d8fa4706b844393728518b22e8ecde16f97ee6cd13541d984`). This is a grammatical note embedded in a `ليت` source entry, not an assertion that `لات` shares the root of wishing or diminishing. QAC [morphology](https://corpus.quran.com/wordmorphology.jsp?location=(38:3:8)) tags the token as a perfect verb from `ل و ت`, while the QAC [grammar page](https://corpus.quran.com/grammar.jsp?chapter=38&verse=3) calls `لات` a negating particle acting like `ليس`. This divergence increases the need for a dedicated lexical decision; it does not support `ل ي ت`.

## Source integrity note

The frozen source entry text in `the frozen Furuq database` was read only after compact navigation. `root_000209` contains Mufradat's `ثبات` interpretation, though B001's compact source phrase does not quote the verse; its boundary and `lu_007` cover groups. `root_000751` contains the Ṣiḥāḥ and Mufradat explanations of `يتسنه`, though its branch selection omits that verb. The earlier proposed branch hashes identify stable evidence anchors, not proof of root equivalence. **No reviewed-alias JSON should be added for these six under the current root-level schema; the resolution map should continue to show six `unresolved_identity` records.**

## Word-scoped ranked analyses — 2026-09-23

The later editorial decision permits **documented alternative analyses for the
particular word or lemma**. The source-owned record is
`data/bridges/qac-dictionary-word-root-analyses.json`; its schema is
`schemas/qac-dictionary-word-root-analyses.md`. The first item is the selected
primary reading for that selector. Later items are attributed disputed
accounts, not a numerical claim that their proponents were a minority. This
decision supersedes the strict primary-only presentation in the earlier notes
above, while retaining their rejection of root-wide aliases. The six
`unresolved_identity` root records and all withheld occurrence targets stay
unchanged.

The source scopes `ٱسْم` to QAC lemma plus `سمو`: Basran `س م و` is primary and
Kufan `و س م` is attributed to Ibn al-Anbārī's account of the dispute. The
alternative applies to the noun and its plural, not to `سَمَآء` or other
`سمو` lemmas. The single occurrences `ثُبَاتٍ` (4:71:7:1),
`يَتَسَنَّهْ` (2:259:42:1), and `يَنقَضَّ` (18:77:17:1) have cited competing
accounts: `ث ب ي` / `ث و ب` / `ث ب و`, `س ن ه` / `س ن ن` / `س ن و`, and
`ق ض ض` / `ن ق ض`, respectively. The `ن ق ض` account is now included because
Lisān al-ʿArab's `قضض` article explicitly attributes the analysis of this
very verse to Abū ʿAlī al-Fārisī. The earlier rejection concerned a
root-wide alias inferred from semantic proximity without that direct
attribution.

The records for `إِدًّا` (19:89:4:1), `كَيْفَ` (QAC lemma), and `لَاتَ`
(38:3:8:2) document the missing exact lexical or grammatical headword.
They do not assign the nearby `ء د ي` or `ل ي ت` dictionary entries. The QAC
`ل و ت` key remains identified as its morphological indexing choice, while
the cited grammar sources analyze `لَاتَ` as a negating expression.

**Correction to the embedded earlier audit:** its statement that all 83
`كَيْفَ` morphemes have QAC `POS:INTG` is inaccurate. The committed
`qac.sqlite.gz` snapshot has 80 `POS:INTG` and 3 `POS:N` morphemes, all with
lemma `كَيْف` and root key `كيف`. The word-scoped source and its integrity
check use these exact counts.

**Source review status (2026-09-23): complete.** An independent read-only
review checked the exact selectors, the cited competing analyses, and 16
local SHA-256 evidence anchors. Its two precision corrections were applied:
the doubled-`ن` account is attributed to Abū ʿAmr as quoted by al-Jawharī,
and Abū ʿAlī's `ن ق ض` account was identified as the `أَفْعَلَ` form. The
source now contains 7 selectors covering 127 QAC morphemes, 13 analyses
(7 primary and 6 documented alternatives), and 37 evidence items. Three
focused source-integrity checks pass. Each selector pins the exact set of
matching QAC refs and its relevant root-resolution state; current dictionary
branch phrases retain their own hashes. The whole-file QAC/map hashes and
dictionary commit at the top of the source record are historical review
provenance, so unrelated future source updates do not require re-adjudicating
these words.

**2026-09-24 correction to the 2026-09-23 form label:** The earlier `أَفْعَلَ`
vocalization above was an error. [Ibn Sīdah, al-Muḥkam 6:98](https://najafdesertlibrary.com/book/المحكم-والمحيط-الأعظم/v/6/p/98)
attributes the `ن ق ض` derivation of this verse to Abū ʿAlī and explicitly
vocalizes it `افْعَلَّ` (Form IX). Lisān al-ʿArab's `قضض` article also transmits
the attribution, but the linked plain-text rendering does not carry the final
shadda reliably. The word-scoped `18:77:17:1` alternative now cites the exact
Muḥkam witness and states Form IX; QAC's primary `ق ض ض` Form VII analysis and
the restriction to this occurrence remain unchanged. This does not create a
global `قضض -> نقض` alias.

**Publication checkpoint (2026-09-23):** quran-data commit
`86f66b3025e9c798d24d495905e3179c78c1d65a` contains the transfer of
all 14 reviewed entries. The live tafsir evidence remains generation 5 and
the live Reader catalog remains generation 8. Generation 9 was only partly
uploaded; its publisher encountered the Free plan's 10 ms Worker CPU limit
before activation. The user chose to remain on the Free plan. A SQLite
Durable Object route for the existing publication handler, with the Free
plan's 30 s CPU allowance, is the approved repair in quran-apps and awaits
deployment and live verification. The word-scoped ranked analyses described
here are source work and have not yet been published live.


## Live publication and final integration — 2026-09-24

This checkpoint supersedes earlier publication-pending notes. The source
production and transfer are complete: 14 independently reviewed Turkish
entries, 93 added branches, 1,696 total entries and 11,741 branch records.
There are no missing entries among resolved root identities. Proper-name
handling and the documentary وشـي decisions above remain part of the record.

### Source revisions and editorial policy

- Dictionary production: `ee70049ad`; transfer source pin: `7daa18787`;
  policy/session checkpoint: `ac1dd765e`.
- quran-data transfer: `86f66b302`; scoped analyses and source contract:
  `e523a206c2d08718fd4b35c836ac83e272632ead`.
- The scoped source has 7 selectors, 127 QAC morphemes, 13 ordered analyses,
  37 evidence items, and 16 verified local SHA-256 evidence anchors.
- اسم presents primary سمو and attributed disputed وسم with the Basra–Kufa
  reason; سمم is excluded. وسم does not spread to سماء or سمّوهم.
- The six global identities ءدد, ثبي, سنه, قضض, كيف and لوت remain unresolved
  (88 canonical QAC morphemes). The review is complete; this is an explicit
  evidence decision. Word-scoped alternatives preserve competing accounts
  without asserting global root equivalence. Exact missing entries remain
  visible even when a linked alternative has an entry.
- Next editorial work: dedicated evidence-backed root entries for ءدد, ثبي,
  سنه and قضض, and grammatical headwords for كيف and لات. Prioritize كيف's
  83 occurrences. Do not route لات at 38:3 to the deity اللّات at 53:19.
- **Correction to the earlier embedded audit:** كيف has 80 QAC INTG and 3 N
  morphemes, not 83 INTG. All 83 share the selected lemma and root key.

### Live artifacts and application changes

- Reader generation 9 was activated first; generation **10** is now active.
  Final catalog:
  `/content/v2/catalogs/10.3950bd2ef28d4d6c658b45bd0fe1d51754572dc5b1870dfa210bab7b39b6995f.json`.
  All 229 packs and the source lock passed publication verification. The exact
  Worker-signed activation was adopted into the local mirror and plan.
- Tafsir evidence generation **6** is active. Catalog:
  `/evidence/generations/catalog.6a10b78b390ee04442e714404d816e98505811bc61b5d4abf2a699138f9c7745.json`.
  All 847 immutable objects (429,331,900 bytes) passed full-body verification;
  activation and both pinned legacy pointers were checked.
- Data publication commit in quran-apps: `e41b8f36`; scoped UI/compiler:
  `e58c618b`; final TM branch-title fix: `b02b3d4f`. That fix uses each
  branch's root identity because entry IDs include a language suffix (`/tr`).
- KK **0.1.62**, module `/assets/index-Dl3QKRZa.js`, and TM **0.2.14**, build
  `12cf3ddb7b350186902a8fb1`, are deployed. Primary and disputed root cards
  include the reason, attribution, source links, and relevant branch title.

### Free-plan publication and repeatability

The user chose to keep Cloudflare Free. Commit `c1f0edb3` routes the existing
publication handler through an internal SQLite Durable Object; deployed Worker
version `4b28e9b7-c37f-48e8-b079-bfd3eae96a4c`. Live generation 9 and 10
publication succeeded through this path. No paid-plan upgrade was made.
Authentication, checksums, signatures, receipts and activation compare-and-swap
remain enforced; CONTROL R2 is authoritative. Verified immutable objects are
reused on retry. The single publisher command is unchanged.

`npm run data:update -- --quran-data-ref e523a206c` was rerun after activation.
It reported Reader local/live generation 10 and current evidence, with no new
release. SHA-256 values of all eight source-lock/publication/activation files
were unchanged. Local source builds use committed Git snapshots. Unrelated
inter-ayah edits in the original quran-data checkout were preserved; that
checkout was not reset, stashed or merged over those edits. This documentation
checkpoint does not change the source revision used by the published data.

Regression results: Reader 282/282, contracts 97/97, publication Worker
113/113, deployment/tools 56/56, and final TM branch-display suite 5/5; focused
source, transfer and dictionary checks also passed. The Worker typecheck,
dry-run deployment, both application builds and live CDN verification passed.

Separate limitation: the existing iOS activation-transition check requires an
exact predecessor hash and may reject a client jumping from generation 8 to
10. This session deployed and verified KK and TM; it did not change or verify
iOS update behavior.

## Dictionary badge and gloss-assessment phase — 2026-09-24

This entry follows the Reader 10 / evidence 6 checkpoint above. The pinned
quran-data source is still `e523a206c2d08718fd4b35c836ac83e272632ead`;
later session documentation did not change the released lexical corpus. No new
root alias, branch meaning, gloss fit, or other source lexical judgment was
made for these badges. The six global identities ءدد, ثبي, سنه, قضض, كيف and
لوت remain unresolved and retain their explicit missing states.

### Editorial and projection boundary

Commit `b125d307` exposes source-authored usage, provenance, and Turkish gloss
assessments through the projector and Reader UI. The projection preserves all
**37,846** existing `error_profile` assessments: 11,741 concept glosses,
21,430 contextual renderings, and 4,675 excluded renderings. Each optional
`glossAssessments` record is tied to exactly one gloss by `kind`, zero-based
`index`, and exact `text`; absent profiles do not become an invented `none`
assessment. Excluded renderings remain excluded. A fit badge describes the
comparison with a branch's Arabic concept, not the correctness of a verse
translation or of the whole dictionary entry.

The governed `root_001123/B001` source exception is retained as authored:
“hâlâ yapmak” is `broadening` because it loses a mandatory negative
construction; “yapmayı bırakmamak” is `narrowing` because it adds an
intentional-choice implication. The apps do not infer fit from which
explanation field is populated. This preserves the existing editorial
assessment without weakening structural validation.

The only two linguistic usage types shown are **Yalın kullanım** (`bare`) and
**Kalıba bağlı kullanım** (`collocation`). Legacy `mixed_non_bare`, `non_bare`,
and `unresolved` classifier states are neutral usage metadata, not additional
branch types or claims about a selected word's affixes, case, or figurative
status. Branch provenance comes from `sources`, displayed as six consistent
colored circles: AY, JA, MQ, MU, SI, and TA. A source circle indicates a
source roster, not unanimous agreement; `sourceNotes` is not a substitute for
the roster, and no numeric count badge was added. Full names are available by
touch and keyboard. The shared wording and source names are recorded in
`docs/dictionary-badges.md` in quran-apps.

### Live data and application checkpoint

Reader generation **11** is live at
`/content/v2/catalogs/11.3f0ff12704e99f1143dcf42ccbdc8997a5d3c7b26f3d3b7f1dcf20411248c277.json`.
Tafsir evidence generation **7** is live at
`/evidence/generations/catalog.5a399a1edc5bf5a029daf3d664a8ebe8d68bf59791fb3b64762c67a50d6c21da.json`.
Each release passed independent full CDN verification; the evidence check
covered 847 objects totaling 450,750,732 bytes. These new generations reflect
the projector/schema and application work while retaining the same source pin.
The quran-apps data publication commit is `32125972`.

The Reader first-click fix `9c38fe01` keeps a clicked word panel open during
commentary hydration. The badge/projector change is `b125d307`; subsequent
badge wording and mobile source display were refined in `e0205cf2`. Reader
reported 287 passes in the full run; one build timed out there and passed on
an isolated rerun. The latest focused checks passed 11/11, contracts 97/97,
tools 56/56, TM badge/mobile 9/9, and the earlier ranked-analysis checks 5/5.

KK **0.1.63** is deployed with module `/assets/index-DL4mLdNW.js`; TM
**0.2.15** is deployed with build `95f417a4a49d9602af7a9f55`. Fresh live
root probes passed 11 KK and 8 TM cases; warm probes passed 3 KK and 2 TM
cases, all without failures. A cached KK generation 10 session updated to
generation 11 and module `/assets/index-DL4mLdNW.js`; a cached TM 0.2.14
session updated to build `95f417a4a49d9602af7a9f55` through the
service-worker prompt and reload. A repeat
`data:update -- --quran-data-ref e523a206c` found Reader 11 and evidence 7
already current and left all eight publication, lock, and activation SHA-256
values unchanged. The badge-specific desktop/mobile and first-click probes
passed **10/10** across KK and TM: ism, adhāb, and thawāb on desktop; ism
and thawāb on mobile. They verified branch source rosters (including SI alone
and MQ+TA together), circle color/geometry, usage labels, names on focus,
click and tap without changing the branch, exact concept `none` and contextual
`narrowing` kind/index/text bindings, and TM visible-source to editor roundtrip.
The settled panel opacity was 1; page errors, failed responses, and failures
were all zero. Report and ten screenshots are under
`.scratch/live-dictionary-badges/2026-09-24T16-34-06-324Z-29590b2e-`.
A read-only compatibility audit found that the older TM
0.2.14 loader ignores the new optional gloss profiles without invoking the
strict shard validator. The warm probe confirmed its service-worker prompt
and reload path. No iOS behavior was changed in this phase.

## Six-entry supplemental integration opened — 2026-09-24

The new dictionary source registry will own four exact lexical roots: ء د د,
ث ب ي, س ن ه, and ق ض ض. Separate `headword_` identities will cover the
grammatical كَيْفَ and لَاتَ by exact QAC selectors. The intake, independent
writer/reviewer decisions, export and committed transfer are pending; none of
these six is recorded here as accepted or published. The frozen Furuq database,
existing seven aliases, and unrelated word analyses remain unchanged.

The quran-data transfer now has a source-owned registry/intake path and a
separate grammatical-headword manifest. It verifies committed source bytes,
typed citations, exact Arabic quotations and source phrases, QAC bindings,
and QAC occurrence evidence. The root-resolution builder accepts reviewed
supplemental roots only by exact Arabic identity. Grammatical headword coverage
does not turn كيف or لوت into resolved lexical roots. Existing scoped analyses
retain their historical `sourceSnapshot` fields; four baseline identities and
primary branch links will be updated only after the reviewed exports provide
the actual accepted branch IDs.

## Six-entry quran-data transfer completed — 2026-09-24

Dictionary commit `e553f0afe23f32c422561bcd3ee7e65f0b503b2b` contains
the independently reviewed six-entry source batch. The committed transfer
copied four lexical root exports and two separate grammatical headwords, plus
the hash-closed registry, six intakes, and source-name map. The root corpus now
has 1,700 entries and 11,756 branches; the separate headword manifest has two
entries. The frozen Furuq database and existing aliases remain unchanged.

The root-resolution gateway has 1,633 exact identities, seven reviewed
aliases, and two root-unresolved keys (`كيف`, `لوت`). Four scoped analyses now
link their primary interpretation to the corresponding new B001 branch, with
exact source-phrase hashes; competing interpretations remain scoped. The
historical `sourceSnapshot` and earlier resolution source-ref digest are
preserved, and their notes date the earlier unresolved state. The corrected
`قضض` alternative continues to cite al-Muḥkam's vocalized `افْعَلَّ` Form IX
witness without creating a global alias.

The full dictionary audit passed: 1,711 component roots, zero missing Arabic
evidence, and zero missing mapped entries. Transfer `--check` reported no
changes; root-resolution `--check` and focused dictionary/scoped-analysis
tests passed. This records source integration, not Reader or app publication.

## Six-entry live publication — 2026-09-24

The reviewed source batch in dictionary
`e553f0afe23f32c422561bcd3ee7e65f0b503b2b` was transferred in quran-data
`aa2aef1966eceb4169660b2a874f3de2c081c748` and published through quran-apps.
Reader **generation 12** activated at `2026-09-24T18:46:31.744Z` with catalog
SHA-256 `4c022f0b22ec89a417cf134d51daf087db4902ecaf75d583afab53f9ab47cd58`.
Tafsir evidence **generation 8** has catalog SHA-256
`52d6ea7a57d7d665bf89028c915dff4850f3c0587349e9842af383990d01770b`.

KK **0.1.64** (`/assets/index-C-wcA-_W.js`) and TM **0.2.16**
(build `dd16911b8815ff75dafb0962`) are deployed. Their common dictionary has
1,700 root entries, 1,711 component roots and 11,756 branches, plus two
separate grammatical headwords covering 84 morphemes. The four lexical
additions cover four further morphemes. The lexical root-resolution keys
`كيف` and `لوت` intentionally remain unresolved as roots; their exact words
are served by grammatical entries. They are not outstanding entry-production
gaps. The raw QAC noun/verb tags and documented alternative analyses remain
available, and the deity at 53:19 is excluded from the grammatical لَاتَ entry.

The publication barrier and final remote evidence check verified all 847
immutable objects (451,007,837 bytes), the active pointer and the two pinned
legacy pointers. Reader uploaded 230 objects (229 packs plus its source lock),
validated the release, adopted the exact Worker-signed activation and passed
its separate live verification. Both channels were published on the existing
Cloudflare Free configuration. No commentary channel changed in this batch.

The quran-apps root `CDN-UPDATE-RUNBOOK.md` documents the committed-source
transfer, single `data:update` build, separate evidence/Reader publishers,
retry rules and live checks. Later documentation-only commits do not supersede
the source pins above or require another data release.

### Verification scope and remaining audit recommendation

The source/transfer checks, contract/runtime suites, application builds, live
CDN verification, and 31 sampled live static agent files passed. These establish
release integrity and the tested entry behavior; they do not certify the semantic
accuracy of every existing dictionary definition.

The complete legacy compiler suite still has two unrelated fixture setup
failures: the committed QAC crosswalk manifest expects a different quran-data
`RELEASE.json` hash, and the committed demo lock expects a different
`packages/content-compiler/target-mappings/s001.tr.json` hash. Both actual inputs
match their repository HEAD versions. The focused six-entry projector tests and
actual publication builds pass. Those old locks were not silently regenerated
as part of this dictionary release.

The controller recommends a whole-corpus mechanical audit of entry coverage,
root and exact-word mappings, transfer parity, citation/source ownership,
review provenance, branch type, and gloss-assessment consistency. Independent
editorial review should prioritize proper names, grammatical headwords, weak
and doubled roots, disputed derivations, and older review records. A stratified
sample of the remaining entries should determine whether a complete semantic
re-review is warranted. The six deliberately difficult gaps are not a random
sample, so their findings must not be extrapolated into a corpus-wide error
rate. This recommendation is documented; no new whole-corpus editorial
production campaign has been started.

### TM startup correction found by the live browser audit

The post-publication browser audit found that TM could still show the legacy
third `سمم` candidate for `اسم` while its bundled demonstration corpus was
visible. The generation-8 catalog and KK contained only the accepted `سمو`
and `وسم` analyses. TM treated a seeded ayah as already loaded, and its startup
loader chose a surah only after awaiting another catalog request. Navigation
during startup could therefore leave seeded research data in use.

The TM 0.2.17 correction tracks ayahs merged from live loader results, fetches
seeded ayahs when needed, captures the initial surah before awaiting the
catalog, and shares in-flight loads between startup and navigation. Production
research panels show loading or unavailable status until live data is ready;
the local demonstration mode is retained. The source dictionary and CDN
catalogs did not need another data release. This case is further evidence that
an audit must cover source-to-screen behavior in both clients, including slow
loads and navigation, as well as source content and transfer hashes.

TM 0.2.17 was subsequently deployed with build ID
`d6a0d86a16179f9b46b32bf0`. Its served HTML, application script and translations
match the reviewed build byte for byte. Independent review, all 25 TM tests
(including two new asynchronous startup/retry regressions), and the production
build passed. The application release is committed in quran-apps `79810f9e`;
the TM startup correction is committed in `0fbcd8ba`.

The final deployed browser audit passed **34/34 cases** on September 24
(8 existing-profile cases and 26 fresh desktop/mobile cases), with zero page
errors and zero failed application/CDN responses. It covered all four new
roots, both headwords, the three QAC noun-tagged كَيْفَ occurrences, the deity
exclusion, and اسم's two accepted roots without سمم. Source circles, usage
badges, typed citations, authored citation notes and gloss-assessment bindings
were checked against the live payloads. The existing TM profile visibly
upgraded from 0.2.16 to 0.2.17; the earlier KK 0.1.63/Reader-11 to
0.1.64/Reader-12 upgrade evidence was retained. The local quran-apps audit report
is `.scratch/six-live/2026-09-24T21-17-18-337Z-14b7ea1b-report.json`.

An additional live TM slow-load/navigation check also passed: delaying the
public evidence activation GET for three seconds showed loading status and
zero bundled root cards. Releasing the response displayed only `سمو`/`وسم`;
navigation `1:1 → 2:28 → 1:1` displayed the كَيْفَ headword and then restored
only those two اسم roots, including after settling. There were no page errors
or failed responses. The local report is
`.scratch/six-live/2026-09-24T21-22-14-436Z-e1a23ed4-delayed-tm-report.json`.

### S1 sampling audit after publication — September 24

At the user's request, GPT-6 Sol Max screened all 157 branches of the 19
existing root entries linked from S1, including both اسم alternatives.
Separate deeper checks retained nine branches for surgical correction and
dismissed ten initial flags. The 157 source anchors and the exported authored
fields matched their dictionary originals. Findings therefore concern existing
authored wording, not this transfer. No canonical data or CDN release changed.
148 English definition drafts were saved separately; nine remain pending.

The earlier broad audit recommendation is narrowed: the original mapping and
new-draft problems did not establish widespread semantic errors in existing
entries. This targeted sample provides concrete findings, not a corpus error
rate. Continue compact screening then deeper review only of flags, preserving
root ambiguity and existing source anchoring. Detailed rationale and proposed
repairs are in dictionary's root `S1-DICTIONARY-AUDIT-2026-09-24.md` and
`v2/audits/s001-2026-09-24/`. The nine proposals have not been applied.

Dictionary audit artifact commit: `d503c52db`. quran-data records this audit
without changing dictionary exports or release manifests.

### Blind Luna comparison of S1 — September 24

The user authorized a blind GPT-6 Luna Max repeat using the same 157 branch
inputs and instructions. Fresh workers saw no Sol findings; completed batches
were compared immediately. Luna referred three of the previous nine problem
branches and passed six. Its reasons did not explicitly identify those three
retained problems. It independently raised two other wording issues retained
by Astra review, plus one unresolved eye-terminology concern. The combined
queue is eleven documented correction branches and one unresolved concern.

A blinded comparison of 22 shared English drafts found five minor fidelity
deviations and one substantive error in Luna drafts, versus no errors in Sol
drafts in that particular comparison. Keep Sol as the main screener and
definition drafter; Luna may contribute an additional independent pass. Do not
use this one targeted sample as a corpus-wide error-rate estimate. All drafts
remain unapproved; no canonical source, export or live release changed.

Detailed reasoning, raw outputs, adjudications, and the English hold list are
in dictionary's root `S1-LUNA-BLIND-COMPARISON-2026-09-24.md` and
`v2/audits/s001-luna-blind-2026-09-24/`.

Dictionary blind-comparison artifact commit: `b76b4e139`.
