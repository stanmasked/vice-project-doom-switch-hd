# Stage 82 — byte-level PPU/RAM snapshot integrity

## Previous limitation

Stage79's independent capture verifier checked the size and presence of
private FCEUX PPU and RAM dumps, but an accidental bit flip could leave a
file **the same length** and still pass verification. Stage81 improved
metadata publication but did not prove the saved blob bytes matched the
bytes captured.

## Capture-side change

`tools/capture_fceux_ppu.lua` now computes the **Adler-32** checksum of
every binary artifact in each captured frame:

- `frame_NNNNNN.ppu.bin` (16384 bytes)
- `frame_NNNNNN.ram.bin` (2048 bytes)
- `frame_NNNNNN.screen.rgb.bin` (184320 bytes, when screen capture enabled)
- `frame_NNNNNN.screen.pal.bin` (61440 bytes, when enabled)

The Lua helper `write_verified_blob` writes each file, checks closing,
reopens it, reads back its **entire content**, and compares all bytes to
the captured data. A mismatch raises an error before the frame's
metadata is finalized. The stage79 capture failure counter then
prevents a session from being certified complete.

Metadata now contains:

```text
snapshot_checksum=adler32_v1
ppu_adler32=BAEE413C
ram_adler32=6BE08801
screen_rgb_adler32=not_captured
screen_pal_adler32=not_captured
```

The checksum values above are **synthetic test examples**, not original
game data. If screenshots are captured, the latter two fields instead
contain eight uppercase hexadecimal digits.

**Adler-32 is an accidental-corruption checksum, not cryptographic
authentication**. It can collide and cannot establish original-ROM
identity or protect against deliberate tampering.

## Offline independent verification

`tools/verify_ppu_capture_session.py` now uses Python's built-in
`zlib.adler32` to recompute the checksum from **every saved byte**.
It rejects altered files even when size is unchanged, missing or
malformed metadata checksums, incorrectly described optional screen
files, and older snapshot metadata lacking the checksum schema.

The existing session-level checks remain necessary: the matching
checksum is not sufficient by itself to establish continuity, event
provenance, or capture completion.

Run against a complete private capture:

```sh
python3 tools/verify_ppu_capture_session.py \
  private/ppu_capture_session.meta.txt --require-cycle
```

## Evidence and tests

- Stage79/82 Python suite: **24/24 locally passed** using the exact
  Git blobs committed to the research branch, including seven new
  checks for unchanged-length PPU, RAM, RGB and palette corruption,
  missing checksums and legacy metadata.
- A standalone LuaTeX probe of the production-equivalent Lua checksum
  and binary readback routines: **6/6 locally passed**, including
  checksums that match independently computed Python results and an
  injected same-size corruption on readback. This is not a complete
  FCEUX integration run.
- New `tests/test_fceux_ppu_snapshot_integrity.lua` exercises the
  real capture script under three synthetic scenarios: PPU/RAM capture
  without a screen, capture with synthetic RGB/palette, and deliberate
  same-size PPU readback modification. It is wired into GitHub
  Actions, but a successful full Lua execution is **not yet confirmed**
  in this environment.

No original ROM, game images, reconstructed first-stage geometry,
or Nintendo Switch NRO is added or claimed.
