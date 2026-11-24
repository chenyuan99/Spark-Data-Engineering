## Context

The benchmark reuses the Chapter 3 aggregation and compares engines against plain Spark.

## Goals / Non-Goals

- Define reproducible checks for the fixture, scaled workload, and Comet UI.
- Preserve existing engine modes and avoid additional test dependencies.

## Decisions

- Separate engine-independent tests from live acceptance, which needs Java, Spark, and either Sail or a Linux Comet runtime.
- Treat a matching result and a visible Comet operator as distinct acceptance criteria.

## Risks / Trade-offs

- A mocked plan verifies the fallback guard. Live execution is required to establish which operators Comet actually runs.
- One warm round on the fixture verifies the execution path and is sensitive to timing noise.
