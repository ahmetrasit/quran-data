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
`ttsText`, same voice/prompt/config, hence the same `requestSha256` (both
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
sends each unsent `requests/*.json` to Google TTS, writes
`responses/*.json`, decodes WAV into `originals/wav/`, converts to MP3 in
`originals/mp3/` (`ffmpeg` or macOS `afconvert` required), and joins each
section's paragraph WAVs into `sections/wav/` + `sections/mp3/`. Idempotent:
re-running skips any chunk whose response hash still matches its request.

Ported unmodified from
`latent_activation/_audio/scripts/synthesize_tts_chunks.py` (that copy is
the original for `latent_activation`'s own, unrelated network-v3 discovery
pipeline -- the two `_audio/` trees are intentionally decoupled; see the
"why not reuse `prepare_tts_chunks.py`" note below).

Requires `gcloud auth login` against a project with Text-to-Speech API
access (`PROJECT_ID = "quran-roots"` in the script).

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

# 2. Synthesize recitation FIRST -- ayah/summary reuse its reference audio (step 3)
touch ../audio/recitation/S001/.tts-generation.lock       # advisory, see below
python3 synthesize_tts_chunks.py ../audio/recitation/S001 --limit 3   # smoke-test first
python3 synthesize_tts_chunks.py ../audio/recitation/S001
rm ../audio/recitation/S001/.tts-generation.lock

# 3. Seed ayah/summary reference chunks from the recitation audio just generated
python3 reuse_recitation_references.py ayah S001
python3 reuse_recitation_references.py summary S001

# 4. Synthesize ayah/summary -- only pays for what step 3 couldn't seed
touch ../audio/ayah/S001/.tts-generation.lock
python3 synthesize_tts_chunks.py ../audio/ayah/S001 --limit 3
python3 synthesize_tts_chunks.py ../audio/ayah/S001
rm ../audio/ayah/S001/.tts-generation.lock
```

`--all` mode in the prepare scripts never aborts the whole run on one bad
surah: it logs the failure to stderr, keeps going, and the process exits
non-zero only if at least one surah failed. Check stderr for a
`processed=.. skipped=.. failed=..` summary line.

## `.tts-generation.lock`

Advisory only -- `synthesize_tts_chunks.py` does not create, check, or
remove it. `prepare_commentary_chunks.py` / `prepare_recitation_chunks.py`
*do* refuse to run if they find one (`check_generation_lock()` in
`tts_common.py`), to stop a prepare re-run from regenerating requests (and
invalidating in-flight response hashes) while a synthesis run against that
same folder is in progress. The convention: touch the lock file yourself
before starting a synthesis run you're actively driving, remove it when
done.

## Cost notes

Gemini 3.1 Flash TTS Preview is token-based: $1.00 / 1M input text tokens,
$20.00 / 1M output audio tokens (~25 tokens/sec of audio). Output cost
dominates -- always `--limit` a smoke test before running a full surah,
especially `ayah`/`summary` collections whose prose can run long. Full
pricing/format notes: `latent_activation/_audio/tts-generation-spec.md`.

## Verifying a prepare script after editing it

There is no pytest suite for these scripts (they live in `quran-data`, a
data/generation repo, not a code repo with a test runner). Before trusting a
change:

1. `python3 tts_common.py` -- eyeballs the Turkish ordinal table.
2. `python3 prepare_commentary_chunks.py ayah 1 --dry-run` and diff its
   `text`/`ttsText` fields against the real, already-shipped
   `audio/ayah/S001/chunks.jsonl` (git history: commit `c9a4fe5d`) -- every
   paragraph body should match exactly; only the surah-name spelling should
   differ (see git blame / conversation history for why "Fatiha" became
   "Fâtiha").
3. Run every prepare script with `--all --dry-run` and confirm
   `failed=0` across the whole real corpus.
4. Offline-validate a real prepared folder against synth's own hash check,
   without hitting the network or spending money:

   ```python
   import sys; sys.path.insert(0, "scripts")
   from synthesize_tts_chunks import validate_request_file, load_jsonl
   from pathlib import Path
   surah_dir = Path("audio/ayah/S001")
   for chunk in load_jsonl(surah_dir / "chunks.jsonl"):
       validate_request_file(surah_dir / chunk["request"], chunk)  # raises on mismatch
   ```

5. To check `reuse_recitation_references.py` without spending money: fabricate
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
