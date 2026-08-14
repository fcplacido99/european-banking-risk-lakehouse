# European Banking Risk & Performance Lakehouse

> **Project status:** repository foundation in progress. The data pipeline and
> analytical findings are not implemented yet.

This portfolio project will build a reproducible Databricks lakehouse from the
2024 European Banking Authority (EBA) EU-wide Transparency Exercise. It is
designed to demonstrate data engineering through deterministic ingestion,
governed Bronze/Silver/Gold datasets, automated tests, data-quality controls,
and traceable SQL findings.

## Business question

Which individual European banks should a consulting team prioritise for deeper
review because they are peer outliers on capital strength, asset quality,
profitability, or deterioration between September 2023 and June 2024, and
which credit-exposure or NACE sectors explain their non-performing-exposure
profile?

This is a transparent screening exercise. It is not a regulatory risk rating,
stress test, prediction, or investment recommendation.

## Locked v1 scope

- 2024 EBA Transparency Exercise only.
- Two fact domains: `tr_cre.csv` and `tr_oth.csv`.
- Three supporting artifacts: `TR_Metadata.xlsx`, `SDD.xlsx`, and the official
  CSV/tools guide.
- Databricks, Python, SQL, Delta tables, pytest, and explicit data-quality
  checks.
- Raw EBA files remain outside Git.

The accepted scope and KPI contract are recorded in
[`docs/decisions/001-2024-vertical-slice.md`](docs/decisions/001-2024-vertical-slice.md).

## Planned architecture

```text
Official EBA files
        |
Local verified acquisition + manifest
        |
Manual upload to Databricks Volume
        |
Bronze source-preserving Delta tables
        |
Silver typed facts and conformed references
        |
Gold KPI, review-candidate, and driver marts
        |
SQL-driven consulting findings
```

## Repository layout

```text
config/       Versioned source and pipeline configuration
docs/         Decisions, contracts, architecture, limitations, and plan
notebooks/    Thin Databricks entry points and findings presentation
resources/    Small public documentation assets and sample outputs
sql/          Silver, Gold, and quality SQL
src/          Importable Python package source
tests/        Small fixtures and local pytest suite
```

Implementation evidence will be added incrementally. Until an acceptance gate
is supported by committed tests or run evidence, it remains unfinished.
