# Stage 70 — end-to-end synthetic READ provenance regression

After the stage69 correction, FCEUX `memory.registerread` callback's
third parameter must not be treated as the byte loaded from memory.
Stage70 introduces `tests/test_stage70_read_provenance_pipeline.py`
to compare the **actual validators and analysis functions** across
multiple trace formats. It tests separate invented sessions:

- **Stage41/43**: pointer RAM READ has an `unknown` callback value,
  while four separately sampled RAM bytes remain labelled as snapshots.
- **Stage45/46/47**: mapper SELECT/DATA writes remain byte-valued;
  PRG READs are address-only; the reported physical offset and
  noncausal read runs stay available.
- **Stage49/50**: joint CPU/MMC3 trace is accepted only when READ byte
  values are `unknown`, and forged `AB` bytes are rejected.
- **Stage53/54/56**: CPU registers and event order remain usable for
  address hypotheses, while byte provenance and causality remain
  explicitly unproven.
- **Legacy data**: missing provenance metadata and fabricated READ
  values must both be rejected rather than silently upgraded.

No ROM, PRG dumps, user game captures, screenshots, or original assets
are included.

## Run the targeted checks

```sh
python3 -m unittest discover -s tests -p 'test_stage70_read_provenance_pipeline.py' -v
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

GitHub's `python-regressions` job now runs the stage70 group separately
and, **if a runner is allocated**, uploads `stage69-70.log` alongside
the earlier traces. Its final status includes the new group.

## Verification status

Five earlier stage53/ROM-preflight synthetic Lua scripts passed in the
local environment with `luatex --luaonly`. The five stage65 GitHub
runner-diagnostic Python unit tests also passed locally.

The **new stage70 Python tests have not yet been executed against a
local checkout of the complete private repository**. They are committed
for execution in CI or in a properly provisioned clone. Passing
GitHub Actions is likewise not established; recent failures have
occurred with `runner_id=0`, no executed steps and zero billable
runner time, so they do not identify a failing unit test.

Live FCEUX hook behaviour, a verified same-session first-level
trace, stage geometry and a Nintendo Switch binary remain outstanding.
