# Static PPU command queue analysis (original NES USA ROM)

A bounded static inspection of the original game's NMI routine identifies a command stream based at CPU RAM **$0600**. The queue processing index is read from RAM **$16**. Procedure **$E5DC** initializes a per-pass budget of **$3C = 60** units, looks up a command's cost at the table starting at **$E609**, and branches to the next iteration after dispatch through **$E612**.

## Key findings

- The table interval $E609–$E611 provides a terminator slot and cost slots for **eight** defined command IDs (1–8).
- The 6502 dispatcher doubles the command index, pushes an address from low/high-byte tables at **$E61B/$E61C**, then executes **RTS**. Actual handler execution starts at the saved address **plus one**, because the CPU increments its stack-return address.
- There are **seven distinct handler entrypoints** among eight command IDs; commands 1 and 6 share a handler but have different budget costs.
- The queue is tied to PPU register updates observed at **$2006** (address) and **$2007** (data).
- Twenty instruction anchors were checked against the owner's ROM; none required the original ROM to enter source control.

This confirms the structure of the command dispatcher but **does not** yet reconstruct palette values, stage tiles/metatiles, or per-frame command sequences. The cost bytes should not be identified with actual CPU cycles.

## Reproduce privately

~~~sh
python3 tools/inspect_ppu_queue.py '/path/to/owned.nes' --summary-only --out private/ppu_queue.json
python3 -m unittest discover -s tests -p 'test_ppu_queue.py' -v
~~~

The command table emitted by the analyzer is derived from the original ROM, so it belongs only in the ignored local private directory. GitHub CI exercises the algorithm using invented command costs and handler pointers. See [VIDEO_PIPELINE.md](VIDEO_PIPELINE.md) for the six CHR bank register sources.

**Next:** decode each handler's payload layout and capture actual $0600 command buffers during first-stage loading. A static command table alone cannot reconstruct a complete frame.
