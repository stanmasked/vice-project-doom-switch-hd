#!/usr/bin/env python3
"""Run synthetic-only research Python regressions from a complete local checkout.

Explicitly rejects missing test patterns and zero-test success, which
`unittest discover` otherwise reports with exit status 0.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

GROUPS = {
    'stage38-54': ('test_dispatch_execution.py', 'test_prg_read_mapping.py',
                   'test_prg_capture_completeness.py', 'test_prg_read_ranges.py',
                   'test_joint_cpu_context_validation.py'),
    'stage55-60': ('test_6502_read_address.py',
                   'test_6502_prg_instruction_verification.py',
                   'test_verified_prg_read_correlation.py',
                   'test_prg_identity_gate.py', 'test_stage60_integration.py'),
    'stage70-71': ('test_stage70_read_provenance_pipeline.py',
                   'test_stage71_discovery_isolation.py'),
    'research': ('test_*.py',),
}
COUNT = re.compile(r'^Ran ([0-9]+) tests? in [0-9.eE+-]+s\r?


def run_group(root, group, *, timeout=180, python=sys.executable):
    root = Path(root).resolve()
    tests = root / 'tests'
    if group not in GROUPS:
        raise ValueError('Unknown group')
    if not tests.is_dir():
        raise ValueError('Missing tests directory; use a complete checkout')
    results = []
    for pattern in GROUPS[group]:
        matches = list(tests.glob(pattern))
        if not matches or (group != 'research' and len(matches) != 1):
            raise ValueError('Missing or ambiguous test pattern: ' + pattern)
        command = [str(python), '-m', 'unittest', 'discover',
                   '-s', 'tests', '-p', pattern, '-v']
        try:
            completed = subprocess.run(command, cwd=root, capture_output=True,
                                       text=True, timeout=timeout, check=False)
            output = completed.stdout + '\n' + completed.stderr
            # unittest's summary is emitted on stderr. Ignore plausible-looking
            # banners printed to stdout by individual test cases.
            count_matches = COUNT.findall(completed.stderr)
            count = int(count_matches[0]) if len(count_matches) == 1 else None
            passed = completed.returncode == 0 and count is not None and count > 0
            error = None if passed else output[-4000:]
            results.append({'pattern': pattern, 'tests_run': count,
                            'passed': passed, 'exit_code': completed.returncode,
                            'error_tail': error})
        except subprocess.TimeoutExpired:
            results.append({'pattern': pattern, 'tests_run': None,
                            'passed': False, 'exit_code': None,
                            'error_tail': 'Test command timed out'})
    return {'schema': 1, 'group': group, 'passed': all(r['passed'] for r in results),
            'results': results, 'live_fceux_verified': False,
            'real_level_data_verified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--group', choices=sorted(GROUPS), default='stage70-71')
    parser.add_argument('--timeout', type=int, default=180)
    args = parser.parse_args()
    if not 1 <= args.timeout <= 3600:
        parser.error('timeout must be between 1 and 3600 seconds')
    try:
        report = run_group(args.root, args.group, timeout=args.timeout)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
, re.MULTILINE)


def run_group(root, group, *, timeout=180, python=sys.executable):
    root = Path(root).resolve()
    tests = root / 'tests'
    if group not in GROUPS:
        raise ValueError('Unknown group')
    if not tests.is_dir():
        raise ValueError('Missing tests directory; use a complete checkout')
    results = []
    for pattern in GROUPS[group]:
        matches = list(tests.glob(pattern))
        if not matches or (group != 'research' and len(matches) != 1):
            raise ValueError('Missing or ambiguous test pattern: ' + pattern)
        command = [str(python), '-m', 'unittest', 'discover',
                   '-s', 'tests', '-p', pattern, '-v']
        try:
            completed = subprocess.run(command, cwd=root, capture_output=True,
                                       text=True, timeout=timeout, check=False)
            output = completed.stdout + '\n' + completed.stderr
            # unittest's summary is emitted on stderr. Ignore plausible-looking
            # banners printed to stdout by individual test cases.
            count_matches = COUNT.findall(completed.stderr)
            count = int(count_matches[0]) if len(count_matches) == 1 else None
            passed = completed.returncode == 0 and count is not None and count > 0
            error = None if passed else output[-4000:]
            results.append({'pattern': pattern, 'tests_run': count,
                            'passed': passed, 'exit_code': completed.returncode,
                            'error_tail': error})
        except subprocess.TimeoutExpired:
            results.append({'pattern': pattern, 'tests_run': None,
                            'passed': False, 'exit_code': None,
                            'error_tail': 'Test command timed out'})
    return {'schema': 1, 'group': group, 'passed': all(r['passed'] for r in results),
            'results': results, 'live_fceux_verified': False,
            'real_level_data_verified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--group', choices=sorted(GROUPS), default='stage70-71')
    parser.add_argument('--timeout', type=int, default=180)
    args = parser.parse_args()
    if not 1 <= args.timeout <= 3600:
        parser.error('timeout must be between 1 and 3600 seconds')
    try:
        report = run_group(args.root, args.group, timeout=args.timeout)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
