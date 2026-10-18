# Stage149 — Native CPU $2002, $2003, $2004 OAM write audit

## Goal and evidence boundary

Stage148 generates two timing-identical, private Mapper4 ROMs. The
intervention updates sprite entries through real CPU writes while the
control rewrites their original values. Stage149 adds **actual FCEUX CPU
register-handler evidence**, not yet frame-to-frame OAM/XBuf rendering
evidence. Nothing in this test establishes original Vice: Project Doom
gameplay or a runnable Switch remake.

The native source is pinned to upstream FCEUX
\`8cdbeeb248f5a13aa97a58b4a0437ae13fb6aea8\`. The source injector
requires the existing Stage103 $2002 CPU read hook and the unique B2003
and B2004 register handlers. It instruments:

- Actual CPU read of $2002 when its returned value has bit7 set.
- Actual CPU write to OAMADDR $2003 = 31.
- Exactly five CPU writes to OAMDATA $2004 at OAM indices 31–35,
  with actual \`SPRAM\` read-back and original write values.
- Native newppu mode and the existing monotonically advancing
  internal PPU clock, establishing a bounded order between the
  successful $2002 read and the OAM writes.

**Important distinction:** Reading $2002 with bit7 set clears the
VBlank status bit. Requiring bit7 to remain high during later OAM
writes is incorrect. The audit saves the returned high-read event and
checks that the writes follow it within a bounded clock interval.

## Generated ROMs

The two ROMs have identical opcodes and write addresses; five operand
bytes per PRG bank differ:

| CPU register evidence | activate_ninth | preserve_eight |
|---|---:|---:|
| OAMADDR | 31 | 31 |
| Sprite7 X at OAM31 | 160 | 64 |
| Sprite8 Y at OAM32 | 120 | 255 |
| Sprite8 tile at OAM33 | 2 | 255 |
| Sprite8 attribute input at OAM34 | 0 | 255 |
| Sprite8 X at OAM35 | 64 | 255 |
| Attribute read-back in newppu | 0 | 227 |

The newppu B2004 handler masks attribute bits using
\`V &= 0xE3\` when the OAM address modulo four is two. Therefore
a control write of 255 to attribute OAM34 is stored as 227;
this does **not** make the ninth sprite active because its Y remains
255. The observer tests both the original register data value and
the masked in-memory stored value instead of assuming they are equal.

## Fail-closed gates

The native runner requires one source PASS per scenario, rejects the
same activation ROM deliberately labelled \`preserve_eight\` (five
actual data mismatches), and requires a probe-off FCEUX process to
remain alive with no witness. The runner may emit the summary

\`STAGE149_NATIVE_VBLANK_OAM_CPU_WRITE_PROOF\`

only after two authentic source witnesses, the wrong-mode rejection,
and probe-off control pass.

The Python and compiled C++ regressions exercise certificate parsing,
source-hook location, C++ event order, status-high omission, masked
attribute corruption and deliberately wrong case labels. These are
preflights, **not** proof of a real FCEUX execution.

Stage149 will count as native-confirmed only when the pinned FCEUX
GitHub Actions job succeeds with the exact summary marker. It still
does not show the newly active sprite being selected/excluded by PPU
on later frames. That separate OAM-status-XBuf bridge must be tested
in a subsequent stage with genuine render hooks.

No commercial ROM assets are uploaded or included in CI.
