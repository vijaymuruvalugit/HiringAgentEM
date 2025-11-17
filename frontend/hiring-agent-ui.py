import streamlit as st
import pandas as pd
import requests
import yaml
import re
import json
from pathlib import Path

# Page configuration
st.set_page_config(
    page_title="Hiring Agent",
    page_icon="📊",
    layout="wide"
)

st.title("Hiring Agent")
st.write("Upload your hiring tracker CSVs (Summary, Feedback, Funnel, etc.) to see insights from multiple agents.")

# Load configuration from config.yaml
@st.cache_data
def load_config():
    config_path = Path(__file__).parent.parent / "config.yaml"
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        st.error(f"Configuration file not found: {config_path}")
        st.stop()
    except yaml.YAMLError as e:
        st.error(f"Error parsing config.yaml: {e}")
        st.stop()

config = load_config()
st.caption("Tip: if you edit config.yaml while the app is running, rerun the page to reload the cached settings.")

# Get available agents
n8n_config = config.get('n8n', {})
base_url = n8n_config.get('base_url', 'http://localhost:5678')
agents = n8n_config.get('agents', {})
default_agent = config.get('default_agent', 'sourcing_quality_agent')

# Filter enabled agents
enabled_agents = {name: agent for name, agent in agents.items() if agent.get('enabled', False)}

# Agent grouping / ordering for display
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
GROUP_SEQUENCE_LOOKUP = {}
for idx, (group_label, agent_list) in enumerate(GROUPED_AGENT_ORDER):
    for agent_key in agent_list:
        AGENT_GROUP_LOOKUP[agent_key] = group_label
        GROUP_SEQUENCE_LOOKUP[agent_key] = idx

if not enabled_agents:
    st.error("No agents are enabled in config.yaml. Please enable at least one agent.")
    st.stop()

st.info(
    "✅ Upload multiple agent CSVs (e.g., _Summary_, _Feedback_, _Funnel_). "
    "Each will be processed automatically by its associated agent and results displayed below."
)

uploaded_files = st.file_uploader(
    "Upload agent CSVs (Summary, Feedback, Funnel, etc.)",
    type="csv",
    accept_multiple_files=True,
)

def get_agent_for_file(filename, agent_configs, enabled_agent_configs, fallback_agent):
    """Returns the first matching agent (for backward compatibility)."""
    matches = get_all_agents_for_file(filename, agent_configs, enabled_agent_configs, fallback_agent)
    return matches[0] if matches else None

def get_all_agents_for_file(filename, agent_configs, enabled_agent_configs, fallback_agent):
    """Returns ALL agents that match the filename."""
    filename_lower = filename.lower()
    matched_agents = []
    
    def normalized(text):
        return text.replace("_", "").replace("-", "").lower()

    def match_by_keywords(pool):
        matches = []
        for agent_key, agent_info in pool.items():
            keywords = agent_info.get('filename_keywords') or agent_info.get('file_patterns') or []
            for keyword in keywords:
                if keyword.lower() in filename_lower:
                    matches.append(agent_key)
                    break  # Only add once per agent
        return matches

    # Check enabled agents first
    keyword_matches = match_by_keywords(enabled_agent_configs)
    if keyword_matches:
        matched_agents.extend(keyword_matches)
    
    # Also check by agent name matching
    for agent_key in enabled_agent_configs.keys():
        if normalized(agent_key) in normalized(filename_lower):
            if agent_key not in matched_agents:
                matched_agents.append(agent_key)

    # If no matches, check disabled agents (for fallback)
    if not matched_agents:
        keyword_matches = match_by_keywords(agent_configs)
        if keyword_matches:
            matched_agents.extend(keyword_matches)
        
        fallback_config = agent_configs.get(fallback_agent, {})
        if fallback_config.get('enabled', False) and fallback_agent not in matched_agents:
            matched_agents.append(fallback_agent)

    return matched_agents

def get_records_from_n8n_response(result_data):
    all_records = []
    if isinstance(result_data, list) and len(result_data) > 0:
        for item in result_data:
            if isinstance(item, dict):
                if 'json' in item:
                    json_data = item['json']
                    if isinstance(json_data, list):
                        all_records.extend(json_data)
                    elif isinstance(json_data, dict):
                        if 'sources' in json_data:
                            sources_data = json_data['sources']
                            if isinstance(sources_data, list):
                                all_records.extend(sources_data)
                            elif isinstance(sources_data, dict):
                                sources_list = list(sources_data.values())
                                all_records.extend(sources_list)
                        else:
                            all_records.append(json_data)
                else:
                    all_records.append(item)
            elif isinstance(item, list):
                all_records.extend(item)
    elif isinstance(result_data, dict):
        if 'sources' in result_data:
            sources_data = result_data['sources']
            if isinstance(sources_data, list):
                all_records.extend(sources_data)
            elif isinstance(sources_data, dict):
                sources_list = list(sources_data.values())
                all_records.extend(sources_list)
            else:
                all_records.append(sources_data)
        elif 'data' in result_data:
            all_records.extend(result_data['data'])
        elif 'results' in result_data:
            all_records.extend(result_data['results'])
        else:
            extracted = False
            for value in result_data.values():
                if isinstance(value, list) and value and all(isinstance(v, dict) for v in value):
                    all_records.extend(value)
                    extracted = True
                elif isinstance(value, dict):
                    nested_values = list(value.values())
                    if nested_values and all(isinstance(v, dict) for v in nested_values):
                        all_records.extend(nested_values)
                        extracted = True
            if not extracted:
                all_records.append(result_data)
    elif isinstance(result_data, list):
        all_records.extend(result_data)
    else:
        all_records.append(result_data)
    return all_records


def parse_json_string(value):
    """
    Parse a JSON string, handling markdown code blocks and plain JSON strings.
    """
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return value
    
    # Remove markdown code blocks if present
    value = re.sub(r'```json\s*', '', value)
    value = re.sub(r'```\s*', '', value)
    value = value.strip()
    
    try:
        parsed = json.loads(value)
        return parsed
    except (json.JSONDecodeError, TypeError):
        return value

def repair_json_like_string(text: str):
    """
    Attempts to repair JSON-like strings where inner double quotes are unescaped.
    Returns a parsed dict/list or None.
    """
    candidate = text.strip()
    if not (candidate.startswith("{") and candidate.endswith("}")):
        return None

    repaired = []
    in_string = False
    i = 0
    length = len(candidate)

    while i < length:
        ch = candidate[i]

        if ch == '"':
            prev = candidate[i - 1] if i > 0 else ""
            if prev != "\\":
                if in_string:
                    # Peek ahead to determine if this should close the string
                    j = i + 1
                    while j < length and candidate[j].isspace():
                        j += 1
                    if j < length and candidate[j] in ",]}":
                        in_string = False
                        repaired.append('"')
                        i += 1
                        continue
                    else:
                        repaired.append('\\"')
                        i += 1
                        continue
                else:
                    in_string = True
                    repaired.append('"')
                    i += 1
                    continue

        repaired.append(ch)
        i += 1

    try:
        return json.loads("".join(repaired))
    except (json.JSONDecodeError, TypeError):
        return None


def expand_structured_entries(entries):
    """
    Some responses might return a single JSON string containing nested items.
    Expand those into plain entries so the UI stays consistent.
    """
    expanded = []
    for entry in entries or []:
        if isinstance(entry, dict):
            collected = []
            for key in (
                "actionable_insights",
                "recommendations",
                "insights",
                "items",
                "data",
            ):
                value = entry.get(key)
                if isinstance(value, list):
                    collected.extend(str(v) for v in value)
            if collected:
                expanded.extend(collected)
                continue

        if isinstance(entry, str):
            candidate = entry.strip()

            # Try parsing with the generic helper (handles ```json``` wrappers)
            parsed = parse_json_string(candidate)
            collected = []
            if isinstance(parsed, dict):
                for key in (
                    "actionable_insights",
                    "recommendations",
                    "insights",
                    "items",
                    "data",
                ):
                    value = parsed.get(key)
                    if isinstance(value, list):
                        collected.extend(str(v) for v in value)
                if collected:
                    expanded.extend(collected)
                    continue

            repaired = repair_json_like_string(candidate)
            if isinstance(repaired, dict):
                for key in (
                    "actionable_insights",
                    "recommendations",
                    "insights",
                    "items",
                ):
                    value = repaired.get(key)
                    if isinstance(value, list):
                        collected.extend(str(v) for v in value)
            if collected:
                expanded.extend(collected)
                continue

            # If parsing failed, fall back to splitting on newlines
            fragments = [
                frag.strip(" -•")
                for frag in re.split(r"\n+", candidate)
                if frag.strip(" -•")
            ]
            if fragments:
                expanded.extend(fragments)
                continue

        expanded.append(entry)

    return expanded

def clean_display_text(text):
    """
    Normalize text for display to keep font consistent.
    """
    cleaned = str(text).strip()
    cleaned = cleaned.replace("```json", "").replace("```", "").replace("`", "")
    cleaned = cleaned.strip('"').strip("'")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def extract_offer_rejection_payload(result_data):
    """
    Try to extract the structured payload from the Offer Rejection Agent.
    Supports both:
    - { "offer_rejection_summary": {...} }
    - [ { "offer_rejection_summary": {...} } ]
    - [ { "json": { "offer_rejection_summary": {...} } } ]
    """
    candidates = []

    if isinstance(result_data, dict):
        candidates.append(result_data)

    if isinstance(result_data, list) and result_data:
        for item in result_data:
            if isinstance(item, dict):
                candidates.append(item)
                if "json" in item and isinstance(item["json"], dict):
                    candidates.append(item["json"])

    for obj in candidates:
        if not isinstance(obj, dict):
            continue
        if "offer_rejection_summary" in obj:
            return obj.get("offer_rejection_summary")
        # Also check if it's nested directly (support both old and new field names)
        if any(
            key in obj
            for key in (
                "totalOffers",
                "totalRejected",
                "totalCandidateDeclined",
                "rejectionRate",
                "declineRate",
                "reasons",
            )
        ):
            return obj

    return None

def extract_standardized_agent_response(result_data):
    """
    Extract standardized agent response format.
    Supports:
    - { "agent_name": "...", "sections": [...] }
    - [ { "json": { "agent_name": "...", "sections": [...] } } ]
    - [ { "agent_name": "...", "sections": [...] } ]
    """
    candidates = []

    if isinstance(result_data, dict):
        candidates.append(result_data)

    if isinstance(result_data, list) and result_data:
        for item in result_data:
            if isinstance(item, dict):
                candidates.append(item)
                if "json" in item and isinstance(item["json"], dict):
                    candidates.append(item["json"])

    for obj in candidates:
        if not isinstance(obj, dict):
            continue
        if "agent_name" in obj and "sections" in obj:
            return obj

    return None

def render_standardized_agent_response(agent_response):
    """
    Render a standardized agent response with sections.
    Each section can be: metrics, table, chart, insights, recommendations
    """
    if not agent_response:
        return False
    
    display_title = agent_response.get("display_title", "Agent Analysis")
    sections = agent_response.get("sections", [])
    
    if not sections:
        return False
    
    st.subheader(display_title)
    
    for section in sections:
        section_type = section.get("type")
        section_title = section.get("title", "")
        
        if section_type == "metrics":
            # Display metrics in columns (max 4 per row)
            metrics_data = section.get("data", {})
            if metrics_data:
                metrics_list = list(metrics_data.items())
                num_metrics = len(metrics_list)
                cols_per_row = min(4, num_metrics)
                
                for i in range(0, num_metrics, cols_per_row):
                    cols = st.columns(cols_per_row)
                    for j, (key, value) in enumerate(metrics_list[i:i+cols_per_row]):
                        with cols[j]:
                            st.metric(key, value)
        
        elif section_type == "table":
            # Display table
            rows = section.get("rows", [])
            columns = section.get("columns", [])
            
            if rows:
                if section_title:
                    st.markdown("---")
                    st.subheader(section_title)
                
                # Create DataFrame with specified columns (if provided) or use all keys
                if columns:
                    # Filter rows to only include specified columns
                    filtered_rows = []
                    for row in rows:
                        filtered_row = {col: row.get(col, "") for col in columns}
                        filtered_rows.append(filtered_row)
                    df = pd.DataFrame(filtered_rows)
                else:
                    df = pd.DataFrame(rows)
                
                st.dataframe(df, hide_index=True)
                
                # Auto-generate chart if numeric columns exist
                if len(df) > 0 and len(df) <= 20:  # Only show chart for reasonable number of rows
                    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                    if len(numeric_cols) > 0:
                        # Use first column as index, first numeric column as value
                        index_col = df.columns[0]
                        chart_col = numeric_cols[0]
                        try:
                            chart_df = df.set_index(index_col)[chart_col]
                            st.bar_chart(chart_df, use_container_width=True)
                        except Exception:
                            pass  # Skip chart if there's an error
        
        elif section_type == "insights":
            # Display insights as bullet points
            insights = expand_structured_entries(section.get("data", []))
            if insights:
                if section_title:
                    st.markdown("---")
                    st.markdown(f"### 💡 {section_title}")
                for i, insight in enumerate(insights, 1):
                    st.write(f"{i}. {clean_display_text(insight)}")
        
        elif section_type == "recommendations":
            # Display recommendations as numbered list
            recommendations = expand_structured_entries(section.get("data", []))
            if recommendations:
                if section_title:
                    st.markdown("---")
                    st.markdown(f"### 📋 {section_title}")
                for i, rec in enumerate(recommendations, 1):
                    rec_text = re.sub(r'^\d+\.\s*', '', str(rec))
                    st.write(f"{i}. {clean_display_text(rec_text)}")
    
    return True

if uploaded_files:
    for file in uploaded_files:
        # Debug: show matching process
        with st.expander(f"🔍 Debug: File matching for {file.name}", expanded=False):
            filename_lower = file.name.lower()
            st.write(f"**Filename:** {file.name} (lowercase: {filename_lower})")
            st.write(f"**Enabled agents:** {list(enabled_agents.keys())}")
            for agent_name, agent_info in enabled_agents.items():
                keywords = agent_info.get('filename_keywords', [])
                matches = [kw for kw in keywords if kw.lower() in filename_lower]
                st.write(f"- **{agent_name}**: keywords={keywords}, matches={matches}")
        
        # Get ALL matching agents (not just the first one)
        matched_agents = get_all_agents_for_file(file.name, agents, enabled_agents, default_agent)
        if not matched_agents:
            continue

        ordered_agents = []
        matched_set = set(matched_agents)
        for _, agent_list in GROUPED_AGENT_ORDER:
            for agent_key in agent_list:
                if agent_key in matched_set:
                    ordered_agents.append(agent_key)
        for agent_key in matched_agents:
            if agent_key not in ordered_agents:
                ordered_agents.append(agent_key)

        printed_group_headers = set()
        group_counters = {}

        # Process file with each matching agent
        for agent_key in ordered_agents:
            agent_config = agents.get(agent_key, {})
            if not agent_config.get('enabled', False):
                continue

            agent_info = agent_config
            webhook_path = agent_info.get('webhook_path', '')
            n8n_webhook_url = f"{base_url}{webhook_path}" if webhook_path else None
            agent_title = agent_info.get('description', agent_key)

            group_label = AGENT_GROUP_LOOKUP.get(agent_key)
            prefix = ""
            if group_label:
                if group_label not in printed_group_headers:
                    st.markdown(f"### {group_label}")
                    printed_group_headers.add(group_label)
                    group_counters[group_label] = 0
                group_counters[group_label] += 1
                prefix = f"{group_counters[group_label]}. "

            st.markdown(f"#### {prefix}{agent_title}:")

            if not n8n_webhook_url:
                st.error(f"Webhook path not set for {agent_key} in config.yaml")
                continue

            with st.spinner(f"Processing {file.name} with {agent_title}..."):
                try:
                    file.seek(0)
                    files = {'file': (file.name, file, 'text/csv')}
                    response = requests.post(n8n_webhook_url, files=files, timeout=90)
                    response.raise_for_status()
                    try:
                        result_data = response.json()
                    except ValueError:
                        st.error("Received a non-JSON response from the n8n webhook.")
                        continue

                    # Show debug if needed
                    with st.expander(f"🔍 Raw n8n response for {file.name}", expanded=False):
                        st.json(result_data)

                    # Specialized rendering for the offer rejection agent
                    offer_rejection_payload = (
                        extract_offer_rejection_payload(result_data)
                        if agent_key == "offer_rejection_agent"
                        else None
                    )

                    if offer_rejection_payload:
                        # 1. Summary Statistics
                        st.subheader("📊 Candidate Offer Declines Summary")
                        st.caption("Analyzing why candidates rejected offers (candidate-initiated declines)")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Total Offers", offer_rejection_payload.get("totalOffers", 0))
                        with col2:
                            declined = offer_rejection_payload.get("totalCandidateDeclined", 0)
                            st.metric("Candidate Declined", declined, 
                                     delta=f"-{declined}")
                        with col3:
                            st.metric("Accepted", offer_rejection_payload.get("totalAccepted", 0),
                                     delta=f"+{offer_rejection_payload.get('totalAccepted', 0)}")
                        with col4:
                            st.metric("Decline Rate", offer_rejection_payload.get("declineRate", "0%"))
                        
                        # Delay Analysis
                        st.markdown("---")
                        st.subheader("⏱️ Delay Analysis")
                        delay_col1, delay_col2, delay_col3 = st.columns(3)
                        with delay_col1:
                            st.metric("Avg Days (Declined)", 
                                     offer_rejection_payload.get("avgDaysDeclined", "0"))
                        with delay_col2:
                            st.metric("Avg Days (Accepted)", 
                                     offer_rejection_payload.get("avgDaysAccepted", "0"))
                        with delay_col3:
                            diff = float(offer_rejection_payload.get("delayDifference", "0"))
                            st.metric("Difference", 
                                     f"{diff:.1f} days",
                                     delta=f"{diff:.1f} days" if diff != 0 else None,
                                     delta_color="inverse" if diff > 0 else "normal")
                        
                        # 2. Decline Reasons Breakdown
                        reasons_rows = offer_rejection_payload.get("reasons") or []
                        if reasons_rows:
                            st.markdown("---")
                            st.subheader("🔍 Top Decline Reasons")
                            reasons_df = pd.DataFrame(reasons_rows)
                            # Rename columns for better display
                            if "reason" in reasons_df.columns:
                                reasons_df = reasons_df.rename(columns={
                                    "reason": "Reason",
                                    "count": "Count",
                                    "percentage": "% of Declines",
                                    "avgDaysInPipeline": "Avg Days in Pipeline",
                                    "avgSalaryExpectation": "Avg Salary Expectation",
                                    "topSource": "Top Source"
                                })
                            st.dataframe(reasons_df, hide_index=True)
                            
                            # Chart for reasons
                            if "Count" in reasons_df.columns and "Reason" in reasons_df.columns:
                                chart_df = reasons_df.set_index("Reason")["Count"]
                                st.bar_chart(chart_df, use_container_width=True)
                        
                        # 3. Recent Declines (Source analysis removed - handled by sourcing_quality_agent)
                        recent_rows = offer_rejection_payload.get("recent_declines") or []
                        if recent_rows:
                            st.markdown("---")
                            st.subheader("📋 Recent Candidate Declines (Last 10)")
                            recent_df = pd.DataFrame(recent_rows)
                            # Rename columns for better display
                            if "candidate" in recent_df.columns:
                                recent_df = recent_df.rename(columns={
                                    "candidate": "Candidate",
                                    "date": "Date",
                                    "reason": "Reason",
                                    "daysInPipeline": "Days in Pipeline",
                                    "source": "Source"
                                })
                            st.dataframe(recent_df, hide_index=True)
                        
                        continue

                    # Check for standardized agent response format
                    standardized_response = extract_standardized_agent_response(result_data)
                    if standardized_response:
                        if render_standardized_agent_response(standardized_response):
                            continue

                    # Generic handling for other agents (fallback)
                    all_records = get_records_from_n8n_response(result_data)
                    if not all_records:
                        st.warning(f"No data returned for this agent ({file.name}).")
                        continue

                    try:
                        agent_df = pd.DataFrame(all_records)
                    except Exception as df_error:
                        st.error(f"Unable to display data for {file.name}: {df_error}")
                        continue

                    if agent_df.empty:
                        st.warning(f"No rows to display for {file.name}.")
                        continue

                    st.dataframe(agent_df, hide_index=True)

                except Exception as e:
                    st.error(f"Error processing file {file.name} with {agent_key}: {e}")
else:
    st.info("Please upload your CSV files to begin multi-agent analysis.")
