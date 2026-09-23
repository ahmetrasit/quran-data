# Scoped QAC dictionary root analyses, version 1

The authored source is
`data/bridges/qac-dictionary-word-root-analyses.json`. It records documented
analyses of a **word or lemma** where the QAC root key alone would be too broad.
The existing `qac-dictionary-root-resolutions.json` remains the root-wide
dictionary baseline. A record here does not add a reviewed root alias and must
never be unioned into every word with the same QAC root.

## Source object

- `schemaVersion`: exactly `qac-dictionary-word-root-analyses-v1`.
- `reviewedOn`: editorial review date (`YYYY-MM-DD`).
- `sourceSnapshot.qacMorphologyGzipSha256`: SHA-256 of the committed compressed
  `data/morphology/qac.sqlite.gz` bytes at editorial review. The exact QAC
  lemma and morpheme ref come from `qac_morphemes` in that snapshot.
- `sourceSnapshot.rootResolutionsSha256`: SHA-256 of the committed
  `data/bridges/qac-dictionary-root-resolutions.json` bytes at review time.
- `sourceSnapshot.dictionarySourceCommit`: 40-character commit of the
  dictionary transfer source at review time, also pinned in the transfer
  manifest for that review.
- `records`: nonempty array of scoped records.

These three snapshot values are **historical provenance**. Later changes to
unrelated QAC rows, root-resolution rows, or dictionary entries do not require
rewriting the editorial source. Current validity is checked against the scoped
fields described below.

Each record has `selector` and `analyses`:

```json
{
  "selector": { "qacRootJoinKey": "سمو", "qacLemma": "ٱسْم" },
  "selectorRefsSha256": "b47507e027cb1e1d0af721d508c58680387d2347b4ea0507c75b53bd8fabfb3f",
  "baselineResolution": {
    "resolution": "exact_root",
    "rootIds": ["root_000745"]
  },
  "analyses": [
    {
      "rank": 1,
      "standing": "primary",
      "rootArabic": "س م و",
      "dictionaryRootId": "root_000745",
      "dictionaryBranchRef": "root_000745/B005",
      "reasonTr": "...",
      "attributionTr": "...",
      "evidence": [
        {
          "sourceTitle": "İbnü’l-Enbârî, el-İnsâf, I. mesele",
          "sourceUrl": "https://books.rafed.net/view/1878/page/8",
          "noteTr": "..."
        }
      ]
    }
  ]
}
```

`selector.qacRootJoinKey` is the unspaced Arabic QAC root key. It must be
combined with exactly one of:

- `qacLemma`: the exact `qac_morphemes.lemma_ar` string. This applies to all
  morphemes with that root and lemma, including inflected forms and plurals.
- `qacRef`: the exact `qac_morphemes.qac_ref` string. This applies to one
  morpheme only.

If both selector types ever match, the exact `qacRef` record wins. A root-only
selector is invalid. The same selector may occur only once. For example, the
`سمو` + `ٱسْم` record covers its 39 noun morphemes and cannot affect `سَمَآء`
or `سَمَّىٰ`, although those QAC lemmas share `سمو`.

`selectorRefsSha256` is the SHA-256 of the UTF-8 bytes of
`JSON.stringify(sortedMatchingQacRefs)`, with no trailing newline. The array
contains the exact QAC morpheme ref strings selected by the record, sorted
lexicographically. The digest detects additions, removals, and substitutions
within that scope without depending on unrelated QAC changes.

`baselineResolution` copies only `resolution` and `rootIds` from the matching
row in the root-resolution map. A change to that row's relevant identity
requires review. Changes to other root rows, observation counts, and withheld
targets do not change this record's standing. Linked dictionary branches are
checked by their exact phrase hashes below.

`analyses` are sorted by consecutive `rank` values starting at 1. The first
item has `standing: primary`; later items have
`standing: documented_alternative`. The order means the editorial display
choice for this specific word. It is **not** a count of scholars, a universal
majority claim, or a root-wide ranking. The Turkish `reasonTr` states why the
analysis belongs to this exact selector and any limits of the linked
dictionary branch. `attributionTr` names the scholars or sources responsible
for the account. An alternative is recorded only when a cited source supports
that actual form or verse. Observed bridge targets and nearby spelling alone
are insufficient.

`rootArabic` is a spaced Arabic radical key or the QAC indexing key when no
lexical root headword has been established. In the latter case, `reasonTr` must
say so explicitly. `dictionaryRootId` and `dictionaryBranchRef` are nullable.
When an exact dictionary headword is absent, both are `null`. A dictionary root
may be linked without a branch when the available branch only supports an
adjacent sense; the reason must explain that limit. A nonnull branch reference
has the full `root_000000/B000` form and belongs to `dictionaryRootId`.

Every analysis has a nonempty `evidence` array. Each item has `sourceTitle`,
`noteTr`, and at least one verifiable location:

- `sourceUrl`: a directly relevant public primary text, such as a classical
  lexicon or tafsīr passage, or the QAC word/root analysis.
- `sourceRef` with `sourceSha256`: a frozen local source anchor. For
  `root_.../B...#source_phrase_ar`, the hash is of the exact UTF-8 branch
  `source_phrase_ar` string. For `furuq:dictionary_entries/...`, it is the
  frozen `entry_text_sha256` of the full entry, even if `sourceRef` identifies
  a relevant subsection. For the resolution file, it is the SHA-256 of the
  complete JSON file.

The source currently records `ثبي`, `سنه`, and `قضض` as cases with genuine
competing analyses. It records the Basran and Kufan derivations of `ٱسْم` as a
lemma-only dispute. `ءدد`, `كيف`, and `لوت` retain explicit missing lexical
headword notes; nearby but unsupported dictionary roots are not presented as
alternatives. For `كيف` and `لوت`, the QAC root key is an indexing fact and
does not settle the grammatical status of the word.
