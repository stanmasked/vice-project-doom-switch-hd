# Native Switch probe (ROM-free)

This probe builds a minimal independent libnx console application, not a playable port. It does not require, download, read, embed, or distribute a NES ROM or game art.

It checks that the devkitPro toolchain can compile/link code targeting Nintendo Switch and produce a .nro. A successful GitHub Actions build is **not** proof of running correctly on hardware.

Local build with devkitPro devkitA64/libnx configured:

```sh
make -C switch_probe
python3 tests/check_nro.py switch_probe/vpd_native_probe.nro
```

The binary prints a plain console message and polls for the Plus button to exit. It intentionally contains no original game data. GitHub Actions uploads the .nro as a diagnostic artifact, once successfully built.
