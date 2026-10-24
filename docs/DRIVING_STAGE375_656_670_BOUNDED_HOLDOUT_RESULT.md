# Stage375 — genuine preregistered original 656–670 RGB/PPU holdout

Date: 2026-10-24. Research branch: `research/stage375-preregistered-environment-656-670`, based on Stage374 Draft PR #102. `main` unchanged.

## Pre-exposure procedure

The four environment-only rectangles, numeric scoring module, 23 manufactured-only regression tests and exact untouched 656–670 input window were committed to GitHub on **`5891ade9f8a644e2274204c2850f4d6de6503865` before the real FCEUX original input replay**. The four masks are the already defined Stage352/359 upper/lower environment regions, not post hoc chosen by observing new Stage375 frames. Offsets -24..24, maximum best RGB mismatch 0.16, minimum best-versus-runner-up gap 0.045 and separate 4/4, guarded 3/4, flat, conflicting, inconclusive results were frozen and never changed.

The preceding Stage374 641–655 prespecified **14/14 inconclusive** finding is preserved without reclassification. Omitting weak marking strips on that *previously observed* sample was explicitly exploratory and does not itself confirm anything about unused frames 656–670.

## Original owner-private FCEUX replay

- Canonical NTSC Vice: Project Doom original ROM and taotao FM2 were SHA-verified from existing owner-private originals. The movie was replayed read-only in the instrumented FCEUX 2.6.5 **classic PPU** (`NewPPU=0`). Neither ROM/FM2 nor original graphics or full event traces entered public GitHub or CI.
- The FCEUX completion marker confirms **291** sequential original CPU/native frames, 380–670, plus 15 native 256x240 RGB XBuf frames for 656–670, three complete palette planes (656/663/670) and 90 RGB/index cross-probes.
- 1,130 CPU `$2005` writes had matching instruction provenance (1,130/1,130), and 283/283 current-frame second-phase `$2005` writes agreed with RAM `$0D` at capture time. Full traces on frames **380–655** are byte-identical prefixes of the independently archived Stage374 traces; different-length full-file hashes were not falsely compared.
- Before image analysis, independently sealed a **22-member source manifest**, including per-member SHA-256 and byte lengths, original ROM/FM2/binary/private Lua provenance, and fixed frame labels. Original image and native CPU/PPU anchors were checked before correlating their measurements.
- A second, independent owner-private FCEUX replay with unchanged inputs completed and **all 22 source members were byte-identical** to the first run (including all 15 RGB, three indexed planes, CPU, native PPU, probes and COMPLETE marker).

## Original image-motion and first `$2005` relation

Frozen four environment upper/lower masks were scored independently *before* comparing source register values. Private diagnostics and the already committed ROM-free classifier agree on the exact outcome:

| Predeclared category, original 14 adjacent pairs 656->657 through 669->670 | Result |
| --- | ---: |
| Strict, confident **four of four** environment rectangles | **10** |
| Guarded, confident **three of four**, fourth weak but not contradictory | **4** |
| Flat, conflicting or image-inconclusive | **0** |
| Qualified original RGB shifts | **+5 pixels x14** |
| Opposite original CPU/native `$2005` Y register delta matches | **14 / 14** |
| Qualified register contradictions / unsupported | **0 / 0** |

The exact same score-tier and source-register classifications were reproduced by feeding the private authenticated numerical summaries into the **precommitted** `tools/stage375_environment_motion_contract.py`. This audit was independent of the private motion auditor, which checked source byte/hash identity, RGB and palette probes, and same-session CPU/native frame anchors.

### Scientific boundary

The **bounded preregistered original 14-pair evidence gate PASSED**, correcting the independent-replication gap left by exploratory Stage374 environment-only analysis. This is real finite original image/register correlation, not a test of the remade game's original-driving physics or proof of universal camera speed, road geometry, collision response, driver movement, hardware PPU-dot timing or original NES assets in the guest NRO. Stage355 negative and Stage357 inconclusive results remain unchanged.

## Reproducibility and privacy

Two owner-private evidence ZIPs (first complete replay and byte-identical second replay), immutable original source manifest, per-pair private diagnostic scores and independent Drive readback receipt remain in the existing private Drive archive `Project Evidence Archive — Private / Vice Project Doom HD Remake`. **Neither derivative ZIP contains a NES ROM or FM2**. Public changes only include synthetic tests, numerical code, this research report and safe aggregate counts; no owner-specific source SHA or original images/traces.

Pending step at the instant this result document was prepared: confirm Google Drive upload plus independently downloaded full ZIP SHA-256, ZIP CRC and 22/22 member digests before declaring durability complete; the separate private handoff contains its latest verified archival status.

Stage375 research branch remains Draft, not merged to `main`. Further gameplay reconstruction must first test whether the observed finite motion model can actually drive native game rendering without altering original physics from unsupported inference.
