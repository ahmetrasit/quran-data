# Spending ledger

`synthesize_tts_chunks.py` creates this ledger automatically. Before every
remote HTTP call it durably appends an `attempted` event; once the outcome is
known it appends a terminal event. Cached materialization is logged as well.
Preparation and response reuse never create spending entries.

## Layout

One append-only JSONL file is used per UTC day:

```text
_audio/ledger/2026-08-01.jsonl
```

Parallel workers serialize each append with `flock`, then flush and `fsync`
it. Ledger files are never rewritten.

## Events

| event | meaning |
| --- | --- |
| `attempted` | persisted immediately before a remote request; billing is possible until a terminal event appears |
| `synthesized` | valid audio returned and the remote attempt is known to be new spend |
| `synthesized_recovered` | a saved valid response repaired a missing terminal ledger entry |
| `cached` | a matching response was already present; no new remote spend |
| `failed` | the API returned a known error response |
| `unknown` | transport may have completed, but no trustworthy result was committed |

`attemptId` joins the attempted and terminal records. An unknown outcome is
also persisted in the chunk/manifest and cannot be resent without
`--reconcile-unknown` plus a new request and cost confirmation.

## Schema

A synthesized entry includes:

```json
{
  "timestamp": "2026-08-01T03:22:41Z",
  "event": "synthesized",
  "attemptId": "7b14...",
  "projectId": "quran-roots",
  "collection": "ayah",
  "surahId": "S100",
  "chunkId": "sec-001-p-002",
  "kind": "paragraph",
  "requestSha256": "b447fd9a...",
  "textCharCount": 531,
  "promptCharCount": 604,
  "estimatedInputTokens": 284,
  "durationSeconds": 12.34,
  "outputAudioTokens": "308.500",
  "newSpend": true,
  "possibleNewSpend": false,
  "estimatedBilledInputUsd": "0.000284",
  "billedOutputUsd": "0.006170",
  "estimatedBilledTotalUsd": "0.006454"
}
```

Input tokens are estimated as the ceiling of prompt plus text characters
divided by four because this REST response does not return input usage.
Output tokens are derived from measured audio duration at 25 tokens/second.
The pricing constants are $1.00 per million input text tokens and $20.00 per
million output audio tokens. Re-check official pricing before a later large
run because this is a preview model.

## Checking spend

```bash
cd _audio/scripts
python3 ledger_summary.py
python3 ledger_summary.py --collection ayah
python3 ledger_summary.py --surah S100
```

The summary supports legacy and current entries, labels totals as estimates,
and reports remote attempts that lack a known terminal event.
