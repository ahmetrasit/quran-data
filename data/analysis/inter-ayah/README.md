# Focus-ayah agent-review outputs

Each completed run belongs at:

```text
focus_<surah>_<ayah>_cutoff_100.tsv
```

The Terra High review agent writes this file directly. It is a plain TSV file
with no header. Every line has exactly three tab-separated fields:

```text
strength<TAB>ayah_ref<TAB>short_explanation
```

The first 100 lines are the reviewed candidates in package rank order. Any
later lines are missing-ayah suggestions appended by that same agent after the
fixed follow-up.

The orchestrator does not write the review. Do not add hashes, model or session
details, prompt transcripts, or orchestration metadata to the file.

These are evaluation records, not promoted semantic ground truth. The
`strength` labels describe marginal usefulness in the given order. Suggested
missing ayat are recall hypotheses and must not be inserted automatically into
source networks or future packages.
