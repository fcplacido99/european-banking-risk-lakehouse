# Project execution plan

## Capacity and sequencing

- Week 1 capacity: 6 project hours remaining.
- Week 2 capacity: 9 project hours as an approved exception.
- Weeks 3–25 capacity: 8 project hours per week.
- Only the earliest unfinished subtask may be worked on.
- A subtask becomes **FINISHED** only when every evidence item is checked.
- Overruns move forward; technical gates are never removed to preserve dates.
- The final 30 minutes of each week are reserved for evidence and review.
- Course hours are outside this project plan.

Allowed statuses are **NOT STARTED**, **ONGOING**, and **FINISHED**.

## Current verified state

| ID | Status | Evidence |
|---|---|---|
| P0.1 | **FINISHED** | Official 2023–2025 EBA files are stored in year folders outside this repository. |
| P0.2 | **FINISHED** | The 2024 files were profiled and the consulting question selected in the private implementation guide. |
| P0.3 | **FINISHED** | 2024 counts, hashes, KPI coverage, keys, and reconciliation behaviour are recorded in Decision 001. |
| P0.4 | **FINISHED** | Public implementation repository exists with the committed 2024 decision record and a safe documentation-first skeleton. |

## Week 1 — 10 Aug to 16 Aug 2026

Goal: publish a safe, documentation-first GitHub repository.

| ID | Status | Budget | Subtask | Tools | Finish evidence |
|---|---|---:|---|---|---|
| W1.1 | **FINISHED** | 1h | Freeze the 2024 vertical slice in Decision 001. | VS Code; implementation guide | Accepted record contains the business question, five-file scope, hashes, KPI set, exclusions, and non-goals. |
| W1.2 | **FINISHED** | 1h | Select Python 3.12 and create `.venv` in the repository. | Python launcher; PowerShell; `venv` | `.venv/pyvenv.cfg` records Python 3.12.10; activation, Python, and pip files exist; terminal execution confirmed by the project owner. |
| W1.3 | **FINISHED** | 1.5h | Create the safe repository skeleton. | VS Code; PowerShell | Required directories and documentation placeholders exist; repository audit found zero CSV/XLSX/PDF data files; raw year folders remain outside the repository. |
| W1.4 | **FINISHED** | 1h | Add exclusions, initialize Git, audit, and make the first commit. | Git; PowerShell | Commit 94881ae; clean working tree; 15 audited files tracked; no raw EBA files, secrets, generated outputs, or virtual environment tracked.|
| W1.5 | **FINISHED** | 1h | Create the public GitHub repository and push `main`. | GitHub website; Git |Public repository verified at `https://github.com/fcplacido99/european-banking-risk-lakehouse`; README renders; Decision 001 is tracked; raw datasets and `.venv` are absent. |
| W1.6 | **FINISHED** | 0.5h | Record actual hours and Week 1 evidence. | This file; GitHub | Evidence section identifies Decision 001, commits `94881ae`, `243cb5d`, and `062e381`, the public repository, and the verified final state: synchronized `main`, clean working tree, and no raw EBA files or virtual environment tracked. |

### Evidence

- Decision record: `docs/decisions/001-2024-vertical-slice.md`
- Initial audited commit: `94881ae`
- W1.4 evidence commit: `243cb5d`
- Public-repository evidence commit: `062e381`
- Public repository: <https://github.com/fcplacido99/european-banking-risk-lakehouse>
- Final state: public repository, synchronized `main`, clean working tree, and no raw EBA files or virtual environment tracked.

## Week 2 — 17 Aug to 23 Aug 2026

Goal: establish an installable, locally testable Python foundation grounded in
the real 2024 EBA schemas.

| ID | Status | Budget | Subtask | Tools | Finish evidence |
|---|---|---:|---|---|---|
| W2.1 | **FINISHED** | 1.5h | Configure the Python package and local pytest path. | Python 3.12; pip; setuptools; pytest | Python 3.12.10; editable installation succeeded; `pip check` passed; package version `0.1.0` and pytest 8.4.2 import outside Databricks. |
| W2.2 | **FINISHED** | 1.5h | Add immutable contract types and controlled error codes. | Python standard library; pytest | Six contract tests passed; isolated standard-library import succeeded; enum values, immutable records, docstrings, and controlled error behavior were verified without Databricks. |
| W2.3 | **FINISHED** | 3.5h | Inspect real schemas and create minimal dataset-grounded fixtures. | EBA files read-only; Python; CSV; openpyxl; pytest | Twelve fixture-contract tests passed; six CSV and one XLSX fixture reproduce verified schema and failure modes; combined fixture size remains below 100 KB; no raw EBA artifact was copied into Git. |
| W2.4 | **FINISHED** | 2h | Implement initial normalization, period, identifier, and division helpers. | Python standard library; pytest | Thirty-six focused helper tests and all 54 project tests passed; package imports outside Databricks; header, LEI, aggregate, month-end, missingness, and denominator contracts are verified. |
| W2.5 | **FINISHED** | 0.5h | Audit, record, and publish Week 2 evidence. | pytest; pip; Git; GitHub | Python 3.12.10, dependency checks, and all 54 tests passed; repository safety audit found no forbidden tracked files; completion evidence was committed and published. |

### Week 2 evidence

- Package configuration: commit `7d65a3f`
- Source and validation contracts: commit `d976ece`
- Dataset-grounded fixtures: commit `cceeb10`
- Normalization helpers and unit tests: commit `3f4c93f`
- Runtime: Python 3.12.10
- Installed package version: `0.1.0`
- Dependency result: `pip check` reported no broken requirements
- Automated tests: 54 passed
- Fixture footprint: 9,710 bytes
- Repository audit: no raw EBA artifacts, secrets, `.venv`, or generated outputs tracked
- Databricks dependency: none; the complete Week 2 suite runs locally

## Week 3 — 24 Aug to 30 Aug 2026

Goal: implement safe streamed source acquisition and validation without a live
EBA dependency in the automated test suite.

| ID | Status | Budget | Subtask | Tools | Finish evidence |
|---|---|---:|---|---|---|
| W3.1 | **FINISHED** | 1.5h | Correct contract documentation and add validated 2024 source configuration. | Python; PyYAML; pytest | Fifteen focused tests and all 63 project tests passed; five official EBA URLs and locked hashes load as immutable contracts; invalid releases, URLs, paths, hashes, duplicates, and type mismatches fail without network access. |
| W3.2 | **FINISHED** | 2.5h | Stream responses safely to temporary files. | Python; requests; pytest | Three focused staging tests and all 66 project tests passed; mocked multi-chunk transfer preserved byte order, size, and SHA-256 without loading the full response; interrupted and timed-out transfers left no temporary or final artifact. |
| W3.3 | **FINISHED** | 2h | Validate and atomically publish artifacts. | Python; requests; filesystem APIs; pytest | Thirteen focused download tests and all 76 project tests passed; CSV headers, XLSX/PDF signatures, nonzero size, and SHA-256 are validated before atomic publication; invalid, empty, mismatched, and existing-destination cases leave no final or temporary artifact. |
| W3.4 | **FINISHED** | 1.5h | Prove HTTP and content failure behavior. | pytest; mocked HTTP boundary | Eighteen focused acquisition tests and all 81 project tests passed without internet access; HTTP 404/500, connect/read timeout, interruption before and after partial transfer, empty content, invalid signatures and headers, hash mismatch, and existing destinations produce controlled behavior with complete cleanup. |
| W3.5 | **FINISHED** | 0.5h | Audit, record, and publish Week 3 evidence. | pytest; pip; Git; GitHub | Python 3.12.10, dependency checks, and all 81 project tests passed; the tracked-file and credential-pattern audits found no forbidden source artifact, secret, virtual environment, temporary download, or local path; completion evidence was committed and published. |

### Week 3 evidence

- Validated 2024 source configuration: commit `82f233f`
- Streamed temporary-file staging: commit `7000742`
- Content validation and atomic publication: commit `bc8384b`
- Acquisition failure boundaries: commit `f5a99a6`
- Runtime: Python 3.12.10
- Dependency result: `pip check` reported no broken requirements
- Automated tests: 81 passed
- Source contracts: five official 2024 EBA artifacts with locked SHA-256 values
- HTTP boundary: fully mocked; automated tests require no live EBA access
- Failure coverage: HTTP 404/500, connect/read timeout, interrupted transfer, empty content, invalid signature/header, hash mismatch, and existing destination
- Publication behavior: only validated content receives its final filename
- Repository audit: no raw EBA source, `.venv`, secret, local path, `.part` file, or exploratory output tracked


## Milestone calendar

Detailed subtasks remain governed by the accepted weekly execution guide. This
table provides the repository-visible delivery sequence.

| Week | Planned outcome | Gate status |
|---:|---|---|
| 2 | Locally testable Python package foundation | **FINISHED** |
| 3 | Safe streamed acquisition and validation | **FINISHED** |
| 4 | Manifests, CLI, and acquisition idempotency | **NOT STARTED** |
| 5 | Institution and dimension workbook parsing | **NOT STARTED** |
| 6 | Metric, bank, and dimension bridges | **NOT STARTED** |
| 7 | Databricks Free Edition setup and verified landing | **NOT STARTED** |
| 8 | Source-preserving Bronze CSV tables | **NOT STARTED** |
| 9 | Bronze references, quarantine, and rerun safety | **NOT STARTED** |
| 10 | Conformed Silver references | **NOT STARTED** |
| 11 | Typed Silver facts and natural keys | **NOT STARTED** |
| 12 | Silver quality and deterministic rerun | **NOT STARTED** |
| 13 | Capital and profitability KPI components | **NOT STARTED** |
| 14 | Asset-quality KPIs and coverage validation | **NOT STARTED** |
| 15 | Quarterly KPI and review-candidate marts | **NOT STARTED** |
| 16 | Exposure-driver mart and reconciliation | **NOT STARTED** |
| 17 | NACE driver and persistent Gold reconciliation | **NOT STARTED** |
| 18 | Parameterised five-task Databricks Workflow | **NOT STARTED** |
| 19 | Clean execution, rerun, and controlled failure | **NOT STARTED** |
| 20 | Consolidated automated tests and public CI | **NOT STARTED** |
| 21 | SQL-derived consulting findings | **NOT STARTED** |
| 22 | Traceable consulting output | **NOT STARTED** |
| 23 | Operational hardening and measured performance | **NOT STARTED** |
| 24 | Release candidate and recruiter path | **NOT STARTED** |
| 25 | Final acceptance, walkthrough, and conditional v1 tag | **NOT STARTED** |

## Weekly review template

| Measure | Value |
|---|---|
| Planned project hours | |
| Actual project hours | |
| Earliest unfinished subtask at start | |
| Earliest unfinished subtask at end | |
| Commit or run evidence | |
| Work carried forward | |
| Scope or risk change | |

No status is advanced solely because a calendar week has ended.
