# Stage 65 — GitHub Actions runner allocation blocker

CI run [#322](https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/38971225203)
for commit `aa10d3162174f11f98df97a7d6f3d6474db61174` finished
with `conclusion=failure`, but its **two job records each show**
`runner_id=0` and `steps=[]`. The run timing endpoint reports
`billable.UBUNTU.total_ms=0`. Both jobs lasted approximately three
seconds, and no job logs or uploaded artifacts were available.

**Interpretation:** those records do not demonstrate that a Python,
Lua or C++ test ran or failed. The immediate blocker appears to be
job execution/runner allocation, **not an identified failing test**.
The API data does not establish *why* runners were unavailable. Check
the run's GitHub Actions banner and account-level Actions/billing
eligibility, spending limits or account restrictions before inferring
a specific reason.

## Reproducible offline audit

Save the raw JSON from the GitHub REST endpoints
`GET /repos/stanmasked/vice-project-doom-switch-hd/actions/runs/38971225203/jobs`
and `GET /repos/stanmasked/vice-project-doom-switch-hd/actions/runs/38971225203/timing`
to private local files, then run:

```sh
python3 tools/audit_actions_execution.py private/run322_jobs.json --timing private/run322_timing.json
python3 -m unittest discover -s tests -p 'test_actions_execution_audit.py' -v
```

The utility distinguishes unallocated-runner/no-step observations from
jobs that actually recorded steps. It **never** claims a specific
billing, policy or code failure without supporting evidence.

The five synthetic tests were executed locally with Python 3.13.5 and
passed, along with Python syntax compilation. That verification covers
only the new tool and its own tests, **not the entire repository**.
The GitHub Actions workflow remains red until a runner executes it.

When runners become available, run the existing complete Python/Lua/C++
checks, inspect any actual failing steps, and only then report full CI
health. This issue is separate from obtaining authentic first-level
FCEUX gameplay traces; no game ROMs are committed.
