# Benchmark verification

| Run | Evidence |
| --- | --- |
| Spark 3.5.8 on Windows | 90 input rows, 30 stock groups, 0.497 s for one warm round in the user's PowerShell. |
| Sail | The Spark Connect server started. The reported comparison attempt failed importing PyArrow. A later shutdown log did not include a totals verdict. |
| Comet in Docker | Verified November 23, 2026 (New York): Spark 3.5.9 median 2.881 s, Comet 1.2.0 median 1.800 s across five warm runs; 90 rows, 30 groups, matching totals. Native operators and completed executions verified through the Spark UI HTTP response and REST API. Browser automation was denied. See the [run record](comet-run.md). |
| Scaled workload | Generation and cross-engine timings are unverified. |

A single warm run on 90 rows is a smoke test. Compare medians across multiple rounds on the same larger dataset before drawing performance conclusions.

## Test coverage

Run from the repository root with the benchmark's Python environment:

```powershell
python -m unittest discover -s tests -v
```

| OpenSpec requirement | Automated coverage | Live acceptance |
| --- | --- | --- |
| Compare stock aggregations | Timing round count, input-row count, grouping normalization, and session cleanup | Run Spark and Sail on the fixture and confirm 90 rows, 30 groups, and matching totals. |
| Reject mismatches | Missing groups, different counts, different values, and floating-point tolerance | Confirm the successful run prints `Stock totals match.` |
| Require Comet execution | Spark-only plans fail, and a Comet scan plan passes | Run the Docker pilot and inspect the executed plan. |
| Protect fixture data and validate options | Invalid rounds, threads, and UI options, plus refusal to overwrite the fixture | Generate two copies into a fresh directory, then run Spark on it and confirm 180 rows and 30 groups. |
| Inspect Comet in the Spark UI | Docker command arguments checked by inspecting the runner | Run with `-UiSeconds 60`, verify the SQL tab on localhost, then verify the runner exits. |

The [OpenSpec change](../openspec/changes/document-stock-benchmark/proposal.md) tracks these acceptance checks. With the OpenSpec CLI available, run `openspec validate document-stock-benchmark --strict` from the repository root.
