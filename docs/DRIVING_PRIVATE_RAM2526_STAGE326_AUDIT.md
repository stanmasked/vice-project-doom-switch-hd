# Stage 326 — RAM $25/$26 indirect-access site audit

Stage 326 introduces a private-input auditor for the Stage 325 FCEUX event trace. It is an analysis tool, not a gameplay or physics change.

## Checks performed

- Accepts CSV/TSV trace headers with common aliases for frame, CPU cycle, instruction PC/opcode/operand, RAM write address/value, pointer bytes, Y, effective address, and optional bank context.
- Recognizes 6502 indirect-indexed instructions using zero-page operands $25 and $AA.
- Validates each captured effective address against ((pointer_high << 8) | pointer_low) + Y, wrapped to 16 bits.
- Separates $25 and $26 write counts and write sites; classifies the bytes written between consecutive $25 indirect accesses as both, low only, high only, or none.
- Compares the observed pointer pair between consecutive accesses without printing the pointer bytes or effective addresses.
- When a bank-context field is actually present, groups access sites by that context and assigns opaque local labels. If the field is absent, the report explicitly marks bank context unavailable rather than inferring an MMC3 bank from the CPU PC alone.
- Counts $AA decoder accesses and same-frame effective-address overlaps, plus same-frame co-occurrence with writes to $0B–$0D. These are temporal observations, not proof of semantic or causal relationships.

## Rechecking the Stage 325 source trace

Run against the existing private trace, not a guessed or regenerated trace:

    python tools/audit_private_ram2526_indirect.py --input /private/path/to/existing-stage325-trace.tsv --require-stage325-baseline --output /private/path/to/stage326-aggregate.json --sites-output /private/path/to/stage326-observed-sites.tsv

The baseline guard requires the already reported observations: 22,146 writes to $25, 31,474 writes to $26, 20,524 $25 indirect accesses, 20,508 LDA ($25),Y, 16 ADC ($25),Y, and accesses in 319 of the 321 frames. A mismatch stops the analysis. The site list contains only observed PC/opcode/operand triples and must remain private; do not commit it.

The aggregate JSON intentionally omits raw PCs, pointer bytes, effective addresses, ROM/FM2 hashes, and local paths. The tool never changes the input trace.

## Evidence boundary and current next step

CI still uses synthetic trace fixtures; raw ROM/FM2 files and source captures remain in private Drive. The Stage 325 raw trace has now been recaptured and archived, and later private captures provide MMC3 bank context and writer attribution. These private traces are not committed to GitHub, so CI success does not mean the original-source site clusters were computed by CI.

Stage 327 found no $AA accesses in frames 600–920, while Stage 329 observed three in an earlier window and exactly reproduced the Stage 325 event subset in the overlapping frames 600–640. Stage 330 attributed all ten RAM $0B–$0D writes in frames 380–400 to actual instruction sites at the same FCEUX cycle. Stages 331–332 verified a $AA record/descriptor-processing call chain. This is not proof of road-scroll semantics.

Next, keep the $AA descriptor path separate from the $25/$26 and RAM $0D/PPU $2005 road-scroll investigation. Use the auditor on private traces locally, preserve aggregate-only outputs, and rerun GitHub Actions after repository changes. No raw private trace, site list, ROM/FM2 file, or local path belongs in the repository.
