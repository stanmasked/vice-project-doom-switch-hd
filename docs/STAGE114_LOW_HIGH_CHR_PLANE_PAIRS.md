# Stage114 — bounded native low/high background CHR plane pairing

The pinned FCEUX newppu implementation reads a low CHR pattern plane into
`pt[0]`, advances its internal source clock twice, and reads the high plane
into `pt[1]` in the same `BGData::Record::Read()` C++ call.

Stage114 installs two source-guarded observations immediately after those
real reads and attaches them to Stage113's begin/end record and pixel sink.
For each consumed 8-pixel background tile, it requires matching buffered
bytes and addresses offset by 8. The source sequence captures the actual
register-write epoch at each plane read, classifies pairs as both blank,
both filled or mixed, and detects writes between the two plane observations.

Four generated synthetic Mapper-4 ROMs with 0, 4, 8 or 12 NOP phase delays
must provide 128 pre-switch old-bank and 128 post-switch new-bank tile
pairs, plus their Stage111 tile and Stage113 prefetch witnesses in the
same native process. The strict current contract expects no mixed pair
and no switch between the planes. If such an event is observed, it rejects
the positive conclusion and exposes the failure in its diagnostic marker.
Both a fixed-bank ROM and a disabled-probe control must remain negative.

Crucial limitation: absence of mixed tiles for **these sampled synthetic
runs of this pinned FCEUX source** does not mean mixed tiles are impossible
on genuine NES PPU silicon, another emulator, a different register timing,
or the original Vice: Project Doom ROM. The low/high source-clock gap
is not a verified NES dot count.
