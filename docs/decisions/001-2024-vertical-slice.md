# Decision 001: Freeze the 2024 EBA vertical slice

- Status: Accepted
- Decision date: 2026-08-14
- Project version: 2024 vertical-slice v1

## Context

Portfolio Project 1 must demonstrate data engineering with Databricks, Python,
SQL, automated tests, explicit data-quality controls, deterministic reruns, and
thin notebooks. The first release must remain small enough to finish and explain
within the available eight project hours per week.

## Business question

> Which individual European banks should a consulting team prioritise for
> deeper review because they are peer outliers on capital strength, asset
> quality, profitability, or deterioration between September 2023 and June
> 2024, and which credit-exposure or NACE sectors explain their
> non-performing-exposure profile?

The result is a transparent screening dataset. It is not a regulatory risk
rating, probability-of-default model, stress test, or investment recommendation.

## Decision

Version 1 uses only the 2024 EBA EU-wide Transparency Exercise and these five
official artifacts:

| Artifact | SHA-256 |
|---|---|
| `tr_cre.csv` | `4175521FBBE352E7E8973C37F419F16A8FE3B6FC5974EA7955BAF67AADF2060E` |
| `tr_oth.csv` | `E2C6D0B9DDB887F96FF0AF7A51BBBD7D8E7B467A9E9E1110514660AECBCAA584` |
| `TR_Metadata.xlsx` | `ECD488DFFA578DABB89594CCC00409303B14446E7B0EAEBAB2BDAA7A65E7BC21` |
| `SDD.xlsx` | `9F350211B2D54AE7A273526A0402AB43965822FF527DC2E587149C98BD13D6A9` |
| `CSV_and_Tools_guide_Transparency_2024.pdf` | `95302EF9E86DB6354CEFC44B027977A894FADC2C4A17F71EF47D40232FE1F5F2` |

Official release page:
<https://www.eba.europa.eu/risk-and-data-analysis/risk-analysis/eu-wide-transparency-exercise/2024-eu-wide-transparency-exercise>

The two fact domains implemented in v1 are:

- `tr_oth.csv`: capital, leverage, assets, profit and loss, risk-weighted
  assets, liabilities, and key metrics.
- `tr_cre.csv`: credit risk, non-performing exposures, forborne exposures,
  NACE breakdowns, and collateral.

## KPI contract

| KPI | 2024 source rule |
|---|---|
| Fully loaded CET1 ratio | `tr_oth`, item `2420146` |
| Fully loaded leverage ratio | `tr_oth`, item `2420906` |
| Total assets | `tr_oth`, item `2421010` |
| Profit YTD | `tr_oth`, item `2420335` |
| Annualised profit-to-assets proxy | `(profit_ytd * 4 / n_quarters) / total_assets` |
| Gross loan NPE ratio | `tr_cre`, item `2420603`: `Perf_Status=2 / Perf_Status=0` |
| NPE coverage ratio | `tr_cre`, item `2420613`, `Perf_Status=2` divided by item `2420603`, `Perf_Status=2` |
| NPE exposure drivers | Item `2420605`, `Perf_Status=2`; additive top-level codes `101`, `102`, `201`, `202`, `301`, `401` |
| NACE NPE drivers | Item `2421301`, `Perf_Status=2`; sectors `1..19`, total code `0` |

Ratios are stored as decimals. Zero denominators return null with an explicit
missing reason. Profit is a cumulative flow and is annualised with
`n_quarters`; balance-sheet amounts are never annualised. The profitability
measure is labelled a proxy, not official return on assets.

Latest-period review candidates are identified by transparent adverse flags.
Every flag exposes its underlying value, percentile, eligibility, and reason.
No weighted or opaque risk score is permitted.

## Source contracts and fixed 2024 controls

- `tr_cre.csv`: 606,922 data rows and 17 columns.
- `tr_oth.csv`: 99,324 data rows and 16 columns.
- Reference periods: `202309`, `202312`, `202403`, `202406`.
- Published population: 123 individual banks plus the `All other banks`
  aggregate identified by `NSA='OT'`.
- June 2024 expected coverage: 123 individual banks for capital/leverage, 111
  for profit/assets/NPE ratio, and 109 with defined NPE coverage.
- Common September-to-June cohort: 117 banks for capital and 105 for
  profit/NPE metrics.
- Exposure and NACE reconciliation tolerance: EUR 0.01 million.
- EBA dimension code `0` is a valid total/no-breakdown member, not null.
- Fact-to-dictionary joins use source domain, sheet/template, and item. Joining
  only on item is prohibited because it can multiply credit-risk rows.

## Architecture boundary

- Python performs local acquisition, hashing, manifests, workbook parsing, and
  reusable validation.
- Raw files remain outside Git and are uploaded manually to a Databricks Unity
  Catalog Volume after hash verification.
- Databricks uses source-preserving Bronze Delta tables, typed/conformed Silver
  tables, SQL Gold marts, and a parameterised five-task Workflow.
- SQL owns KPI calculation, percentiles, driver marts, and reconciliation.
- Notebooks are thin entry points and explanations only.

## Explicit non-goals for v1

- Ingesting the 2023 or 2025 releases before the 2024 v1 acceptance gates pass.
- Market-risk or sovereign-exposure CSVs.
- ECB macroeconomic or interest-rate enrichment.
- Pillar 3 Data Hub or XBRL processing.
- AWS, Airflow, Docker, dbt, Kafka, a frontend, or streaming.
- Machine learning, causal claims, stress scenarios, or investment advice.
- An opaque weighted bank score or production regulatory-reporting platform.

## Consequences

This decision prioritises a complete, reproducible, explainable project over a
larger technology demonstration. Expansion to 2023 and 2025 is allowed only
after the 2024 vertical slice passes its end-to-end, idempotency, testing,
reconciliation, documentation, and interview-readiness gates.
