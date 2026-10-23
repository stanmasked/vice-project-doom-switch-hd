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

## Evidence boundary and next step

CI uses only synthetic trace fixtures. The original Stage 325 raw trace is not included in the repository, so CI success does not claim that the original-source site clusters have been computed. The Stage 325 trace as described so far has no verified PRG-bank context; the auditor will say bank_context=no until a bank context is actually captured and joined to the observed sites.

After the private site list is generated and checked against the Stage 325 baseline, the next source-side capture should instrument those exact observed sites while tracking MMC3 $8000/$8001 writes and $0B–$0D writes. Only a capture with validated ROM/FM2 identity and matching frame/cycle context can supply the missing bank labels. No inference about road scroll, camera position, or physics is made at this stage.
