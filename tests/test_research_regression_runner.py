"""Pure synthetic regression runner tests; no original game materials."""
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from run_research_regressions import run_group


class ResearchRunnerTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.root = Path(self.work.name)
        (self.root / 'tests').mkdir()

    def write(self, name, text):
        (self.root / 'tests' / name).write_text(text, encoding='utf8')

    def test_missing_file_is_hard_failure(self):
        with self.assertRaisesRegex(ValueError, 'Missing or ambiguous'):
            run_group(self.root, 'stage70-71')

    def test_zero_tests_cannot_pass(self):
        self.write('test_empty.py', '# no tests here\n')
        result = run_group(self.root, 'research')
        self.assertFalse(result['passed'])
        self.assertEqual(result['results'][0]['tests_run'], 0)

    def test_successful_fixture_reports_exact_counts(self):
        source = ('import unittest\n'
                  'class T(unittest.TestCase):\n'
                  '  def test_ok(self): self.assertTrue(True)\n')
        self.write('test_stage70_read_provenance_pipeline.py', source)
        self.write('test_stage71_discovery_isolation.py', source)
        result = run_group(self.root, 'stage70-71')
        self.assertTrue(result['passed'])
        self.assertEqual([r['tests_run'] for r in result['results']], [1, 1])
        self.assertFalse(result['live_fceux_verified'])

    def test_failed_fixture_cannot_pass(self):
        self.write('test_broken.py', 'import unittest\n'
                   'class T(unittest.TestCase):\n'
                   '  def test_fail(self): self.fail("expected")\n')
        result = run_group(self.root, 'research')
        self.assertFalse(result['passed'])
        self.assertEqual(result['results'][0]['tests_run'], 1)
        self.assertIn('expected', result['results'][0]['error_tail'])

    def test_missing_checkout_is_failure(self):
        with self.assertRaisesRegex(ValueError, 'Missing tests directory'):
            run_group(self.root / 'nonexistent', 'research')


if __name__ == '__main__':
    unittest.main()
