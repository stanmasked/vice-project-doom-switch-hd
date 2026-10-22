# Stage181: owner-private complete 321-frame CPU $2005 writer trace

The seven known original image-space road references and the
37/4 numeric road-mask report **do not establish effective NES
scroll or physical driving motion**. The full per-frame CPU evidence
for FM2 movie frames **600 through 920** was previously missing.

This optional capture tool uses an owner-controlled, **already loaded
original US ROM** and private readonly FM2 in FCEUX. It requires
exact ROM MD5 verification and exact movie frame count supplied by
the owner; the script does not open, copy or publish game bytes.
Set four environment variables locally:

- `VPD_PRIVATE_PPU321_OUTPUT_DIR`: existing empty private output folder
- `VPD_PRIVATE_FM2_PATH`: owner-only original FM2 input path
- `VPD_PRIVATE_ROM_PAYLOAD_MD5`: verified 32-hex MD5 for the loaded ROM
- `VPD_PRIVATE_FRAME_COUNT`: validated original movie length

Then launch FCEUX with the script and your **local** ROM (never in
public Actions):

```bash
fceux --loadlua tools/capture_private_road_ppu_321.lua /private/owned_game.nes
python3 tools/audit_private_road_ppu_321_trace.py \
  --private-dir /private/road_321_capture \
  --summary /private/new_summary.json
```

The private directory must have no existing output files. The
script stops recording at movie frame 920 and produces:

- `road_321_writers.tsv`: four ordered source CPU store-PC/A/cycle
  observations **per frame** at E8EC,E8F1,E369,E36C
- `road_321_postframe.tsv`: 321 source after-frame RAM $0D samples and
  the actual $2005 registerwrite count
- `COMPLETE.txt`: frame continuity, 1,284 CPU callbacks and port writes,
  runtime ROM MD5 and read-only FM2 assertions, **no ROM or movie hashes**

Independent audit rejects frame, callback, writer-PC, CPU pair-cycle,
published second-write/RAM anchor, counter, schema or attestation
mismatches. The only sharable output is an aggregate summary of
counts and explicit *not proven* flags. Raw CPU cycles, local paths,
the private FM2, ROM and complete original data **stay private**.

The script measures **raw absolute CPU cycles**, not the verified
per-frame cycle phase used by Stage168's independent joining audit.
A subsequent separate and explicitly validated frame-phase conversion
is still required before the Stage169 complete 321-frame PPU/image
joining gate can be claimed. No original execution of this new script
is yet confirmed; public CI uses only fabricated Lua hooks and Python
event tables.
