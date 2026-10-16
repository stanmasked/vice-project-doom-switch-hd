# Stage 54 — unified CPU-context capture validation

Run the strict stage53 TSV and adjacent metadata audit:

```sh
python3 tools/validate_joint_cpu_context.py private/first_level/stage53_joint_context.tsv --meta private/first_level/stage53_joint_context.meta.txt --out private/first_level/stage54_context_audit.json
```

The audit rejects incomplete captures, missing or contradictory metadata,
invalid A/X/Y/S/P register fields, event gaps, malformed addresses and
incorrect MMC3 bank replay. Unknown register values remain explicit.
The result always marks instruction read causality and effective addresses
as **not proven**: same-session register sampling is not an instruction
decoder or verified gameplay map.

Seven ROM-free regression tests are discoverable in Python CI. Live FCEUX
read-callback behavior and actual first-level source evidence are not
confirmed; no copyrighted game files are committed.
