# Stage 59 — optional PRG identity pinning and rejection explanations

Stage58's `tools/correlate_verified_prg_reads.py` now accepts optional
`--expected-prg-sha256`. When provided, the SHA-256 digest of the
**local headerless PRG** must match the supplied 64-digit value before
any instruction/read candidates can be returned. The digest is an
independent *expected input supplied by the operator*; it is not
authentication against an official reference or FCEUX's full ROM MD5.

Example:

```sh
python3 tools/correlate_verified_prg_reads.py private/first_level/stage53_joint_context.tsv --meta private/first_level/stage53_joint_context.meta.txt --prg private/game_prg_raw.bin --exec-seq 5 --instruction-hex AD5C83 --expected-prg-sha256 YOUR_PRECOMPUTED_64_HEX_DIGITS
```

Mismatch: `prg_identity_mismatch` and zero read candidates. Unknown
bank, byte mismatch and bank-window boundary are reported using
`verification.status` plus a top-level `reason`; no original bytes
are exported. SHA-256 pinning protects against accidental use of a
different local PRG file only when the expected digest comes from a
trusted independently recorded source. It does not establish code/read
causality, stage geometry, or ROM authenticity.

Three synthetic tests cover matching, mismatching and malformed digest
inputs. A passing CI result and real FCEUX traces remain unconfirmed.
