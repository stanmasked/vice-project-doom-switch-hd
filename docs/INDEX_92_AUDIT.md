# Stage 36 — RAM $92 assignments and the conditional 0–21 index cycle

## Summary of original-ROM evidence

Local analysis of the user-owned Vice: Project Doom (USA) NES ROM
confirmed **six** precise instruction signatures in three physical
MMC3 8 KiB PRG banks. This extends the stage-35 investigation of
`$92 → $AA/$AB`. The ROM, table contents, original images and
live game captures are **not** committed to GitHub.

| Physical PRG bank | Offset | Verified behavior |
|---:|---:|---|
| 15 (fixed) | `$0418` (CPU `$E418`) | `LDA #$15; STA $92`, initializes index to 21 |
| 15 (fixed) | `$050F` (CPU `$E50F`) | For zero index loads `#$16` then `DEX`; otherwise decrements X, jumping to the shared store at `$E522` |
| 15 (fixed) | `$0519` (CPU `$E519`) | Compares to `#$15` unsigned, increments if smaller, otherwise sets X to `#$FF` before `INX; STX $92` |
| 14 | `$0138` | `LDA #$93; LDY #$11; STA $92`, a different constant value **147** |
| 14 | `$01C8` | Indirect data reads via `($A8),Y`, with second read stored to `$92` at Y=`$18` |
| 12 | `$035B` | The previously verified `$92` consumer that calculates the `$AA/$AB` pointer |

**Bank 14 offsets are not unconditional CPU addresses:** mapping
depends on active MMC3 mode and bank configuration. Neither the
relative execution order nor active first-level call sites are proven.

## What the 0–21 wrap actually guarantees

The fixed-bank seed and two selected update procedures preserve the
set **0 through 21 inclusive**, provided this is the only writer
sequence on the path.

For an input `n` already in 0–21:

- **Increment:** `n + 1` when `n < 21`, otherwise **0**.
- **Decrement:** `n - 1` when `n > 0`, otherwise **21**.

That is a **22-state cycle on these code paths**. It does **not**
establish 22 actual levels, the maximum stage index, a descriptor
table length or a globally enforced invariant of RAM `$92`.

For example, the decrement path given an *unexpected* `$92 = 147`
would produce 146, not a clamped value. The increment path given 147
would produce 0. The completely different bank-14 code also assigns
147 directly, and reads a value from indirect data with an unknown
range.

An earlier stage-35 observation therefore remains essential:
the `ASL/ADC` pointer calculation **does not always equal**
unbounded arithmetic `$8376 + 3 * $92`. Examples from exact
symbolic 6502 carry emulation:

| Hypothetical index | Emulated pointer | Naive 16-bit formula |
|---:|---:|---:|
| 0 | `$8376` | `$8376` |
| 21 | `$83B5` | `$83B5` |
| 86 | `$8379` | `$8478` |
| 147 | `$8430` | `$852F` |

These are **hypothetical inputs**, not measured values during gameplay.
In particular, code setting 147 does not by itself prove that the
bank-12 descriptor lookup subsequently executes with that value.

## Conservative supplementary scan

The new audit identifies **15 literal direct write/RMW patterns**
and **4 indexed zero-page base patterns** potentially related to
RAM `$92` across all 16 physical PRG banks.

Literal byte matches are not proofs of executable instructions:
some may be graphics/data, unreachable code, or other game modes.
For indexed addressing, the target address depends on a runtime
index and therefore **may not actually be $92 at all**.

## Reproduce against your local ROM

~~~sh
python3 tools/audit_index_92.py "private/Vice - Project Doom (USA).nes" \
  --out private/stage36_index_92_audit.json
python3 -m unittest discover -s tests -p test_audit_index_92.py -v
~~~

Seven synthetic tests verify all six anchors, reject mutations,
check every 0–21 wrap transition, distinguish behavior outside that
domain, classify raw/indexed byte matches, validate ROM/trainer
headers and exercise the CLI using a **fabricated** MMC3 PRG.

The public tests never contain actual Vice PRG-ROM data. The private
original-ROM report should not be pushed to the repo.

## Better reference snapshots and next steps

The FCEUX Lua capture adds postframe RAM samples `$90`, `$91`
and `$93` to the already captured `$92`, `$AA/$AB` and
`$A8/$A9`. All are marked as **static-source candidates**, not
verified camera variables. Real cycle-timed debugging must:

1. Distinguish which writer sets `$92` during actual first-stage play.
2. Verify MMC3 bank selection while the bank-14 indirect read runs.
3. Trace whether the bank-12 pointer routine runs afterward and
   whether another writer changes `$92` or `$AA/$AB` between calls.
4. Verify the actual descriptor domain and collision/map format
   independently of PPU scrolling.

No authentic first-stage map, enemy placement, collision format,
or verified world camera has been recovered. No Switch NRO changed.

## Verification status

The original-ROM anchors match locally and seven synthetic Python
tests passed. Hosted GitHub CI has repeatedly failed before a
runner was assigned in previous research milestones. A green
GitHub Actions result must be explicitly checked rather than assumed.
