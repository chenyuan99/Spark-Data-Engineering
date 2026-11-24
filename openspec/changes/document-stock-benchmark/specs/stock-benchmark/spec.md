# Stock benchmark spec delta

## Purpose

Verify that each benchmark engine runs the Chapter 3 aggregation against shared data and produces comparable stock totals.

## ADDED Requirements

### Requirement: Compare stock aggregations

The benchmark SHALL execute the Chapter 3 aggregation against the same input for both selected engines and report median elapsed time after a warm-up round.

#### Scenario: Benchmark the bundled fixture

- **WHEN** a comparison is run on the bundled fixture
- **THEN** each engine reports 90 input rows and 30 stock groups
- **AND** the warm-up round is excluded from the reported median

### Requirement: Reject mismatches

The benchmark SHALL reject differing group keys or stock totals, with a tolerance for floating-point closing values.

#### Scenario: An engine changes a group or total

- **WHEN** the date-and-item keys or totals differ beyond the accepted tolerance
- **THEN** the comparison fails before reporting matching totals

### Requirement: Require Comet execution

The Comet comparison SHALL verify the executed plan contains a Comet scan, hash aggregate, or shuffle operator.

#### Scenario: Comet falls back entirely to Spark

- **WHEN** the executed plan has no qualifying Comet operator
- **THEN** the Comet comparison fails

### Requirement: Protect fixture data and validate options

The benchmark SHALL reject invalid rounds, thread counts, UI combinations, and unsafe generator output paths before starting Spark.

#### Scenario: Generate into an existing directory

- **WHEN** a generator run targets an existing directory
- **THEN** the command rejects the path without overwriting it

#### Scenario: Scale the stock fixture

- **WHEN** a generator run creates two copies in a fresh directory
- **THEN** it writes 180 rows across the original date and warehouse partitions
- **AND** the stock aggregation still produces 30 groups

### Requirement: Inspect Comet in the Spark UI

The Docker runner SHALL bind the optional Spark UI to localhost and retain the Comet session for the requested inspection window after verification.

#### Scenario: Request a live Comet UI

- **WHEN** a Docker run passes verification and has a positive UI duration
- **THEN** the Comet queries are available at localhost port 4040 for that duration
- **AND** the runner exits after the inspection window
