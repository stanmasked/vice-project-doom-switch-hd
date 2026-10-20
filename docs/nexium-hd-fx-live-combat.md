# NeXium live-wave HD FX toggle — native pad evidence

This independent ROM-free Switch diagnostic extends the already verified
post-victory L+R control proof. It does **not** replace or weaken any previous
four-playthrough, retry, collision, dust, hit, sentry or post-victory V2 gate.

## Live input source

After the fourth real pad-driven guard defeat and the fourth second-wave
activation, NeXium **keeps Right (D) and Fire (Z) held**. While both remain
held and the sentry is alive, it physically presses and releases Q+E (the
NeXium keyboard mappings for libnx L+R) twice: OFF, then ON. It takes actual
X11 screen captures for each mode **before** the fourth exit record exists.

On the real guest's normal game tick, the new C++ source gate insists on:
- fourth-wave state, sentry HP 1 or 2, hero HP positive, guard defeated;
- simultaneous libnx Right+Fire, actual 2-pixel (`512` fixed unit)
  hero movement and at least one previously fired projectile;
- a fresh L+R edge changing the HD mode from ON to OFF or OFF to ON;
- source-identical gameplay simulation fingerprints before and after
  rendering alternate/presented HD framebuffers from the **same** scene;
- two differing 414,000-pixel HUD-free scene hashes (not an ON/OFF label).

These two live edges are recorded separately as
`sdmc:/switch/vice_project_doom/hd_fx_live_combat.txt`, format
`VPD_HD_FX_LIVE_V1`. The previously certified after-victory
`VPD_HD_FX_GUEST_V2` file remains untouched and must **also** contain its
two independent later edges. The test thus requires four new guest events
in one visible NRO session, two during wave combat and two after victory.

## Independent audit

`tools/audit_nexium_hd_fx_live.py` requires ordered live events strictly
between **real** fourth-wave activation and earned fourth-stage exit
frames, strict 512-fixed movement, valid Right+Fire, live sentry and hero,
equal simulation hashes before/after rendering, differing scene hashes,
matching physically injected host key records, and two real X11 screenshots
captured before the terminal event. Its PASS also requires the prior
after-victory V2 audit to have completed successfully.

The synthetic tests deliberately corrupt each field, reverse frame order,
move the samples outside the true wave boundaries, or remove the matching
host/X11 evidence. They cannot establish a NeXium guest PASS by themselves.

This is a research-only independently authored test stage. It does **not**
prove the original NES game's mechanics/artwork, a complete commercial
remake, real Switch frame rate, or actual Nintendo Switch hardware behavior.
