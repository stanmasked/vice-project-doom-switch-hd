# Stage136 — eight-sprite scanline selection and overflow source/model contract

Stage135 [GitHub Actions №39120926609](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/39120926609) successfully established native FCEUX 8×16 CHR bank selection and vertical tile-half ordering on four synthetic Mapper-4 ROMs. This stage examines the **next distinct question**: the selection of at most eight simultaneously visible sprites from the original 64 OAM slots.

## Source-backed constraints

The pinned FCEUX `newppu` renderer evaluates original OAM indices in ascending order. When the ninth sprite on the same scanline qualifies with PPU rendering enabled and the configured hardware eight-sprite limit, the code sets `PPU_status |= 0x20` and breaks out of the evaluation pass. It retains the first eight qualifying indices in the sprite buffer.

`tools/audit_stage136_oam_eight_limit.py` checks eleven exact ordered C++ operations in pinned upstream `ppu.cpp` before instrumentation. Missing, duplicated or reordered operations fail closed; the audit does not accept an arbitrary FCEUX fork.

The separate Python reference model requires exactly 64 valid OAM Y bytes, rendering enabled, a visible scanline and an explicit sprite height of 8 or 16. It records the earliest eight matching OAM indices and whether a ninth candidate sets the overflow bit.

Six regression methods cover:

- Nine sprites on one scanline: first eight selected, overflow set
- Exactly eight sprites: all eight selected, overflow clear
- Sparse OAM indices: original priority/order preserved
- The ninth candidate appearing only within the lower eight rows of an 8×16 sprite
- Malformed sprite heights, OAM arrays, coordinates or rendering-control values
- Mutation and duplication of the pinned FCEUX sprite-selection source anchors

```bash
python -m unittest discover -s tests -p 'test_fceux_stage136_oam_eight_limit.py' -v
python tools/audit_stage136_oam_eight_limit.py /path/to/pinned/fceux/src/ppu.cpp
```

The emitted `STAGE136_PINNED_OAM_EIGHT_LIMIT_SOURCE_PASS` is **source-only**. It does **not** prove that an actual ninth sprite has been dropped from the native FCEUX XBuf, nor that the original *Vice: Project Doom* uses this exact pattern. This stage deliberately does not modify the confirmed Stage135 native ROM or instrumentation.

## Next native evidence boundary

To claim native nine-OAM behavior, generate a private synthetic ROM containing eight visible sprites plus a ninth uniquely colored sprite; instrument FCEUX's true OAM evaluation loop, capture the overflow bit and final XBuf, and require controls for eight sprites with no overflow, nine overlapping sprites with overflow, a ninth offscreen sprite, and the 8×16 lower-half boundary. No original game ROM or captured assets should enter public GitHub.
