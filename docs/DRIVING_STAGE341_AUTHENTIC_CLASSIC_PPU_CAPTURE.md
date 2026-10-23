# Stage 341 — authentic FCEUX 2.6.5 classic-core PPU address witness

An isolated GitHub Actions build compiled the complete FCEUX **v2.6.5** tree after a pinned, opt-in patch to the **classic** PPU path. The output was an emulator-only executable, containing **no ROM, FM2, game screenshots, or traces**. Owner-private original game input was subsequently replayed locally in `movie.play(fm2, true)` mode.

The owner-private session reused the verified Stage335 Lua capture on the same run as the native `RefreshAddr`/`TempAddr` probe. The CPU-side trace SHA-256 **exactly matched** the previously sealed Stage335 original trace, which makes this a repeatable-source check rather than an invented or modeled trace.

In the source window, 261 core frames produced **312,189** native classic-PPU probe events, including 3,048 actual second-half `$2006` writes, 60,480 internal horizontal reloads, 60,480 vertical increments and three categories of 62,640 line-boundary slices each.

The private verifier reconstructed the entire 14-bit PPU address from the original movie's CPU write pair and compared it with the native source's full `RefreshAddr` at each `$2006` second write. All **3,048/3,048** values agreed, in the same order and the same numbered frame, with zero mismatches. Adjacent frame-shift alternatives failed. Therefore core frame ordinals **380–640** were aligned to original FM2 frame labels for the sampled address events, rather than assumed to be aligned.

**Interpretation boundary:** These are genuine values of FCEUX's legacy renderer/internal PPU address, but legacy `scanline` and timing slices are not independently calibrated NES hardware dots. The evidence does **not** establish the effective per-pixel raster scroll, road geometry, camera speed, or collision. Do not change gameplay physics on this basis.

Only ROM-free workflow and code/tests/aggregate are eligible for GitHub. Full raw native event data, original code/data addresses, ROM, movie and local runtime logs are owner-private. Preserve the native raw trace and manifest in Drive and re-download with SHA-256 verification before considering durable archival complete.
