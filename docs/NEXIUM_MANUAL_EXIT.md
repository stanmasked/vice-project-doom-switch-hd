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
