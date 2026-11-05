"""The release gate must reject missing, failed or skipped suites."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

SPEC = importlib.util.spec_from_file_location('qualification', Path(__file__).resolve().parents[1] / 'ci/qualify_local.py')
QUALIFICATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(QUALIFICATION)

class QualificationTests(unittest.TestCase):
    def test_complete_report_and_growing_case_counts(self):
        self.check_report(None)

    def test_incomplete_or_failed_reports_are_rejected(self):
        for mode in ('missing', 'duplicate', 'failure', 'error', 'skipped', 'notrun', 'nestedskip'):
            with self.subTest(mode=mode):
                self.check_report(mode)

    def check_report(self, mode):
        names = ('transport', 'bounded-hashing', 'mcp-integration', 'public-operation-tools', 'client-adapters', 'qualification-report')
        root = ET.Element('testsuite')
        for name in names:
            case = ET.SubElement(root, 'testcase', name=name, status='run')
            ET.SubElement(case, 'system-out').text = 'Ran 50 tests\nOK'
        if mode == 'missing': root.remove(root[3])
        elif mode == 'duplicate': ET.SubElement(root, 'testcase', name='transport', status='run')
        elif mode == 'notrun': root[0].set('status', 'notrun')
        elif mode == 'nestedskip': root[0][0].text = 'OK (skipped=1)'
        elif mode: ET.SubElement(root[0], mode)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'report.xml'
            ET.ElementTree(root).write(path)
            if mode:
                with self.assertRaises(RuntimeError): QUALIFICATION.validate_test_report(path)
            else: self.assertEqual(QUALIFICATION.validate_test_report(path), sorted(names))

if __name__ == '__main__': unittest.main()
