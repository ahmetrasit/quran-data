# Spending ledger

Every real network call `synthesize_tts_chunks.py` makes -- and every time it
materializes audio from an already-cached response instead of calling the
API -- gets one line here. This is the only place in the pipeline that
touches the network, so it's the only place that logs: `prepare_*.py` and
`reuse_recitation_references.py` never call the API and never write here.

## Layout

One append-only JSONL file per UTC calendar day:

```text
_audio/ledger/
  2026-08-01.jsonl
  2026-08-02.jsonl
  ...
```

Never overwritten, never rewritten -- only appended to, one line per chunk
processed. Safe to `cat`, `tail -f`, or `wc -l` while a run is in progress.

## Schema

One JSON object per line:

```json
{
  "timestamp": "2026-08-01T03:22:41Z",
  "event": "synthesized",
  "collection": "ayah",
  "surahId": "S100",
  "chunkId": "sec-001-p-002",
  "kind": "paragraph",
  "requestSha256": "b447fd9a...",
  "textCharCount": 531,
  "promptCharCount": 604,
  "durationSeconds": 12.34,
  "audioTokens": 308.5,
  "inputTokensEst": 283.75,
  "billedInputUsd": 0.000284,
  "billedOutputUsd": 0.00617,
  "billedTotalUsd": 0.006454
}
```

| field | meaning |
| --- | --- |
| `timestamp` | UTC, when this chunk finished processing |
| `event` | `synthesized` (real paid API call) / `cached` (matching response already on disk -- e.g. a prior run, or seeded by `reuse_recitation_references.py` -- materialized locally, zero new cost) / `failed` (API returned an error, zero cost, see `error`) |
| `collection` | `recitation` / `ayah` / `summary` / `surah`, read from the surah folder's parent directory name |
| `surahId`, `chunkId`, `kind` | identify the chunk, same as in that folder's `chunks.jsonl` |
| `requestSha256` | ties this entry back to the exact request that was (or would have been) sent |
| `textCharCount`, `promptCharCount` | characters actually sent, body text and the fixed narrator prompt separately |
| `durationSeconds` | **measured**, from the real decoded audio -- not estimated, for both `synthesized` and `cached` events |
| `audioTokens` | `durationSeconds * 25` -- exact, since duration is measured, not guessed |
| `inputTokensEst` | `(textCharCount + promptCharCount) / 4` -- a **rough estimate**; the Cloud TTS REST response used here carries no token-usage field the way a Gemini `generateContent` call would. Input cost is under 2% of total spend, so this doesn't need to be exact. |
| `billedInputUsd`, `billedOutputUsd`, `billedTotalUsd` | actual dollars charged for this entry. **Zero for `cached` and `failed` events** -- no new API call means no new spend, even though duration/tokens are still recorded for reference. |
| `error` | only present on `failed` events |

## Pricing basis

$1.00 / 1M input tokens, $20.00 / 1M output audio tokens, 25 audio tokens = 1
second of audio. Verified against three independent sources on 2026-07-31
(OpenRouter, LLMReference, ALM Corp) -- see conversation history. Preview
model pricing can change; re-verify before trusting this ledger's totals for
a large run if much time has passed. The constants live in one place,
`tts_common.py`'s `COST_PER_M_INPUT_TOKENS_USD` / `COST_PER_M_OUTPUT_TOKENS_USD`
/ `AUDIO_TOKENS_PER_SECOND`, if they ever need updating.

## Checking your spend

```bash
cd _audio/scripts
python3 ledger_summary.py                    # totals across every ledger file
python3 ledger_summary.py --collection ayah   # filter to one collection
python3 ledger_summary.py --surah S100        # filter to one surah
```

Or by hand, e.g. total actually billed today:

```bash
python3 -c "
import json
total = sum(json.loads(l)['billedTotalUsd'] for l in open('2026-08-01.jsonl', encoding='utf-8'))
print(f'\${total:.4f}')
"
```
