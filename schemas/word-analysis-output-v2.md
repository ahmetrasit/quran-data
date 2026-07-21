# Word analysis output v2

Each JSONL row is one ayah object with:

```text
schema_version
prompt_version
ref
bundle_id
words[]
```

Each word preserves its aligned QAC reference, display forms, gloss range,
prose, topic decisions, source-row coverage, and review notes. The files are a
lossless compaction of the validated production JSON objects; no semantic field
is removed or rewritten.
