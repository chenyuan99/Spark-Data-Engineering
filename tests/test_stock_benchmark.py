import contextlib
import io
import sys
import unittest
from datetime import date
from unittest.mock import MagicMock, patch

from pyspark.sql import Row

import benchmark_stock_sail as benchmark


class StockBenchmarkTests(unittest.TestCase):
    def test_result_comparison(self):
        key = ("2021-06-01", "item")
        expected = {key: (3, 100.0)}
        benchmark.compare(expected, {key: (3, 100.00000001)})
        for actual, error in [
            ({}, "Stock groups differ"),
            ({key: (4, 100.0)}, "Stock totals differ"),
            ({key: (3, 101.0)}, "Stock totals differ"),
        ]:
            with self.subTest(actual=actual), self.assertRaisesRegex(RuntimeError, error):
                benchmark.compare(expected, actual)

    def test_warmup_excluded_and_results_normalized(self):
        spark = MagicMock()
        spark.sql.return_value.collect.return_value = [
            Row(STOCK_DATE=date(2021, 6, 1), ITEM_NAME="item", TOTAL_REC=90)
        ]
        output = io.StringIO()
        with patch.object(benchmark, "perf_counter", side_effect=[0, 1, 2, 5]):
            with contextlib.redirect_stdout(output):
                groups, duration = benchmark.run_query(spark, "Spark", 2, "fixture path")
        self.assertEqual(spark.sql.return_value.collect.call_count, 3)
        self.assertEqual(duration, 2)
        self.assertEqual(groups, {("2021-06-01", "item"): (90,)})
        self.assertIn("90 input rows, 1 stock groups", output.getvalue())
        spark.read.parquet.assert_called_with("fixture path")
        spark.stop.assert_called_once()

    def test_comet_plan_gate_and_cleanup(self):
        for plan in ("FileScan parquet", "CometNativeScan parquet"):
            with self.subTest(plan=plan), contextlib.redirect_stdout(io.StringIO()):
                spark = MagicMock()
                query = spark.sql.return_value
                query.collect.return_value = [
                    Row(STOCK_DATE="2021-06-01", ITEM_NAME="item", TOTAL_REC=1)
                ]
                query._jdf.queryExecution().executedPlan().toString.return_value = plan
                if plan.startswith("Comet"):
                    benchmark.run_query(spark, "Comet", 1, "fixture", keep_alive=True)
                    spark.stop.assert_not_called()
                else:
                    with self.assertRaisesRegex(RuntimeError, "no Comet"):
                        benchmark.run_query(spark, "Comet", 1, "fixture")
                    spark.stop.assert_called_once()

    def test_invalid_options_fail_before_starting_spark(self):
        for args, error in [
            (["--rounds", "0"], "rounds must be positive"),
            (["--threads", "0"], "threads must be positive"),
            (["--ui-seconds", "60"], "ui-seconds requires"),
            (["--generate", "2"], "a new --data path"),
        ]:
            stderr = io.StringIO()
            with self.subTest(args=args), patch.object(sys, "argv", ["benchmark", *args]):
                with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as exit:
                    benchmark.main()
                self.assertEqual(exit.exception.code, 2)
                self.assertIn(error, stderr.getvalue())
