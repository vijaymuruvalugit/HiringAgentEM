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

# Agent grouping structure: (group_label, [(agent_key, agent_display_name), ...])
GROUPED_AGENT_ORDER = [
    ("1. Hiring Tracker Agents", [
        ("sourcing_quality_agent", "A. Sourcing Quality Agent"),
        ("rejection_pattern_agent", "B. Rejection Pattern Agent"),
        ("panel_load_balancer", "C. Panel Load Balancer"),
        ("open_roles_agent", "D. Open Roles Agent"),
    ]),
    ("2. Offer & Funnel Agents", [
        ("offer_rejection_agent", "A. Offer Rejection Insight Agent"),
        ("pipeline_health_agent", "B. Pipeline Health Agent"),
    ]),
]

AGENT_GROUP_LOOKUP = {}
AGENT_DISPLAY_NAMES = {}
for group_label, agent_list in GROUPED_AGENT_ORDER:
    for agent_key, display_name in agent_list:
        AGENT_GROUP_LOOKUP[agent_key] = group_label
        AGENT_DISPLAY_NAMES[agent_key] = display_name


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
    # Handle dict/object case - extract meaningful content
    if isinstance(text, dict):
        # Try to extract text from common keys
        for key in ("text", "content", "message", "value", "item"):
            if key in text and isinstance(text[key], str):
                return clean_display_text(text[key])
        # If it's a single-key dict with a string value, use that
        if len(text) == 1:
            val = list(text.values())[0]
            if isinstance(val, str):
                return clean_display_text(val)
        # Otherwise, try to convert to JSON string
        try:
            return json.dumps(text, ensure_ascii=False)
        except Exception:
            return str(text)
    
    # Handle list case
    if isinstance(text, list):
        # If it's a list with one string item, extract it
        if len(text) == 1 and isinstance(text[0], str):
            return clean_display_text(text[0])
        # Otherwise convert to JSON
        try:
            return json.dumps(text, ensure_ascii=False)
        except Exception:
            return str(text)
    
    # Handle string case
    s = str(text)
    # Remove [object Object] if present (JavaScript artifact)
    if "[object Object]" in s:
        # Try to parse if it looks like JSON
        return s
    s = s.replace("```json", "").replace("```", "")
    s = s.strip('"').strip("'")
    s = re.sub(r"\s+", " ", s)
    return s


def _format_table_cell(value: Any) -> Any:
    """
    Ensure complex objects render cleanly inside tables instead of [object Object].
    """
    if isinstance(value, (dict, list, tuple)):
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return str(value)
    if isinstance(value, set):
        try:
            return json.dumps(sorted(value), ensure_ascii=False)
        except Exception:
            return str(value)
    return value


def sanitize_dataframe_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert nested structures to readable strings for Streamlit tables.
    """
    if df.empty:
        return df
    return df.applymap(_format_table_cell)


def expand_structured_entries(items: Any) -> List[Any]:
    """
    Expand structured insight/recommendation entries into a flat list.
    Handles strings, JSON blobs, dicts, and nested lists.
    """
    if not items:
        return []

    expanded_items: List[Any] = []

    # Normalize input: convert single string or dict to list for uniform processing
    if isinstance(items, str):
        entries = [items]
    elif isinstance(items, dict):
        # If items is a dict (e.g., {"actionable_insights": [...], "recommendations": [...]}),
        # treat it as a single entry to extract from
        entries = [items]
    elif isinstance(items, list):
        entries = items
    else:
        entries = [items]

    for it in entries:
        if isinstance(it, str):
            it_cleaned = it.strip()
            # Remove markdown code fences if present
            it_cleaned = re.sub(r"^```(?:json)?\s*", "", it_cleaned, flags=re.IGNORECASE)
            it_cleaned = re.sub(r"\s*```$", "", it_cleaned, flags=re.IGNORECASE)
            it_cleaned = it_cleaned.strip()

            if it_cleaned.startswith("{") and it_cleaned.endswith("}"):
                try:
                    parsed = json.loads(it_cleaned)
                    if isinstance(parsed, dict):
                        extracted = False
                        for key in ("actionable_insights", "recommendations", "insights"):
                            if key in parsed:
                                val = parsed[key]
                                expanded_items.extend(val if isinstance(val, list) else [str(val)])
                                extracted = True
                        if not extracted:
                            for _, val in parsed.items():
                                if isinstance(val, list):
                                    expanded_items.extend(val)
                                elif isinstance(val, str) and val.strip():
                                    expanded_items.append(val)
                    elif isinstance(parsed, list):
                        expanded_items.extend(parsed)
                    else:
                        expanded_items.append(it)
                except (json.JSONDecodeError, ValueError):
                    expanded_items.append(it)
            else:
                expanded_items.append(it)
        elif isinstance(it, dict):
            extracted = False
            # Check for common keys that contain lists of insights/recommendations
            for key in ("actionable_insights", "recommendations", "insights", "data", "items", "text", "content", "message"):
                if key in it:
                    val = it[key]
                    if isinstance(val, list):
                        expanded_items.extend(val)
                        extracted = True
                    elif isinstance(val, str) and val.strip():
                        # If value is a string, try to parse it as JSON
                        try:
                            parsed_val = json.loads(val)
                            if isinstance(parsed_val, list):
                                expanded_items.extend(parsed_val)
                            elif isinstance(parsed_val, dict):
                                # Recursively extract from nested dict
                                nested = expand_structured_entries(parsed_val)
                                if nested:
                                    expanded_items.extend(nested)
                            else:
                                expanded_items.append(val)
                        except (json.JSONDecodeError, ValueError):
                            expanded_items.append(val)
                        extracted = True
                    elif isinstance(val, dict):
                        # Recursively extract from nested dict
                        nested = expand_structured_entries(val)
                        if nested:
                            expanded_items.extend(nested)
                            extracted = True
            if not extracted:
                # If no recognized keys, try to extract all list values from the dict
                for _, val in it.items():
                    if isinstance(val, list):
                        expanded_items.extend(val)
                        extracted = True
                    elif isinstance(val, str) and val.strip():
                        expanded_items.append(val)
                        extracted = True
                if not extracted:
                    # Last resort: if dict has a single string value, use it
                    if len(it) == 1:
                        single_val = list(it.values())[0]
                        if isinstance(single_val, str):
                            expanded_items.append(single_val)
                        else:
                            # Convert dict to JSON string for display
                            try:
                                expanded_items.append(json.dumps(it, ensure_ascii=False))
                            except Exception:
                                expanded_items.append(str(it))
                    else:
                        # Convert dict to JSON string for display
                        try:
                            expanded_items.append(json.dumps(it, ensure_ascii=False))
                        except Exception:
                            expanded_items.append(str(it))
        elif isinstance(it, list):
            expanded_items.extend(it)
        else:
            expanded_items.append(it)

    return expanded_items

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
**What this app does:** Accepts hiring tracker CSVs (Summary, Feedback, Funnel, OpenRoles, etc.) → calls specialised agents in n8n → renders metrics, tables, charts and prioritized recommendations for Engineering Managers.
"""
    )

with col_mid:
    st.header("Upload data")
    uploaded_files = st.file_uploader("Upload agent CSVs (Summary, Feedback, Funnel, OpenRoles, etc.)", type="csv", accept_multiple_files=True)
    st.caption("Tip: name files with keywords like 'summary', 'feedback', 'funnel', 'openroles', 'roles' to auto-match agents")

with col_right:
    st.header("Quick actions")
    run_all = st.button("▶️ Run agents for uploaded files")

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

def call_n8n_agent(agent_key: str, file_obj, agents_config: Optional[Dict[str, Any]] = None, base_url: Optional[str] = None) -> Optional[Any]:
    """
    Call n8n agent webhook with uploaded file.
    
    Args:
        agent_key: Agent identifier
        file_obj: File object to upload
        agents_config: Agent configuration (defaults to global AGENTS_CONFIG)
        base_url: n8n base URL (defaults to global BASE_URL)
        
    Returns:
        Agent response or None on error
    """
    agents_config = agents_config or AGENTS_CONFIG
    base_url = base_url or BASE_URL
    
    agent_conf = agents_config.get(agent_key, {})
    webhook_path = agent_conf.get("webhook_path") or agent_conf.get("endpoint")
    if not webhook_path:
        st.error(f"Agent {agent_key} does not define a webhook_path/endpoint in config.")
        return None
    url = f"{base_url}{webhook_path}" if webhook_path.startswith("/") else f"{base_url}/{webhook_path}"
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
                num_cols = min(4, len(data))
                if num_cols > 0:
                    cols = st.columns(num_cols)
                    for i, (k, v) in enumerate(data.items()):
                        with cols[i % num_cols]:
                            st.metric(k, v)
        elif t == "table":
            rows = section.get("rows") or []
            cols = section.get("columns") or []
            if rows:
                df = pd.DataFrame(rows)
                # Store original df before column filtering for chart detection
                df_original = df.copy()
                df = sanitize_dataframe_for_display(df)
                if cols:
                    df = df[cols] if all(c in df.columns for c in cols) else df
                st.table(df)
                if not df.empty:
                    # Special handling: if RejectionRate column exists, always use it for chart
                    # This ensures sourcing quality agent shows rejection rate, not candidate count
                    # Check both original and filtered df for RejectionRate (case-insensitive)
                    rejection_rate_col = None
                    for col in df_original.columns:
                        if "rejection" in col.lower() and "rate" in col.lower():
                            rejection_rate_col = col
                            break
                    
                    if rejection_rate_col:
                        # Convert RejectionRate from "XX.X%" string to numeric
                        df_chart = df_original.copy()
                        # Handle percentage string format
                        if df_chart[rejection_rate_col].dtype == 'object':
                            # Remove % and convert to float
                            df_chart["RejectionRateNum"] = df_chart[rejection_rate_col].astype(str).str.replace("%", "").str.strip().astype(float)
                        else:
                            df_chart["RejectionRateNum"] = df_chart[rejection_rate_col].astype(float)
                        # Use first column (usually Source) as index, RejectionRateNum as value
                        index_col = df_chart.columns[0]
                        chart_data = df_chart.set_index(index_col)["RejectionRateNum"]
                        st.bar_chart(chart_data)
                    else:
                        # Default behavior: use first numeric column
                        num_cols = df.select_dtypes(include=["number"]).columns.tolist()
                        if num_cols:
                            st.bar_chart(df.set_index(df.columns[0])[num_cols[0]])
        elif t in ("insights", "recommendations"):
            items = section.get("data") or section.get("items") or []
            if items:
                if title:
                    st.markdown(f"**{title}**")
                
                # Pre-process: handle various input formats
                processed_items = []
                
                # Case 1: items is a single JSON string
                if isinstance(items, str):
                    # Remove markdown code fences if present
                    items_cleaned = items.strip()
                    items_cleaned = re.sub(r"^```(?:json)?\s*", "", items_cleaned, flags=re.IGNORECASE)
                    items_cleaned = re.sub(r"\s*```$", "", items_cleaned, flags=re.IGNORECASE)
                    items_cleaned = items_cleaned.strip()
                    
                    try:
                        parsed = json.loads(items_cleaned)
                        if isinstance(parsed, dict):
                            # Extract based on section type
                            if t == "insights":
                                processed_items = parsed.get("actionable_insights") or parsed.get("insights") or []
                            elif t == "recommendations":
                                processed_items = parsed.get("recommendations") or []
                            # If not found, try to extract any list values
                            if not processed_items:
                                for key, val in parsed.items():
                                    if isinstance(val, list):
                                        processed_items.extend(val)
                                    elif isinstance(val, str):
                                        processed_items.append(val)
                        elif isinstance(parsed, list):
                            processed_items = parsed
                        else:
                            processed_items = [items]
                    except (json.JSONDecodeError, ValueError):
                        # If parsing fails, check if it's a JSON-like string we can extract from
                        # Try to find JSON object in the string
                        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', items_cleaned)
                        if json_match:
                            try:
                                parsed = json.loads(json_match.group(0))
                                if isinstance(parsed, dict):
                                    if t == "insights":
                                        processed_items = parsed.get("actionable_insights") or parsed.get("insights") or []
                                    elif t == "recommendations":
                                        processed_items = parsed.get("recommendations") or []
                            except Exception:
                                processed_items = [items]
                        else:
                            processed_items = [items]
                # Case 2: items is a list
                elif isinstance(items, list):
                    # Check if list contains JSON strings
                    for item in items:
                        if isinstance(item, str) and item.strip().startswith("{"):
                            # Try to parse as JSON
                            try:
                                item_cleaned = item.strip()
                                item_cleaned = re.sub(r"^```(?:json)?\s*", "", item_cleaned, flags=re.IGNORECASE)
                                item_cleaned = re.sub(r"\s*```$", "", item_cleaned, flags=re.IGNORECASE)
                                parsed = json.loads(item_cleaned)
                                if isinstance(parsed, dict):
                                    # Extract based on section type
                                    if t == "insights":
                                        extracted = parsed.get("actionable_insights") or parsed.get("insights") or []
                                    elif t == "recommendations":
                                        extracted = parsed.get("recommendations") or []
                                    if extracted:
                                        processed_items.extend(extracted if isinstance(extracted, list) else [extracted])
                                    else:
                                        # If no specific key found, extract all list values
                                        for val in parsed.values():
                                            if isinstance(val, list):
                                                processed_items.extend(val)
                                elif isinstance(parsed, list):
                                    processed_items.extend(parsed)
                                else:
                                    processed_items.append(item)
                            except (json.JSONDecodeError, ValueError):
                                processed_items.append(item)
                        else:
                            processed_items.append(item)
                # Case 3: items is a dict
                elif isinstance(items, dict):
                    if t == "insights":
                        processed_items = items.get("actionable_insights") or items.get("insights") or []
                    elif t == "recommendations":
                        processed_items = items.get("recommendations") or []
                    if not processed_items:
                        # Extract any list values
                        for val in items.values():
                            if isinstance(val, list):
                                processed_items.extend(val)
                else:
                    processed_items = [items]
                
                # Now expand and display
                if processed_items:
                    expanded_items = expand_structured_entries(processed_items)
                    if expanded_items:
                        for idx, it in enumerate(expanded_items, 1):
                            # Skip if it's still a dict/object that couldn't be extracted
                            if isinstance(it, dict) and not any(k in it for k in ("text", "content", "message", "value")):
                                # Try one more time to extract or convert
                                try:
                                    it = json.dumps(it, ensure_ascii=False)
                                except Exception:
                                    it = str(it)
                            cleaned = clean_display_text(it)
                            # Skip if it's just "[object Object]" or empty
                            if cleaned and cleaned.strip() and cleaned.strip() != "[object Object]":
                                # Check if it's a full JSON object string (starts with { and has both actionable_insights and recommendations)
                                cleaned_stripped = cleaned.strip()
                                if cleaned_stripped.startswith("{") and ("actionable_insights" in cleaned_stripped or "recommendations" in cleaned_stripped):
                                    # Try to extract just the relevant part
                                    try:
                                        # Remove markdown fences if present
                                        to_parse = cleaned_stripped
                                        to_parse = re.sub(r"^```(?:json)?\s*", "", to_parse, flags=re.IGNORECASE)
                                        to_parse = re.sub(r"\s*```$", "", to_parse, flags=re.IGNORECASE)
                                        parsed_again = json.loads(to_parse)
                                        if isinstance(parsed_again, dict):
                                            if t == "insights":
                                                relevant = parsed_again.get("actionable_insights") or parsed_again.get("insights") or []
                                            elif t == "recommendations":
                                                relevant = parsed_again.get("recommendations") or []
                                            if relevant:
                                                # Display each item in the relevant array
                                                for r_idx, r in enumerate(relevant if isinstance(relevant, list) else [relevant], start=idx):
                                                    r_cleaned = clean_display_text(r)
                                                    if r_cleaned and r_cleaned.strip() and r_cleaned.strip() != "[object Object]":
                                                        # Don't show if it's still a JSON object
                                                        if not (r_cleaned.strip().startswith("{") and ("actionable_insights" in r_cleaned or "recommendations" in r_cleaned)):
                                                            st.write(f"{r_idx}. {r_cleaned}")
                                                # Skip the original item since we've displayed the extracted items
                                                continue
                                    except (json.JSONDecodeError, ValueError, Exception):
                                        # If parsing fails, check if we can extract JSON from the string
                                        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', cleaned_stripped)
                                        if json_match:
                                            try:
                                                parsed_match = json.loads(json_match.group(0))
                                                if isinstance(parsed_match, dict):
                                                    if t == "insights":
                                                        relevant = parsed_match.get("actionable_insights") or parsed_match.get("insights") or []
                                                    elif t == "recommendations":
                                                        relevant = parsed_match.get("recommendations") or []
                                                    if relevant:
                                                        for r_idx, r in enumerate(relevant if isinstance(relevant, list) else [relevant], start=idx):
                                                            r_cleaned = clean_display_text(r)
                                                            if r_cleaned and r_cleaned.strip() and r_cleaned.strip() != "[object Object]":
                                                                if not (r_cleaned.strip().startswith("{") and ("actionable_insights" in r_cleaned or "recommendations" in r_cleaned)):
                                                                    st.write(f"{r_idx}. {r_cleaned}")
                                                        continue
                                            except Exception:
                                                pass
                                        # If all parsing fails, skip this item (it's a full JSON object we can't extract from)
                                        continue
                                # If it's not a full JSON object, display it normally
                                st.write(f"{idx}. {cleaned}")
                    else:
                        # Fallback: show raw items if expansion failed
                        for idx, it in enumerate(processed_items, 1):
                            cleaned = clean_display_text(it)
                            if cleaned and cleaned.strip() and cleaned.strip() != "[object Object]":
                                st.write(f"{idx}. {cleaned}")
                else:
                    # Last resort: try original items
                    expanded_items = expand_structured_entries(items)
                    if expanded_items:
                        for idx, it in enumerate(expanded_items, 1):
                            cleaned = clean_display_text(it)
                            if cleaned and cleaned.strip() and cleaned.strip() != "[object Object]":
                                st.write(f"{idx}. {cleaned}")
        else:
            # Fallback — display raw
            st.write(section)
    return True

# -----------------------------
# Main processing: run agents and render
# -----------------------------

def process_uploaded_files(
    uploaded_files: List[Any],
    run_all: bool,
    agents_config: Dict[str, Any],
    base_url: str,
) -> List[str]:
    """
    Process uploaded files through matching agents and return consolidated recommendations.
    
    Args:
        uploaded_files: List of uploaded file objects
        run_all: Whether to process files
        agents_config: Agent configuration dictionary
        base_url: n8n base URL
        
    Returns:
        List of consolidated recommendations
    """
    consolidated_recs: List[str] = []
    
    if not (uploaded_files and run_all):
        return consolidated_recs
    
    # Helper function to get agent order for sorting
    def get_agent_order(agent_key):
        """Get the order of agent within its group."""
        group_label = AGENT_GROUP_LOOKUP.get(agent_key)
        if not group_label:
            return (999, 999)  # Put unknown agents at the end
        
        # Find group index
        group_idx = next((i for i, (gl, _) in enumerate(GROUPED_AGENT_ORDER) if gl == group_label), 999)
        
        # Find agent index within group
        agent_list = next((al for gl, al in GROUPED_AGENT_ORDER if gl == group_label), [])
        agent_idx = next((i for i, (ak, _) in enumerate(agent_list) if ak == agent_key), 999)
        
        return (group_idx, agent_idx)
    
    # Step 1: Collect all file-agent pairs across all files
    file_agent_pairs = []
    for uf in uploaded_files:
        matching_agents = get_matching_agents_for_file(uf.name)
        for agent_key in matching_agents:
            if agent_key in agents_config:  # Only include valid agents
                file_agent_pairs.append((uf, agent_key))
    
    # Step 2: Sort all pairs globally by agent order (group, then position)
    file_agent_pairs.sort(key=lambda x: get_agent_order(x[1]))
    
    # Step 3: Process in sorted order, showing group headers only once
    displayed_groups = set()
    current_file_name = None
    
    for uf, agent_key in file_agent_pairs:
        # Show file header when file changes
        if uf.name != current_file_name:
            st.markdown(f"### 🔁 Processing file: `{uf.name}`")
            current_file_name = uf.name
        
        # Use display name from GROUPED_AGENT_ORDER if available, otherwise use description
        agent_title = AGENT_DISPLAY_NAMES.get(agent_key) or agents_config[agent_key].get("description", agent_key)
        
        # Show group header if this is the first agent in this group (globally)
        group_label = AGENT_GROUP_LOOKUP.get(agent_key)
        if group_label and group_label not in displayed_groups:
            st.markdown(f"### {group_label}")
            displayed_groups.add(group_label)
        
        st.markdown(f"#### {agent_title}")

        with st.spinner(f"Calling agent `{agent_key}`..."):
            resp = call_n8n_agent(agent_key, uf, agents_config=agents_config, base_url=base_url)
        if resp is None:
            st.error("No response returned from agent.")
            continue
        if isinstance(resp, str):
            resp_str = resp.strip()
            parsed = parse_json_string(resp_str) or repair_json_like_string(resp_str)
            if parsed is None:
                try:
                    parsed = json.loads(resp_str)
                except Exception:
                    parsed = None
            if parsed is not None:
                resp = parsed
        if isinstance(resp, list) and resp and all(isinstance(item, dict) and item.get("type") for item in resp):
            resp = {
                "agent_name": agent_key,
                "display_title": AGENT_DISPLAY_NAMES.get(agent_key) or agents_config[agent_key].get("description", agent_key),
                "sections": resp,
            }
        if isinstance(resp, dict) and isinstance(resp.get("sections"), str):
            sections_raw = resp["sections"].strip()
            # Handle escaped quotes ("" -> ")
            sections_raw = sections_raw.replace('""', '"')
            # Remove surrounding quotes if present
            if sections_raw.startswith('"') and sections_raw.endswith('"'):
                sections_raw = sections_raw[1:-1]
            sections_parsed = None
            # Try multiple parsing strategies
            for parser in [parse_json_string, repair_json_like_string]:
                try:
                    parsed = parser(sections_raw)
                    if parsed is not None and isinstance(parsed, list):
                        sections_parsed = parsed
                        break
                except Exception:
                    continue
            # Fallback to direct json.loads
            if sections_parsed is None:
                try:
                    sections_parsed = json.loads(sections_raw)
                except Exception:
                    # Try unescaping and parsing again
                    try:
                        sections_raw_unescaped = sections_raw.encode().decode('unicode_escape')
                        sections_parsed = json.loads(sections_raw_unescaped)
                    except Exception:
                        sections_parsed = None
            if isinstance(sections_parsed, list):
                resp["sections"] = sections_parsed

        # Try standardized response
        std = None
        # Check if response is standardized (must have agent_name and sections as a list)
        if isinstance(resp, dict) and resp.get("agent_name"):
            sections = resp.get("sections")
            # If sections is a list, we're good
            if isinstance(sections, list):
                std = resp
            # If sections is a string, we already parsed it above, so check again
            elif isinstance(sections, str):
                # This shouldn't happen if parsing worked, but double-check
                pass
        else:
            # extract records
            records = get_records_from_n8n_response(resp)
            if len(records) == 1 and isinstance(records[0], dict) and records[0].get("agent_name"):
                std = records[0]

        if std:
            # Final check: ensure sections is a list before rendering
            if isinstance(std.get("sections"), list):
                rendered = render_standardized_agent_response(std)
                # collect recommendations from rendered response
                for s in std.get("sections", []):
                    if s.get("type") == "recommendations" or s.get("type") == "insights":
                        items = s.get("data") or s.get("items") or []
                        for it in items:
                            consolidated_recs.append(clean_display_text(it))
                continue
            else:
                # Sections parsing failed, fall through to legacy handling
                std = None

        # fallback: show DataFrame table and capture text fields as recommendations
        # Skip if this looks like a standardized response (even if parsing failed)
        # We don't want to show agent_name/display_title/sections as a table
        if isinstance(resp, dict) and resp.get("agent_name"):
            # This is a standardized response format - don't show as raw table
            # If we got here, sections parsing failed, so show helpful error
            sections = resp.get("sections")
            if isinstance(sections, str):
                st.error(f"Failed to parse sections JSON string for agent {resp.get('agent_name')}. Please check the n8n workflow output format.")
            else:
                st.warning(f"Agent {resp.get('agent_name')} returned invalid response format. Expected sections to be a list.")
            continue
        
        records = get_records_from_n8n_response(resp)
        if records:
            try:
                df = pd.DataFrame(records)
                # Skip if DataFrame looks like a standardized response structure
                # Check if it has agent_name and sections columns (standardized response format)
                if "agent_name" in df.columns or ("sections" in df.columns and "display_title" in df.columns):
                    st.warning("Received standardized response format but failed to parse. Check n8n workflow output.")
                    # Try to show what we received for debugging
                    with st.expander("🔍 Debug: Raw response structure"):
                        st.json(resp)
                    continue
                df_original = df.copy()
                df_display = sanitize_dataframe_for_display(df)
                st.dataframe(df_display, use_container_width=True)
                
                # Special handling for legacy sourcing quality agent: chart by RejectionRate
                if not df_original.empty:
                    # Check for RejectionRate column (case-insensitive)
                    rejection_rate_col = None
                    for col in df_original.columns:
                        if "rejection" in col.lower() and "rate" in col.lower():
                            rejection_rate_col = col
                            break
                    
                    if rejection_rate_col:
                        # Convert RejectionRate from "XX.X%" string to numeric
                        df_chart = df_original.copy()
                        if df_chart[rejection_rate_col].dtype == 'object':
                            df_chart["RejectionRateNum"] = df_chart[rejection_rate_col].astype(str).str.replace("%", "").str.strip().astype(float)
                        else:
                            df_chart["RejectionRateNum"] = df_chart[rejection_rate_col].astype(float)
                        # Use first column (usually Source) as index, RejectionRateNum as value
                        index_col = df_chart.columns[0]
                        chart_data = df_chart.set_index(index_col)["RejectionRateNum"]
                        st.bar_chart(chart_data)
                    else:
                        # Default: chart first numeric column
                        num_cols = df.select_dtypes(include=["number"]).columns.tolist()
                        if num_cols:
                            st.bar_chart(df.set_index(df.columns[0])[num_cols[0]])
                
                # heuristics: look for columns named 'recommendation' or 'action'
                for col in df.columns:
                    if re.search(r"recommend|action|insight", col, re.I):
                        vals = df[col].dropna().astype(str).tolist()
                        for v in vals:
                            consolidated_recs.append(clean_display_text(v))
            except Exception as e:
                st.write(records)
        else:
            st.write(resp)
    
    return consolidated_recs


def format_consolidated_insights(consolidated_recs: List[str]) -> List[str]:
    """
    Format and deduplicate consolidated recommendations.
    
    Args:
        consolidated_recs: List of recommendation strings
        
    Returns:
        Deduplicated list of recommendations
    """
    if not consolidated_recs:
        return []
    
    # De-duplicate while preserving order
    seen = set()
    deduped = []
    for r in consolidated_recs:
        if r not in seen:
            seen.add(r)
            deduped.append(r)
    
    return deduped


CONSOLIDATED_RECS: List[str] = []

if uploaded_files and run_all:
    CONSOLIDATED_RECS = process_uploaded_files(
        uploaded_files=uploaded_files,
        run_all=run_all,
        agents_config=AGENTS_CONFIG,
        base_url=BASE_URL,
    )

# -----------------------------
# Consolidated Insights Panel
# -----------------------------
st.markdown("---")
st.header("📋 Consolidated Insights & Recommendations")
deduped = format_consolidated_insights(CONSOLIDATED_RECS)
if deduped:
    for i, r in enumerate(deduped, 1):
        st.write(f"{i}. {r}")
    st.download_button("Download recommendations (TXT)", "\n".join(deduped), file_name="recommendations.txt")
else:
    st.info("No recommendations collected yet. Run agents on uploaded files to generate insights.")


# End of file
