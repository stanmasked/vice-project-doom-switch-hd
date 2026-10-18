# Stage 71 — isolated Python regression discovery

Targeted stage70 execution should run **exactly seven READ-provenance
tests**. Before stage71, the module directly imported four fixture
classes which subclass `unittest.TestCase`:

```python
from test_joint_cpu_context_validation import JointContextTests
```

Python `unittest` module discovery enumerates any exported
`TestCase` subclasses, **including classes imported from other
modules**. Therefore targeting one stage70 file unexpectedly
rediscovered fixture test suites, obscuring the requested seven-test
signal and causing unnecessary re-execution.

Stage71 uses module aliases instead, e.g.:

```python
import test_joint_cpu_context_validation as joint53_fixtures
# The class is only accessed as joint53_fixtures.JointContextTests
```

The new `tests/test_stage71_discovery_isolation.py` ensures
`loadTestsFromModule(stage70_module).countTestCases() == 7` and
checks that only the intended stage70 test class is directly exposed.

## Commands for a complete local checkout

```sh
python3 -m unittest discover -s tests -p 'test_stage70_read_provenance_pipeline.py' -v
python3 -m unittest discover -s tests -p 'test_stage71_discovery_isolation.py' -v
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

The isolated CI group records these runs to `stage69-71.log` if a
runner executes it. Its final success criteria include this group.

## Verification caveat

A standalone Python 3.13 test-loader reproduction in the assistant's
local environment confirmed that directly exposed imported TestCase
classes are rediscovered, whereas classes accessed through module
aliases are not. The exact seven stage70 regressions were **not**
executed against a complete private repository checkout here.
GitHub Actions remains blocked before allocating runners (recent
runs show `runner_id=0` with `steps=[]`). These statuses do not
establish a failure in the Python tools themselves.

No original ROM/game resources, game geometry or Switch binary were
created or added in this stage.
