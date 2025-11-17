import streamlit as st
import pandas as pd
import requests
import yaml
import re
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# -----------------------------
# Streamlit: Hiring Agent (Refactored)
# - Improved layout: Executive summary, architecture, upload, agent panels, consolidated insights
# - Keep helper functions for robust n8n response parsing
# - Replace your previous single-file app with this improved one
# -----------------------------

st.set_page_config(page_title="Hiring Agent — Multi-Agent Insights", page_icon="📊", layout="wide")

# -----------------------------
# Constants & Utility
# -----------------------------
ROOT = Path(__file__).parent
DEFAULT_CONFIG_PATH = ROOT.parent / "config.yaml"

GROUPED_AGENT_ORDER = [
    ("A. Hiring Tracker Agents", [
        "sourcing_quality_agent",
        "rejection_pattern_agent",
        "panel_load_balancer",
    ]),
    ("B. Offer & Funnel Agents", [
        "offer_rejection_agent",
        "pipeline_health_agent",
    ]),
]

AGENT_GROUP_LOOKUP = {}
for group_label, agent_keys in GROUPED_AGENT_ORDER:
    for key in agent_keys:
        AGENT_GROUP_LOOKUP[key] = group_label

# -----------------------------
# Helpers (configuration)
# -----------------------------
@st.cache_data
def load_config(path: Optional[Path] = None) -> Dict[str, Any]:
    cfg_path = path or DEFAULT_CONFIG_PATH
    try:
        with open(cfg_path, "r") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}
    except yaml.YAMLError:
        return {}

config = load_config()

# n8n defaults
n8n_config = config.get("n8n", {})
BASE_URL = n8n_config.get("base_url", "http://localhost:5678")
AGENTS_CONFIG = n8n_config.get("agents", {})
DEFAULT_AGENT = config.get("default_agent", "sourcing_quality_agent")
ENABLED_AGENTS = {k: v for k, v in AGENTS_CONFIG.items() if v.get("enabled")}

# -----------------------------
# Robust response parsing (re-used/adapted from your file)
# -----------------------------

def parse_json_string(value: Any) -> Any:
    if isinstance(value, (list, dict)):
        return value
    if not isinstance(value, str):
        return value
    v = re.sub(r'```json\s*', '', value)
    v = re.sub(r'```\s*', '', v).strip()
    try:
        return json.loads(v)
    except Exception:
        return value


def repair_json_like_string(text: str) -> Optional[Any]:
    candidate = text.strip()
    if not (candidate.startswith("{") and candidate.endswith("}")):
        return None
    # Simple heuristic: escape inner quotes that look unescaped
    try:
        repaired = candidate.replace("\n", "\\n")
        return json.loads(repaired)
    except Exception:
        return None


def get_records_from_n8n_response(result_data: Any) -> List[Any]:
    all_records: List[Any] = []
    if isinstance(result_data, list) and result_data:
        for item in result_data:
            if isinstance(item, dict) and "json" in item:
                j = item["json"]
                if isinstance(j, list):
                    all_records.extend(j)
                else:
                    all_records.append(j)
            else:
                all_records.append(item)
    elif isinstance(result_data, dict):
        # Common wrappers
        for key in ("sources", "data", "results"):
            if key in result_data:
                val = result_data[key]
                if isinstance(val, list):
                    all_records.extend(val)
                elif isinstance(val, dict):
                    all_records.extend(list(val.values()))
                else:
                    all_records.append(val)
                return all_records
        # otherwise push dict
        all_records.append(result_data)
    else:
        all_records.append(result_data)
    return all_records


def clean_display_text(text: Any) -> str:
    s = str(text)
    s = s.replace("```json", "").replace("```", "")
    s = s.strip('"').strip("'")
    s = re.sub(r"\s+", " ", s)
    return s

# -----------------------------
# UI: Sidebar (Executive Summary, Config view)
# -----------------------------
st.sidebar.title("Hiring Agent — Controls")
with st.sidebar.expander("Executive Summary", expanded=True):
    st.markdown(
        """
**Problem:** EMs lack real-time visibility into hiring funnels → slow cycles & poor experience.

**Solution:** Multi-agent system (n8n + LLMs) to surface bottlenecks, panel fatigue, sourcing quality, and offer declines.

**Quick actions:** Upload CSVs, run agents (calls to n8n webhooks), review consolidated recommendations.
"""
    )

with st.sidebar.expander("Configuration", expanded=False):
    st.write("Base n8n URL")
    base_url_input = st.text_input("n8n base URL", value=BASE_URL)
    if base_url_input != BASE_URL:
        BASE_URL = base_url_input

    st.markdown("**Enabled Agents (from config.yaml)**")
    if ENABLED_AGENTS:
        for k, v in ENABLED_AGENTS.items():
            st.write(f"- **{k}** — {v.get('description', '')}")
    else:
        st.info("No agents enabled in config.yaml. Edit config or provide sample agents.")

# -----------------------------
# Top-level layout: header + 3 columns for summary, upload, quick actions
# -----------------------------
st.title("📊 Hiring Agent — Multi-Agent Insights")
st.markdown("---")

col_left, col_mid, col_right = st.columns([2, 3, 2])
with col_left:
    st.header("Overview")
    st.markdown(
        """
**What this app does:** Accepts hiring tracker CSVs (Summary, Feedback, Funnel, Offer) → calls specialised agents in n8n → renders metrics, tables, charts and prioritized recommendations for Engineering Managers.
"""
    )

with col_mid:
    st.header("Upload data")
    uploaded_files = st.file_uploader("Upload agent CSVs (Summary, Feedback, Funnel, Offer)", type="csv", accept_multiple_files=True)
    st.caption("Tip: name files with keywords like 'summary', 'feedback', 'funnel', 'offer' to auto-match agents")

with col_right:
    st.header("Quick actions")
    run_all = st.button("▶️ Run agents for uploaded files")
    show_raw = st.checkbox("Show raw agent responses (debug)")

st.markdown("---")

# -----------------------------
# Agent matching helpers
# -----------------------------

def normalized(text: str) -> str:
    return text.replace("_", "").replace("-", "").lower()


def match_by_keywords(filename: str, pool: Dict[str, Any]) -> List[str]:
    filename_lower = filename.lower()
    matches = []
    for agent_key, agent_info in pool.items():
        keywords = agent_info.get("filename_keywords") or agent_info.get("file_patterns") or []
        for kw in keywords:
            if kw.lower() in filename_lower:
                matches.append(agent_key)
                break
        # also match by agent name
        if normalized(agent_key) in normalized(filename_lower) and agent_key not in matches:
            matches.append(agent_key)
    return matches


def get_matching_agents_for_file(filename: str) -> List[str]:
    if ENABLED_AGENTS:
        matches = match_by_keywords(filename, ENABLED_AGENTS)
        if matches:
            return matches
    # fallback to full agent list
    matches = match_by_keywords(filename, AGENTS_CONFIG)
    if matches:
        return matches
    # final fallback
    if DEFAULT_AGENT:
        return [DEFAULT_AGENT]
    return []

# -----------------------------
# Call n8n agent
# -----------------------------

def call_n8n_agent(agent_key: str, file_obj) -> Optional[Any]:
    agent_conf = AGENTS_CONFIG.get(agent_key, {})
    webhook_path = agent_conf.get("webhook_path") or agent_conf.get("endpoint")
    if not webhook_path:
        st.error(f"Agent {agent_key} does not define a webhook_path/endpoint in config.")
        return None
    url = f"{BASE_URL}{webhook_path}" if webhook_path.startswith("/") else f"{BASE_URL}/{webhook_path}"
    try:
        file_obj.seek(0)
        files = {"file": (file_obj.name, file_obj, "text/csv")}
        resp = requests.post(url, files=files, timeout=60)
        resp.raise_for_status()
        try:
            return resp.json()
        except Exception:
            return resp.text
    except Exception as e:
        st.error(f"Error calling agent {agent_key}: {e}")
        return None

# -----------------------------
# Rendering helpers
# -----------------------------

def render_standardized_agent_response(agent_response: Dict[str, Any]):
    if not agent_response:
        return False
    display_title = agent_response.get("display_title") or agent_response.get("agent_name") or "Agent Output"
    st.subheader(display_title)
    sections = agent_response.get("sections") or []
    for section in sections:
        st.write("\n")
        t = section.get("type")
        title = section.get("title") or ""
        if t == "metrics":
            data = section.get("data") or {}
            if data:
                cols = st.columns(min(4, len(data)))
                for i, (k, v) in enumerate(data.items()):
                    with cols[i % len(cols)]:
                        st.metric(k, v)
        elif t == "table":
            rows = section.get("rows") or []
            cols = section.get("columns") or []
            if rows:
                df = pd.DataFrame(rows)
                if cols:
                    df = df[cols] if all(c in df.columns for c in cols) else df
                st.table(df)
                if not df.empty:
                    num_cols = df.select_dtypes(include=["number"]).columns.tolist()
                    if num_cols:
                        st.bar_chart(df.set_index(df.columns[0])[num_cols[0]])
        elif t in ("insights", "recommendations"):
            items = section.get("data") or section.get("items") or []
            if items:
                if title:
                    st.markdown(f"**{title}**")
                for idx, it in enumerate(items, 1):
                    st.write(f"{idx}. {clean_display_text(it)}")
        else:
            # Fallback — display raw
            st.write(section)
    return True

# -----------------------------
# Main processing: run agents and render
# -----------------------------

CONSOLIDATED_RECS: List[str] = []

if uploaded_files and run_all:
    # iterate files and run matching agents
    for uf in uploaded_files:
        st.markdown(f"### 🔁 Processing file: `{uf.name}`")
        matching_agents = get_matching_agents_for_file(uf.name)
        st.write(f"Matched agents: {matching_agents}")

        for agent_key in matching_agents:
            if agent_key not in AGENTS_CONFIG:
                st.warning(f"Agent {agent_key} not found in config.yaml")
                continue
            agent_title = AGENTS_CONFIG[agent_key].get("description", agent_key)
            st.markdown(f"#### {agent_title}")

            with st.spinner(f"Calling agent `{agent_key}`..."):
                resp = call_n8n_agent(agent_key, uf)
            if resp is None:
                st.error("No response returned from agent.")
                continue
            if show_raw:
                with st.expander("Raw agent response (debug)"):
                    try:
                        st.json(resp)
                    except Exception:
                        st.write(resp)

            # Try standardized response
            std = None
            if isinstance(resp, dict) and resp.get("agent_name") and resp.get("sections"):
                std = resp
            else:
                # extract records
                records = get_records_from_n8n_response(resp)
                if len(records) == 1 and isinstance(records[0], dict) and records[0].get("agent_name"):
                    std = records[0]

            if std:
                rendered = render_standardized_agent_response(std)
                # collect recommendations from rendered response
                for s in std.get("sections", []):
                    if s.get("type") == "recommendations" or s.get("type") == "insights":
                        items = s.get("data") or s.get("items") or []
                        for it in items:
                            CONSOLIDATED_RECS.append(clean_display_text(it))
                continue

            # fallback: show DataFrame table and capture text fields as recommendations
            records = get_records_from_n8n_response(resp)
            if records:
                try:
                    df = pd.DataFrame(records)
                    st.dataframe(df, use_container_width=True)
                    # heuristics: look for columns named 'recommendation' or 'action'
                    for col in df.columns:
                        if re.search(r"recommend|action|insight", col, re.I):
                            vals = df[col].dropna().astype(str).tolist()
                            for v in vals:
                                CONSOLIDATED_RECS.append(clean_display_text(v))
                except Exception as e:
                    st.write(records)
            else:
                st.write(resp)

# -----------------------------
# Consolidated Insights Panel
# -----------------------------
st.markdown("---")
st.header("📋 Consolidated Insights & Recommendations")
if CONSOLIDATED_RECS:
    # De-duplicate while preserving order
    seen = set()
    deduped = []
    for r in CONSOLIDATED_RECS:
        if r not in seen:
            seen.add(r)
            deduped.append(r)
    for i, r in enumerate(deduped, 1):
        st.write(f"{i}. {r}")
    st.download_button("Download recommendations (TXT)", "\n".join(deduped), file_name="recommendations.txt")
else:
    st.info("No recommendations collected yet. Run agents on uploaded files to generate insights.")

# -----------------------------
# Final: Helpful debug / sample data loader
# -----------------------------
st.markdown("---")
with st.expander("Developer / Debug tools", expanded=False):
    st.write("Base URL:" , BASE_URL)
    st.write("Agents in config:")
    st.write(list(AGENTS_CONFIG.keys()))
    if st.button("Run sample local dataset (demo)"):
        st.success("Demo runner triggered — you should wire sample CSVs and agents in n8n to exercise this.")

# End of file
