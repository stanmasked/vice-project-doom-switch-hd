# Stage 37 — exact RAM $92 index-state dispatch and input branching

This research step inspects the **fixed 8KiB PRG bank** of the owner's
original Vice: Project Doom (USA) NES image. No original ROM data,
graphics, level binaries or memory captures are distributed in GitHub.
The finding is a *static instruction/control-flow proof*, **not** proof
that this code runs during the first playable level.

## Verified dispatch relationship

Nine exact instruction anchors and seven branch/table destinations
are checked in
[`audit_index_dispatch.py`](../tools/audit_index_dispatch.py).

The verified code at CPU **$E479** reads RAM **$90**, doubles it and
fetches a little-endian function address from table **$E4A6**, then
indirectly jumps via RAM **$25/$26**. Table word **index 13** lives at
**$E4C0** and contains destination **$E4E6**.

Consequently, **if** the dispatcher executes with RAM `$90=13`,
then this table entry directs execution to `$E4E6`.
This is a justified *conditional static link*, not a demonstrated
first-level runtime event. Other conditions leading to the dispatcher
and the full state machine remain under investigation.

At **$E4E6**, the code reads RAM **$91**:

- `$91 = 0`: invokes existing helper `$E577`, then `$E522`,
  increments RAM `$91` and returns. At `$E522`, the code stores
  register X into `$92` and sets other helper variables.
- `$91 ≠ 0`: relative `BNE` from **$E4E8** goes directly to
  **$E4F3**, the conditional input-routing procedure.

The important discovery is that **$E4F3 is reached by a relative
branch**. Looking only for `JSR $E4F3` or raw absolute function
pointers would fail to find this connection.

## Exact RAM $07 bit priority

The verified sequence at `$E4F3` tests the RAM byte **$07**.
The word “input” refers only to this suspected input-like variable;
its relationship to physical NES controller buttons is **not verified
here**.

| Condition | Exact static outcome |
|---|---|
| RAM `$91 = 0` | Initial refresh path, no RAM $07 branch |
| RAM `$91 ≠ 0`, RAM `$07` bit 7 set | Branch to **$E500**; sets `$90=$0B`, `$91=0` and jumps away |
| bit 7 clear, bit 2 set | Branch `BCS` at **$E4FA** → **$E50F**, index decrement |
| bits 7/2 clear, bit 3 set | Branch `BCS` at **$E4FD** → **$E519**, index increment |
| none | `RTS` at **$E4FF**, no index change |

Three `LSR A` instructions test the original **bit 2**, not
bit 3. A fourth `LSR A` tests **bit 3**. Thus bit 2 has priority
when both bit 2 and bit 3 are set. Bit 7's `BMI` has first priority.

The stage-36 update contracts apply to **this** branch:

- decrement with RAM `$92=0` produces **21**; otherwise one less;
- increment with RAM `$92 < 21` produces one more; otherwise **0**.

These conditions do **not** establish that $92 is globally bounded
to 0–21. Other original instructions set $92 to 147 or read it
from indirect game data, as documented in
[INDEX_92_AUDIT.md](INDEX_92_AUDIT.md).

## Static edge checks

| Source | Confirmed destination |
|---|---|
| `$E4E8 BNE` | `$E4F3` |
| `$E4F5 BMI` | `$E500` |
| `$E4FA BCS` | `$E50F` |
| `$E4FD BCS` | `$E519` |
| `$E511 BNE` | `$E515` |
| `$E51D BCC` | `$E521` |
| Table `$E4A6 + 2*13` | `$E4E6` |

The audit confirms the **full instruction signatures** as well as
the separately recomputed destinations. It refuses changed/mutated
code instead of silently claiming that an unknown ROM revision has
identical game logic.

One more mapping caveat: earlier initialization at **$E418**
writes `$92=$15` then executes **`JSR $C147`**. The identity
of the `$C147` callee depends on **MMC3 PRG bank mode and selected
bank**; it cannot be assigned unconditionally to physical bank 14.

## Reproduce, tests, and current limitations

Run on your *own* original ROM; the report contains metadata and
derived evidence but should remain private:

~~~sh
python3 tools/audit_index_dispatch.py "private/Vice - Project Doom (USA).nes" \
  --out private/stage37_dispatch_audit.json
python3 -m unittest discover -s tests -p test_audit_index_dispatch.py -v
~~~

Seven invented-ROM unit tests cover the nine anchored instruction
groups, changed signature rejection, seven static destinations,
bit priority including simultaneous bits, index boundaries without
global clamping, NES trainer/header handling, and a CLI round trip.

All nine anchors and seven transitions have been verified locally
against the user-owned original ROM, and all seven synthetic tests
passed locally.

**Not yet recovered:** real gameplay call frequency/state sequence,
NES controller bit meanings, MMC3 bank selection at indirect calls,
actual camera location, authentic first-stage collision/metatiles,
NPCs and events. A real FCEUX execution trace is still required
before moving those findings into the native Switch gameplay.
