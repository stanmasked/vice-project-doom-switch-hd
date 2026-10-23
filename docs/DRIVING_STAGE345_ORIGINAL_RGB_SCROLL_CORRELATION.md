# Stage 345 — authenticated original RGB displacement vs first $2005 Y scroll

## Original-source recovery and provenance

The previously unlocated owner-private Stage344 evidence ZIP was **recovered from Google Drive**, not rebuilt from public aggregates.

- Owner-private Drive file: Stage344_original_consecutive_rgb_witness_private.zip, 2,139,906 bytes, file ID `1a4JoMHf4wnd6QoJ3gEnVNZsuO46W3Gc0`.
- A prior Drive readback receipt records full-archive SHA-256 and ZIP CRC. This stage downloaded it anew and matched the archive bytes to that independent receipt.
- All **32 manifest-listed original members** matched their SHA-256 digests. Four extra service files in the ZIP (Lua, log, embedded manifest and aggregate) have valid ZIP CRC but are not included in the 32-of-32 per-file SHA claim.
- The independently recorded manifest digest also matched the newly downloaded private manifest.
- Separately downloaded canonical owner-private Stage335 CPU and Stage341 classic PPU TSVs from Drive were byte-identical to their counterparts in the recovered archive.
- Never put ROM, FM2, RGB frames, raw CPU/PPU fields, private full SHA values or gameplay traces in GitHub.

## Stage 345 observation

Replayed the Stage344 SHA-gated local motion analysis on the recovered 25 consecutive native 256×240 classic-core FCEUX frames (420–444). Again observed 11 stationary and 13 +1-pixel downward background transitions. All four independent environment/marking texture bands agreed; vehicle and HUD remain masked.

Joined the **first second-phase $2005 vertical Y byte** in the 25 source CPU frames to the matching live RAM $0D value and classic PPU `TempAddr` vertical fields at native renderer line zero. All **25/25** checked frames agreed in the first-write/source-state comparison. No intervening $2005/$2006 PPU register write occurred before the native sample.

| Visible adjacent background displacement | First $2005 Y difference | Verified pairs |
| --- | --- | ---: |
| 0 pixel | Unchanged | 11 |
| +1 display pixel downward | -1 byte step | 13 |

Total: **24/24** consecutive image-to-first-scroll comparisons agreed. The *later* second-phase $2005 Y byte remained constant across all 24 pairs; interpreting it as the first scroll byte would obscure the result. 14 of 25 frames had RAM $0D writes; 11 had none.

This proves only a bounded **software-register/image correlation** in the selected 25 game frames. It does **not** independently establish an exact NES hardware PPU dot, camera or automobile speed, road perspective, steering or collisions. No driving physics code was adjusted.

## Implementation and verification

- `tools/audit_private_stage345_scroll_motion.py`: reruns authenticated Stage344 pixel analysis with *independent prior Stage335/341 SHA-256 pins*, verifies CPU/native events and compares all 24 source pairs. Never emits raw private values.
- `tests/test_stage345_scroll_motion.py`: **18 fabricated-only** negative/regression tests, including contradictions, a changed later phase, source ordering, time reversal, missing native anchors and 8-bit wrap.
- `docs/stage345_public_aggregate.json`: safe bounded counts only; no original pixel, ROM/movie, register values, source SHA or raw addresses.

The source-backed Stage345 analysis was executed in an owner-private local workspace, never in public GitHub Actions. Public CI proves only ROM-free behavior. PR #99 stays Draft; main remains unchanged.

## Owner-private reproduction

1. Fetch the canonical Stage344 ZIP and manifest privately, verify full archive SHA against the earlier Drive readback receipt, ZIP CRC and 32 per-member hashes.
2. Extract to a new owner-local path and separately validate the prior Stage335/341 trace identities; pins must originate outside the just-rebuilt capture manifest.
3. Execute: `python tools/audit_private_stage345_scroll_motion.py --root "$OWNER_PRIVATE_STAGE344_ROOT" --manifest "$OWNER_PRIVATE_STAGE344_MANIFEST" --sealed-cpu-sha256 "$OWNER_PREVIOUS_STAGE335_SHA256" --sealed-native-sha256 "$OWNER_PREVIOUS_STAGE341_SHA256" --output "$NEW_PRIVATE_STAGE345_AGGREGATE"`.
4. Run: `python -m unittest discover -s tests -p 'test_stage345_*.py' -v` using only synthetic fixtures.

Next: capture and authenticate additional consecutive windows, check transition boundaries and 8-bit wraps, and avoid inferring general road/camera physics from the 24 bounded source pairs.
