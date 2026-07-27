# Production roadmap

Status: 2026-07-27

For the complete cross-repository audit and verification record, read
[`STATUS.md`](STATUS.md). `RELEASE.json` remains the authority for what is
available now.

This is the direction for future `quran-data` releases. `RELEASE.json` remains
the authority for what is available now.

## Latest checkpoint

On 2026-07-27, the first post-`2026.07.21` canonical imports were staged in `quran-data` with local provenance files:

- Turkish dictionary entries: 1,679 JSON files under `data/dictionary/tr/`;
- Turkish translation glosses: 1,572 reviewed JSON files under `data/translation/glosses/locales/tr/`;
- Turkish V12 ayah activation/publication support: 114 surahs plus full-context packets/control directories and 6 focus runs under `data/analysis/ayah-activation/v12-tr/`;
- network v3 generated channel outputs: 111 eligible surahs plus 110 review files and pericopes under `data/analysis/channels/network-v3/`;
- inter-ayah focus review TSVs: 5,604 of 6,236 focus outputs under `data/analysis/inter-ayah/`.

These staged imports are not yet a formal release. The next release work is validation, explicit exception ledgers, `RELEASE.json`, coverage/provenance manifests, checksums, and a release tag. Network v3 remains generated candidate data until blind review and adjudication close. Inter-ayah focus reviews remain partial until the 632 missing TSVs are produced and `focus_29_55_cutoff_100.tsv` is rerun.

V11 remains the intended high-recall source for accepted, occurrence-anchored
surah image chains. The last documented coverage is 29 surahs: S1 and
S87-S114. No later corpus-close record was found during the July 24 audit, so
S2-S86 remains pending until the source repo records otherwise. For long
surahs, completion still requires pericope runs and reviewed cross-pericope
integration; a run directory alone is not completion.

Do not wait for full V11 breadth to test consumer contracts. Freeze and validate
the chain, relation, commentary, and app-export contracts on a small reviewed
vertical slice before repeating them corpus-wide.

## Source roles

| Source | Production role |
|---|---|
| `word_analysis` | Final independent word-level critical analysis; also contributes linguistic evidence to ayah commentary. Do not regenerate it. |
| V12 plus/minus 2 and plus/minus 5 | Ayah-anchored primary, secondary, and exploratory activation. |
| V11 | High-recall within-surah discovery and accepted image-chain/channel structure. |
| Quran-SLM baseline and Neo | Cross-root semantic candidate retrieval, including cluster alignment between surahs. |
| QNet | Edge compatibility: themes, keywords, and Q2 relations between chain nodes. |
| Dictionary V2 | One comprehensive root master record and deterministic translation-agent, user-dictionary, and scholar projections. |
| V3 prose synthesis under `latent_activation/_prose` | Rendering accepted evidence into ayah and surah commentary; it must not invent new analysis. |
| Study/V10 | Experimental taxonomy and calibration examples only. Do not promote its raw or gated outputs. |

## Required work order

### 1. Enforce frozen lexical identity

The canonical selection is now explicit, but every future import must enforce
it.

1. Record the exact release snapshot, source commit, SHA-256, filtering rules,
   root count, branch count, and accepted/contaminated policy.
2. Treat `root_id` and `branch_id` as meaningful only with that snapshot.
3. Build an explicit crosswalk for any already-produced artifact that used an
   older snapshot; rebuild when a safe one-to-one crosswalk is impossible.
4. Verify or synchronize Dictionary packets, V12 publications, QNet, and
   Quran-SLM indexes against the frozen snapshot before promotion.

This is not theoretical drift. `latent_activation` still contains an older
18,781-clean-card resource with SHA-256
`318d7128daa25e15dc753ea7cb035ed5b145989c22a8d555a7f6986443d4c0af`,
while Dictionary and the rebuilt Quran-SLM catalogs use the current
18,785-clean-card input with SHA-256
`1099db0d56515d2eb3e8d72f104f2e338c2c9a8c1fa6abbb046406d3b327e722`.
Never join them by branch ID without snapshot verification.

### 2. Finish Dictionary V2

Dictionary V2 already has the right architecture: one validated master entry
per root and deterministic consumer projections. Complete it rather than
designing another entry format.

The current checkpoint is 1,679 Turkish dictionary entry JSON files staged in `data/dictionary/tr/` and 1,572 reviewed Turkish gloss result JSON files staged in `data/translation/glosses/locales/tr/`. The gloss layout is locale-compatible for future languages. There are 107 staged Turkish entry envelopes without a copied Turkish gloss result; record those exceptions before release formalization. No English entry or gloss payload has been staged. Full entries for Furuq-only roots remain optional later coverage; those branches can still serve as verified neighbor evidence and semantic mediators.

An entry is promotable only when:

- every branch in the frozen root roster appears exactly once;
- its target-language explanations and gloss judgments are reviewed or
  published, not merely schema-valid drafts;
- provenance binds it to the exact packet, branch evidence, Furūq snapshot,
  occurrences, morphology, and attachments;
- the master and all requested projections reproduce deterministically; and
- the selected release languages have explicit complete coverage or explicit
  documented exceptions.

The three projections remain:

- `translation_agent`: branch boundaries, gloss candidates, and
  preservation/loss/addition/collision guidance;
- `user_dictionary`: concise definition, ranked glosses, and the key neighbor
  distinction;
- `scholar_view`: full sources, neighbors, branches, occurrences, morphology,
  and attachments.

### 3. Freeze the remaining analysis contracts

The V12 cross-run publication contract is frozen and complete across all 114 surahs. Its publication support artifacts are staged under `data/analysis/ayah-activation/v12-tr/`; the remaining gate is release validation and metadata formalization.

Before bulk V11 completion, use S1 plus a representative selection from
S87-S114 to freeze the contracts that remain open:

- the accepted V11 image-chain contract;
- the accepted inter-surah relation contract; and
- ayah- and surah-commentary contracts with evidence references.

V12 publication is not “one run is primary and the other is secondary.”
Primary activation is the strongest fixed-ayah-anchored mechanism from either
window when it has explicit branch evidence, is compatible with the other
window, avoids a speculative jump, and materially supports the main reading.
Defensible but less necessary extensions are secondary; weak analogies remain
exploratory. `word_analysis` supplies independent linguistic evidence, not an
automatic vote that turns a candidate activation into an accepted one.

For V11, `08-graph.json` is a recall reservoir, not a set of accepted image
chains. Normalize only reviewed/promoted chains, with concrete ayah-occurrence
anchors. Preserve rejected and merely mechanical candidates upstream.

### 4. Complete corpus coverage

- Run V11 for S2-S86.
- Use pericopes for dense/long surahs and produce final cross-pericope
  integration.
- Normalize all V11 schema generations into one chain schema.
- Validate the staged V12 occurrence, branch, root, ayah, source, and snapshot joins.
- Add release coverage, provenance manifests, and checksums for staged imports chosen for the next release.
- Complete blind first-pass network v3 review for the 18 remaining eligible
  surahs, then freeze an adjudication contract before promoting any channels.

### 5. Build accepted inter-surah relations

Use two first-class discovery routes.

**Ayah-window cluster match**

1. Start from accepted V12 primary/secondary branches and the plus/minus 2 and
   plus/minus 5 context.
2. Retrieve cross-root semantic neighbors with Quran-SLM/Neo and aggregate them
   into compact target ayah windows.
3. Prefer multiple aligned mechanisms, window agreement, mechanism
   preservation, and baseline/Neo agreement.
4. Treat same-root recurrence as a landing zone whose nearby ayahs may complete
   the concept, never as sufficient evidence by itself.
5. Verify the target occurrence with V12 and `word_analysis`.

**V11 image-chain match**

1. Use an accepted source chain as a topology template.
2. Align nodes with Quran-only and full-Furūq Neo similarity.
3. Require compatible QNet edges and preserve meaningful order, reversal, or
   transformation.
4. As an initial pilot gate, require roughly three aligned nodes or two strong
   connected edges; calibrate this against reviewed examples.
5. Anchor both sides to Quran occurrences through V12/`word_analysis`.

Furūq-only branches can be one-hop semantic mediators between Quran-attested
branches. They cannot be Quran endpoints, occurrence evidence, or commentary
claims. Penalize generic hubs. Agreement between Quran-only and full-Furūq
retrieval is stronger than a full-network-only hit.

Semantic scores and QNet paths generate candidates; they do not establish
relations. Only reviewed relations enter `quran-data`.

### 6. Render commentary

- Ayah commentary combines the final word analysis, accepted V12
  primary/secondary activation, and accepted inter-surah relations.
- Surah commentary combines accepted V11 channels/image chains and reviewed
  network relations.
- V3 synthesis renders those records into prose under the layered
  `_prose` architecture.
- Every commentary claim points back to stable claim, chain, relation, ayah,
  root, and branch IDs. Prose is never the sole evidence store.

## Future artifacts to bring here

Paths are provisional until each schema is frozen.

| Dataset | Proposed location | Minimum promotion condition |
|---|---|---|
| Root encyclopedia entries | `data/dictionary/<locale>/` | Complete reviewed Quranic root-envelope coverage, deterministic export, frozen branch snapshot |
| Translation glosses | `data/translation/glosses/locales/<locale>/` | Reviewed locale gloss results with explicit entry coverage and exceptions |
| Ayah activation ledger | `data/analysis/ayah-activation/` | Staged V12 support exists; formal release requires schema, join validation, manifests, checksums |
| Surah image chains | `data/analysis/surah-image-chains/` | Accepted normalized chains for all 114 surahs with occurrence anchors |
| Inter-surah relations | `data/relations/inter-surah/` | Reviewed relation ledger with reconstructable evidence and snapshot IDs |
| Inter-ayah focus reviews | `data/analysis/inter-ayah/` | Complete 6,236 TSV outputs, schema-clean rows, and explicit evaluation-vs-truth boundary |
| Ayah commentary | `data/commentary/ayah/` | Final prose plus references to accepted evidence |
| Surah commentary | `data/commentary/surah/` | Final V3 synthesis for all 114 surahs plus evidence references |
| Network snapshot registry | `manifests/network-snapshots.json` | Model, catalog, source hashes, filtering, dimensions, and build provenance |

Do not copy raw reader prose, prompts, packets, V11 candidate graphs, rejected
relations, Study experiments, or dense similarity matrices here. Keep the
rebuildable matrices in `quran-slm`. If runtime semantic search becomes a
consumer requirement, release a separately versioned compact nearest-neighbor
index; otherwise the accepted relation ledger and snapshot manifest are enough.

## Promotion procedure

For each dataset:

1. Freeze its schema and stable-ID/snapshot dependencies in the source repo.
2. Complete generation, review, coverage audit, and deterministic validation
   upstream.
3. Export from a recorded source commit; never hand-edit compiled data here.
4. Validate canonical joins and ensure every exception is explicit.
5. Add the payload and schema, then update `RELEASE.json`,
   `manifests/coverage.json`, `manifests/provenance.json`, and
   `CHECKSUMS.sha256` in the same release change.
6. Tag the release so earlier accepted states remain in Git history rather than
   parallel version directories.

## Missing channels to plan explicitly

Root/branch networks will not recover every useful Quran relation. Before
calling extended commentary complete, add separately gated discovery for:

- proper names, pronouns, and referent threads;
- formula and phrase recurrence;
- discourse-person shifts; and
- syntactic or structural parallels.

The useful Study/V10 labels—such as image chain, bridge, echo, person, forward,
formula, activation, and chain—may seed the relation taxonomy after each label
has a precise contract. Study's generated relations remain calibration material,
not production evidence.

## Definition of done

The next full commentary release is ready when:

- one canonical lexical snapshot and all required crosswalks are frozen;
- Dictionary V2 has reviewed target-language entry and gloss coverage, explicit exceptions, and deterministic projections;
- V11 has accepted, occurrence-anchored chain coverage for all 114 surahs;
- the staged V12 coverage ledger is release-validated;
- inter-surah relations pass review and target-side contextual verification;
- non-root relation channels have either been implemented or declared outside
  the release scope;
- ayah and surah prose can be traced back to accepted evidence; and
- every imported artifact passes the normal `quran-data` release gate.
