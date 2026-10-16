# Stage 50 — strict joint trace audit

The script `tools/validate_joint_trace.py` checks the new stage49 event
schema, adjacent metadata, completeness, sequence continuity, frame order,
per-event bank labeling and MMC3 R6/R7 mapping replay.

```sh
python3 tools/validate_joint_trace.py private/first_level/stage49_joint.tsv --meta private/first_level/stage49_joint.meta.txt --out private/first_level/stage50_joint_audit.json
```

Any dropped events, mismatched counts, wrong banks or falsified provenance
cause rejection. The validator deliberately reports
`cpu_read_causality_proven=false`: an EXEC hook followed by a READ callback
does not identify the instruction responsible for the read. The available
hooks cover only five selected PCs. No original game capture has been
validated, so this audit cannot restore real level geometry.

Six ROM-free Python tests cover a valid log, false bank, missing event,
overflow, forged metadata and an uninstrumented EXEC PC. These tests are
included in the existing Python unittest-discovery CI step, but their
passing run has not yet been confirmed.
