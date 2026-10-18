# Stage 72 — local Python regression runner

The repository's GitHub Actions PR checks have recently failed **before
any test steps execute**: jobs show `runner_id=0`, `steps=[]`, and zero
billable runner time. That is an infrastructure blocker, not an observed
Python test failure.

To make testing reproducible independently of GitHub Actions, stage72
adds `tools/run_research_regressions.py`.

From a complete local checkout of the private research branch:

```sh
python3 tools/run_research_regressions.py --group stage70-71
python3 tools/run_research_regressions.py --group research
```

The first group runs the stage70 READ-provenance tests and the stage71
unittest-discovery isolation tests separately. The second group runs
all `tests/test_*.py` using Python's standard `unittest` runner.
Both commands return **nonzero** if a test fails, times out, no tests
run, or a required test file is absent. A simple successful process
with `Ran 0 tests` is *not* treated as successful validation.

Each command prints a JSON summary listing the test pattern, discovered
test count, return code and (only on failure) a bounded diagnostic tail.
Flags `live_fceux_verified=false` and
`real_level_data_verified=false` prevent accidental overclaiming.
An explicit `--root` may point to another complete checkout.

The stage72 self-check is:

```sh
python3 -m unittest discover -s tests -p 'test_research_regression_runner.py' -v
```

## Verified results

The runner and its five synthetic tests were executed **locally** with
Python 3.13.5: **5/5 passed**. Syntax compilation of both files also
passed. Their Git blob hashes match the uploaded files.

A negative local test on an intentionally incomplete fixture returned
exit code 2, correctly rejecting the missing stage70 file.

**The real stage70-71 group and the complete Python test suite are not
yet locally confirmed**, because the current environment has only
selected historical Lua copies and does not have a complete authenticated
clone of the private repository. Cloning via unauthenticated git failed
due to unavailable GitHub networking. Do not report this self-check as
proof of full integration.

The CI workflow contains an explicit stage72 runner self-test step,
which will execute only if GitHub allocates a runner. No original ROM
data or Nintendo Switch build is included.
