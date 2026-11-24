# Stock aggregation benchmark

The pilot reuses the Chapter 3 stock aggregation SQL and the 12 bundled
Parquet files in `spark-data-engg/raw_data`. It reads the stock data and
collects query results in memory, independent of the Java job and MariaDB.

## Spark and Sail

From the exercise repository root, use a separate Python 3.11 environment and set
`JAVA_HOME` to a complete Java 17 installation for the Spark baseline. On Windows,
use the [Windows Hadoop setup](../README.md#environment-setup-windows).

```powershell
python -m pip install "pyspark[connect]==3.5.8" "pysail==0.7.3" "pyarrow==16.1.0"
python benchmark_stock_sail.py
```

The PyArrow pin supports the project's Python 3.11 and NumPy 1.26 setup.

The script starts local Spark and then a local Sail server, reads the bundled
partitioned Parquet data, and runs the Chapter 3 aggregation in each engine.
It compares row counts and stock totals for every date and item, and prints
median warm timings for scan, aggregation, and result collection. Use
`--spark-only` to run the baseline with PySpark alone. The script never writes
to MariaDB.

The bundled dataset is a compatibility fixture. To generate a larger synthetic
dataset outside the repository and benchmark it separately, run:

```powershell
$stockData = Join-Path $env:TEMP "stock-benchmark-5000"
python benchmark_stock_sail.py --generate 5000 --data $stockData
python benchmark_stock_sail.py --data $stockData --threads 2 --rounds 7
```

The generator writes 5,000 rows per source row, varies opening inventory
deterministically, and preserves the date and warehouse partitions. It requires
a new output directory. The benchmark excludes generation time.

`--threads` sets Spark's local worker threads and shuffle partition count and
Sail's execution parallelism. For a controlled run, give the benchmark
environment a fixed CPU and memory budget, such as a Linux container with
`--cpus=2 --memory=4g`, and record the actual input row count and Parquet size.
The timings include the Sail Spark Connect round trip. For engine-only
comparisons, use Spark Connect for both engines.

## Spark with Comet

Use Linux or WSL2 with Java 17. The published Comet JAR includes Linux native
libraries. Download the **Spark 3.5 / Scala 2.12** JAR from the
[Comet 1.2 installation guide](https://datafusion.apache.org/comet/user-guide/1.2/installation.html)
and use a separate Python environment with Spark 3.5.9:

```bash
python -m pip install "pyspark==3.5.9"
python benchmark_stock_sail.py \
  --comet-jar "$HOME/comet-spark-spark3.5_2.12-1.2.0.jar" --rounds 1
```

Run the command from the exercise repository root. Set the JAR path to the
actual download location. If `SPARK_HOME` points to a different Spark version,
unset it to use the distribution bundled with PySpark.

This mode compares stock Spark and Spark with Comet on the same Parquet files
and verifies their stock totals. It prints Comet's executed plan and fails if
the plan shows no Comet scan, hash aggregate, or shuffle. Use `--data` to run
both engines on the same scaled dataset.

On Windows with Docker Desktop's Linux engine, run five warm rounds and keep
the Comet session available for an hour:

```powershell
.\run_comet_docker.ps1 -Rounds 5 -UiSeconds 3600
```

Open http://localhost:4040/SQL/ after the totals comparison completes. Select
a completed query to inspect the Comet scan, aggregate, and shuffle operators
and their metrics. The live UI contains the Comet session; the preceding Spark
baseline is stopped before Comet starts. The container is limited to two CPUs
and 4 GiB of memory, and the UI port is bound only to localhost. It exits after
the requested UI duration. Omit `-UiSeconds` for a normal run without the UI.

## Troubleshooting

| Symptom | Check or fix |
| --- | --- |
| Python cannot open the benchmark script | From the parent project folder, run `python ".\Exercise Files\benchmark_stock_sail.py"`. From the exercise repository root, use `python benchmark_stock_sail.py`. |
| `JAVA_GATEWAY_EXITED` or `'Failed' is not recognized` | Run `& "$env:JAVA_HOME\bin\java.exe" -version`. If it reports `Failed setting boot class path`, point `JAVA_HOME` at a complete JDK 17. Clear a stale `SPARK_HOME` with `Remove-Item Env:SPARK_HOME -ErrorAction SilentlyContinue` to use PySpark's bundled Spark. |
| Hadoop reports a missing path containing `Exercise%20Files` | Use the current benchmark, which passes a native filesystem path to Spark and a file URI to Sail. |
| PyArrow is missing or requires NumPy 2 | Install the Spark Connect extras and PyArrow pin above in the active Python environment. Run `python -c "import pyarrow, numpy; print(pyarrow.__version__, numpy.__version__)"` to verify the import. |
| Windows cleanup prints process termination errors | Read the benchmark output above the cleanup lines. Check for a traceback and the comparison verdict. |
| Docker reports permission denied on `dockerDesktopLinuxEngine` | Run `docker --context desktop-linux info` in the same session as the benchmark. If regular PowerShell shows a Linux server, run the wrapper there. A managed Codex session needs a profile that permits access to the Docker engine. |
| UI is unavailable on port 4040 | Supply a positive `-UiSeconds`, check if another service occupies port 4040, and open the UI before the inspection window ends. Sail's Spark Connect port serves the client connection. Inspect Sail with `spark.sql(QUERY).explain()` while its session is active. |

See [verification and test coverage](benchmark-verification.md) for the evidence needed to confirm each engine.
