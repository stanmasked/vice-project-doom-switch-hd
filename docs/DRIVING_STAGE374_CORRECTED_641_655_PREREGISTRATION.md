# Stage374 — corrected preregistered original-image holdout

Date: 2026-10-24. Frozen before the new original capture.

## Correction of the preliminary protocol
The earlier private Stage374 draft described original frames 560–574 as previously unobserved. That description is wrong: Stage351 had already measured original frames 560–584. Do not promote any 560–574 observation into an independent holdout. Retain the original draft as an audit artifact. Stage351 remains 23/24 under its original fixed mask, one inconclusive; its later adapted environment-submask results are exploratory.

## New untouched candidate: 641–655
Before any new original pixels are opened, prospectively select frames 641–655 inclusive (15 native 256x240 RGB frames, 14 adjacent transitions 641->642 through 654->655). Previously inspected Stage335/341 complete CPU/native coverage ends at frame 640, and inspected captured RGB windows end at/before frame 634. If a prior capture of these exact RGB frames is discovered, do not score it as a novel holdout.
Generate three full index planes (641,648,655) plus six cross-checked RGB/index probes per source frame, in the same original FCEUX frame-end callback.

## Predeclared scoring only
Fixed half-open rectangles (x0,x1,y0,y1) copied from Stage344: left_environment=(0,52,20,175); right_environment=(195,255,20,175); left_marking=(93,99,20,175); right_marking=(157,163,20,175). These are selected texture bands, not proven driving collision boundaries.
Integer signed vertical-image offsets -24..+24; exact RGB mismatch fraction at best shift <= 0.16; difference between runner-up and best >= 0.045; reject flat bands and tied/ambiguous candidates. Preserve distinct classifications strict_four_of_four, qualified_three_of_four, mask_conflict, flat and inconclusive. A fourth confidently disagreeing band is a conflict, not 3/4. Do not impute motion for inconclusive original pixels or tune rectangles after exposure.
Only AFTER qualifying image movement, extract the observed second-phase first Y $2005 write for adjacent frames and compare signed image delta to negative signed modulo-240 source-Y delta, with classic PPU line-zero witness in that same capture. Missing CPU/native anchors, ambiguity of modulo wrap, unsupported source values, or inconsistent writes are not matches. Preserve counts of qualified matches, contradictions, missing-register/unsupported and inconclusive separately. Do not use Stage361's older finite envelope to select the new image displacement.

## Private provenance and replay
Original NTSC Vice Project Doom ROM and taotao FM2 remain read-only and outside GitHub/CI. Independently verify original ROM/FM2 full SHA-256, instrumented FCEUX 2.6.5 classic PPU binary, original Lua, and derived private capture Lua BEFORE executing in a fresh owner-private directory.
Old exact native CPU/PPU traces cover frames 380–640 (261 frames). New run targets 380–655 (276 frames): the FULL new files cannot be assumed byte-identical to 261-frame originals; require independently checked original 380–640 prefix equivalence whenever event schemas permit, plus verified new 641–655 same-session CPU/native anchors. Do not require false equality between different-length trace SHA hashes.
Before analysis, seal an owner-private immutable manifest with source hashes, executable & Lua SHA-256, frame provenance, capture completion, and full per-member SHA-256/byte sizes. Reject missing, mismatched, reordered, duplicate or linked files. Do not publish original RGB/index/CPU/native TSV, original ROM/FM2, private Lua, or source-specific private digests.
After a real run and independent verification, save raw evidence/manifest/diagnostics to private Drive; download and compare full ZIP SHA-256, CRC, extracted-member SHA-256 before declaring durable archive. Source-only synthetic checks in public CI are not actual original-game replay.

## Scientific boundary
Image-to-$2005 correlation across this finite section, if ever measured, is not proof of universal camera velocity, vehicle speed, road projection, collision physics, original artwork porting or hardware PPU dots. Never reinterpret Stage355 failed/inconclusive or Stage357 five image-inconclusive pairs. This holdout may be flat, a transition or otherwise unqualifiable; publish that outcome honestly.

STATUS: PRE-EXPOSURE PROTOCOL ONLY. No 641–655 original pixels captured, audited, or scored at time of this commit. Results must be appended in a distinct result document; this preregistration remains immutable.
