# Memo: Root Cause of Loan Approval Delays

**To:** VP of Operations  
**From:** Business Process Analytics  
**Date:** August 12, 2026  
**Subject:** Eliminating Rework Bottlenecks to Accelerate Loan Approvals  

## The Headline
The Manager Review stage is currently responsible for **48.1% of all processing delays**. By fixing the upstream data collection process that causes massive rework loops, we project we can cut the average end-to-end approval time from **8.61 days to 2.27 days**—saving the bank an average of **6.35 business days per application**.

---

## 1. The Problem
Customer satisfaction and conversion rates are dropping due to unpredictable loan turnaround times. Currently, **33.9% of all loan applications breach our assumed 10-day SLA**. Until now, the exact source of this delay was anecdotal.

## 2. Root Cause Analysis
Process mining analysis of 13,087 recent loan applications reveals a massive gap between the process "as-designed" and the process "as-it-runs":
* **0% Conformance:** While a perfectly rigid 100% "happy path" baseline can be an overly strict strawman, a 0% conformance rate on real data is a stark measurement of how far reality has drifted from the linear ideal expected by legacy management. Every single case contained some form of looping.
* **The Ping-Pong Effect:** The true bottleneck is not staff speed, but *rework*. There were **5,089 instances** where a case reached Underwriting only to be kicked backward to Document Check for missing information. 
* **The Cost of Rework:** Our statistical tests show that these backward rework loops mathematically guarantee delays. Applications that suffer backward rework take an average of **14.33 days** to complete, compared to just **2.27 days** for clean cases. (Mann-Whitney U Test p < 0.0001, Rank-Biserial Correlation = -0.83, a massive non-parametric effect size).

## 3. Recommendation
**Shift validation left.** The majority of delays occur because Manager Review and Underwriting cannot proceed without bouncing cases back for missing documents. 

We must implement a hard "Document Completeness Gate" *before* any application enters Underwriting. 

## 4. Quantified Projected Impact
We ran a Monte Carlo simulation (100 iterations) projecting the impact of eliminating these specific backward rework loops. If cases flow through a redesigned, clean pipeline without bouncing backward, the projected impact is:
* **Average Cycle Time Reduction:** 73.7%
* **New Average SLA:** 2.27 days (down from 8.61 days)
* **Time Saved:** 6.35 days per customer.

### Caveats & Assumptions
* *SLA Benchmarks*: The dataset did not contain an official SLA policy, so we modeled the bottlenecks against assumed standard banking thresholds (E2E = 10 days).
* *Simulation Exchangeability Assumption*: The Monte Carlo simulation swaps clean case durations into the previously "messy" cases. This relies on the assumption of exchangeability—that the *only* reason the messy cases were slow was the structural rework loop, and that they are otherwise fundamentally identical to clean cases.
