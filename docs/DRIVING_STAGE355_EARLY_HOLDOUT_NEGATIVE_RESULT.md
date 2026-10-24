
# Stage355 — genuine original 380–404 RGB holdout: failure of pre-registered full confidence gate

## Frozen prior protocol and original-source provenance

Before original frames 380–404 were captured, commit 2d097054c9b6d58288639a8aa443d0067edb24a5 froze the untouched 25-frame source interval, the four source-environment RGB rectangles, 49 integer candidate shifts from −24 through +24, best RGB mismatch at most 0.16, minimum runner-up confidence gap 0.045 and 4-of-4, 3-of-4, mask conflict, and inconclusive tiers. No region or threshold was tuned after original source inspection.

An owner-private read-only FCEUX 2.6.5 classic PPU (NewPPU=0) replay of the authentic Vice: Project Doom NTSC ROM and taotao FM2 completed. Exactly 25 256×240 original XBuf RGB images, three complete indexed palette planes at 380, 392 and 404, and 150 independent RGB/index probes were checked. Complete CPU Stage335 and native PPU Stage341 original event traces and read-only FM2 completion marker were byte-identical to independently held source SHA-256 seals. All 32 per-file original source hashes matched the manifest.

## Negative/inconclusive result under frozen gates

The preregistered 25-frame pixel/PPU correlation audit did NOT pass. In eight of the 25 genuine source frames the mandatory first vertical second-phase CPU PPU $2005 write is absent; 17 frame records retain it. Nine adjacent pairs therefore lack two independent complete first-write anchors. Missing register inputs are not filled, inferred, or treated as zero.

The frozen four source RGB environment masks scored all 24 adjacent original image pairs: **0 strict four-of-four qualified**, **0 only three-of-four qualified**, **0 confident mask conflicts**, **24 inconclusive** (not enough unique texture features). Thus **no qualified image-vs-PPU modulo-240 comparisons exist for this source interval**. This is NOT a 24/24 success, NOT an observed contradiction to the prior model, and NOT proof of camera physics or velocity. The source material passed fidelity/integrity gates but the preregistered original motion-evidence gate FAILED/INCONCLUSIVE.

## Owner-only durable archive

- Original source ZIP (2,054,597 bytes; 37 members): https://drive.google.com/file/d/1aIb6glmFOjgaq5mCADHkVSeLqSHo5Dn4/view
- Independent 32-member SHA source manifest: https://drive.google.com/file/d/12QjAt2X8nWrV5oSMXzgYZNIrWmCUcp11/view
- Owner-only derived failed-gate aggregate: https://drive.google.com/file/d/1deMw-YdONhfCVuJkgIv4PsCpmUhEX4Dl/view
- Owner-only per-pair image/confidence diagnostics: https://drive.google.com/file/d/1Yz72CgX2vaUCybJ3sJVZX3KDRrqA12ZZ/view
- Owner-only preupload seal: https://drive.google.com/file/d/1LwMpeHKR2ZmtAiEElFBga1uE2MEgK88N/view

Five artifacts were independently fetched back from owner-only Google Drive and their SHA-256 compared with original local files. ZIP CRC passed, all 32 original source members independently matched SHA. No original ROM or FM2 is in ZIP.

## Public code, implications and next step

The precommitted source-authenticated ROM-free tool tools/audit_private_stage355_early_holdout.py, tests/test_stage355_early_holdout.py (17 fabricated-only tests), preregistered protocol and this negative-results document are maintained in Draft PR #99, main unchanged. No original game assets, source traces, raw RGB, owner-only hashes, movie, or capture Lua are committed publicly.

Stage356 should separately preregister new early-scene visible-mask selection and a careful PPU retained-state hypothesis for frames with no first scroll write; test any new model on an untouched original window, not by changing this failed Stage355 result. No physical car speed, collision, perspective, or exact hardware PPU dot has been proved.
