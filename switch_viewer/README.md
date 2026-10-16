# Switch SDL2 diagnostic CHR viewer — experimental

This is **not** a playable port of Vice: Project Doom. The source demonstrates native rendering of locally generated CHR atlas BMPs; no Switch `.nro` build is validated yet.

Prerequisites: devkitPro with Switch development libraries, SDL2 Switch portlibs, and the developer's own dumped/generated atlas files.

From the project root, first build the native CLI and use your own local ROM to generate the resources:

```bash
cmake -S native_core -B build/native_core
cmake --build build/native_core
mkdir -p switch_viewer/assets
build/native_core/vpd_chr_cli '/path/to/your/ROM.nes' switch_viewer/assets/
```

Then from a correctly configured devkitPro environment run `make -C switch_viewer`. The intended target is `vpd_chr_viewer.nro`. This build step depends on the external toolchain and may require further work. Do not upload `.nro` files containing ROM-derived atlas images.

Left/right D-pad or L/R cycles pages; Plus/Start exits. Source uses SDL2 APIs and ROMFS loading. Generated `assets/` is ignored by Git.
