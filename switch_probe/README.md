# ROM-free native Switch scene: version 0.2.0

The earlier console smoke test is now an independent fixed-step native game scaffold.
It displays a 40-column ASCII viewport over an original test level. Move using the
D-pad / left stick, jump with A or B, and exit with Plus.

**This is not the original NES game or a completed remake.** Its movement constants,
tile layout, actor size, and physics are placeholders and have not been matched to
the commercial game's behavior. No ROM content is embedded in the NRO.

With devkitPro devkitA64 and libnx available:

```sh
make -C switch_probe clean all
python3 tests/check_nro.py switch_probe/vpd_native_probe.nro
```

See `docs/NATIVE_SIMULATION.md` for model details and current limitations.
CI compilation alone does not verify runtime on Switch hardware.
