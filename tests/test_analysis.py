import contextlib
import csv
import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import analyze


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "data").mkdir()
        (self.root / "analysis.sql").write_text(
            (Path(analyze.__file__).parent / "analysis.sql").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        self.rows = [
            "2011-01-01,8,0,2,3,5",
            "2011-01-02,8,0,1,2,3",
            "2011-01-03,8,1,4,6,10",
            "2011-02-01,17,1,2,10,12",
        ]

    def run_with_rows(self, rows):
        payload = "dteday,hr,workingday,casual,registered,cnt\n" + "\n".join(rows) + "\n"
        with zipfile.ZipFile(self.root / "data" / "source.zip", "w") as z:
            z.writestr("hour.csv", payload)
        with patch.object(analyze, "ROOT", self.root), contextlib.redirect_stdout(io.StringIO()):
            analyze.main()

    def test_known_aggregates(self):
        self.run_with_rows(self.rows)
        with (self.root / "outputs" / "hourly_demand.csv").open(encoding="utf-8", newline="") as f:
            hourly = list(csv.DictReader(f))
        self.assertEqual([(x["workingday"], x["hour"], x["observed_hours"], float(x["avg_rentals_per_observed_hour"])) for x in hourly],
                         [("0", "8", "2", 4.0), ("1", "8", "1", 10.0), ("1", "17", "1", 12.0)])
        with (self.root / "outputs" / "monthly_demand.csv").open(encoding="utf-8", newline="") as f:
            monthly = list(csv.DictReader(f))
        self.assertEqual([int(x["total_rentals"]) for x in monthly], [18, 12])

    def test_rejects_inconsistent_counts_and_duplicate_hours(self):
        for rows in (self.rows + [self.rows[0]], ["2011-01-01,8,0,2,3,6"]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.run_with_rows(rows)

    def test_rejects_empty_data(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            self.run_with_rows([])


if __name__ == "__main__":
    unittest.main()
