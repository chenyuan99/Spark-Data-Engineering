# Apache Spark Essential Training: Big Data Engineering

Exercise files for the LinkedIn Learning course **Apache Spark Essential Training: Big Data Engineering**.

---

## Project Structure

```
.
├── PySpark Playground.ipynb          # Interactive PySpark notebook
├── .env                              # Environment variable config
├── .venv311/                         # Python 3.11 virtual environment
└── Exercise Files/
    └── spark-data-engg/              # Java/Spark Maven project
        ├── pom.xml
        ├── raw_data/                 # Partitioned Parquet stock data
        │   └── STOCK_DATE=.../
        │       └── WAREHOUSE_ID=.../
        └── src/main/java/com/learning/sparkdataengg/
            ├── setup/                # Prerequisites setup
            ├── chapter3/             # Batch processing – Stock data
            ├── chapter4/             # Structured Streaming – Website analytics
            └── chapter6/             # Advanced Streaming – Scorecards
```

---

## Environment Setup (Windows)

### Tools

| Tool | Path |
|---|---|
| Java 17 (OpenJDK) | `C:\devhome\tools\Java\jdk-17.0.2` |
| Spark 3.5.8 | `C:\devhome\tools\spark-3.5.8-bin-hadoop3` |
| Hadoop winutils 3.3.6 | `C:\devhome\tools\hadoop-3.3.6` |

### Environment Variables (`.env`)

```
JAVA_HOME=C:\devhome\tools\Java\jdk-17.0.2
SPARK_HOME=C:\devhome\tools\spark-3.5.8-bin-hadoop3
HADOOP_HOME=C:\devhome\tools\hadoop-3.3.6
PYSPARK_PYTHON=<project>\.venv311\Scripts\python.exe
PYSPARK_DRIVER_PYTHON=<project>\.venv311\Scripts\python.exe
```

> `HADOOP_HOME` is required on Windows so the Python worker can find `winutils.exe`.
> Without it, PySpark tasks fail with `java.net.SocketException: Connection reset`.

### Python Virtual Environment

```bash
# Activate
.venv311\Scripts\activate

# Key packages
pyspark==3.5.8
python-dotenv
jupyter
```

---

## PySpark Playground Notebook

Open `PySpark Playground.ipynb` in Jupyter and run cells top-to-bottom.

The main cell creates a local Spark session:

```python
import os
from pyspark.sql import SparkSession
from dotenv import load_dotenv

load_dotenv()

os.environ["JAVA_HOME"]   = r"C:\devhome\tools\Java\jdk-17.0.2"
os.environ["SPARK_HOME"]  = r"C:\devhome\tools\spark-3.5.8-bin-hadoop3"
os.environ["HADOOP_HOME"] = r"C:\devhome\tools\hadoop-3.3.6"

spark = (
    SparkSession.builder
    .master("local[*]")
    .appName("MySparkApp")
    .config("spark.pyspark.python", os.environ["PYSPARK_PYTHON"])
    .config("spark.pyspark.driver.python", os.environ["PYSPARK_DRIVER_PYTHON"])
    .getOrCreate()
)
```

**Spark UI** is available at `http://localhost:4040` while a session is active.

---

## Java Exercises (spark-data-engg)

Built with **Maven**, targeting **Java 11**, **Spark 3.1.1**, **Scala 2.12**.

### Build

```bash
cd "Exercise Files/spark-data-engg"
mvn clean package
```

---

### Chapter 3 – Batch Processing: Global Stock Aggregation

Reads daily warehouse stock data from partitioned Parquet files, aggregates across warehouses, and writes results to MariaDB.

| Class | Description |
|---|---|
| `RawStockDataGenerator` | Generates synthetic stock Parquet data into `raw_data/` |
| `DailyStockUploaderJob` | Uploads a single day's stock data |
| `StockAggregatorJob` | Aggregates all warehouses → writes to `global_stock.item_stock` in MariaDB |
| `GlobalStockDBBrowser` | Queries and displays the aggregated MariaDB table |

**Raw data layout** (Hive-style partitioning):
```
raw_data/
  STOCK_DATE=2021-06-01/
    WAREHOUSE_ID=London/
    WAREHOUSE_ID=LosAngeles/
    WAREHOUSE_ID=NewYork/
```

**Aggregation SQL:**
```sql
SELECT STOCK_DATE, ITEM_NAME,
       COUNT(*)                                    AS TOTAL_REC,
       SUM(OPENING_STOCK)                          AS OPENING_STOCK,
       SUM(RECEIPTS)                               AS RECEIPTS,
       SUM(ISSUES)                                 AS ISSUES,
       SUM(OPENING_STOCK + RECEIPTS - ISSUES)      AS CLOSING_STOCK,
       SUM((OPENING_STOCK + RECEIPTS - ISSUES) * UNIT_VALUE) AS CLOSING_VALUE
FROM GLOBAL_STOCK
GROUP BY STOCK_DATE, ITEM_NAME
```

**Prerequisites:** MariaDB running on `localhost:3306`, database `global_stock`, user `spark`/`spark`.

---

### Chapter 4 – Structured Streaming: Real-Time Website Analytics

Consumes a live stream of website visit events from Kafka and fans out to three sinks simultaneously.

| Class | Description |
|---|---|
| `WebsiteVisitsDataGenerator` | Publishes synthetic visit events to Kafka topic `spark.streaming.website.visits` |
| `StreamingWebsiteAnalytics` | Main streaming job (see pipeline below) |
| `MariaDBWriter` / `MariaDBManager` | Writes 5-second windowed summaries to MariaDB |
| `RedisWriter` | Updates country-level duration counters in Redis |
| `ShoppingCartTopicBrowser` | Reads from the outgoing `spark.streaming.carts.abandoned` Kafka topic |
| `CountryStatsBrowser` | Displays Redis country stats |
| `VisitStatsDBBrowser` | Displays MariaDB windowed stats |

**Streaming pipeline:**
```
Kafka (website.visits)
    │
    ├─► stdout (raw record logging)
    ├─► Kafka topic: spark.streaming.carts.abandoned  (filter: lastAction == 'ShoppingCart')
    ├─► Redis       (country → total duration scorecard)
    └─► MariaDB     (5-second tumbling window, grouped by lastAction)
```

**Visit event schema:**
```json
{ "visitDate": "string", "country": "string", "lastAction": "string", "duration": int }
```

**Prerequisites:** Kafka on `localhost:9092`, MariaDB, Redis.

---

### Chapter 6 – Advanced Streaming: Long-Action Scorecard

Consumes the `spark.exercise.lastaction.long` Kafka topic (produced by Chapter 4's extractor) and maintains a Redis scorecard for sessions longer than 15 seconds.

| Class | Description |
|---|---|
| `LongLastActionExtractorJob` | Filters visits with `duration > 15s`, publishes to `spark.exercise.lastaction.long` |
| `ScoreCardForLastActionJob` | Reads from that topic, updates Redis scorecard |
| `RedisWriter` | Redis sink |
| `LastActionStatsBrowser` | Displays the Redis scorecard |

---

## Infrastructure Dependencies

| Service | Default | Used by |
|---|---|---|
| MariaDB | `localhost:3306` | Chapter 3, Chapter 4 |
| Apache Kafka | `localhost:9092` | Chapter 4, Chapter 6 |
| Redis | `localhost:6379` | Chapter 4, Chapter 6 |

A Docker Compose file is provided at `Exercise Files/spark-docker.yml` to spin up all dependencies:

```bash
docker compose -f "Exercise Files/spark-docker.yml" up -d
```
