# Stage359 — prospective gap 545–559 original FCEUX source holdout

**PRE-CAPTURE FREEZE:** Commit this precise source window and confidence thresholds to Draft PR #99 **BEFORE capturing or reading any original native RGB files 545–559**. No Stage359 new-original source measurements are known when this document is committed. This is the unsampled gap between earlier source windows 520–544 and 560–584. It contains **15 consecutive frames and 14 adjacent transitions**, not 25/24. Stage355's previous failure and Stage357's five inconclusive pairs remain unaltered.

## Precommitted original replay / independent provenance

- Owner-private authenticated original NTSC Vice: Project Doom ROM, canonical taotao FM2 played **read-only** in real FCEUX v2.6.5 classical PPU (NewPPU=0). Never publish ROM/FM2, original raw GD RGB, raw index planes, full CPU/PPU trace rows, original-source hashes, or Lua source capture script to public GitHub/CI.
- Record original native 256×240 full RGB GD frames **545 through 559 inclusive**, indexed full planes **545, 552, 559**, and exactly six RGB/index probes per frame (**90** total). Retain complete 261-frame Stage335 CPU (frame380–640) and native Stage341 classic PPU traces. Independently compare each complete-trace SHA to a held-out Stage335/Stage341 source manifest before source inspection. Verify 261 frame-begin and native PPU anchors; ROM/FM2 replay identity and readonly COMPLETE marker.
- Require exactly **22** source-member per-file SHA256 pins: 15 full GD, 3 full indexed planes, one CPU TSV, one native PPU TSV, one RGB/index sample TSV, and one COMPLETE marker. Separately seal the manifest SHA before scoring.

## Frozen environmental source RGB displacement estimator

Four independent **half-open** native environment masks remain unchanged:
1. `left_env_upper`: (0,52,20,98)
2. `left_env_lower`: (0,52,98,175)
3. `right_env_upper`: (195,255,20,98)
4. `right_env_lower`: (195,255,98,175)

For every adjacent source RGB pair evaluate all 49 vertical signed candidate offsets **-24 through +24** on each region, with intersection cropped within that one region. Pixel mismatch fraction is the proportion of source pixels in the overlapping region for which **at least one RGB channel differs**. Pick a unique best candidate only if its mismatch fraction is <=**0.16** and second-best minus best score is >=**0.045**.

Evidence categories:
- **strict four-of-four**: all four independently confident and same shift;
- **qualified three-of-four**: exactly three independently confident and same shift, fourth weak;
- **conflicting confident**: >=2 confident and disagree, preserve contradictory negative;
- **inconclusive**: all other cases, preserve null displacement.

**Do not infer displacement from an identical/one-color full image** even when an independent register witness exists; ambiguous RGB must remain ambiguous. Keep exact source frame shape/probes and full-frame equality/flatness counts. On qualified image shift only, separately compare with **negative** signed modulo240 delta of first independently bound second-phase CPU $2005 vertical Y value, with native PPU source line0 provenance. If either frame lacks its first CPU write/native classic PPU line0 anchor, mark register comparison *unsupported*; never assume zero or forward-fill retained state. A disagreement between qualified image displacement and verified source register **is a contradiction**, not a pass.

Keep all 14 pairs with strict/3of4/conflict/inconclusive totals, qualified pixel-vs-first-register agreement/disagreement/unsupported, uniform/identical frames, 15 CPU write present/missing and native line0 mask zero/nonzero counts. Do not infer general camera speed, vehicle dynamics, road perspective/collision or hardware PPU dot timing. Even zero contradictions with some unsupported or ambiguous source data does not prove these.

## Capture and archiving

Owner-private source directory and final ZIP (exclude original NES and FM2 files) under
`Project Evidence Archive — Private/Vice Project Doom HD Remake/02_Raw_Traces_and_Captures`.
Keep owner-private manifest, private detailed per-pair reports, archive SHA256/ZIP CRC and 22/22 original source-member hashes; archive in dedicated private Drive directories, then independently re-download each artifact and compare full-file SHA256 and exact size. Save readback receipt and stage handoff separately. Public repository gets only safe auditor, fabricated-only tests, this pre-capture protocol and source-free aggregate after original experiment completes.

If any original check fails, report FAIL/INCONCLUSIVE instead of smoothing missing writes, changing ROI thresholds or trying alternative intervals after source inspection. Draft PR #99 stays Draft; main is not merged.
