# Stage 73 — fix masked Python regression failures in CI

Reviewing `.github/workflows/ci.yml` uncovered a **real false-green
failure mode** in all three grouped Python regression jobs. Previously,
each ran multiple commands within a Bash brace group:

```bash
set -o pipefail
{
  python -m unittest discover -s tests -p 'test_first.py' -v
  python -m unittest discover -s tests -p 'test_second.py' -v
} 2>&1 | tee grouped.log
```

`pipefail` only propagates the **brace group's final status**, not the
status of each earlier command. If the first test failed and the second
passed, the step appeared successful. The Bash reproducer
`{ false; true; } | cat` exited with code **0**.

## Corrected CI

The three groups now invoke one shared fail-closed runner:

```bash
set -o pipefail
python tools/run_research_regressions.py --group stage38-54 2>&1 | tee stage38-54.log
python tools/run_research_regressions.py --group stage55-60 2>&1 | tee stage55-60.log
python tools/run_research_regressions.py --group stage70-71 2>&1 | tee stage69-71.log
```

These are **separate CI steps**, not a single shell block. Each runner
executes every required test pattern, accumulates all results into a
JSON report and exits nonzero if **any** pattern failed, timed out,
ran zero tests or was missing. The existing `continue-on-error: true`
steps preserve diagnostics, while the final explicit outcome check
still fails the job after artifact upload.

The runner's unittest-count parser now uses the canonical summary on
**stderr**, anchored to the entire line, rather than accepting a
plausible `Ran 999 tests` string printed on stdout by a test.

## Verification performed

- Reproduced the original Bash masking bug: `false; true` in a brace
  group returned **0**; explicit cumulative failure returned **1**.
- Ran the runner's **eight** synthetic Python unit tests locally with
  Python 3.13.5: **8 passed**, including three new regressions for
  earlier failure + later success, completing all five test patterns
  even after a failure, and forged test-count output.
- `python -m compileall -q tools tests` succeeded for the updated
  runner and self-tests in the locally available stage72 slice.
- Compared the current Git blob IDs with the locally tested exact
  files: runner `da02a1e3d37e5510b1b3cbd611d117a72d581f4c`,
  tests `339b197dd91f08c9da3b883320fb9d384473fa51`.
- Verified in GitHub that all three CI groups now call the shared
  runner and that the final outcome gate still checks all three.

The **full repository** Python/Lua/C++ tests are **not** claimed as
passing. The latest checked GitHub Actions run still had zero allocated
runners and zero executed steps. No original game assets, verified
first-level geometry or Nintendo Switch build were produced.
