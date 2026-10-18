# Stage 56 — compare supplied 6502 instructions with observed PRG read addresses

`tools/compare_6502_read_candidates.py` combines the strict stage54
capture validator and stage55 effective-address calculator. The user
must supply explicit candidate instruction bytes and a recorded EXEC
sequence number. It inspects only later READ events in the same frame,
within an event-count limit, stopping at any intervening EXEC, SELECT,
or DATA mapper event.

Example with a **synthetic or private** stage53 capture:

```sh
python3 tools/compare_6502_read_candidates.py private/first_level/stage53_joint_context.tsv --meta private/first_level/stage53_joint_context.meta.txt --exec-seq 1 --opcode-hex AD5C83 --max-gap 3 --out private/first_level/stage56_candidates.json
```

The hex bytes are *externally supplied, unverified instructions*.
Even if a computed address matches a READ callback, the classification
is only `address_match_only`. The tool does not prove that the supplied
instruction bytes match the ROM, that this instruction generated the bus
read, or that it reads level data. Sparse execution callbacks may skip
intervening instructions. Missing register operands never yield guessed
addresses. Incomplete stage53 logs are rejected.

Five new synthetic tests cover mapper barriers, address matches without
causality claims, missing register context, invalid EXEC selection, and
incomplete logs. Live FCEUX behavior and real level geometry remain
unverified.
