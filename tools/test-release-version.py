"""Verify date labels, daily revisions, and ordering across dates and legacy versions."""
import json
from pathlib import Path
import tempfile
import unittest
from release_version import read_release


class DateReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def version(self, day='2026-10-21', revision=1):
        (self.root / 'release-version.json').write_text(json.dumps({'schema_version': 1, 'date': day, 'revision': revision}))
        return read_release(self.root)

    def test_public_label_and_legacy_upgrade_order(self):
        sequence, label = self.version()
        self.assertEqual(label, '10.21.26.1')
        self.assertEqual(sequence, 20261021001)
        self.assertGreater(sequence, 302)
        self.assertGreater(sequence, 25)

    def test_daily_counter_and_next_day(self):
        self.assertLess(self.version()[0], self.version(revision=2)[0])
        self.assertLess(self.version(revision=999)[0], self.version('2026-10-22')[0])
        self.assertLess(self.version('2026-12-31', 999)[0], self.version('2027-01-01')[0])

    def test_invalid_dates_and_revisions(self):
        for day, revision in [('2026-02-30', 1), ('20261021', 1), ('2026-10-21', 0), ('2026-10-21', True), ('2026-10-21', 1000)]:
            with self.subTest(day=day, revision=revision):
                with self.assertRaises(ValueError):
                    self.version(day, revision)

    def test_missing_config_keeps_legacy_packaging_available(self):
        self.assertIsNone(read_release(self.root))


if __name__ == '__main__':
    unittest.main(verbosity=2)
