# Stage 26 — external VANM animation timing and paired SD asset reload

The Nintendo Switch **ROM-free graphical diagnostic** can now import both
independently authored sprite pixels and separately authored clip timings
**without recompiling the NRO**. Unlike the original NES game, these
resources are new, synthetic research assets with invented animation times.

## SD card structure

Place the files in:

```text
sdmc:/switch/vice_project_doom/
    hero.vpat       (versioned RGBA sprite atlas from stage 25)
    hero.vanm       (versioned animation clip and duration data)
```

On startup, and every time **X** is pressed, the application checks both
files. Press **Y** to restore the red embedded artwork and original
embedded clip timings. A small HUD labels an accepted external animation.

If the animation file is **missing**, the loader intentionally supports
stage-25 legacy behavior: a valid four-frame external VPAT may load while
the embedded manifest controls its timing. If VANM is *present but invalid*,
the entire replacement attempt fails; no new VPAT is accepted.

In particular, reloading a complete pair is **transactional**. The two
resources are read into separate, temporary owners; the loader checks the
atlas integrity, clip structure and matching frame count *before* accepting
either. On failure the last accepted pair stays active. On success, the
animation controller resets its clip position so it cannot retain an index
from a previous timeline.

This is an integrity / structural compatibility rule, **not** a guarantee
that arbitrary user-authored poses match authored timings artistically.
The metadata does not cryptographically bind to the exact VPAT content.

## VANM v1 binary structure

All integers are unsigned, little-endian:

| Byte offset | Type | Description |
|---:|---|---|
| 0 | char[4] | ASCII magic VANM |
| 4 | u16 | Version 1 |
| 6 | u16 | Number of frames in accompanying VPAT |
| 8 | u16 | State count, always 4 |
| 10 | u16 | Total number of frame records (4–256) |
| 12 | u16 | Reserved flags = 0 |
| 14 | u32 | CRC32 of everything beginning at offset 18 |
| 18 | 4×4 bytes | Four ordered state descriptors |
| 34 | N×4 bytes | Frame records |

Each descriptor contains `u16 first_record; u8 record_count; u8 loop`.
The four fixed states are **idle, run, rise, fall**. Each count must be
1–64; descriptors must partition all records in the correct order.
Loop must be 0 or 1.

Each frame record contains `u16 atlas_frame; u16 duration_ticks`.
Frame indices must be less than the referenced atlas count; durations
must be 1–600 **simulation ticks**. CRC32 and a maximum 1,058-byte size
limit prevent accidental corruption or oversized animation metadata.
No external JSON parsing runs on the Switch itself.

## Create a user-authored replacement

Edit a JSON document with the same schema as
[demo_animation.json](../assets/demo_animation.json). It has four named
states, a loop flag and one or more frame/duration pairs.

~~~sh
python3 tools/pack_animation_binary.py private/hero_animation.json private/hero.vanm
python3 tools/pack_vpat.py private/hero.png \
    --frame-width 24 --frame-height 32 --frames 4 \
    --binary private/hero.vpat
~~~

Transfer both files to the SD directory. Then press X to reload while the
diagnostic is running. Changing **pixel art or durations** does not
require a new NRO. Changing number of states, state-machine logic or
maximum runtime constraints still requires updating code and recompiling.

A separate downloadable stage-26 ZIP contains a **synthetic blue sprite**
plus VANM timings (idle 8, run 3/4, rise 5, fall 6 ticks), the editable
PNG and JSON. These are only demonstration timing differences—not
values reverse-engineered from Vice: Project Doom.

## Safety checks and validation

The host C++ and Python tests cover binary schema, little-endian
fields, descriptor coverage, CRC, editable durations, invalid frame
references, atlas-count mismatches, missing files, corrupted atlas or
manifest, state rollback, pointer ownership and legacy atlas-only
compatibility. The same portable implementation is compiled to the
libnx graphical NRO in
[GitHub Actions](../.github/workflows/native-graphics.yml).

**Hardware execution, frame timing and actual SD I/O performance remain
untested.** First-stage geometry, animations and HD artwork from the
original game have also not been recovered. A successful devkitPro
build does not demonstrate acceptable display speed on a physical Switch.

See [ASSET_PIPELINE.md](ASSET_PIPELINE.md) and
[SD_ASSET_OVERRIDE.md](SD_ASSET_OVERRIDE.md) for the earlier texture format.

## Stage 27: VANM v2 — bind clip timing to the exact VPAT atlas

To prevent an animation schedule from being applied to the **wrong
same-frame-count sprite sheet**, the animation resource now optionally
contains the CRC32 of its intended VPAT **pixel payload**. The CRC comes
from VPAT header bytes 18–21 and is rechecked when VPAT is loaded.

VANM v2 uses the same record semantics as v1, with a four-byte identity
inserted immediately before the clip descriptors:

| Offset | Contents |
|---:|---|
| 0–3 | Magic `VANM` |
| 4–5 | Version `2` (legacy `1` still readable) |
| 6–13 | Frame count, four states, total records and reserved flags |
| 14–17 | CRC32 of *everything from offset 18 onward* |
| 18–21 | **CRC32 of accompanying VPAT pixel payload** (v2 only) |
| 22–37 | Four 4-byte state descriptors |
| 38 onward | `u16 atlas_frame; u16 duration_ticks` records |

VANM v1 retains its original offsets (descriptors start at 18, records
at 34), and **does not** provide content binding. A missing VANM file
also retains the legacy stage-25 embedded timing fallback.

To generate a new **v2 bound** animation file, pack the final VPAT first:

~~~sh
python3 tools/pack_vpat.py private/hero.png --frame-width 24 --frame-height 32 \
  --frames 4 --binary private/hero.vpat
python3 tools/pack_animation_binary.py private/hero_animation.json \
  private/hero.vanm --atlas private/hero.vpat
~~~

The packer checks VPAT dimensions, stored CRC and frame count. If
you **change any pixel**, rebuild both VPAT and its bound VANM v2 before
pressing X. Otherwise the game refuses the new pair and keeps its
last valid atlas plus timings.

For compatibility with an old SD package, omitting `--atlas` produces
an intentionally **unbound legacy VANM v1**:

~~~sh
python3 tools/pack_animation_binary.py private/hero_animation.json private/hero.vanm
~~~

The host unit tests now include two *independently authored* VPAT
files with **identical frame counts** but different pixels. The
same bound VANM must not load with both. The already-active pair must
remain unchanged if the replacement is incompatible.

**Security boundary:** CRC32 helps detect accidental version mixing
and file corruption; a determined person could intentionally forge a
matching CRC32. This feature is **not** authentication, encryption, a
licensing system, or cryptographic proof of an art source. Real-game
visuals, authentic timing and physical Switch performance are still
unverified.
