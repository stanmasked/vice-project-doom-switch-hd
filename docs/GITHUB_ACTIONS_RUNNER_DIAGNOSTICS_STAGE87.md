# GitHub Actions blocked before runner allocation — diagnosis

## Reproducible evidence, 2026-10-17

The private repository `stanmasked/vice-project-doom-switch-hd`
uses standard `runs-on: ubuntu-latest` on both jobs in
`.github/workflows/ci.yml`. Workflow syntax is recognized by
GitHub and runs are created, but the jobs fail **before any steps**.

- Native Core CI #775:
  https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/39020267809
  — both jobs `runner_id=0`, `steps=0`.
- Minimal `GitHub Runner Smoke Test` #2:
  https://github.com/stanmasked/vice-project-doom-switch-hd/actions/runs/39020634971
  — the job `runner_id=0`, `steps=0`.
- An explicit GitHub API retry of the smoke run was **accepted**.
  Attempt #2 again finished before runner allocation, with
  `runner_id=0` and `steps=0`.

The smoke workflow needs no checkout, package installation,
project code or secrets. Consequently, a failure of the same type
there is strong evidence of **GitHub account/repository Actions
policy, usage/billing restriction, or GitHub runner service**, not a
failing C++, Python or Lua test. It does NOT prove a specific billing
problem: the connected GitHub API does not provide the user's
personal billing information or Actions permissions policy.

## Owner action checklist

1. Go to repository
   https://github.com/stanmasked/vice-project-doom-switch-hd/settings/actions
   and verify **Actions permissions** are enabled; allow GitHub-authored
   actions and external actions used by this repository.
2. Visit https://github.com/settings/billing — open
   **Usage** and **Budgets and alerts**. Review Actions included
   minutes, budget stops, billing lock or other account warning.
   A free plan can have included minutes; do not pay for a higher
   plan unless actual account restrictions require it. If billing is
   blocked, contact GitHub Support and share the smoke run URL.
3. Open the smoke test run URL above and choose **Re-run all jobs**.
   This is safe; the smoke job only prints diagnostic information.
4. If the smoke run allocates a runner and executes both steps, open
   https://github.com/stanmasked/vice-project-doom-switch-hd/actions,
   select **Native Core CI**, then **Re-run failed jobs** on the most
   recent run of PR #3.
5. If even the smoke job still has `runner_id=0`, go to
   https://support.github.com/contact and report the URLs and the
   before-runner failure. GitHub account-level flags cannot be
   modified through our current connector.

The smoke workflow's automatic trigger is restricted to edits to
`.github/workflows/runner-smoke.yml` on the research branch, to avoid
creating extra red checks for every normal development commit.
Existing failed smoke jobs can still be manually rerun.

Documentation: GitHub's repository Actions settings, account budgets
and Actions billing:
- https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository
- https://docs.github.com/en/billing/how-tos/set-up-budgets
- https://docs.github.com/en/billing/concepts/product-billing/github-actions

## Development and testing boundary

Changes to the game's runtime, ROM processing, graphics, mapper, build
flags or testing fixtures **cannot** independently solve this
pre-execution runner-allocation failure. Until GitHub assigns a
runner, do not report CI as passing or failing tests as though they
ran. Local tests may continue, with exact scope stated separately.
