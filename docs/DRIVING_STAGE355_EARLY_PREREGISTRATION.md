# Stage355 — pre-registered first sealed source-window RGB holdout

**Pre-capture original-source experiment: commit this protocol before replaying or examining the previously uncaptured original frames 380–404.** The owner-only NTSC ROM/FM2 inputs, Lua capture, raw original RGB/CPU/PPU traces and private digest values must not appear in public GitHub or public CI.

## Exact untouched source window and emulator

Read-only instrumented FCEUX v2.6.5 classical PPU (NewPPU 0), original NTSC Vice: Project Doom ROM plus canonical taotao FM2. Native source 256×240 XBuf RGB, frames **380–404 inclusive**, 25 consecutive images and **24 adjacent transitions**. Full index/palette captures at 380,392,404, and 150 independently sampled RGB/index probes. Source full CPU/native-PPU event coverage is anchored from frame 380 through 640; early frame 380 is its original documented start. No earlier original RGB image sample in this series spans 380–404.

## Source-independent frozen visual discriminator

Use the same four environment mask rectangles as Stage353/354, with half-open pixel coordinates: left upper (0,52,20,98), left lower (0,52,98,175), right upper (195,255,20,98), right lower (195,255,98,175). Do not adjust these according to screen appearance.

For each mask search the 49 signed integer shifts **−24..+24 pixels**; an individually confident region needs RGB mismatch ≤0.16 and runner-up gap ≥0.045. Decide visual motion *without consulting* register predictions. Keep separate categories:
- strict four-of-four individually confident consensus;
- exactly three-of-four consensus, fourth region independently not confident;
- any disagreement among confident regions (negative/conflict);
- two or fewer confident masks, without confident disagreement (inconclusive).

Then compare only qualified image shifts to inverse signed 240-pixel modular first vertical second-phase $2005 Y register differences. Source scroll bytes outside 0…239 or half-period ambiguity are unsupported, not silently wrapped or excluded. Every qualified contradiction must be counted and retained. Scene/background changes that invalidate fixed mask should fail confidence and stay inconclusive; never force matches.

## Source integrity and storage

Before accepting any original result, externally pin source manifest SHA-256 separately from its contents, verify independent prior Stage335 CPU and Stage341 classic PPU full-original witness digest values, original read-only FM2 completion, 261-frame event coverage, 25 native image hashes, 3 whole palette planes, and 150 RGB/index cross-probes. Zero ROM/movie or original CPU/PPU raw data in GitHub. Save owner-only source archive, aggregate, per-pair diagnostics and checksum manifest under the canonical Google Drive Project Evidence Archive; download each uploaded file back and validate full SHA, ZIP CRC and all 32 original source-member digests.

**No Stage355 original pixel result exists at the time of freezing this protocol.** This test examines bounded original PPU register versus screen texture motion, not vehicle physics/camera velocity/collision or precise PPU hardware dots.
