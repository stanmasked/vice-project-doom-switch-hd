# Stage 41: focused pointer-byte read/write evidence

This opt-in FCEUX Lua script is **experimental** and separate from the
stage38 dispatcher tracer. It writes only to a private, git-ignored directory.
It does not export ROM contents or prove that any pointer is a level loader.

In a local FCEUX Lua session with a legally held ROM:

```lua
VPD_POINTER_DIRECTORY = "private/first_level"
VPD_POINTER_MAX_EVENTS = 20000
dofile("tools/capture_fceux_pointer_access.lua")
```

The script observes accesses to $AA/$AB/$A8/$A9 using `memory.registerread`
and `memory.registerwrite`. It records callback values and nearby bytes,
with a recursion guard so inspecting RAM doesn't recursively log itself.
The metadata marks overflows as incomplete. The program counter and effective
target address **are not recorded**. This does not establish that an indexed
instruction dereferenced the pointer or that the bytes contain map data.

The script expects byte-valued callback arguments; if a FCEUX version omits
read values, the script raises an error rather than silently inventing them.
The live API behavior, concurrent-hook interactions, and actual first-stage
observations still require emulator validation. Run this separately from the
stage38 logger until those conditions have been established.

A future confirmed result needs an execution trace identifying the instruction,
its operand/index register, the active physical PRG bank and the data read,
then independent agreement with the observed video/PPU scene.

## Stage 43: validate provenance before interpretation

Run `python3 tools/validate_pointer_access.py private/first_level/stage41_pointer_access.tsv --meta private/first_level/stage41_pointer_access.meta.txt --out private/first_level/stage43_pointer_audit.json`.

This checks row structure, ordered event identifiers, tracked RAM byte
addresses, event counts, ROM identity format and metadata consistency.
It **never** upgrades pointer-byte callback events into PRG-ROM reads,
instruction PCs or effective addresses. A truncated log remains explicitly
incomplete. Six synthetic Python regressions cover these boundaries.

The stage39 CI YAML was also corrected to restore actual newlines in the
video-alignment test step. Passing CI and authentic FCEUX instrumentation
still require independent confirmation.
