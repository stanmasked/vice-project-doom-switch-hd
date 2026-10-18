# Nintendo Switch demo runtime witness (ROM-free prototype)

Both Switch NRO frontends now attempt to append a bounded diagnostic
record after completion of a 200-tick synthetic combat demonstration.
The graphical NRO records only after successful frame submission;
the ASCII NRO records only after consoleUpdate. No original ROM assets.

Optional writable SD location:

    sdmc:/switch/vice_project_doom/demo_witness.txt

The program writes at most four records per application session. Missing
or read-only SD never prevents launch or gameplay. Example expected
format (NOT yet observed on Switch or an emulator):

    VPD_ROMFREE_DEMO_WITNESS_V1 cycle=1 frames=200 shots=11 hits=3 health=0 fnv=5947277116621119566 state_match=yes frame_submitted=yes original_game_proven=no

Live simulation state must equal the full pinned FNV64 and exact shot/hit
counts to receive state_match=yes. Failed comparisons are recorded with
state_match=no; they are never hidden or silently described as success.

The graphical display also shows CORE STATE MATCH after a successful
completed synthetic cycle. This is not a hardware-runtime certificate.

## First-run procedure

1. Record the exact NRO SHA-256 from the green Actions artifact.
2. Start the NRO in a legal NRO-capable Switch homebrew environment
   configured with a writable SD device.
3. Observe the original synthetic shooting scene for at least 200
   simulation ticks. The test scene loops automatically.
4. Read demo_witness.txt, verify the expected counts and full fingerprint.
5. Independently record emulator name/version, actual display, controller
   response and application exit; the witness file alone cannot prove
   scanout, frame rate or even which binary created it.

## Regressions

Host CTest romfree_switch_demo_witness checks four full loops, strict
formatting, early/wrong-state rejection and the record-count limit.
Python source tests verify both NROs use the same writer and do not log
before the frame presentation step. Successful host CI or NRO compilation
is not evidence of a real device/emulator execution.
