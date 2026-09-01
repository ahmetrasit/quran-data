# Quran Project Ecosystem Status

Snapshot date: 2026-08-31

This document records the latest verified state of `quran-data` and its sibling
repositories. It is an operational status snapshot, not a new data release.
The current release remains `2026.07.21`; use `RELEASE.json`,
`manifests/coverage.json`, and `manifests/provenance.json` for the exact released
payload.

## Authority Order

When status documents disagree, use this order:

1. `quran-data/RELEASE.json` and manifests for already released datasets.
2. The newest dated status file and validated outputs in the owning source repo.
3. Older roadmaps, migration plans, and root-level README status sections.

Several source-repo documents lag the July 23-24 outputs. In particular:

- `quran-roots/README.md` still says the iOS app is not scaffolded, although a
  real SwiftUI app, package, tests, pack tools, and bundled content exist.
- `word_analysis/README.md` still says "production candidate", although all
  6,236 canonical outputs are complete, validate, and are released here.
- `quran-note-app/progress.md` contains an obsolete warning that a missing
  `config/appSettings` document keeps public access closed; the current store
  defaults `authGateEnabled` to `false`.

## Main Project Shape

The project has three distinct centers:

| Center | Role |
| --- | --- |
| `quran-roots` | Research/build/review factory and intended curated iOS product |
| `quran-data` | Canonical, consumer-facing, final-only release repository |
| `quran-note-app` | Existing comprehensive web experience for advanced use |

The intended flow is:

```text
source and synthesis repos
  -> reviewed, contract-stable artifacts
  -> quran-data release
  -> dictionary, web, mobile, book, and other consumers
```

Products should consume `quran-data` contracts. They should not depend on raw
agent packets, source-repo working directories, or machine-specific absolute
paths.

## Readiness Summary

| Repository or artifact | State | Current conclusion |
| --- | --- | --- |
| `quran-data` release `2026.07.21` | READY, local release | Current payload is complete and checksum-valid |
| `word_analysis` word outputs | READY | 6,236 of 6,236 outputs validate against their bundles |
| `latent_activation` V12 Turkish publication | COPIED to quran-data | Regular V12 support staged under `data/analysis/ayah-activation/v12-tr/`; plus/minus-5 reader walks staged under `data/analysis/ayah-activation/v12-tr-11ayah/`; final cross-run findings staged under `data/analysis/ayah-activation/v12-cross-run/tr/` with source provenance |
| `quran-slm` engine and local networks | READY as infrastructure | Tested candidate-retrieval substrate, not accepted interpretation truth |
| `quran-slm` inter-ayah focus reviews | COMPLETE staged evaluation corpus | 6,236 of 6,236 directional TSV outputs are schema-clean under `data/analysis/inter-ayah/`; reciprocal-expanded traversal documents live under `data/analysis/inter-ayah/reciprocal/` |
| `dictionary` Turkish entries and glosses | COPIED to quran-data | 1,679 Turkish entry JSON files and 1,572 reviewed Turkish gloss JSON files staged with source provenance |
| `latent_activation` network v3 | GENERATED and copied | 111 eligible surah output folders, 110 review files, and pericopes staged under `data/analysis/channels/network-v3/`; still candidate data pending blind review/adjudication |
| `quran-note-app` | BUILDABLE beta | Builds pass; lint, external Firebase configuration, and emulator tests remain |
| `quran-roots` iOS app | FUNCTIONAL prototype | Pack validation passes; reproducible build, final content, hosting, and device gates remain |
| `study` | LEGACY/reference | Explicitly excluded from production release inputs |

No end-user product is fully release-ready from the current checkouts. The
strongest complete deliverable is the `quran-data` release itself, followed by
the production word-analysis corpus, the staged Turkish dictionary/gloss payloads, and the staged Turkish V12 publication artifacts.

## Current Quran Data Release

Release: `2026.07.21`

Released:

- Quran text: 6,236 numbered ayahs plus 112 prefatory basmalahs;
- QAC morphology and indexes;
- V4 dictionary and positive handles;
- QAC-to-V4 bridge;
- Furuq/V4 lexical database;
- reviewed attachment enrichment `final_v3`, all 114 surahs;
- reviewed contextual profiles `final_v3`, all 114 surahs;
- production word analysis, all 6,236 ayahs.

Staged but not yet reflected in `RELEASE.json`, manifests, checksums, and a release tag:

- Turkish dictionary entries, 1,679 JSON files under `data/dictionary/tr/`;
- Turkish translation glosses, 1,572 reviewed JSON files under `data/translation/glosses/locales/tr/`;
- V12 ayah activation/publication support, 114 surahs plus full-context packets/control directories and 6 focus runs under `data/analysis/ayah-activation/v12-tr/`;
- V12 plus/minus-5 reader walks, 114 surahs under `data/analysis/ayah-activation/v12-tr-11ayah/`;
- V12 cross-run publication findings, 114 Turkish per-surah JSON files under `data/analysis/ayah-activation/v12-cross-run/tr/`;
- network v3 generated candidate outputs, 111 eligible surahs plus 110 review files and pericopes under `data/analysis/channels/network-v3/`;
- inter-ayah focus review outputs, 6,236 directional TSVs plus a deterministic reciprocal-expanded projection under `data/analysis/inter-ayah/reciprocal/`.

Still not release-ready:

- accepted network/channel synthesis after blind review and adjudication;
- accepted inter-surah relation adjudication beyond the reciprocal review-evidence projection;
- integrated ayah or surah commentary;
- app-specific product exports.

Repository release operations still pending:

- configure a Git remote for `quran-data`;
- create a release tag for `2026.07.21`;
- define the next release ID only when a new dataset is actually promoted.

## Source Repository Status

### `word_analysis`

Role: final independent word-level reader-payoff analysis.

Verified state:

- 6,236 compact production input bundles exist;
- 6,236 production word outputs exist;
- all 6,236 outputs pass `validate_agent_output` against the corresponding
  bundle;
- the released `quran-data` shards cover all 114 surahs and 6,236 ayahs.

Pending:

- `commentary/production/` contains no canonical production commentary files;
- update the source README to say the word-output corpus is production, not a
  production candidate;
- do not regenerate the released word-analysis corpus unless its contract is
  deliberately versioned.

### `latent_activation`

Role: ayah-attached activation/publication, channel discovery, and future
integrated prose.

V12 Turkish publication is complete:

- canonical regular V12 complete for S001-S114;
- plus/minus-5 V12 complete for S001-S114;
- 114 final `*_ayah_findings_publication.json` files;
- 6,348 publication rows including prefatory basmalahs;
- 12,807 findings;
- all findings use an allowed grade and contain at least one anchor;
- source status declares the deterministic contract production-ready.

The corpus-wide V12 extraction, grading, reconciliation, and publication lane is complete upstream. On 2026-07-27 the regular V12 publication support artifacts were copied into `quran-data/data/analysis/ayah-activation/v12-tr/`; the plus/minus-5 reader-walk family was copied into `quran-data/data/analysis/ayah-activation/v12-tr-11ayah/`; and the compact final Turkish cross-run publication findings were copied into `quran-data/data/analysis/ayah-activation/v12-cross-run/tr/`, all from source commit `f47613506937b980f2708aed73eca9ef776deb65`. The remaining V12 work is release formalization: freeze the public schema, validate joins, add release manifests/checksums, and tag the next release.

Network v3 generation is also complete:

- 111 eligible surahs generated;
- S103, S108, and S110 intentionally excluded by the minimum-span policy;
- 89,199 dense candidates;
- 11,572 dense families;
- 4,157,715 sparse paths;
- 457,281 sparse path families.

Network v3 review remains incomplete:

- 93 of 111 eligible surahs have a first-pass `reader_a_pilot.md`;
- 18 eligible surahs remain: S013-S017, S019-S029, S113, and S114;
- generated families remain candidates until blind review and adjudication;
- the integrated Turkish prose output directory is still empty;
- the first prose plan targets S001, S100, and S103, starting with S103.

Operational caveat at the snapshot:

- local `main` was eight commits ahead of `origin/main`;
- first-pass review files for S050-S066 had uncommitted changes.

### `quran-slm`

Role: Arabic-only lexical branch proximity and conditional path retrieval.

Verified state:

- current Quran/QAC catalog: 10,932 branch cards;
- current Quran/QAC plus Furuq catalog: 18,785 branch cards;
- baseline and Neo ensemble views exist for all 114 surahs;
- test result: 286 passed, 1 skipped.

Boundary:

- this repository is ready as reusable retrieval infrastructure;
- similarity scores and paths nominate candidates;
- they do not establish occurrence-to-sense assignments, accepted channels, or
  commentary claims by themselves.

Inter-ayah focus review outputs were initially copied on 2026-07-27 and later
completed in the repository:

- all 6,236 `focus_*_cutoff_100.tsv` files are staged in `quran-data/data/analysis/inter-ayah/`;
- all 923,267 directional rows have three tab-separated fields;
- the earlier malformed `focus_29_55_cutoff_100.tsv` row is no longer present;
- `data/analysis/inter-ayah/reciprocal/` supplies a deterministic per-ayah view in which every same- or cross-surah source row is discoverable from both endpoints;
- inherited labels are typed nomination, counterevidence, or self-reiteration metadata, not reverse-direction judgments;
- its 6,236 generated documents contain 923,286 directional plus 923,286 mirrored records, and the committed manifest binds every document by hash and count;
- all staged files remain review/evaluation records, not promoted semantic ground truth.

### `dictionary`

Role: comprehensive per-root master encyclopedia entries with deterministic
translation-agent, user-dictionary, and scholar projections.

Verified tooling:

- 77 v2 tests passed;
- 53 legacy/top-level entry tests passed;
- 3,449 deterministic root packet envelopes exist;
- 920 root work directories exist;
- 887 current writer fragments exist.

Content checkpoint:

- 1,679 Turkish dictionary entry JSON files are staged in `quran-data/data/dictionary/tr/`;
- 1,572 Turkish gloss result JSON files are staged in `quran-data/data/translation/glosses/locales/tr/`;
- all copied gloss result records have `status: reviewed`;
- 107 staged Turkish entry envelopes do not yet have copied Turkish gloss results;
- no English entry or gloss payload has been staged in `quran-data`.

Conclusion:

- Turkish dictionary entry coverage for Quranic root envelopes is now copied into `quran-data`;
- Turkish glosses are copied in a locale-compatible translation workflow layout;
- the remaining dictionary work is release formalization, explicit exceptions for the 107 missing gloss envelopes, additional locale exports, and deterministic consumer projections.

### `quran-roots`

Role: meaning-infrastructure factory plus the intended curated iOS product.

Upstream data that is already released through `quran-data`:

- Quran text, QAC, V4, positive handles, QAC-to-V4 bridge, Furuq lexical data,
  attachment `final_v3`, and contextual `final_v3`.

iOS prototype that exists now:

- SwiftUI sources and XcodeGen specification;
- platform-neutral `QuranRootsKit`;
- content store, OTA catalog client, selection persistence, TTS filtering, and
  reader/card UI;
- bundled deep S001 pack;
- bundled light S112, S113, and S114 packs;
- all four bundled packs pass the content validator.

iOS product gaps:

- intended S096 content is still cataloged as `comingSoon`;
- bundled packs contain numerous explicit draft fields;
- light Turkish cards currently expose English content with a notice;
- full RTL locale layout is deferred;
- recitation is a stub;
- the production content endpoint is a placeholder;
- simulator and physical-device verification remain;
- native watchOS and dedicated CarPlay apps are deferred.

Reproducibility blocker:

- `app/tools/build_app_pack.py` hard-codes
  `/Volumes/oz/_projects/word_analysis/outputs/production`;
- that path does not exist in the current workspace;
- a clean pack rebuild fails before writing S112;
- the builder should consume a configurable path or, preferably, a released
  `quran-data` contract.

Local Swift verification blocker:

- `swift test` and `swift build` could not run because the installed Command
  Line Tools expose no usable XCTest platform and the compiler/SDK patch
  versions do not match;
- this is an environment failure, so it neither proves nor disproves the Swift
  code, but the app cannot be certified from this machine until the toolchain
  is corrected.

### `quran-note-app`

Role: comprehensive React/Firebase web application.

Verified:

- client TypeScript/Vite production build passes;
- Firebase Functions TypeScript build passes;
- dependency audit reported zero known vulnerabilities in the installed lock
  set.

Pending:

- ESLint reports 9 errors and 13 warnings;
- Firebase Anonymous Authentication must be enabled for public analytics;
- Firestore and Functions emulator suites were not run;
- Functions declare Node 20 while the audit machine used Node 25;
- the current documentation should remove the obsolete fail-closed
  `appSettings` warning.

This app is a usable product shell, but it is not the canonical data release
and is not release-clean from this checkout.

### `study`

Role: historical monorepo, experiments, and calibration/reference material.

Its April 6 status recorded:

- Phase 3 per-ayah JSON: 54 surahs, 3,539 ayahs, 56.7%;
- Phase 4 guided-discovery JSON: 36 surahs, 2,311 ayahs, 37.1%.

`quran-data/manifests/provenance.json` explicitly excludes Study legacy and
intermediary data. Do not resume Study as the canonical production pipeline.
Migrate a useful artifact only through a current owner, current schema,
validation, provenance, and a normal `quran-data` promotion.

## Verification Record

| Check | Result |
| --- | --- |
| `quran-data` SHA-256 verification | All listed files passed |
| `word_analysis` full output-to-bundle validation | 6,236 passed, 0 failed |
| `quran-slm` pytest suite | 286 passed, 1 skipped |
| `dictionary` v2 unit tests | 77 passed |
| `dictionary` top-level unit tests | 53 passed |
| `latent_activation/network/v3` unit tests | 12 passed |
| `latent_activation/v2.1` unit tests | 13 passed |
| `latent_activation/v3` publication suite | 12 passed, 1 stale exact-prompt-text assertion failed |
| `quran-roots` app content validation | 4 packs passed, no findings |
| `quran-roots` content regeneration | Failed on hard-coded missing sibling path |
| `quran-roots` Swift build/test | Blocked by local SDK/compiler/XCTest setup |
| `quran-note-app` client build | Passed |
| `quran-note-app` Functions build | Passed |
| `quran-note-app` ESLint | Failed: 9 errors, 13 warnings |

The failing latent publication test expects the exact sentence
`Never write or speak a bare spaced root`; the current prompt contains the
semantically equivalent, more explicit sentence
`Never write or speak isolated Arabic root letters separated by spaces`.
Treat this as test/document drift unless the exact old wording is itself a
contract.

## Ordered Next Work

1. Validate the July 27 staged imports and decide the next release ID.
2. Update `RELEASE.json`, `manifests/coverage.json`, `manifests/provenance.json`, and `CHECKSUMS.sha256` for the staged dictionary, gloss, activation, and any accepted analysis payloads chosen for release.
3. Record explicit exceptions for the 107 Turkish entry envelopes without copied Turkish gloss results.
4. Review and adjudicate reciprocal inter-ayah nominations and counterevidence before promoting any relation into an accepted inter-surah ledger.
5. Finish network v3 blind review/adjudication before treating generated channel outputs as accepted interpretation data.
6. Make the iOS pack builder consume released or configurable inputs, then produce a reviewed S001 plus S096 vertical slice without draft content.
7. Build the first integrated Turkish prose slice for S103, with a closed source-finding and placement audit.
8. Correct the local Xcode/Swift toolchain and complete simulator/device, accessibility, RTL, audio, OTA-hosting, and App Store checks.
9. Clear `quran-note-app` lint failures and run its Firebase emulator suites if the web product remains an active release target.
10. Complete V11 coverage and future locale dictionary/gloss exports after the first app and prose vertical slices prove the consumer contracts.

Do not start more word-analysis generation, V12 reader generation, or network
v3 corpus generation. Those lanes are complete. Current effort should go into
review, canonical import, product integration, and release verification.
