# Stage364 — real NeXium manually initiated numeric-scroll DEMO confirmed

**Source qualification:** completed real emulator execution of **the source-safe DEMO mode**, NOT original NES ROM/FM2 replay, original NES picture reconstruction, global camera speed or vehicle physics. Existing original Stage355 image-motion confidence gate stays **FAILED/INCONCLUSIVE**; Stage357 five image-inconclusive pairs remain inconclusive.

## Verified exact-head, genuine NeXium guest control

- [Stage364 manual-scroll workflow #40072628961](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/40072628961) **SUCCESS** on source revision `c8ec5b46174f3759d40152e5d596582f79e3c1f9`.
- A fresh ROM-free Switch NRO built from **the same commit**. Its source `vpd_native_scene.nro` is 487,480 bytes with SHA-256 `af18d57ee7c2bd00613560750ab0ef4a0ca05fac9277e12d5b4f79a779e6e3c4`; this matches its separately downloaded NRO Actions ZIP and the SHA written by the real emulator-input procedure.
- NeXium Linux nightly archive downloaded after authoritative GitHub release digest/size/ID attestation. Release asset ID `670955988`, archive SHA-256 `d08e89d15632c2ba3ef0521635286793885ac1eaabed6ab93f2d0ec7d5c10180`. This is a mutable nightly asset pinned for this actual test; no general emulator behavior is inferred.
- Real X11 keyboard `R+T+Q` from NeXium's default upstream keymap is presented to libnx as **ZL+ZR+L**, only after verified real guest entry into the manual driving preview. This launches a manual source-free numeric DEMO; keyboard-only events do not count as proof.
- NRO-written `sdmc:/switch/vice_project_doom/scroll_demo_guest.txt` contains exactly two guests events, taken from **the actual libnx-produced framebuffer**, not a synthetic host-written fixture:

| Real NRO report | Previously published source *numeric reference pair start* | Real guest NRO presentation frame | Displayed source-safe number |
| --- | ---: | ---: | ---: |
| `VPD_STAGE363_NUMERIC_DEMO_V1 event=on` | **519** | **12** | **+3 px** |
| `VPD_STAGE363_NUMERIC_DEMO_V1 event=last` | **559** | **52** | **+5 px** |

Both original-free NRO records carry identical platform simulation fingerprint `598b80987cb50c02` (this fingerprint belongs to the running ROM-free demonstration, not any commercial ROM), and exactly verified framebuffer pixels `panel_pixel=ff5b4118`, `edge_pixel=ffefda66`, `demo_glyph_pixel=ffefda66`. Real guest frame difference **40** proves the 41-entry sequence's endpoints were displayed in the running guest, with the previously synthetic-only exact shift mode segments (eight +3, thirty-two +4, one +5). This does not by itself independently authenticate each intermediate original NES image.

Host screenshots were saved directly from real `xwd` X11 capture, not generated mock views. Three of four `1280×720` screenshots (`screen-demo-1.png`, `-2.png`, `-3.png`) contain the distinctive cyan DEMO label/panel. An additional independent byte inspection of `screen-demo-2.png` found **1,867 exact RGB(102,218,239) cyan pixels**. `screen-demo-0.png` did not yet show the panel; the audit reports that distinction rather than inventing a missing first screenshot.

The strict auditor `tools/audit_nexium_stage364_scroll.py` validates actual guest ON/LAST, the genuine host chord, NRO screenshot-backed pixel marker, an unchanged source-free game fingerprint, source-only boundary values and no original-ROM or original-physics claims. `tests/test_nexium_stage364_scroll.py` supplies **17 fabricated-only negative/source-gate tests**, all 17 successful in the real NeXium workflow. The separately built official GUI nightly ran as a real process in Ubuntu 26.04/Xvfb with software Vulkan, not a host-side-only calculator.

## Public Stage364 reproducible code

- `.github/workflows/stage364-nexium-scroll.yml` — isolated, narrow CI on the actual working branch; one exact-head devkitPro NRO build plus one new real NeXium job. It refuses to return success without guest evidence.
- `tools/run_nexium_stage364_scroll_ci.sh` — official mutable-release metadata/asset digest verification; isolated GUI execution and strict report.
- `tools/nexium_stage364_scroll_probe.sh` — sends actual keyboard events after native manual driving entry; never writes guest `on`/`last` markers itself. Keeps genuine X11 snapshots.
- `tools/audit_nexium_stage364_scroll.py` and `tests/test_nexium_stage364_scroll.py` — strict evidence checking and synthetic negative regressions. No original NES media.

## Long-term owner-private evidence and SHA256 readback

- [Actual 12-member genuine NeXium guest evidence ZIP, 92,600 bytes](https://drive.google.com/file/d/1LGDTpDhBk5sfVmWsCCm2uQKRJfxYmRMa/view)
- [Exact-head ROM-free Switch NRO build artifact ZIP, 163,670 bytes](https://drive.google.com/file/d/1H0KSH_r-r8_VLOyugowg3Zt_CVwIw6gT/view)
- [Real NeXium screenshot with DEMO overlay](https://drive.google.com/file/d/11qPDWnjaY4dtkFWmT0FazWuICghTTo2M/view)
- [Strict JSON guest verdict](https://drive.google.com/file/d/1jTHh3Bw8UQWNBOwtfmwx2akVJ8cKMqNL/view)
- [Private source-safe Stage364 numerical outcome](https://drive.google.com/file/d/1_dRyNRq5jWRB52rjChYL8RdchQRH1L7T/view)
- [Private six-member Stage364 derived ZIP](https://drive.google.com/file/d/1Z_whlRv14RKXyuixeobk0yo_1IPI0Nbr/view)
- [Private source-safe SHA manifest](https://drive.google.com/file/d/1kzVvphqv_dkmfcMXo1xF1dNuAU8-OG7H/view)
- [Preupload SHA seal](https://drive.google.com/file/d/1ChFo6LoGpn_ovlHhXBp9bFcy0BCoeY_s/view)
- [Owner-only handoff](https://drive.google.com/file/d/193XKEk6cYcJaoN0GhXKsDhqC7DnSdDLn/view)
- [Independent Drive readback receipt](https://drive.google.com/file/d/1YtWyb-JM90GMw8QBxYCGFb9ciuxOsNvs/view)

Nine primary owner-private Google Drive assets were independently downloaded: **9/9 exact SHA-256 and byte-length** matches; 6-member derived ZIP CRC and all inner SHA matched; 12-member raw real NeXium evidence ZIP CRC and guest trace digest matched; separately downloaded original-free NRO ZIP CRC and extracted NRO SHA matched. The separate receipt was itself independently re-downloaded and byte-identical. The technical archive contains no original NES ROM/FM2, RGB or indexed proprietary frames, full original CPU/PPU traces or private original-source SHA pins.

**Engineering boundary:** Stage364 confirms opt-in manual diagnostic pixels, not new source-game camera simulation. Draft PR #99 remains Draft, branch `main` untouched. Proposed Stage365: preserve real emulator evidence and add a source-safe paused/manual frame stepping test (if needed) before any independent original NES comparison, with a prospective protocol for any new original-source capture.