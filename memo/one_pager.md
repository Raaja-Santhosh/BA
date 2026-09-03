# Memo: Root Cause of Loan Approval Delays

**To:** VP of Operations  
**From:** Business Process Analytics  
**Date:** August 12, 2026  
**Subject:** Eliminating Rework Bottlenecks to Accelerate Loan Approvals  

## The Headline
The Manager Review stage is currently responsible for **48% of all processing delays**. By fixing the upstream data collection process that causes massive rework loops, we project we can cut the average end-to-end approval time from **8.6 days to as low as 2.3 days** — saving between **3 and 6 days per application**, depending on how much rework the fix eliminates.

---

## 1. The Problem
Customer satisfaction and conversion rates are dropping due to unpredictable loan turnaround times. Currently, **34% of all loan applications breach our assumed 10-day SLA** (see Caveats below). Until now, the exact source of this delay was anecdotal.

## 2. Root Cause Analysis
Process mining analysis of 13,087 recent loan applications reveals a massive gap between the process "as-designed" and the process "as-it-runs":
* **Process Drift:** Token-based replay fitness is 0.54, and 0% of cases perfectly match the expected linear flow. While a rigid "happy path" baseline is a strict benchmark, total non-conformance confirms the process has drifted far from legacy expectations.
* **The Ping-Pong Effect:** The true bottleneck is not staff speed, but *rework*. There were **5,089 instances** where a case reached Underwriting only to be kicked backward to Document Check for missing information. 
* **The Cost of Rework:** Applications that suffer backward rework take an average of **14.3 days** to complete, compared to just **2.3 days** for clean cases — approximately **12 days** of added delay. (Mann-Whitney U Test p < 0.0001, Rank-Biserial Correlation = −0.83).

## 3. Recommendation
**Shift validation left.** Implement a hard "Document Completeness Gate" *before* any application enters Underwriting. 

## 4. Quantified Projected Impact
Monte Carlo simulation (100 iterations) projecting the impact at varying levels of rework elimination:

| Rework Eliminated | Projected Avg E2E | Days Saved | Cycle Time Reduction |
|---|---|---|---|
| 50% (conservative) | 5.4 days | 3.2 days | 37% |
| 75% (moderate) | 3.9 days | 4.8 days | 55% |
| 100% (best case) | 2.3 days | 6.3 days | 74% |

### Caveats & Assumptions
* **SLA Benchmarks**: The 10-day SLA is an assumed retail lending threshold, not a contractual dataset figure.
* **Activity Mapping**: Raw Dutch `W_` codes were mapped to English banking stages for readability.
* **Simulation Exchangeability**: The simulation assumes messy cases would behave like clean cases if rework were removed. Some Manager Review delay may be genuine capacity constraints, which is why the sensitivity table above is provided rather than a single point estimate.
