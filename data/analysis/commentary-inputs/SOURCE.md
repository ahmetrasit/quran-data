# Commentary Inputs

Staged on 2026-07-30 from `../latent_activation`.

This directory holds analysis inputs used by commentary generation. These are
not final prose artifacts, so they are kept under `data/analysis/` rather than
`data/commentary/`.

## Layout

```text
data/analysis/commentary-inputs/
  focus-trace-hermetic/
    tr/
      runs/
        sNNN/
          packets/
            S_A.packet.json
          readers/
            reader_hft_a/
              S_A.focus_trace.json
              S_A.<variant>.focus_trace.json

  v11-surah-activation/
    run/
      sNNN/
        ...
```

## Source

Source repository:

```text
../latent_activation
commit a698343d1eb3859992bebe1d5e61f7cc7797b6d9
```

Copied source paths:

- `focus_trace/runs/*/readers/*/*.focus_trace.json`
- matching `focus_trace/runs/*/packets/*.packet.json`
- selected `focus_trace/runs/s100/` run metadata:
  - `COLD_HANDOFF.md`
  - `PRE_RUN_REPORT.md`
  - `RUN_MANIFEST.json`
- `v11/run/`

Source paths intentionally not copied:

- `focus_trace/prompts/`
- `focus_trace/scripts/`
- `focus_trace/schemas/`
- `focus_trace` packet-size reports
- `v11/prompts/`
- `v11/audits/`
- `.DS_Store` files

## Counts

Copied focus-trace hermetic files:

| Type | Count |
| --- | ---: |
| Reader output JSON, `*.focus_trace.json` | 1,769 |
| Matching packet JSON, `*.packet.json` | 1,759 |
| Run metadata files | 3 |

Copied V11 run files:

| Type | Count |
| --- | ---: |
| `v11/run/` files, excluding `.DS_Store` | 657 |

## V12 Inputs

The V12 input families used by layer-2 commentary were already staged in
`quran-data` before this commentary import, so they are not duplicated under
`commentary-inputs/`.

Use these existing locations:

```text
data/analysis/ayah-activation/v12-tr/
data/analysis/ayah-activation/v12-tr-11ayah/
data/analysis/ayah-activation/v12-cross-run/tr/
```

Current local counts at the time of this note:

| V12 family | Path | Count |
| --- | --- | ---: |
| Regular full-context V12 | `data/analysis/ayah-activation/v12-tr/` | 1,043 files |
| Plus/minus-5 wide V12 | `data/analysis/ayah-activation/v12-tr-11ayah/` | 233 files |
| Cross-run publication findings | `data/analysis/ayah-activation/v12-cross-run/tr/` | 114 files |

## Notes

The source `focus_trace` run directories used unpadded surah names such as
`s1`, `s12`, and `s100`. The copied quran-data layout normalizes these to
three-digit surah directories such as `s001`, `s012`, and `s100`.

The focus-trace files are Turkish workflow artifacts in the sense that they were
used by Turkish commentary generation, but their JSON structural keys and many
generated labels are English. V11 Markdown and JSON files likewise preserve the
language and structure emitted by the upstream run.
