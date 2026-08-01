# Audio pipeline

Turns Turkish reader content into narrated audio via Google TTS
(`gemini-3.1-flash-tts-preview`, voice `Rasalgethi`, `tr-TR`). Two source
families, four output collections, one shared send/receive step.

```text
_audio/
  scripts/
    tts_common.py                     shared helpers (no network calls)
    prepare_recitation_chunks.py      Group 1 prepare
    prepare_commentary_chunks.py      Group 2 prepare (ayah / summary / surah)
    reuse_recitation_references.py    seeds ayah/summary reference audio from recitation
    synthesize_tts_chunks.py          shared send/receive (both groups)
    run_tts_batch.py                  bounded parallel planner/runner
  tests/test_audio_pipeline.py        offline workflow tests
  audio/
    recitation/
      surah-names.tr.tsv           Turkish surah-name lookup, hand-authored
      besmele/                     ONE shared basmalah clip, reused before every
                                    surah except S001 and S009 -- see below
      S001/, S002/, ...            one folder per surah, see shape below
    ayah/S001/, ...
    summary/S001/, ...
    surah/S001/, ...
  audio-canary/ayah/S001/          old one-ayah pilot smoke test, kept for reference
```

## The two groups

**Group 1 -- recitation.** Standalone per-ayah audio: spoken surah name +
ayah ordinal + the canonical Arabic ayah text, nothing else. Source is just
`data/text/quran-uthmani.tsv` (Arabic) and `audio/recitation/surah-names.tr.tsv`
(Turkish names) -- no prose_generation commentary involved.

Basmalah is a special case: `quran-uthmani.tsv` carries an explicit `:0` row
before every surah except al-Fatiha (whose own ayah 1 *is* the basmalah) and
at-Tawbah (which has none). All 112 of those rows share one identical
Arabic string (verified), so per-surah sections skip `:0` rows entirely and
`prepare_recitation_chunks.py --besmele` builds exactly one shared,
surah-agnostic clip at `audio/recitation/besmele/` instead of 112
near-duplicate requests. Playback/app assembly is expected to prepend that
one clip before every surah's own recitation, except S001 and S009 -- these
scripts do not splice it into each surah's own folder.

**Group 2 -- commentary.** Three tiers, all sourced from
`data/commentary/` (Turkish commentary staged from the sibling
`prose_generation` repo -- see `data/commentary/README.md` for that import):

| collection | source | shape |
| --- | --- | --- |
| `ayah` | `ayah/detailed/tr/sNNN/{S}_{A}.prose.tr.md` | one section per ayah: spoken ayah reference, then full analytical prose |
| `summary` | `ayah/summary/tr/sNNN/{S}_{A}.prose.summary.tr.md` | same per-ayah shape, compact prose |
| `surah` | `surah/detailed/tr/sNNN/{S}.surah-reading.tr.md` | one section for the whole surah, continuous essay, no per-ayah Arabic |

Both prepare scripts are pure text processing: no network calls, safe to
re-run any number of times, deterministic given the same source files. Full
design rationale (why titles are spelled-out ordinals in commentary but
digit form in recitation, how the ayah-0 basmalah row is labelled, why
`ayah`/`summary`/`surah` have different section shapes, the exact
`{ar,tr,gloss}` -> `Arabic (gloss)` conversion rule) lives in the module
docstrings at the top of each script -- read those before changing behavior,
they are the actual spec.

## Avoiding duplicate spend: `reuse_recitation_references.py`

Every `ayah_reference` chunk in the `ayah`/`summary` collections is
byte-for-byte identical to its counterpart in `recitation` -- same
`ttsText`, same strict recitation prompt/voice/config, hence the same
`requestSha256` (both
are built from the same `ayah_spoken_label()` + Arabic text). Verified
against the full real corpus: 1,393/1,393 `ayah` reference chunks and
979/979 `summary` reference chunks match recitation's exactly. Left alone,
synthesizing all three collections would pay for the same short "Fatiha
birinci ayet. `<arabic>`"-style clip up to three times per ayah.

`reuse_recitation_references.py` closes that gap without modifying
`synthesize_tts_chunks.py` at all: it copies an already-synthesized
`responses/*.json` from `recitation/<surahId>/` into the matching
`ayah|summary/<surahId>/responses/` slot whenever the request hash matches.
Synth's own existing idempotency check then recognizes the seeded response
on its next run and materializes wav/mp3 locally -- zero API calls for those
chunks. It writes only into `responses/`; chunks.jsonl/manifest.json are
still updated by the normal synth run, exactly as if that chunk had been
freshly synthesized.

This only works for ayahs recitation has *already* synthesized -- run
recitation through the synthesizer before running this script. See "Running
it" below for the full recommended order.

## The shared step: `synthesize_tts_chunks.py`

Collection-agnostic. Reads `<surah_dir>/chunks.jsonl` + `manifest.json`,
validates the complete collection and exact request bytes offline, sends each
confirmed unsent `requests/*.json` to Google TTS, writes
`responses/*.json`, decodes WAV into `originals/wav/`, converts to MP3 in
`originals/mp3/` (`ffmpeg` or macOS `afconvert` required), and joins each
section's paragraph WAVs into `sections/wav/` + `sections/mp3/`. It
automatically appends attempt and terminal events to
`_audio/ledger/YYYY-MM-DD.jsonl`. Re-running skips chunks whose response still
matches the prepared request.

Requires `gcloud auth login` against a project with Text-to-Speech API
access. The default billing/quota project is `quran-roots`; override it with
`--project-id` or `GOOGLE_CLOUD_PROJECT`.

## Running it

```bash
cd _audio/scripts

# 1. Prepare (no network, no cost, safe to re-run)
python3 prepare_recitation_chunks.py --besmele          # one shared basmalah clip
python3 prepare_recitation_chunks.py --all               # every surah, recitation
python3 prepare_commentary_chunks.py ayah --all
python3 prepare_commentary_chunks.py summary --all
python3 prepare_commentary_chunks.py surah --all
python3 prepare_recitation_chunks.py 1 --dry-run          # inspect without writing

# 2. Preflight recitation FIRST. This is offline and prints exact confirmations.
python3 synthesize_tts_chunks.py ../audio/recitation/S001 --limit 1 --dry-run

# 3. Run that canary only after reviewing preflight output.
python3 synthesize_tts_chunks.py ../audio/recitation/S001 --limit 1 \
  --confirm-remote <requestSetSha256> \
  --confirm-cost-usd <maximumCostUsd> \
  --max-cost-usd <approved-ceiling>

# 4. Seed ayah/summary reference chunks from completed recitation audio.
python3 reuse_recitation_references.py ayah S001
python3 reuse_recitation_references.py summary S001

# 5. Preflight commentary. Reused references are excluded from remote calls.
python3 synthesize_tts_chunks.py ../audio/ayah/S001 --dry-run
```

The batch runner executes distinct folders in parallel with a bounded worker
count. First create and review an offline plan, then use the exact plan hash
and aggregate maximum cost it prints:

```bash
python3 run_tts_batch.py recitation --dry-run --workers 4 \
  --write-plan /tmp/recitation-plan.json

python3 run_tts_batch.py --plan /tmp/recitation-plan.json --workers 4 \
  --confirm-plan <planSha256> \
  --confirm-cost-usd <maximumCostUsd> \
  --max-cost-usd <approved-ceiling>
```

Use `--surah-id S001` while planning to select specific folders, or `--limit
1` for a one-chunk-per-folder canary. If a request or cached response changes,
execution refuses the reviewed plan and requires a fresh preflight.

`--all` mode in the prepare scripts never aborts the whole run on one bad
surah: it logs the failure to stderr, keeps going, and the process exits
non-zero only if at least one surah failed. Check stderr for a
`processed=.. skipped=.. failed=..` summary line.

## Collection locks

Preparation, response reuse, and synthesis automatically take an OS lock on
`<collection>/.tts-generation.lock`. Only the same folder is excluded, so
different surahs and collections can run in parallel. Lock files are
persistent and gitignored; do not create or remove them manually.

## Cost notes

Gemini 3.1 Flash TTS Preview is token-based: $1.00 / 1M input text tokens,
$20.00 / 1M output audio tokens (~25 tokens/sec of audio). Output cost
dominates. Preflight's `maximumCostUsd` uses the provider's maximum input and
output tokens for every pending request; this conservative value is the
required confirmation and ceiling basis. The ledger estimates input tokens
from characters and derives output tokens from measured WAV duration.

## Verifying a prepare script after editing it

Before trusting a change:

1. Run `python3 -m unittest discover -s ../tests -v` from `_audio/scripts`.
2. Run `python3 tts_common.py` to inspect the Turkish ordinal table.
3. Run `python3 prepare_commentary_chunks.py ayah 1 --dry-run` and diff its
   `text`/`ttsText` fields against the real, already-shipped
   `audio/ayah/S001/chunks.jsonl` (git history: commit `c9a4fe5d`) -- every
   paragraph body should match exactly; only the surah-name spelling should
   differ (see git blame / conversation history for why "Fatiha" became
   "Fâtiha").
4. Run every prepare script with `--all --dry-run` and confirm
   `failed=0` across the whole real corpus.
5. Offline-validate a real prepared folder with sender preflight:

   ```bash
   python3 synthesize_tts_chunks.py ../audio/ayah/S001 --dry-run
   ```

6. To check `reuse_recitation_references.py` without spending money: fabricate
   a valid response (a tiny silent LINEAR16/24kHz/mono WAV, base64-encoded,
   with `_requestMetadata` copied from a real chunk's five hash fields) under
   a copied `recitation/<surahId>/responses/`, run the reuse script with
   `--audio-root` pointed at the copy, then confirm
   `synthesize_tts_chunks.materialize_wav_from_response()` decodes the seeded
   response in `ayah/<surahId>/responses/` with no network call.

All checks passed against the full real corpus (53 `ayah`, 37 `summary`, 45
`surah`, 114 `recitation` surahs + 1 shared besmele; 73/73 requests
hash-validated for S001's `ayah` folder) when this pipeline was built.

## Why not reuse `prepare_tts_chunks.py`?

`latent_activation/_audio/scripts/prepare_tts_chunks.py` looks like it
should be the commentary preparer, since it lives in the sibling repo's
`_audio/scripts/` too -- it is not. Its `validate_v3_source()` hard-rejects
any path that isn't `v3/run/<run>/<n>-publication.jsonl`, and its parser
(opening/finding/closing records, GÜÇLÜ/ORTA/ZAYIF grade stripping) targets
`latent_activation`'s own network-v3 discovery publications, a different
upstream artifact with nothing to do with `prose_generation`'s ayah/summary/surah
commentary. `prepare_recitation_chunks.py` and `prepare_commentary_chunks.py`
in this repo are the actual commentary/recitation preparers; only
`synthesize_tts_chunks.py` is shared across both `_audio/` trees, because it
is genuinely source-agnostic.
