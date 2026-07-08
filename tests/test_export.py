import csv
import io
import unittest

from pyhomerun import BattingLine, PitchingLine, to_csv


class TestToCsv(unittest.TestCase):
    def test_empty_returns_empty_string(self):
        self.assertEqual(to_csv([]), "")

    def test_plain_iterable_has_no_name_column(self):
        line = BattingLine(at_bats=100, hits=30)
        rows = list(csv.reader(io.StringIO(to_csv([line]))))
        self.assertNotIn("name", rows[0])

    def test_labeled_mapping_adds_name_column(self):
        line = BattingLine(at_bats=550, hits=180, home_runs=53, walks=110)
        text = to_csv({"Aaron Judge": line})
        rows = list(csv.DictReader(io.StringIO(text)))
        self.assertEqual(rows[0]["name"], "Aaron Judge")
        self.assertEqual(rows[0]["home_runs"], "53")
        self.assertEqual(float(rows[0]["avg"]), line.avg)

    def test_pitching_line_columns(self):
        line = PitchingLine(outs=540, hits=160, earned_runs=65, strikeouts=190)
        text = to_csv([line])
        header = text.splitlines()[0].split(",")
        self.assertIn("era", header)
        self.assertIn("fip", header)
        self.assertNotIn("avg", header)

    def test_mixed_types_raises(self):
        with self.assertRaises(TypeError):
            to_csv([BattingLine(), PitchingLine()])

    def test_write_to_file_returns_none(self):
        line = BattingLine(at_bats=10, hits=3)
        buffer = io.StringIO()
        result = to_csv([line], file=buffer)
        self.assertIsNone(result)
        self.assertIn("at_bats", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
