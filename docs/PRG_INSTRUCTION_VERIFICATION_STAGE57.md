# Stage 57 — private PRG byte verification

`tools/verify_6502_prg_instruction.py` compares **user-supplied**
instruction bytes with a **local, headerless 128 KiB PRG image** at an
execution-hook CPU PC. It replays SELECT/DATA events up to the selected
EXEC event, resolves MMC3 PRG bank only if observed, and checks the
physical offset. A read crossing an 8 KiB bank window is rejected
rather than silently borrowing bytes from the adjacent image bank.

```sh
python3 tools/verify_6502_prg_instruction.py private/first_level/stage53_joint_context.tsv --meta private/first_level/stage53_joint_context.meta.txt --prg private/game_prg_raw.bin --exec-seq 5 --instruction-hex AD5C83
```

The tool accepts **raw PRG only**, not an entire NES ROM or a zip.
Do not place private ROM/PRG data or outputs inside tracked Git files.
It prints only match status and an offset, **not raw ROM bytes**.

A matching byte sequence establishes consistency with that specific
local PRG file and observed mapper state, not the identity or authenticity
of the image, nor instruction causality or level-data semantics. The
stage53 trace must pass the strict stage54 validator first. Synthetic
tests cover unknown bank, resolved bank, invalid EXEC, wrong image
length, bad input and incomplete event capture. Real FCEUX validation
and level reconstruction remain outstanding.
