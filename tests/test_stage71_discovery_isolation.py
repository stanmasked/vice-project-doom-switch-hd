"""Stage71: keep targeted unittest discovery isolated from imported fixture cases.

A direct 'from test_foo import FixtureTestCase' makes unittest's module
discovery run the imported class's tests again. Use module imports instead.
"""
import unittest
import test_stage70_read_provenance_pipeline as provenance_tests


class Stage71DiscoveryTests(unittest.TestCase):
    def test_targeted_stage70_suite_contains_exactly_seven_cases(self):
        suite = unittest.defaultTestLoader.loadTestsFromModule(provenance_tests)
        self.assertEqual(suite.countTestCases(), 7)

    def test_stage70_module_exposes_only_its_own_testcase(self):
        exposed = [
            cls for cls in vars(provenance_tests).values()
            if isinstance(cls, type)
            and issubclass(cls, unittest.TestCase)
            and cls is not unittest.TestCase
        ]
        self.assertEqual(exposed, [provenance_tests.ReadProvenanceEndToEndTests])


if __name__ == '__main__':
    unittest.main()
