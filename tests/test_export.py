import csv
import importlib.util
import io
import unittest

from pyhomerun import BattingLine, PitchingLine, to_csv, to_dataframe, to_dict, to_numpy, to_records

_HAS_NUMPY = importlib.util.find_spec("numpy") is not None
_HAS_PANDAS = importlib.util.find_spec("pandas") is not None


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


class TestToRecords(unittest.TestCase):
    def test_empty_returns_empty_list(self):
        self.assertEqual(to_records([]), [])

    def test_labeled_mapping_adds_name_key(self):
        line = BattingLine(at_bats=550, hits=180, home_runs=53)
        records = to_records({"Aaron Judge": line})
        self.assertEqual(records[0]["name"], "Aaron Judge")
        self.assertEqual(records[0]["home_runs"], 53)
        self.assertEqual(records[0]["avg"], line.avg)

    def test_plain_iterable_has_no_name_key(self):
        records = to_records([BattingLine(at_bats=10, hits=3)])
        self.assertNotIn("name", records[0])

    def test_values_are_native_python_types(self):
        records = to_records([BattingLine(at_bats=10, hits=3)])
        self.assertIsInstance(records[0]["at_bats"], int)
        self.assertIsInstance(records[0]["avg"], float)

    def test_mixed_line_types_raises(self):
        with self.assertRaises(TypeError):
            to_records([BattingLine(), PitchingLine()])

    def test_passes_through_dict_rows_unlabeled(self):
        rows = [{"launch_speed": 105.1, "launch_angle": 22.0}]
        self.assertEqual(to_records(rows), rows)

    def test_passes_through_dict_rows_labeled(self):
        rows = {"pitch 1": {"launch_speed": 105.1}}
        records = to_records(rows)
        self.assertEqual(records[0], {"name": "pitch 1", "launch_speed": 105.1})

    def test_non_mapping_row_raises(self):
        with self.assertRaises(TypeError):
            to_records([object()])


class TestToDict(unittest.TestCase):
    def test_default_is_columnar(self):
        result = to_dict([BattingLine(at_bats=10, hits=3), BattingLine(at_bats=20, hits=6)])
        self.assertEqual(result["hits"], [3, 6])
        self.assertEqual(result["at_bats"], [10, 20])

    def test_records_true_is_list_of_dicts(self):
        result = to_dict([BattingLine(at_bats=10, hits=3)], records=True)
        self.assertEqual(result, to_records([BattingLine(at_bats=10, hits=3)]))

    def test_empty_returns_empty_dict(self):
        self.assertEqual(to_dict([]), {})


@unittest.skipUnless(_HAS_NUMPY, "numpy not installed")
class TestToNumpy(unittest.TestCase):
    def test_numeric_columns_are_float(self):
        import numpy as np

        arr = to_numpy([BattingLine(at_bats=550, hits=180, home_runs=53)])
        self.assertEqual(arr["home_runs"][0], 53.0)
        self.assertEqual(arr.dtype["home_runs"], np.dtype("f8"))

    def test_string_column_is_object_dtype(self):
        arr = to_numpy({"Aaron Judge": BattingLine(at_bats=550, hits=180)})
        self.assertEqual(arr["name"][0], "Aaron Judge")

    def test_missing_numeric_value_becomes_nan(self):
        import numpy as np

        arr = to_numpy([{"launch_speed": 105.1}, {"launch_speed": None}])
        self.assertTrue(np.isnan(arr["launch_speed"][1]))

    def test_empty_returns_empty_array(self):
        arr = to_numpy([])
        self.assertEqual(len(arr), 0)


@unittest.skipIf(_HAS_NUMPY, "verifies the ImportError path when numpy is absent")
class TestToNumpyWithoutNumpy(unittest.TestCase):
    def test_raises_helpful_import_error(self):
        with self.assertRaises(ImportError):
            to_numpy([BattingLine(at_bats=10, hits=3)])


@unittest.skipUnless(_HAS_PANDAS, "pandas not installed")
class TestToDataframe(unittest.TestCase):
    def test_builds_dataframe_from_lines(self):
        df = to_dataframe({"Aaron Judge": BattingLine(at_bats=550, hits=180, home_runs=53)})
        self.assertEqual(len(df), 1)
        self.assertEqual(df["home_runs"].iloc[0], 53)
        self.assertEqual(df["name"].iloc[0], "Aaron Judge")

    def test_builds_dataframe_from_dict_rows(self):
        df = to_dataframe([{"launch_speed": 105.1}, {"launch_speed": 98.2}])
        self.assertEqual(len(df), 2)


if __name__ == "__main__":
    unittest.main()
