# NeXium guest-side manual input and Plus cleanup proof

The previous NeXium test proved four native 200-frame automatic shooting
cycles and two changing X11/Vulkan screenshots. Host-sent keyboard commands
alone did not establish that libnx received any controller buttons.

This PR introduces a second, strictly separate *guest-created* record:
`sdmc:/switch/vice_project_doom/manual_witness.txt`. It is truncated
once when the homebrew starts and appended only by real libnx application
code.

The existing R+A combination, mapped in NeXium's default keyboard to
E held while C is pressed, **additionally** toggles into manual mode,
for emulator tests that cannot map a left-stick click. The original
left-stick-click toggle remains intact. During manual play the guest
records **only observed effects** in this exact order:

1. `enter`: R+A reached the native code and reset the game to manual.
2. `right`: native Right produced a positive character X delta.
3. `fire`: native Y caused the projectile counter to increase.
4. `jump`: native B resulted in negative vertical velocity.
5. `left`: native Left produced a negative character X delta.
6. `plus`: native Plus was observed in the input loop.
7. `exit`: application closed its framebuffer and reached cleanup.

A fixed 7-event text format includes sequence, input effect, game frame
and positive numeric effect. Missing SD, wrong input order, spurious
button presses or a failed gameplay effect **cannot** be classified
as a pass by the independent host auditor. Keyboard defaults used:
E=R, C=A, D=right, Z=Y, X=B, A=left, M=Plus. The exact keys and
window lookup are saved separately as host-side input logs.

A host C++ regression checks event validation and serialization without
libnx. Python regressions reject altered, reordered, duplicated and
missing guest records. CI still requires the previously verified
guest-created autonomous-demo log and the actual two changing X11
screenshots.

This is evidence of running *original ROM-free homebrew test-scene
control logic* inside NeXium. It does not prove that the emulator GUI
process terminates, that the physical Switch runs the binary, precise
frame pacing, or reproduction of original Vice: Project Doom gameplay.

## Host GUI lifecycle diagnostics (subsequent stage)

The Plus event and framebuffer cleanup come from the guest NRO. They do **not**
mean the NeXium graphical process closed. The original shell probe inspected
the PID of the `timeout(1)` watchdog and described it as the emulator. That
PID is not an independent observation of the actual GUI process.

The revised runner preserves the existing seven-event guest proof and adds
`host-gui-lifecycle.txt`, including the visible state of the originally
focused X11 window three seconds after injecting Plus, the wait code from
`timeout(1)` and a conservative host-process classification:

- `watchdog` (124): timeout deadline terminated the subprocess.
- `signal_or_watchdog` (137): a signal or escalated watchdog; ambiguous.
- `returned_zero` (0): the wrapped process returned successfully.
- `returned_nonzero`: another return code; no clean-exit assertion.

The independent `audit_nexium_gui_lifecycle.py` rejects contradictory or
truncated records, requires the **separate** successful guest and host-key
audits, and writes `host-lifecycle-result.txt`. A missing original X11
window does not prove the whole GUI exited; a normal process return after
Plus alone does not prove Plus *caused* it. The report therefore explicitly
retains `emulator_gui_exit_caused_by_plus_proven=no`.

This new test provides a reproducible explanation for the previous unknown
host lifecycle, not a claim of original NES-game fidelity or a release-ready
Switch port.

## Native kernel/runner exit proof (subsequent stage)

The previous run [NeXium Actions #39165261054](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/39165261054)
saved its actual native log under `xdg-config/NeXium/logs/`. The log
confirms an additional, *independent* level of completion after the SD
witness's seven manual events:

```text
[20:54:32.561] [ INFO] [nexium_kernel::kernel::svc] svcExitProcess - terminating process (x0=0x0 lr=0x1000162cc)
[20:54:32.561] [ INFO] [nexium_runner::boot] Process exited
[20:54:32.561] [ INFO] [nexium_runner::boot] Emulation complete: 19267000000 cycles, 3166 SVCs
[20:54:32.563] [ INFO] [nexium_runner::boot] [core2] stopped
[20:54:32.563] [ INFO] [nexium_runner::boot] [core1] stopped
[20:54:32.563] [ INFO] [nexium_runner::boot] [core3] stopped
```

The new `tools/audit_nexium_guest_process_exit.py` examines the original
NeXium log, not the guest-created report, and requires exactly one
run-local log, the expected NRO launch, guest CPU start, kernel-level
`svcExitProcess` **with zero status**, runner process-exited/complete
markers, and all three CPU stop records in causal log order. It also
requires both prior independent host and manual guest auditors to pass.
The mutation tests reject dropped, duplicated, reordered, altered-status
and wrong-NRO records. The CI result is saved in `native-exit-result.txt`.

This establishes **normal termination of the homebrew guest process
inside NeXium** and successful runner teardown for the pinned emulator
binary. It does not prove that the NeXium GUI application closes,
that Plus alone was the cause, or that the game matches the original NES
title. A still-visible GUI window after guest process termination is
not, by itself, a homebrew failure.
