"""Run the Chapter 3 stock aggregation on local Spark and Sail."""
import argparse
import os
from math import isclose
from pathlib import Path
from statistics import median
from time import perf_counter

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


DATA = Path(__file__).resolve().parent / "spark-data-engg" / "raw_data"
# Mirrors StockAggregatorJob.java in Chapter 3.
QUERY = """
SELECT STOCK_DATE, ITEM_NAME,
       COUNT(*) AS TOTAL_REC,
       SUM(OPENING_STOCK) AS OPENING_STOCK,
       SUM(RECEIPTS) AS RECEIPTS,
       SUM(ISSUES) AS ISSUES,
       SUM(OPENING_STOCK + RECEIPTS - ISSUES) AS CLOSING_STOCK,
       SUM((OPENING_STOCK + RECEIPTS - ISSUES) * UNIT_VALUE) AS CLOSING_VALUE
FROM GLOBAL_STOCK
GROUP BY STOCK_DATE, ITEM_NAME
"""


def run_query(spark, label, rounds, data):
    def collect():
        spark.read.parquet(data.as_uri()).createOrReplaceTempView("GLOBAL_STOCK")
        return spark.sql(QUERY).collect()

    try:
        rows = collect()  # Warm up the engine and the filesystem cache.
        if not rows:
            raise RuntimeError(f"{label} returned no stock groups")

        timings = []
        for _ in range(rounds):
            start = perf_counter()
            rows = collect()
            timings.append(perf_counter() - start)

        duration = median(timings)
        print(
            f"{label}: {sum(row.TOTAL_REC for row in rows):,} input rows, "
            f"{len(rows):,} stock groups, median {duration:.3f}s "
            f"over {rounds} warm runs",
            flush=True,
        )
        # Normalize the date key in case the engines infer different partition types.
        groups = {(str(row.STOCK_DATE), row.ITEM_NAME): tuple(row[2:]) for row in rows}
        if len(groups) != len(rows):
            raise RuntimeError(f"{label} returned duplicate stock groups")
        return groups, duration
    finally:
        spark.stop()


def compare(spark_groups, sail_groups):
    if spark_groups.keys() != sail_groups.keys():
        raise RuntimeError(
            f"Stock groups differ: {len(spark_groups.keys() - sail_groups.keys())} "
            f"Spark-only, {len(sail_groups.keys() - spark_groups.keys())} Sail-only"
        )

    for key, expected in spark_groups.items():
        actual = sail_groups[key]
        # Floating-point reduction order can vary across engines.
        values_match = expected[-1] == actual[-1] or (
            isinstance(expected[-1], float)
            and isinstance(actual[-1], float)
            and isclose(expected[-1], actual[-1], rel_tol=1e-9, abs_tol=1e-8)
        )
        if expected[:-1] != actual[:-1] or not values_match:
            raise RuntimeError(f"Stock totals differ for {key}: {expected} vs {actual}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--spark-only", action="store_true")
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--generate", type=int, metavar="COPIES",
                        help="Write scaled stock fixtures to a new --data path and exit")
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()
    if args.rounds < 1:
        parser.error("--rounds must be positive")
    if args.threads < 1:
        parser.error("--threads must be positive")
    data = args.data.resolve()
    if args.generate is not None:
        if args.generate < 1 or data.exists():
            parser.error("--generate requires positive copies and a new --data path")
    elif not data.is_dir():
        parser.error(f"Parquet directory does not exist: {data}")

    spark = (
        SparkSession.builder.master(f"local[{args.threads}]")
        .appName("Stock aggregation pilot")
        .config("spark.sql.shuffle.partitions", str(args.threads))
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    if args.generate is not None:
        try:
            stocks = spark.read.parquet(DATA.as_uri())
            copies = spark.range(args.generate).withColumnRenamed("id", "replica")
            scaled = stocks.crossJoin(copies).withColumn(
                "OPENING_STOCK",
                (F.col("OPENING_STOCK") + (F.xxhash64("replica", "ITEM_NAME") % 31 + 31))
                .cast(stocks.schema["OPENING_STOCK"].dataType),
            ).drop("replica")
            scaled.write.partitionBy("STOCK_DATE", "WAREHOUSE_ID").parquet(data.as_uri())
        finally:
            spark.stop()
        return

    spark_groups, spark_time = run_query(spark, "Spark", args.rounds, data)
    if args.spark_only:
        return

    os.environ["SAIL_EXECUTION__DEFAULT_PARALLELISM"] = str(args.threads)
    from pysail.spark import SparkConnectServer

    server = SparkConnectServer()
    server.start()
    try:
        _, port = server.listening_address
        spark = SparkSession.builder.remote(f"sc://127.0.0.1:{port}").getOrCreate()
        sail_groups, sail_time = run_query(spark, "Sail", args.rounds, data)
        compare(spark_groups, sail_groups)
        print(f"Stock totals match. Spark/Sail median time ratio: {spark_time / sail_time:.2f}x.")
    finally:
        server.stop()


if __name__ == "__main__":
    main()
