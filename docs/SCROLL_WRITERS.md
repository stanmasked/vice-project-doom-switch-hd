# Stage 34 — original NES scroll-writer dataflow audit

## What was verified

The user-provided **Vice: Project Doom (USA)** ROM has been inspected
locally. The ROM has mapper MMC3, 128 KiB PRG and 128 KiB CHR.
Eight 6502 code signatures were verified against the original **physical
PRG banks**. This advances stage 33 from *reads used by a PPUSCROLL
emitter* to several concrete **writers of the values**.

These offsets name physical 8 KiB PRG bank data, not unconditional CPU
addresses. In particular physical bank 14 maps to the fixed $C000–$DFFF
slot in MMC3 PRG mode 0, but NOT unconditionally in mode 1.

| Verified anchor | Physical PRG bank / offset | Effect |
|---|---|---|
| Zero initialization | 15 / $0580 | Sets $0D, $0B, $0C to zero |
| Packed-byte decoding | 14 / $0906 | Reads through pointer ($AA),Y and derives $0C, $0B, $0D |
| Subtract two | 14 / $0BB0 | Subtracts two from the $0B/$0C low/high pair with borrow |
| Add two | 14 / $0BC6 | Adds two to that pair with carry |
| Decrement X-like pair | 14 / $17B7 | Conditionally decrements $0C, then $0B |
| Increment X-like pair | 14 / $17C9 | Increments $0B, carries into $0C |
| Decrement second source | 14 / $1801 | Conditionally decreases $0D |
| Increment second source | 14 / $180A | Conditionally increases $0D |

The terminology *X-like pair* describes arithmetic structure only.
It does **not** yet certify a player/world camera coordinate.
Branches leading to these instructions and first-level execution
frequency still need runtime evidence.

### Exact packed-byte relationship (under the verified instruction path)

If the byte read by `LDA ($AA),Y` is `b`, the traced writes produce:

- RAM $0B: `((b & 0xF0) << 1) & 0xFF`
- RAM $0C: `(b >> 7) & 1`
- RAM $0D: `(b & 0x0F) << 4`

For the *artificial example* `b = $95`, the resulting values are
`$0B=$20`, `$0C=$01`, `$0D=$50`.

The same snippet also modifies other memory locations and condition
flags; the formulas summarize **these three output bytes**, not
the entire routine. The source pointer `($AA),Y` is not yet proven
to reference actual first-level metadata.

### Candidate byte-pattern scan

Across 16 physical PRG banks, the conservative scanner found
**150 literal direct-write/RMW byte patterns** whose operands appear
to address $0B/$0C/$0D. Bank 14 contains 23; bank 15 contains 3.

These are **not 150 proven executable instructions**. Without complete
control-flow/bank-switch analysis, byte patterns may occur in data,
unreached code or different game contexts. Indexed zero-page
instructions are separately marked `indexed_base_only_not_target`
because their effective addresses depend on X or Y. Indirect and
indexed absolute writes are NOT resolved by this scan.

## How to reproduce locally

Run only against the user's private original ROM:

```sh
python3 tools/audit_scroll_writers.py "private/Vice - Project Doom (USA).nes" \
  --out private/stage34_scroll_writers.json
python3 -m unittest discover -s tests -p 'test_audit_scroll_writers.py' -v
```

All six public regression tests generate a **synthetic** MMC3 PRG image
and check eight anchored groups, corrupted anchors, transformed values,
raw candidate classification, trainer/header guards and CLI execution.
They use no original NES game bytes.

A private ROM-derived JSON report was created locally. It is **not**
committed to the public source tree, nor is the original ROM.

## Confidence and next decisions

**Verified statically:** existence and exact bytes of eight routines,
their arithmetic and PPU-emitter input/output relationships.

**Still unverified:** which branches execute during the first level,
the pointer origin $AA/$AB, precise MMC3 bank mode at each call, whether
$0B/$0C are actual *world* X camera coordinates, HUD/IRQ scroll
overrides, collision metatiles and first-level entity positions.

Next, trace the source pointer **$AA/$AB** and dynamic call paths in the
private ROM, and capture CPU-cycle PPU register writes in a running
FCEUX first-stage session. Map geometry should only be committed after
those independently measured observations agree.

### CI status

Local six-test suite: passed. GitHub Actions at the stage-34 commits
reported failure before a runner was assigned (`runner_id=0`, zero
executed steps), following a similar incident during stage 33.
This **does not constitute a passing GitHub CI result**.
