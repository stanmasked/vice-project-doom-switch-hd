# Stage138 — delayed ninth sprite at the 8×16 lower-half boundary

[Stage137 native FCEUX run 39124431670](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/39124431670)
confirmed 4 scenarios and 32 XBuf samples, with real OAM status bit
`$20` and the ninth sprite absent from the framebuffer when the first
eight slots are occupied. Full OAM initialization (256 bytes set to
`$FF`) resolved the earlier spurious overflow.

Stage138 introduces a **time-sensitive, source/model test**: the ninth
sprite's Y location is shifted from 120 to 128 so it enters a 16-pixel
sprite scanline only in its lower eight rows. A separate control frees
one earlier OAM slot to prove that the ninth sprite is not intrinsically
transparent or unrenderable.

All ROMs are generated independently with 8×16 PPUCTRL `$38`, the
same self-authored Mapper-4 sprite CHR tiles and complete OAM
initialization. OAM0–7 are normally at Y=120, X=160, whereas OAM8
is at X=64. For `seven_plus_late`, OAM7 instead has Y=`$FF`.

| ROM | Row 124 selected OAM | Overflow 124 | Row 132 selected OAM | Overflow 132 | Expected XBuf X64 (124→132) |
|---|---|---|---|---|---|
| `eight_stable` | 0–7 | No | 0–7 | No | 143→143 |
| `nine_late` | 0–7 | No | 0–7, ninth rejected | Yes | 143→143 |
| `seven_plus_late` | 0–6 | No | 0–6, 8 | No | 143→170 |
| `nine_early` | 0–7, ninth rejected | Yes | 0–7, ninth rejected | Yes | 143→143 |

The table's reference values come from
`tools/audit_stage136_oam_eight_limit.py`, not from any native
framebuffer observation of these new ROMs.

`tools/make_stage138_temporal_oam_rom.py` generates 49,168-byte
synthetic ROMs with the same 16KiB CHR and controlled PRG byte
differences. Six tests in
`tests/test_fceux_stage138_temporal_nine_oam.py` check OAM membership,
timing, overflow transitions, eighth-slot release, palette source,
full OAM clearing, replicated PRG content and invalid-mode refusal.

```bash
python -m unittest discover -s tests -p 'test_fceux_stage138_temporal_nine_oam.py' -v
```

**Evidence boundary:** Stage138 is model/ROM-only until instrumented
FCEUX records the overflow flag *separately* for source scanlines 124
and 132 and the actual XBuf at X64 in both rows. The native runner
should require positive `seven_plus_late` contrast and reject a
forged `nine_late` label on the unchanged `seven_plus_late` ROM.
The PPU overflow bit is frame-sticky, so an actual native test should
capture the *first observed transition* rather than treating status
on every later row as independent.

No commercial game ROM, screenshot capture or copyright asset is
included, and nothing here proves a playable Nintendo Switch build.
