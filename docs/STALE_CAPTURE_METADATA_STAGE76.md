# Stage 76 — prevent old FCEUX metadata from certifying new traces

## Failure mode

FCEUX collectors reused fixed names for private TSV and metadata files.
Previously, on starting a **second** capture, they truncated the TSV
but left the previous session's metadata (`complete=yes`) untouched
until `emu.registerexit`. If the new run crashed, its new partial TSV
could be paired with stale successful metadata from an earlier run.

Event-count and mapper checks reduced the likelihood of acceptance,
but could not prove the two files belonged to the same session.

## Fix in all six collectors

Production collectors for stages **38, 41, 45, 49, 52, and 53** now
replace the previous metadata with a single fail-closed marker before
opening their corresponding TSV:

```text
capture_in_progress=yes
```

An unclosed or interrupted capture therefore does not retain a stale
`complete=yes` marker. A normal `emu.registerexit` closes the TSV
and writes its full metadata as before. Every existing strict Python
validator rejects the pending marker because required provenance,
counts or schema fields are missing.

The stage53 ROM/profile preflight intentionally occurs **before**
metadata invalidation: if the user selects an incompatible ROM and
the preflight rejects it, a previous completed capture remains
unchanged.

This does **not** guarantee atomicity, durability or authenticity:
an unexpected failure during writing final metadata can leave a
partial file; validators must reject it. For reliable capture, run
one collector per target output filename, do not reuse the directory
concurrently, and keep original resources private.

## Tests

`tests/test_fceux_capture_session_invalidation.lua` sets up old
`complete=yes` metadata and stale TSV data for all six collectors,
starts each with synthetic callbacks and confirms that:
- Old metadata becomes exactly the pending marker before completion.
- The TSV no longer contains the old session.
- A normal exit replaces the marker with the completed metadata.
- A stage53 preflight failure leaves an earlier session's files intact.

`tests/test_stage76_capture_session_integrity.py` has six cases
against synthetic Python fixtures for stages38/41/45/49/53. Pending
metadata is rejected even when paired with a formerly valid TSV.
It also rejects truncated final metadata that happens to contain
`complete=yes`.

The Lua suite is wired into the `code-and-tests` CI job. The
Python cases are picked up by the existing `test_*.py` suite and
by `--group research` in `tools/run_research_regressions.py`.

## Verification boundary

Source inspection confirms the pending marker is opened and closed
**before** each production TSV is opened. The existing local
historical stage74 subset's five Lua smoke checks passed again,
but the full new stage76 suite was **not executed on a complete
up-to-date private repository checkout**. The results from older
Lua files must not be reported as a pass of this new patch.
Recent CI failures were before runner allocation and executed no tests.

No original game resources, verified map geometry or Switch NRO
were created in this stage.
