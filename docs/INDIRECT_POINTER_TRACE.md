# Stage 35 — candidate provenance of the indirect scroll-data pointer

This milestone advances the original Vice: Project Doom NES investigation
from stage 34's `LDA ($AA),Y` decoder to an **earlier, separately observed
writer of zero-page pointer $AA/$AB**. All facts below are based on local
static analysis of the user-provided ROM. No original ROM or extracted game
tile bytes are stored in the source repository.

## Three strictly verified instruction anchors

| Physical 8 KiB PRG bank | Bank-local offset | Confirmed instruction behavior |
|---|---:|---|
| 12 | `$035B` | Reads RAM `$92`; performs ASL/ADC arithmetic; writes `$AA/$AB`; reads two bytes via `($AA),Y` into `$A8/$A9` |
| 14 | `$0906` | Starts previously recovered packed-byte scroll-data decoding with `LDA ($AA),Y` at Y=0 |
| 14 | `$08CA` | Contains a literal `JSR $C906` instruction pointing to the decoder **assuming bank 14 is at $C000** |

In the bank-12 routine, the encoded table base is CPU address
`$8376`. The byte at descriptor offset 0 is available through the
pointer in `$AA/$AB`; descriptor offsets 1 and 2 are read into
`$A8/$A9` by this routine. **No meaning for these descriptor fields
has been established.**

These instruction signatures are real, but the *link between the two
routines remains a hypothesis* until their sequence and PRG bank
configuration are observed during execution.

## Critical CPU-bank mapping condition

These are **physical PRG banks**, not globally fixed CPU addresses.
In the relevant MMC3 mode-0 configuration:

- To read table entries at CPU `$8376`, physical bank 12 must
  actually be mapped into the `$8000–$9FFF` slot.
- A bank-14 decoder at CPU `$C906` requires bank 14 to be mapped
  into `$C000–$DFFF`.
- The fixed PRG bank at `$E000–$FFFF` stays a different region.

The data and control flow **cannot** be asserted solely by seeing
matching code in two physical banks. Other RAM writes may overwrite
`$AA/$AB`, and MMC3 bank mapping can change between procedures.

## Index arithmetic — important non-obvious limitation

For some small values of the RAM `$92` input, the anchor's
`ASL; ADC $92; ADC #$76; ADC #$83` carry behavior produces an address
matching `$8376 + 3 × index`. However, this is **not a general 16-bit
multiplication and addition** for every possible 8-bit index.

The tool emulates each of the CPU carry steps, rather than silently
using `base + index × 3`. Examples:

| Hypothetical RAM $92 | Observed instruction semantics | Naive base + 3×index |
|---:|---:|---:|
| 0 | `$8376` | `$8376` |
| 1 | `$8379` | `$8379` |
| 46 | `$8400` | `$8400` |
| 85 | `$8475` | `$8475` |
| 86 | **`$8379`** | `$8478` |

Values in the table are *symbolic test inputs*, not observed in a
first-stage playthrough. The valid RAM `$92` range has **not** been
proven. We therefore cannot infer a table length, stage ID count,
level-selection format or real scrolling position.

A conservative scan reports **13 literal candidate direct writes/RMW
operations to $AA/$AB** across the PRG image. Only the bank-12 setup
sequence is covered by these exact instruction anchors. The remaining
byte matches may be data or unreachable code.

## Reproduce privately

Run against an original ROM you lawfully possess:

```sh
python3 tools/audit_indirect_pointer.py "private/Vice - Project Doom (USA).nes" \
  --out private/stage35_pointer_trace.json
python3 -m unittest discover -s tests -p 'test_audit_indirect_pointer.py' -v
```

The six public tests use **fabricated** 6502 PRG fragments, testing
three anchors, negative mutation cases, exact carry behavior, raw
writer-candidate status, NES mapper/trainer guards and CLI output.
They contain no original ROM or game stage table entries.

## Future FCEUX measurement

The private PPU/RAM capture now records these *postframe* bytes:

- `stage35_candidate_index_ram_92`
- `stage35_candidate_pointer_ram_aa`
- `stage35_candidate_pointer_ram_ab`
- `stage35_candidate_descriptor_ram_a8`
- `stage35_candidate_descriptor_ram_a9`

The metadata explicitly says
`stage35_pointer_provenance=static_bank12_candidate_not_runtime_proven`.

A real first-stage trace must independently establish that bank 12
executes its pointer setup, which MMC3 mode/bank state is active, and
whether bank 14's consumer executes **without pointer replacement**.
That is the prerequisite for linking table entries to a level or
to the PPU scroll writer from stage 33.

## Verification status

- Original-ROM local audit: all **three** static instruction signatures match.
- Local ROM-free unit suite: **six tests passed**.
- GitHub Actions has again failed **before a runner was provisioned**:
  the latest run has `runner_id=0` and zero executed steps. Do not
  describe this as passing GitHub CI.
- No physical Switch testing or new Switch NRO was involved in this
  research-only milestone.

**Original first-stage geometry, collision rules, actual camera origin
and timing remain unverified.**
