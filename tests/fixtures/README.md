# Test fixtures

These fixtures are minimal, synthetic inputs based on the schemas and codes
observed in the official 2024 EBA Transparency Exercise files. They reproduce
specific contracts and failure modes without committing the full source data.

## Observed source contracts

- `tr_cre.csv` has 17 columns.
- `tr_oth.csv` has 16 columns.
- Dimension code `0` is a valid total/no-breakdown member.
- Empty `Footnote` values are expected.
- September 2023 P&L rows use `n_quarters=3`.
- SDD item `2420502` occurs in four credit-risk templates, so `Item` alone is
  not a safe dictionary join key.
- `Other banks` uses row 3 as its header.
- Rows 4–17 contain 14 bank records; row 18 is an explanatory note.
- With openpyxl 3.1.5, the official worksheet reports physical `max_row=28`.
- The workbook fixture deliberately extends physical `max_row` to 50 using a
  formatting-only cell while retaining only two bank records.

All LEIs, names, amounts, and countries in these fixtures are test values or
minimal transformations used to exercise a contract. The fixtures are not
analytical extracts.

## Fixture inventory

| Fixture | Purpose | Expected result |
|---|---|---|
| `csv/tr_cre_valid.csv` | Exact credit schema, mixed-case LEI, code `0`, blank footnote | One valid source row |
| `csv/tr_oth_valid.csv` | Exact other-template schema and `n_quarters` | One valid source row |
| `csv/tr_cre_duplicate_natural_key.csv` | Two rows with the same published credit key | Duplicate-key validation must fail |
| `csv/tr_oth_nonnumeric_amount.csv` | Invalid amount text | Decimal conversion must fail |
| `csv/npe_zero_denominator.csv` | NPE numerator with zero total denominator | Ratio must be null |
| `csv/sdd_reused_item.csv` | Item `2420502` under four templates | Item-only join is unsafe |
| `xlsx/metadata_trailing_formatted_blanks.xlsx` | Two banks, a note row, and formatting at row 50 | Parser must return two bank rows |

## Published natural keys

Credit-risk key:

```text
LEI_Code + NSA + Period + Item + Portfolio + Country + Country_rank
+ Exposure + Status + Perf_Status + NACE_codes