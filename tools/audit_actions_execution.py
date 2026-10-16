#!/usr/bin/env python3
"""Classify GitHub Actions job execution evidence from saved REST responses.

Distinguishes an unallocated runner from a test failure; it does not
assert why GitHub did not allocate a runner.
"""
import argparse
import json
from pathlib import Path


def audit(jobs_payload, timing_payload=None):
    jobs = jobs_payload.get('jobs')
    if not isinstance(jobs, list) or not jobs:
        raise ValueError('Expected nonempty GitHub Actions jobs array')
    observations = []
    for job in jobs:
        if not isinstance(job, dict):
            raise ValueError('Malformed job record')
        job_id = job.get('id')
        if not isinstance(job_id, int) or isinstance(job_id, bool):
            raise ValueError('Job ID missing or invalid')
        steps = job.get('steps')
        if steps is not None and not isinstance(steps, list):
            raise ValueError('Invalid job steps')
        runner = job.get('runner_id')
        if runner is not None and (not isinstance(runner, int) or isinstance(runner, bool)):
            raise ValueError('Invalid runner ID')
        observations.append({
            'job_id': job_id,
            'name': str(job.get('name', '')),
            'conclusion': job.get('conclusion'),
            'runner_allocated': isinstance(runner, int) and runner > 0,
            'recorded_steps': len(steps or []),
        })
    no_runner_no_steps = all(not j['runner_allocated'] and j['recorded_steps'] == 0
                             for j in observations)
    any_steps = any(j['recorded_steps'] > 0 for j in observations)
    billable_ms = None
    if timing_payload is not None:
        billable = timing_payload.get('billable', {})
        if not isinstance(billable, dict):
            raise ValueError('Invalid timing payload')
        amounts = [group['total_ms'] for group in billable.values()
                   if isinstance(group, dict) and 'total_ms' in group]
        if any(type(n) is not int or n < 0 for n in amounts):
            raise ValueError('Invalid billable duration')
        billable_ms = sum(amounts) if amounts else None
    if no_runner_no_steps:
        category = 'no_runner_and_no_steps_observed'
    elif any_steps:
        category = 'some_steps_observed'
    else:
        category = 'insufficient_execution_information'
    return {
        'schema': 1,
        'classification': category,
        'job_count': len(observations),
        'jobs': observations,
        'billable_runner_ms': billable_ms,
        'test_failures_proven': False,
        'root_cause_proven': False,
        'guidance': ('Inspect the GitHub Actions run banner and account Actions/billing '
                     'eligibility before changing tests; no test execution is established.')
                    if no_runner_no_steps else
                    ('Inspect the recorded steps and job logs for specific failures.'),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('jobs_json', type=Path)
    parser.add_argument('--timing', type=Path)
    args = parser.parse_args()
    jobs = json.loads(args.jobs_json.read_text(encoding='utf8'))
    timing = json.loads(args.timing.read_text(encoding='utf8')) if args.timing else None
    print(json.dumps(audit(jobs, timing), indent=2))


if __name__ == '__main__':
    main()
