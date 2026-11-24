# Comet Docker run and Spark UI walkthrough

## Verified run

Executed on November 23, 2026, America/New_York (November 24 UTC), from
Codex after Docker access was enabled for the session.

| Setting | Value |
| --- | --- |
| Docker context / server | `desktop-linux` / 29.9.3 |
| Host engine | Docker Desktop Linux, x86_64, WSL2 |
| Engine capacity | 16 CPUs, 13.51 GiB RAM |
| Container limits | 2 CPUs, 4 GiB RAM |
| Base image | `python:3.11-bookworm` |
| Java | OpenJDK 17 |
| PySpark | 3.5.9 |
| Comet | 1.2.0, Spark 3.5 / Scala 2.12 JAR |
| Spark local threads / shuffle partitions | 2 / 2 |
| Spark off-heap allocation | 512 MiB |
| Input / output | 90 stock rows / 30 date-and-item groups |
| Warm-up / measured rounds | One warm-up per engine / five rounds per engine |

Observed console output:

```text
Spark: 90 input rows, 30 stock groups, median 2.881s over 5 warm runs
Comet: 90 input rows, 30 stock groups, median 1.800s over 5 warm runs
Stock totals match. Spark/Comet median time ratio: 1.60x.
Comet Spark UI available on port 4040 for 3600s.
```

The comparison checks group keys, counts, and stock totals, with a tolerance
for floating-point closing values. These timings include reading the data,
registering the view, planning the SQL, executing it, and collecting results
into Python. Container setup and the warm-up are excluded. The 1.60x ratio
describes this small compatibility fixture only. Larger-workload performance
and Sail were not verified by this run.

## Reproduce

From the outer workspace directory:

```powershell
docker --context desktop-linux info
& '.\Exercise Files\run_comet_docker.ps1' -Rounds 5 -UiSeconds 3600
```

From the Git repository (`Exercise Files`), use:

```powershell
.\run_comet_docker.ps1 -Rounds 5 -UiSeconds 3600
```

The wrapper installs Java and PySpark and downloads the Comet JAR inside the
container. Network access is required. It mounts the exercise directory
read-only at `/work`, binds UI port 4040 to host loopback only, and removes the
container on exit. It does not write to MariaDB. The image tag and operating
system packages are not pinned by digest/version, so future runs may have
different underlying dependencies.

`-Rounds` defaults to 1 and accepts 1–1000. `-UiSeconds` defaults to 0 (UI
disabled) and accepts 0–86400. The Python equivalent is `--ui-seconds`, which
requires Comet mode when positive. Keep the runner running while inspecting
the UI. The one-hour countdown starts after the successful comparison.

## Read the Spark UI

1. Wait for `Stock totals match.` and open <http://localhost:4040/SQL/>.
2. Select a completed `collect at /work/benchmark_stock_sail.py` execution.
3. Read the graph from the bottom toward the top:

| Operator | Work performed |
| --- | --- |
| `CometNativeScan parquet` | Reads and decodes the Parquet data using Comet. |
| `CometProject` | Selects the columns used by the aggregation. |
| `CometHashAggregate` (partial) | Computes per-partition counts and sums. |
| `CometExchange` / `CometNativeShuffle` | Redistributes partial totals by date and item. |
| `AQEShuffleRead` | Reads shuffle partitions after Spark adaptive planning. |
| `CometHashAggregate` (final) | Combines partial totals into 30 output groups. |
| `CometColumnarToRow` | Converts columnar results for the row-based consumer. |

The run's last measured execution was ID 23:
<http://localhost:4040/SQL/execution/?id=23>. Execution IDs and application
IDs can change on rerun, so use the SQL index to find the current query.

The UI response for that query showed 30 final output rows, 30 shuffle records
written, and zero aggregate spills. Its SQL execution duration was 144 ms.
That is a narrower measurement than the 1.800-second median Python loop and
must not be substituted for it in the benchmark comparison.

The baseline Spark session is stopped before Comet starts; its UI history is
not retained here. After the inspection duration, Comet stops and port 4040
becomes unavailable. No persistent Spark event log or History Server is
configured by this runner.

## What was changed

- `benchmark_stock_sail.py`: added `--ui-seconds`, enabled Spark UI on port
  4040 when requested, retained the Comet session during inspection, and
  ensured cleanup with `finally`.
- `run_comet_docker.ps1`: added `-UiSeconds`, conditional loopback port
  publishing, and unbuffered Python output.
- Documentation: setup, limitations, run evidence, and UI interpretation
  are collected under `docs`.

## Access and troubleshooting evidence

Earlier attempts from a restricted local Codex session failed reading
`C:\Users\cheny\.docker\config.json` and the `desktop-linux` context metadata.
Running locally alone did not resolve the restriction. After the session's
permission profile changed, `docker --context desktop-linux info` returned a
Server section and the benchmark ran successfully. Check access from the
same session that will launch the benchmark.

Automatic approval review rejected Google Chrome control with
`Computer Use was not approved to use Google Chrome`. The browser was not
opened automatically. The Spark REST API and SQL page response were checked
directly, confirming a running Spark 3.5.9 application, completed SQL
executions, and Comet operators with metrics. This was endpoint verification,
not visual browser verification.

If localhost requests stall because of proxy configuration, this read-only
check explicitly bypasses proxies:

```powershell
curl.exe -sS --max-time 10 --noproxy '*' http://127.0.0.1:4040/api/v1/applications
```

For an occupied port, inspect `docker --context desktop-linux ps` and the
existing listener before starting another UI run. To stop a run early, use
`docker --context desktop-linux stop <container-id>` with the ID verified
from `docker ps`; avoid stopping unrelated containers.
