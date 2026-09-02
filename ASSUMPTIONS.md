# ASSUMPTIONS LOG

This file logs all non-data-driven assumptions and definitions used throughout the analysis. 

## Phase 1: Environment & Ingestion
- **Lifecycle Filtering**: The BPI Challenge 2012 log contains `SCHEDULE`, `START`, and `COMPLETE` lifecycle transitions for activities. We filtered the log to **only include `COMPLETE` events** to establish one clean timestamp per activity execution per case. This simplifies cycle time calculations but assumes the `COMPLETE` timestamp accurately reflects when work finished.
- **Stage Mapping**: The raw log activities were mapped to standard business stages as follows:
  - `Submitted`: `A_SUBMITTED`, `A_PARTLYSUBMITTED`
  - `Document Check`: `A_PREACCEPTED`, `W_Completeren aanvraag`
  - `Underwriting`: `A_ACCEPTED`, `A_FINALIZED`, `O_CREATED`, `O_SENT`
  - `Manager Review`: `W_Nabellen offertes`, `A_APPROVED`, `A_REGISTERED`, `A_ACTIVATED`
  - `Outcomes`: `A_APPROVED` -> Approved, `A_DECLINED` -> Rejected, `A_CANCELLED`, `O_CANCELLED` -> Cancelled
- **SLA Thresholds (Assumed Benchmarks)**: The dataset does not contain an official SLA policy. For the purpose of bottleneck identification, we assume the following benchmarks based on industry norms:
  - **Document Check**: ≤ 2 business days
  - **Underwriting**: ≤ 3 business days
  - **Manager Review**: ≤ 1 business day
  - **End-to-End**: ≤ 10 business days
