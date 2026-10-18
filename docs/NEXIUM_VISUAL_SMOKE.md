# NeXium graphical screenshot and Plus-key smoke test

Extends the already independently verified NeXium runtime of Vice's
self-authored ROM-free Switch homebrew test scene. No console firmware,
keys, ROMs or original game graphics are used.

## Native capture (not generated placeholder art)

The Ubuntu 26.04 CI runner starts the SHA-256-pinned official NeXium
nightly in Xvfb with Mesa Lavapipe Vulkan. While the actual NRO runs,
X11 xwd captures the root display at two different times. ImageMagick
converts them into PNG images retained in the Actions artifact.

An independent Python stdlib tool checks the underlying binary PPM
pixel buffers for 1280x720 RGB layout, sufficient colors and scene
detail, and changes between two captures. Blank, identical, truncated
and malformed images cause failure. This is evidence of a changing
host display, not of precise video scanout timing or measured 60 FPS.

## Controller trial

After the second capture, the host tries the keyboard M key mapped to
Switch Plus by the known NeXium keyboard configuration. The exact
window lookup, key injection and whether the emulator process remains
alive are recorded in input-probe.txt. A host key-send alone does NOT
prove guest input was consumed or that the game gracefully exited.
These are separately tracked as unproven until guest-side evidence
exists. The emulator can remain open after the guest returns.

## Independent runtime signal

The earlier strict guest-produced sdmc:/ diagnostic file still must
contain 1–4 valid 200-tick synthetic gameplay cycles. The visual audit
is now an additional requirement and never replaces that guest log.
Both emulator logs and the captured screen PNGs are archived, including
on failure. All proofs must refer to the exact NRO and emulator hashes
recorded by the CI run.

Successful markers:

    VPD_NEXIUM_GUEST_DEMO_WITNESS_PASS
    VPD_NEXIUM_VISUAL_FRAME_PASS

No result is asserted until both appear in a successful GitHub Actions
job. This is not a test of actual Vice: Project Doom NES gameplay.
