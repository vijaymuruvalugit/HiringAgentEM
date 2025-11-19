"""Helper module to import the frontend module with hyphenated name."""
import sys
import importlib.util
from pathlib import Path

# Load the hiring-agent-ui module (with hyphen in filename)
frontend_dir = Path(__file__).parent.parent / "frontend"
module_path = frontend_dir / "hiring-agent-ui.py"

spec = importlib.util.spec_from_file_location("hiring_agent_ui", module_path)
hiring_agent_ui = importlib.util.module_from_spec(spec)
sys.modules["hiring_agent_ui"] = hiring_agent_ui
spec.loader.exec_module(hiring_agent_ui)

# Export commonly used functions and constants
from hiring_agent_ui import (
    load_config,
    normalized,
    match_by_keywords,
    get_matching_agents_for_file,
    parse_json_string,
    repair_json_like_string,
    get_records_from_n8n_response,
    clean_display_text,
    call_n8n_agent,
    render_standardized_agent_response,
    sanitize_dataframe_for_display,
    expand_structured_entries,
    process_uploaded_files,
    format_consolidated_insights,
)

# Also export module-level constants that tests might need to mock
import hiring_agent_ui as ui_module

