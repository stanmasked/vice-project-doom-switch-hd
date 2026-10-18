# Stage105 — Pre-clear provenance of FCEUX frame-loop PPUSTATUS reset

Stage104 established a common internal software clock for native FCEUX
source-frame VBlank assignments and CPU $2002 reads on a synthetic NROM.
Stage105 determines **what bit 7 contained immediately before** the
frame loop executes its independent `PPU_status = 0` assignment.

## Native source points

- The Stage102 hook immediately after `PPU_status |= 0x80` opens
  an emulator source-status window.
- The Stage103 hook immediately after the CPU `$2002` read-clear
  records whether bit 7 was returned and then cleared by that read.
- A new Stage105 hook immediately **before** the exact `PPU_status = 0`
  assignment checks bit 7, whether a high-bit CPU read already
  occurred in the window, and elapsed internal runppu tick units.
- The existing Stage102 after-clear hook validates pairing and ensures
  that the frame reset actually left bit 7 unset at the same tick.

The pinned patcher accepts only exact Stage103 source composed from
the original upstream FCEUX Git blob, the Stage98 runppu patch,
the Stage102 status hooks and the Stage103 CPU-read hook. It refuses
modified contexts, repeated instrumentation and mixed line endings.
The original upstream checkout is not modified in this repository.

## Separate reasons for a low bit before the frame reset

Stage105 reports mutually exclusive, aggregate categories:

- Bit already low and a high-bit CPU read occurred earlier in the
  same source window (read-clear already took effect).
- Bit still high, with no recorded high-bit read in the window.
- Bit low, without a recorded high-bit read in that window.
- Bit unexpectedly high **after** a recorded CPU high-bit read
  (an inconsistency that fails validation).

These categories are necessary because a frame-loop write of zero
must **not** be presented as the cause of clearing a bit that
a CPU `$2002` read already cleared.

The witness also checks source-frame pre/post count equality,
valid read-clear behavior, subsequent low CPU reads and the
min/max internal-clock distance between the last high-bit CPU read
and the corresponding frame reset. It only emits aggregated numbers.

## Testing / privacy

A new C++11 unit fixture creates synthetic source windows and
CPU reads, including negative and opt-out cases. The pinned native
FCEUX executable runs another tiny original NROM which repeatedly
executes `LDA $2002`, inside Xvfb/X11. The independent observer
requires compile flags `VPD_NATIVE_RAW_PPU_PROBE` and
`VPD_NATIVE_SYNTHETIC_PRECLEAR`, plus
`VPD_STAGE105_PRECLEAR_PROBE=1`. An opt-out control must remain alive
and emit no evidence. Stage100–104 regressions remain enabled.

The CI stores synthetic ROMs and native run output only in private
temporary directories; no commercial ROM contents, screenshots,
PPU bytes, raster positions or frame-by-frame event traces are
published.

## Explicit limits

All evidence is from FCEUX's **software source and read paths**.
Internal tick units are not verified physical NES dots or VBlank
edge timing. The source code and event order do not establish
the actual original game's first-level background, camera motion,
CHR banking visual output or accurate HD geometry.

The HD graphics substitution remains disabled.

Command to run ROM-free checks:

    python3 -m unittest discover -s tests -p 'test_fceux_stage105_frame_preclear.py' -v
