# Production roadmap

Status: 2026-07-21

This is the direction for future `quran-data` releases. `RELEASE.json` remains
the authority for what is available now.

## Immediate decision

Yes: complete V11 for all 114 surahs before publishing a corpus-complete
surah-image-chain or surah-commentary dataset.

Current V11 source coverage is 29 surahs: S1 and S87-S114. The remaining bulk
run is S2-S86, or 85 surahs. For long surahs, completion includes pericope runs
and a reviewed cross-pericope integration; the existence of a run directory is
not sufficient.

Do not wait for those 85 runs to test the design. Freeze and validate the chain
and inter-surah contracts on the existing 29-surah set first. This prevents a
schema or retrieval mistake from being repeated across the corpus.

V12 is different: standard/plus-minus-2 source runs exist for all 114 surahs,
while the eleven-ayah/plus-minus-5 treatment currently exists for S1-S21. If
the final policy requires both treatments for every surah, S22-S114 (93 surahs)
still need that second run. Decide this after the pilot: either require dual-run
adjudication corpus-wide, or use the plus/minus-5 treatment on demand for
retrieved/high-value cases and report its coverage explicitly. In either case,
the main remaining V12 task is canonical cross-run extraction, grading,
reconciliation, and publication-role assignment. The current
`_status/v12_cross_run` work is a calibration fixture, not yet a corpus-wide
accepted activation dataset.

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

### 1. Freeze lexical identity

This is the first blocker.

1. Select one canonical Furūq/V4 branch database and record its SHA-256,
   filtering rules, root count, branch count, and accepted/contaminated policy.
2. Make `root_id` and `branch_id` stable against that snapshot.
3. Build an explicit crosswalk for any already-produced artifact that used an
   older snapshot; rebuild when a safe one-to-one crosswalk is impossible.
4. Rebuild or synchronize Dictionary packets, V12 inputs, QNet, and Quran-SLM
   indexes against the frozen snapshot before publication.

This is not theoretical drift: the latent-activation documentation records an
older 18,781-clean-card input with SHA-256
`318d7128daa25e15dc753ea7cb035ed5b145989c22a8d555a7f6986443d4c0af`,
while Dictionary records an 18,785-clean-card input with SHA-256
`1099db0d56515d2eb3e8d72f104f2e338c2c9a8c1fa6abbb046406d3b327e722`.
Never join them by branch ID without snapshot verification.

### 2. Finish Dictionary V2

Dictionary V2 already has the right architecture: one validated master entry
per root and deterministic consumer projections. Complete it rather than
designing another entry format.

The current checkpoint is 140 Turkish entries, all drafts, and no English
entries. Treat these as workflow/migration material until reviewed. For the
first Quran release, complete every QAC-attested root envelope. Full entries for
Furūq-only roots are optional later coverage; those branches can still serve as
verified neighbor evidence and semantic mediators.

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

### 3. Freeze analysis contracts and run a pilot

Before bulk V11 completion, use S1 plus a representative selection from
S87-S114 to freeze:

- the accepted V11 image-chain contract;
- the V12 cross-run activation contract;
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
- Complete V12 cross-run adjudication for every intended ayah. If full
  corpus-wide adjudication is too expensive, retrieve from the raw runs and
  adjudicate the top candidates on demand, while recording coverage honestly.
- If dual-run V12 coverage is selected, generate the plus/minus-5 treatment for
  S22-S114 before closing that coverage ledger.
- Validate all occurrence, branch, root, ayah, and source joins.

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
| Root encyclopedia master and projections | `data/lexicon/root-encyclopedia/` | Complete reviewed coverage, deterministic export, frozen branch snapshot |
| Ayah activation ledger | `data/analysis/ayah-activation/` | Accepted cross-run claims, branch evidence, roles, and explicit coverage |
| Surah image chains | `data/analysis/surah-image-chains/` | Accepted normalized chains for all 114 surahs with occurrence anchors |
| Inter-surah relations | `data/relations/inter-surah/` | Reviewed relation ledger with reconstructable evidence and snapshot IDs |
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
- Dictionary V2 has reviewed target-language coverage and deterministic
  projections;
- V11 has accepted, occurrence-anchored chain coverage for all 114 surahs;
- V12 has an explicit accepted-activation coverage ledger;
- inter-surah relations pass review and target-side contextual verification;
- non-root relation channels have either been implemented or declared outside
  the release scope;
- ayah and surah prose can be traced back to accepted evidence; and
- every imported artifact passes the normal `quran-data` release gate.
