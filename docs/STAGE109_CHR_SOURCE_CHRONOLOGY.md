# Stage109: MMC3 → CHR fetch → BG framebuffer chronology

Synthetic-only, pinned native FCEUX instrumentation. Stage106 observed
MMC3 CHR writes; Stage108 observed 8,192 paired reads of selected pattern
bytes, and Stage107 observed 32,768 framebuffer pixels.

Stage109 adds a separate opt-in aggregate keyed to the native runppu advancing
internal-tick counter. It observes the first MMC3 command-2 $8001 write,
subsequent background CHR fetch callbacks, and final background pixel
assignments **in the same FCEUX process**. The two original mapper-4 ROMs
differ in their bank-select program byte only; Stage107/108 witnesses are
still checked independently alongside the timing result. The source-clock
ordering is nondecreasing; equal clock values are tolerated because the
instrumented clock is not a documented NES dot clock. We do not print raw
addresses, CHR bytes, framebuffers, or original-game ROM data.

For each bank, acceptance requires exactly one observed register write,
8,192 first eligible CHR fetches, 32,768 first eligible framebuffer pixels,
consistent expected BG values, a valid source-event order, and bounded
aggregate lags. No cross-process timestamp association is claimed. A
disabled instrumentation control must emit no positive witness.

**Limits:** Observed FCEUX runppu internal tick units are *not* physical NES
timing. This is an A/B synthetic ROM proof, not an authentic Vice: Project
Doom screenshot, first-level map, camera model, sprite reconstruction,
or a per-tile causal witness. The latter needs a further stage.
