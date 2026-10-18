# Stage 95 — FCEUX raster instrumentation capability preflight

## Purpose

Stage94 established **CPU-cycle brackets** between saved FCEUX snapshot
callbacks, without reconstructing physical PPU scanlines. The next meaningful
gate is independent observation of the emulator's **PPU scanline, dot and
VBlank transitions** at the time MMC3/PPU events are processed.

The official FCEUX [Lua functions reference](https://fceux.com/web/help/LuaFunctionsList.html)
documents `emu.framecount`, `emu.registerbefore/after`, memory hooks,
`debugger.getcyclescount`, and `ppu.readbyterange`, but it does not list
a standard scanline/dot Lua getter. The emulator's native PPU implementation
has internal timing state; its presence does **not** imply that state is
available as a supported Lua API.

## New independent preflight

`tools/probe_fceux_ppu_raster.lua` is a standalone **read-only** probe. It
checks for documented frame/cycle/hook symbols and exploratory potential
Lua names (`emu.getscanline`, `emu.getdot`,
`ppu.getscanline`, `ppu.getdot`). The latter are **not assumed to
exist or work**. The script calls none of them, registers no callbacks,
does not read any RAM, PPU memory, images or ROM data, and does not
write files. Only symbol-presence boolean lines are printed.

Run as a standalone script in the intended FCEUX Lua environment. You can
save its non-game capability text to `private/ppu_raster_probe.txt` and
validate it locally:

```bash
python3 tools/audit_fceux_raster_capabilities.py \
  private/ppu_raster_probe.txt \
  --out private/ppu_raster_probe_audit.json
```

`tools/audit_fceux_raster_capabilities.py` strictly validates report
version, field set, symbol status values, and fail-closed `no` markers
for side effects and raster proof. Extra fields or claims of an observed
scanline / VBlank edge are rejected. It outputs only aggregate
capability flags, never raw emulator memory or game graphics.

## What does *not* follow from success

- A symbol named `getscanline` is **not** evidence of an accurate PPU
  raster-time callback. It may be absent, nonstandard, stale, or defined by
  an unrelated Lua extension.
- A callback before or after a *frame* is not an independently observed
  physical VBlank transition.
- A CPU cycle counter cannot establish which scanline used CHR or scroll
  settings without a validated PPU-timing source.
- The probe does not authenticate the owner's ROM, verify a first-level
  capture, separate sprite/background data, or reconstruct camera motion.

**The HD replacement and original first-level geometry gates remain closed.**
Do not publish private first-level captures, ROM bytes, game screenshots or
derived maps.

## Next technical gate

Once this capability check has been run on the **real target FCEUX build**,
evaluate whether a minimally invasive *native PPU instrumentation hook*
is needed. Such a hook must identify its engine version, internal scanline/
dot source, VBlank phase, callback point, and discontinuity behavior, and
must be tested against synthetic raster timing before any real-game evidence
is allowed to carry a raster-proven label.

## ROM-free CI

```bash
lua5.4 tests/test_fceux_ppu_raster_capability_probe.lua
python3 -m unittest discover -s tests -p 'test_fceux_raster_capability_report.py' -v
```

Both tests deliberately use mock function symbols and prove they are not
invoked. No original game material is required.
