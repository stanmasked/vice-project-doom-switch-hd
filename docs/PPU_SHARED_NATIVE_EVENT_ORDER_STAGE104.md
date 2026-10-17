# Stage104 — shared internal PPU clock for source status writes and CPU $2002 reads

Stage102 measured source-level FCEUX assignments at VBlank entry
and its frame-loop clear. Stage103 verified CPU reads of $2002 can
clear the PPUSTATUS VBlank flag independently before the source-level
frame clear. Stage104 correlates these events **inside the same native
FCEUX execution** using its own aggregate count of advancing runppu
internal tick units.

## Implementation and evidence contract

The existing, pinned Stage102/103 injection sites are retained unchanged:
- Immediately after PPU_status |= 0x80 in FCEUX_PPU_Loop
- Immediately after PPU_status = 0 in FCEUX_PPU_Loop
- Immediately after PPU_status &= 0x7F inside the CPU A2002 handler

`tools/vpd_newppu_raw_step_probe.h` adds an explicitly gated
`VPD_NATIVE_SYNTHETIC_EVENT_ORDER` observer. The runtime requires the
separate `VPD_STAGE104_EVENT_ORDER_PROBE=1` opt-in. Unlike the individual
Stage102/103 reporters, this observer receives both families even
when the older reporter environment variables are disabled.

Each source-level VBlank assignment begins or ends an **emulator
source window**. Each CPU read checks whether bit 7 was returned,
present before the clear, and absent afterwards; a high-bit CPU read
must have occurred after a source set but before the frame-loop clear.
The same cumulative internal tick counter is sampled at the source set
and high-bit read, yielding a bounded elapsed-tick difference, never
an absolute frame timestamp.

After 16384 CPU reads, the observer prints a single aggregate:
source entries and clears, number of high returned/cleared CPU reads,
high CPU reads inside an active source window, subsequent low reads
within the window, min/max high-read lag, and inconsistency count.
All raw coordinates, event sequences, ROM bytes, register values,
screenshots, CHR contents and original-game identities are excluded.

## CI and synthetic fixtures

The existing pinned full FCEUX build receives the additional
`-DVPD_NATIVE_SYNTHETIC_EVENT_ORDER` flag and retains all prior
Stage100–103 acceptance checks. Under Xvfb/X11, an independently
generated ROM executes repeated LDA $2002; Stage104 insists on at
least two source sets, at least one CPU high-bit read, correct read
clearing inside an active source window, and subsequent low reads.
A second run disables its observer and must emit no marker while
remaining alive for the bounded observation interval.

Local ROM-free validator and stand-alone C++11 callback tests:

    python3 -m unittest discover -s tests -p 'test_fceux_stage104_native_event_order.py' -v

## Do not overinterpret

Source windows are not the complete hardware PPUSTATUS history.
The upstream FCEUX CPU handler has its own read-clear semantics,
and debugger paths may differ. Callback ordering within a single
emulation step is a software implementation detail.
Advancing runppu tick units are **not independently measured NES
physical dots, scanlines or VBlank timings**. No original first-level
capture, CHR-to-background causality, camera map, or HD geometry has
been established; HD graphics replacement stays disabled.
