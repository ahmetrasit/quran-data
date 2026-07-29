# QAC to furuq_v4 Root Map Schema

Status: staged root-level gateway.

This SQLite database resolves QAC root keys to furuq_v4 root ids and supports
the reverse lookup from furuq_v4 root ids back to QAC roots. It is the required
gateway for root-level joins between QAC morphology and furuq_v4.

Do not use `qac-v4.sqlite.gz` for root identity resolution. That artifact is a
form-level bridge from QAC morpheme occurrences to V4 form handles.

## Tables

### `qac_root_map`

One row per QAC root.

Important fields:

- `qac_root_norm`: spaced Arabic root key.
- `qac_root_join_key`: unspaced root key.
- `qac_total_occurrences`: QAC rooted morpheme count for this root.
- `matched_occurrences`: occurrence count matched through the frozen/MASAQ
  bridge.
- `mapping_status`: `unique`, `split`, or `no_frozen_rooted_surface_match`.
- `dominant_furuq_root_id`: highest-count furuq target when one exists.
- `dominant_furuq_root_norm`: furuq root norm for the dominant target.
- `dominant_resolution`: how the dominant target resolved to furuq_v4.
- `targets_raw`: packed source target record retained for provenance.

### `qac_furuq_targets`

Exploded target rows for QAC roots with one or more frozen/MASAQ targets.

Important fields:

- `qac_root_norm`
- `target_rank`: count-ranked target position.
- `frozen_root_norm`: root from frozen/MASAQ evidence.
- `furuq_root_id`: furuq_v4 root id, blank when missing.
- `furuq_root_norm`
- `furuq_source_root_norm`
- `furuq_resolution`
- `occurrences`: matched occurrence count for this target.
- `is_dominant`: `1` for the count-dominant target.

## Views

### `qac_to_furuq`

All-status QAC lookup view. This is the default gateway view.

It includes all 1,642 QAC roots. Roots without a furuq target are retained with
`has_furuq_root=0` and `unmapped_reason` populated.

### `qac_to_furuq_mapped`

Mapped-only QAC lookup view.

Use this only when the consumer explicitly wants rows with a nonblank
`furuq_root_id`.

### `furuq_to_qac`

Reverse lookup from furuq_v4 root id to QAC root rows. Split mappings remain
visible through `target_rank`, `frozen_root_norm`, `furuq_resolution`,
`target_occurrences`, and `is_dominant`.

## Consumer Rule

Root-level QAC/furuq joins must use this database as the gateway.

Recommended behavior:

- `unique`: safe direct root-id join.
- `split`: preserve all target root ids; use `is_dominant=1` only as a display
  default or when a workflow explicitly permits dominant-only behavior.
- `no_frozen_rooted_surface_match`: known QAC root without frozen/MASAQ
  same-surface evidence; do not treat as equivalent to a proven furuq target.
- `has_furuq_root=0`: known unmapped or missing furuq root target.

## Example Queries

Forward lookup:

```sql
SELECT *
FROM qac_to_furuq
WHERE qac_root_norm = 'ل ف و'
ORDER BY target_rank;
```

Reverse lookup:

```sql
SELECT *
FROM furuq_to_qac
WHERE furuq_root_id = 'root_001366'
ORDER BY qac_root_norm, target_rank;
```
