# Loom Video Script: Loan Process Bottleneck Presentation

**Target Audience:** Non-technical VPs and Hiring Managers
**Duration:** ~3 Minutes
**Screen:** Streamlit Dashboard

---

### [0:00 - 0:30] The Hook & The Problem
**[Visual: Dashboard Tab 2 - Stage Bottlenecks vs SLAs]**
"Hi everyone. Over the last month, we noticed our loan approval pipeline was constantly missing the 10-day SLA target—in fact, nearly 34% of all applications were breaching it. 

I used Process Mining in Python to reverse-engineer our event logs and find out why. As you can see on this chart, the Manager Review stage is taking the most absolute time, averaging almost 11 days. But that’s actually a symptom, not the root cause."

### [0:30 - 1:15] The Root Cause (Process Mining)
**[Visual: Dashboard Tab 3 - As-Designed vs As-Is DFG]**
"If you look at how we *designed* the process to run on the left—it’s a straight line from submission to approval. Now, a perfectly straight line is a bit of a strict baseline, but process mining reveals this complete spaghetti diagram on the right. 

Zero percent of our 13,000 cases actually followed that straight line. Even allowing for reasonable real-world variation, the process has drifted incredibly far from our legacy expectations. Instead of a clean pipeline, our staff are constantly sending applications backward."

### [1:15 - 2:00] The Data Proof (Sankey & Statistics)
**[Visual: Dashboard Tab 4 - Rework Loops Sankey]**
"This Sankey diagram maps those backward steps. Notice this thick band here: over 5,000 times, an application reached Underwriting only to be kicked all the way back to Document Check because of missing info. 

I ran a Mann-Whitney statistical test to isolate the impact of this specific backward loop. The math proves that this rework adds exactly 12 days to the processing time. It’s not statistical noise—it is the direct cause of our SLA breaches."

### [2:00 - 2:45] The Simulation & Recommendation
**[Visual: Dashboard Tab 6 - What-If Simulation]**
"So, I ran a Monte Carlo simulation. I wanted to see what our cycle times would look like if we implemented a hard 'Completeness Gate' up front, ensuring no file goes to Underwriting if it's missing documents.

The simulation projects that by eliminating that one rework loop, our average cycle time drops from 8.6 days down to 2.2 days. 

That is a 73% reduction in turnaround time, saving us over 6 business days per customer, entirely without hiring more staff. We just need to shift our validation to the front of the line."

### [2:45 - 3:00] Sign-off
"All the underlying Python code, the statistical models, and this interactive dashboard are documented in the repository below. Thank you, and I look forward to discussing how we can implement this validation gate."
