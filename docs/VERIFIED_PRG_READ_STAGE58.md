# Stage 58 — local PRG byte gate for CPU read candidates

`tools/correlate_verified_prg_reads.py` connects the stage57 local
128 KiB headerless PRG byte comparison with the stage56 same-session
read-neighbor checks. It emits candidates **only when** the supplied
instruction bytes match the local PRG at a mapped EXEC event.

```sh
python3 tools/correlate_verified_prg_reads.py private/first_level/stage53_joint_context.tsv --meta private/first_level/stage53_joint_context.meta.txt --prg private/game_prg_raw.bin --exec-seq 5 --instruction-hex AD5C83 --max-gap 3 --out private/first_level/stage58_candidate_audit.json
```

A missing mapper bank, mismatch with the private PRG or incomplete
capture cannot generate candidates. The report contains derived
addresses, statuses and counts, **not any ROM bytes**.

**Limits:** a match against a user-provided PRG file is not independent
ROM authentication. EXEC/read adjacency does not establish which
instruction caused the read; no opcode execution, game stage identity,
camera or map data is proven. Private ROMs and traces stay outside Git.

Four new synthetic regression tests cover a byte match, byte mismatch,
unresolved mapping and incomplete capture. They join the existing Python
test discovery; an executed passing result has not been established.
