## Executive Summary

Our hiring intelligence platform applies five specialized agents—coordinated by n8n and powered by an on-prem LLM—to give engineering leaders real-time visibility into funnel health, interview panel workload, offer declines, rejection reasons, and sourcing quality. The system converts noisy tracker CSVs into clean dashboards, automated insights, and prioritized recommendations, shrinking the feedback loop between recruiters, interviewers, and hiring managers. Key outcomes include automated detection of funnel bottlenecks, context-aware interview balancing, and data-backed recommendations that improve candidate experience and recruiter efficiency.

## Business Use Case Overview

**Problem Statement**  
Fast-growing engineering teams lack real-time visibility into their hiring funnel, resulting in stalled requisitions, unbalanced interview panels, unclear rejection trends, and reactive decision-making.

**The Opportunity**
- **Hiring Funnel Visibility** – Continuous monitoring of stage-by-stage conversion, candidate drop-off points, and offer outcomes.
- **Process Insights** – Automated analysis of rejection reasons, offer declines, and sourcing channel quality to target improvements.
- **Panel Load Balancing** – Spotlight overloaded or underutilized interviewers and recommend reallocation.
- **Actionable Interventions** – LLM-generated insights and recommendations packaged per agent for immediate follow-up.

## Technical Architecture

| Technology | Purpose |
| --- | --- |
| Multi-Agent System (Streamlit + Python + pandas) | Ingests tracker files, routes them to the correct agent, and renders dashboards per agent. |
| n8n Agent Orchestrator | Automates file processing, runs analytics code nodes per agent, calls the LLM for insights, and responds via webhook. |
| Local LLM Backend (Ollama / gemma2:2b) | Generates context-aware insights and recommendations for each agent’s analytics output. |
| CSV Data Sources (Summary, Funnel, Feedback) | Provide raw pipeline, offer, rejection, and feedback signals that feed agent workflows. |
| GitHub + Markdown Report | Documents business case, architecture, and results for reviewers. |

**Workflow Diagram Overview**
1. User uploads CSV via Streamlit → agent router (based on filename keywords).
2. Streamlit POSTs file to n8n webhook for that agent.
3. n8n Extract-from-File → Code node computes analytics.
4. LLM request builder formats stats → HTTP request to Ollama.
5. Merge node injects LLM insights/recommendations into standardized JSON.
6. Streamlit renders grouped dashboards (Hiring Tracker Agents / Offer & Funnel Agents).

## Results & Insights Organization

### A. Hiring Tracker Agents

#### 1. Sourcing Quality Agent
- **Metrics/Display:** Table ranking each sourcing channel by candidates, rejections, rejection rate, and avg resume score.
- **Insights:** Highlights channels exceeding rejection rate or falling below quality thresholds.
- **Recommendation (example):** “Deactivate Vendor X until resume scores improve; double down on referral sourcing where rejection rate < 20%.”

#### 2. Rejection Pattern Agent
- **Metrics/Display:** Stage conversion table, top rejection reasons, optional charts (bar for stage drop-offs).
- **Insights:** LLM describes why “Cultural misfit” or “Insufficient experience” dominate certain stages/interviewers.
- **Recommendation:** “Add culture-fit prompts during technical interview; tighten interviewer calibration for Panelist 03.”

#### 3. Panel Load Balancer
- **Metrics/Display:** Table showing total interviews per panelist, avg/week, load ratio, status (Overloaded/Balanced/Underutilized), plus stage coverage summary.
- **Insights:** LLM flags overloaded interviewers and stages with thin coverage.
- **Recommendation:** “Move 3 interviews/week from Panelist 07 to Panelist 15; broaden Stage ‘Technical Interview’ coverage.”

### B. Offer & Funnel Agents

#### 4. Offer Rejection Insight Agent
- **Metrics/Display:** Decline rate, total offers vs accepted, reason breakdown, recent declines table.
- **Insights:** Points to compensation mismatch, delays, or cultural fit issues driving offer declines.
- **Recommendation:** “Shorten offer timeline, add compensation FAQ, and run candidate expectation briefing before final interview.”

#### 5. Pipeline Health Agent
- **Metrics/Display:** Stage-by-stage conversion table, bottleneck table, summary metrics (overall conversion, avg stages completed, top drop stage).
- **Insights:** Identifies conversion leaks, e.g., “Technical Interview drop rate at 32%.”
- **Recommendation:** “Host technical interview retro to revise rubrics; build targeted prep materials for candidates entering this stage.”

## AI Agent Actions & Automation

1. **File Routing:** Streamlit routes each upload to the correct agent based on filename keywords or group configuration.
2. **Analytics Code:** Each agent’s n8n Code node aggregates metrics (stage conversions, workload stats, etc.).
3. **LLM Insights:** n8n builds a prompt with analytics JSON, calls gemma2:2b via Ollama, and merges the structured response.
4. **Standardized Output:** All agents emit `{ agent_name, display_title, sections: [] }` so Streamlit renders them uniformly with grouped headings.
5. **Actionability:** Insights + Recommendations sections provide concrete next steps (panel rebalancing, sourcing adjustments, pipeline interventions).

## Conclusion & Next Steps

- **Impact:** The system turns raw tracker files into actionable dashboards, automates insight generation, and reduces the time-to-decision for hiring managers.
- **Next Steps:**
  - Add historical trend tracking (month-over-month conversion, panel load).
  - Integrate with ATS APIs to eliminate manual CSV uploads.
  - Implement alerting (Slack/email) for thresholds (e.g., offer decline rate > 25%).
  - Expand LLM prompts for prescriptive actions (e.g., interview scheduling suggestions).

By following this structure, the capstone report clearly communicates the business need, technical approach, and tangible benefits of the multi-agent hiring intelligence system. The same Markdown can be converted into slides or a Streamlit “About” tab for easy presentation.


