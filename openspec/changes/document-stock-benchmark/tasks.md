## 1. Documentation and automated checks

- [x] 1.1 Document setup, execution modes, troubleshooting, and available results.
- [x] 1.2 Add tests for parity, plan checks, timing rounds, cleanup, and CLI validation.

## 2. Live acceptance

- [ ] 2.1 Confirm Spark and Sail return matching totals on the bundled fixture.
- [x] 2.2 Confirm Comet operators and matching totals in Docker.
- [ ] 2.3 Confirm the Comet SQL UI is accessible during its configured window and then closes.
- [ ] 2.4 Generate a scaled fixture and confirm its row count and group count.

Comet evidence is recorded in `docs/comet-run.md`. For 2.3, HTTP access and
completed SQL plans were verified during the one-hour window; automatic
shutdown at its end has not been verified.
