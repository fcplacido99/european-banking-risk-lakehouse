# Project execution plan

## Capacity and sequencing

- Week 1 capacity: 6 project hours remaining.
- Weeks 2–25 capacity: 8 project hours per week.
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

## Milestone calendar

Detailed subtasks remain governed by the accepted weekly execution guide. This
table provides the repository-visible delivery sequence.

| Week | Planned outcome | Gate status |
|---:|---|---|
| 2 | Locally testable Python package foundation | **NOT STARTED** |
| 3 | Safe streamed acquisition and validation | **NOT STARTED** |
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
