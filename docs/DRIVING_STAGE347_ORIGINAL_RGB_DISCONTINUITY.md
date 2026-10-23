# Stage 347 — original 470–494 RGB counterexample to naïve $2005 pixel law

## Authentic replay and storage

Stage 347 replayed the owner-held original NTSC Vice: Project Doom ROM + read-only 43,652-input FM2 in the exact previously sealed instrumented FCEUX 2.6.5 classic PPU (`NewPPU 0`), with the now independently preserved Lua 5.1 runtime. A failed first attempt had an incorrect local Lua pathname and produced **no completed source capture**; its temporary native log is not evidence. The corrected run was isolated in a **fresh directory**, produced `COMPLETE.txt`, and passed all original ROM/movie and source event checks.

The successful run produced 25 new **native 256×240 XBuf RGB frames 470–494**, three complete indexed-palette planes (470,482,494) and 150 RGB/index point matches. New-session **full CPU and classic PPU traces are byte-identical** to the owner-sealed Stage335 and Stage341 witnesses; completion marker also matches the prior private sealed source.

The four Stage344 fixed non-sprite/non-HUD environment/road-marking texture windows, inspected independently under authentic RGB pixel scores, unanimously selected **+2 image pixels in all 24 adjacent pairs**. No masked-region conflict or ambiguous texture score was observed in this finite window.

## One exact observed failure of the simplified scroll law

The *first* second-phase CPU $2005 Y bytes, independently verified as equal to live RAM $0D and the native classic PPU TempAddr vertical input, show these bounded differences:

| Original frame-pair category | First $2005 Y signed difference | Native RGB candidate-band vertical shift | Pairs |
| --- | --- | --- | ---: |
| Ordinary | -2 | +2 display pixels | 23 |
| Exceptional | -18 | **still +2 display pixels** | 1 |

Thus the Stage345/346 coincidence `pixel_shift = -signed(first_2005_Y_delta)` **does not generalize unconditionally**. Do not reinterpret this -18 register change as 18 pixels or assume vehicle/camera acceleration. The cause has not yet been isolated; nametable, effective PPU address loading, register semantics, tile periodicity, or a renderer scene transition are hypotheses, **not established explanations**.

Crucially, this is not a failed RGB capture: the independently checked image movement and both sealed source traces are valid. The inconsistency belongs to the over-simple interpretation, not the capture integrity.

## Private archive and independent readback

- [Private Stage347 470–494 raw RGB/CPU/PPU ZIP](https://drive.google.com/file/d/1khw-pYXTVDGbmimSny4QlZKIwI6P9osO/view): 2,144,560 bytes, 36 members. No original ROM/FM2 duplicated.
- [Private 32-file source SHA-256 manifest](https://drive.google.com/file/d/1AZeEyGd0Iq8eEzcezDXIvfxxhiWT6qtI/view).
- [Private derived numeric aggregate](https://drive.google.com/file/d/14PnKKg1I3wen4d6yXewxUShQLNiJyoFc/view).
- [Private pretransfer checksum receipt](https://drive.google.com/file/d/1GKUCZhCsLTkAMQsrgiwL_SGmEGivyLSZ/view).

All four were uploaded to owner-only Google Drive and downloaded back as fresh bytes; SHA-256 matched each local input. ZIP CRC passed and **32/32** original manifest-listed members matched exact SHA-256. Remaining four archive service members are ZIP-CRC checked but not counted as independently manifest-member sealed.

## Public code and limitations

- `tools/audit_private_stage347_scroll_discontinuity.py` reauthenticates the previous sealed CPU and native PPU traces and newly pinned source-image manifest, reruns the Stage344 masked RGB validator, verifies first-scroll $0D/PPU state, and **explicitly counts** the 23 matching and one disagreeing transition without hiding it.
- `tests/test_stage347_scroll_discontinuity.py` comprises 13 **fabricated-only** checks, including 8-bit wrap, bogus 18-pixel inference, missing/duplicated frames, later-scroll tamper and unrecognized discontinuities.
- `docs/stage347_public_aggregate.json` contains only source-backed counters and conservative research limits.

Original image, executable input ROM, FM2, private pixels and raw traces remain owner-only. Public GitHub CI is source-free and must be checked on the exact final commit. PR #99 remains Draft, `main` is unchanged.

## Next

Stage348: independently inspect the one exceptional transition's classic PPU **effective** render address and nametable/fine-Y reload timing, compare its texture periodicity and other nearby source frames, and repeat in additional authentic windows. Do not alter the HD car physics, collision or road geometry based only on first-write Y register differences. Any fresh capture must be durably backed up with checksummed readback before relying on it.
