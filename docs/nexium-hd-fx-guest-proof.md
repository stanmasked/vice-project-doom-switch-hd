# NeXium L+R native guest evidence (ROM-free)

This Draft PR is stacked on the passing host-graphics/Native-Core/Debug+Release
commit of PR #49. No original NES ROM, images or Nintendo intellectual property
are read or published.

## Real guest gesture

After the **fourth earned** manual stage-clear (and only then), the real X11
NeXium runner issues Q followed by E, corresponding to L and R under the
expected NeXium keyboard defaults. It releases both, then repeats the chord.
All prior four-playthrough gameplay/guard/sentry/impact/dust attestations
remain earlier in the same guest session and unchanged.

Only actual libnx `PadState` button transitions can cause the guest record.
An X11 host input log alone does not prove the feature.

## Source-coupled visual proof

On each *actual* manual L+R state change, the NRO:
1. Copies the current authoritative `SceneView` (no new physics tick).
2. Renders the opposite HD settings into its existing native RGBA8888
   framebuffer, then fingerprints 414,000 scene pixels in x=[0,900),
   y=[160,620).
3. Renders the currently selected HD setting into the same framebuffer for
   real NeXium presentation and fingerprints the same region.
4. Appends one strict guest SD record only if the two pixel hashes differ.

This region excludes the right-side `HD FX: ON/OFF` label, so *just changing
the label is not evidence of changing the authored scene effects*. All four
source-conditioned HD layers are independently covered in PR #49 native host
CTest. A pair of real X11 screenshots adds corroborating **visible HUD**
changes: mode OFF, then ON. No screenshot is substituted for guest events.

## Fail-closed gates

`tools/audit_nexium_hd_fx_guest.py` rejects stale/missing/malformed/
duplicate/host-authored records, absent fourth-stage PASS, nonincreasing
frame numbers, equal same-frame scene hashes, absent Q+E evidence, incomplete
X11 screenshots, or missing HUD raster delta.

`tests/test_nexium_hd_fx_guest.py` mutates the guest record to ensure the
parser rejects absent edges, counterfeits, wrong mode order, source changes,
zero pixels, equal images and malformed data. NeXium must still execute the
full native NRO for final acceptance; these synthetic parser tests alone are
never accepted as guest proof.

Original NES game fidelity, real Nintendo Switch hardware latency and
performance are **not** established by these checks.

## Guest V2: same-frame gameplay-state identity

The follow-up native runtime records two **actual** `Simulation::fingerprint()`
values on each real libnx L+R edge, one after the normal simulation step but
**before** any differential drawing, and the other **after** both draws.
These values must be identical for the existing witness to be emitted.
The versioned `VPD_HD_FX_GUEST_V2` line carries `simulation_before` and
`simulation_after` as sixteen lowercase hexadecimal digits. The fail-closed
NeXium auditor checks equality independently, not only through the NRO gate.

It still requires two distinct HUD-free scene hashes and real NeXium
screen captures, so a frozen physics state or unchanged pixel image does not
pass by itself. This proves only that the two native raster passes did not
change the exposed source simulation during that frame; it does **not**
measure real Switch frame rate, gameplay correctness versus the NES ROM, or
runtime performance. PR #51 separately exercises dual-simulation replay and
retry invariance on the host.
