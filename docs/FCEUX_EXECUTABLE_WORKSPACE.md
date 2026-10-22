# Stage 188 — runnable FCEUX in our working environment

A genuine **FCEUX 2.6.5** executable was installed and run inside
the project's Linux working container. Debian package indexes were
unreachable there (DNS), so the executable was restored from a
short-lived **ROM-free official-package GitHub Actions artifact**,
produced by the existing FCEUX Real Runtime Smoke workflow.
Both fceux and liblua5.1 Ubuntu amd64 DEBs passed SHA-256 integrity
verification before extraction. All other Qt, SDL and X11 dependencies
were found locally by the dynamic linker.

In that container the command is `/usr/local/bin/fceux`.
Actual Xvfb execution on a newly invented 6502 NES cartridge
reached frame 20, and an FCEUX Lua callback read original-free
RAM, screen RGB, ROM payload MD5, real CPU cycles and real
emulated CPU instruction events. This is *not* a re-created
screen rendering, synthetic Lua-only mock or original game.

For fresh **compatible amd64 Linux** workspaces, a reproducible
offline setup is provided. First download the existing
`fceux-runtime-package-ubuntu24` artifact from the project's
successful GitHub Actions FCEUX workflow, then run:

```bash
python3 tools/install_local_fceux.py \
  --artifact-zip /private/fceux-runtime-package-ubuntu24.zip \
  --prefix /opt/vice-fceux \
  --bin-dir /usr/local/bin

python3 tools/verify_real_fceux_runtime.py \
  --fceux /usr/local/bin/fceux
```

These scripts install no copyrighted game data, use no network, verify
all two package SHA-256 digests and dynamic link dependencies, and
require actual emulated frame 20 plus Lua/6502/CPU/PPU API proof.
Executable files are kept out of public Git.

The dedicated GitHub workflow `fceux-executable-toolchain.yml`
independently executes (a) a distro-installed real FCEUX and (b) a
reinstalled package-bundle copy on **Ubuntu 24.04** with an invented
NES program. This gives a repeatable check of portability. On other
Linux systems, installed SDL/Qt dependencies must be compatible.

The user's original Vice: Project Doom ROM and FM2 were **not** part
of the installation or smoke test. The private Stage181–187 original
source capture remains a separate evidence gate, and has not yet
been executed simply by installing FCEUX. GitHub Actions tests only
the invented cartridge.
