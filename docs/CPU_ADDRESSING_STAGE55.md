# Stage 55 — constrained 6502 effective-address calculations

`tools/6502_read_address.py` is a small calculation helper for **supplied
synthetic instruction bytes**. Supported read instructions: LDA absolute,
absolute,X, absolute,Y, (indirect),Y; LDX absolute; LDY absolute. It
handles 16-bit wraparound and page crossing. The two zero-page pointer
bytes of (indirect),Y must be supplied explicitly; an unknown pointer or
index does not yield an invented address.

This does **not** load the original ROM or consume stage53 logs.
Those logs have no verified opcode bytes and do not establish that a CPU
read resulted from a particular instruction. Calculating a candidate
effective address is **not** evidence that the instruction executed a
read, that it belongs to the level loader, or that a PRG physical bank
was verified at the moment of access.

Nine synthetic regression tests exercise absolute addressing, indexed
page crossing, 16-bit wrap, indirect,Y, unsupported opcodes, unavailable
operands and malformed inputs. They are included by existing Python
unittest discovery in CI; passing status requires execution confirmation.
