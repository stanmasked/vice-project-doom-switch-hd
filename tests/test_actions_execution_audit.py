"""Local synthetic checks for GitHub Actions runner-vs-test classification."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from audit_actions_execution import audit


class ExecutionAuditTests(unittest.TestCase):
    def test_two_failed_jobs_without_runner_are_not_test_failures(self):
        jobs = {'jobs': [
            {'id': 100, 'name': 'python', 'conclusion': 'failure',
             'runner_id': 0, 'steps': []},
            {'id': 101, 'name': 'native', 'conclusion': 'failure',
             'runner_id': 0, 'steps': []},
        ]}
        timing = {'billable': {'UBUNTU': {'total_ms': 0}}}
        result = audit(jobs, timing)
        self.assertEqual(result['classification'], 'no_runner_and_no_steps_observed')
        self.assertEqual(result['billable_runner_ms'], 0)
        self.assertFalse(result['test_failures_proven'])
        self.assertFalse(result['root_cause_proven'])

    def test_executed_job_does_not_get_false_runner_classification(self):
        result = audit({'jobs': [{'id': 102, 'conclusion': 'failure',
                                  'runner_id': 56, 'steps': [{'name': 'Tests'}]}]})
        self.assertEqual(result['classification'], 'some_steps_observed')
        self.assertEqual(result['jobs'][0]['recorded_steps'], 1)

    def test_empty_job_collection_rejected(self):
        with self.assertRaises(ValueError):
            audit({'jobs': []})

    def test_malformed_timing_rejected(self):
        with self.assertRaises(ValueError):
            audit({'jobs': [{'id': 1}]}, {'billable': {'UBUNTU': {'total_ms': -1}}})

    def test_missing_runner_id_is_not_reported_as_allocated(self):
        result = audit({'jobs': [{'id': 102, 'steps': []}]})
        self.assertEqual(result['classification'], 'no_runner_and_no_steps_observed')


if __name__ == '__main__':
    unittest.main()
