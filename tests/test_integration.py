"""Integration tests using sample data files."""
import pytest
import pandas as pd
from io import BytesIO

from tests.test_helpers import (
    get_matching_agents_for_file,
    get_records_from_n8n_response,
    parse_json_string,
    clean_display_text,
    ui_module,
)


class TestIntegrationWithSampleData:
    """Integration tests using actual sample CSV files."""

    def test_sample_summary_csv_structure(self, sample_summary_csv):
        """Test that sample Summary.csv can be read and has expected structure."""
        if sample_summary_csv is None:
            pytest.skip("Sample Summary.csv not found")
        
        sample_summary_csv.seek(0)
        df = pd.read_csv(sample_summary_csv)
        assert not df.empty
        # Check for common columns that might exist
        assert len(df.columns) > 0

    def test_sample_funnel_csv_structure(self, sample_funnel_csv):
        """Test that sample Funnel.csv can be read and has expected structure."""
        if sample_funnel_csv is None:
            pytest.skip("Sample Funnel.csv not found")
        
        sample_funnel_csv.seek(0)
        df = pd.read_csv(sample_funnel_csv)
        assert not df.empty
        assert len(df.columns) > 0

    def test_sample_feedback_csv_structure(self, sample_feedback_csv):
        """Test that sample Feedback.csv can be read and has expected structure."""
        if sample_feedback_csv is None:
            pytest.skip("Sample Feedback.csv not found")
        
        sample_feedback_csv.seek(0)
        df = pd.read_csv(sample_feedback_csv)
        assert not df.empty
        assert len(df.columns) > 0

    def test_file_matching_with_sample_names(self, sample_config, monkeypatch):
        """Test file matching logic with actual sample file names."""
        monkeypatch.setattr(ui_module, "ENABLED_AGENTS", sample_config["n8n"]["agents"])
        monkeypatch.setattr(ui_module, "AGENTS_CONFIG", sample_config["n8n"]["agents"])
        monkeypatch.setattr(ui_module, "DEFAULT_AGENT", "none")
        
        # Test actual file names from sample_inputs
        assert len(get_matching_agents_for_file("Summary.csv")) > 0
        assert len(get_matching_agents_for_file("Funnel.csv")) > 0
        assert len(get_matching_agents_for_file("Feedback.csv")) > 0

    def test_parse_complex_n8n_response(self):
        """Test parsing a complex n8n response structure."""
        # Simulate a complex response that might come from n8n
        complex_response = {
            "json": {
                "agent_name": "test_agent",
                "sections": [
                    {
                        "type": "metrics",
                        "data": {"Total": 100},
                    }
                ],
            }
        }
        records = get_records_from_n8n_response([complex_response])
        assert len(records) == 1
        assert records[0].get("agent_name") == "test_agent"

    def test_parse_llm_output_with_markdown(self):
        """Test parsing LLM output that includes markdown formatting."""
        llm_output = '```json\n{"actionable_insights": ["Insight 1"], "recommendations": ["Rec 1"]}\n```'
        parsed = parse_json_string(llm_output)
        assert isinstance(parsed, dict)
        assert "actionable_insights" in parsed
        assert "recommendations" in parsed

    def test_clean_llm_output_text(self):
        """Test cleaning LLM output text for display."""
        messy_text = '```json\n"  This   has   extra   spaces  "\n```'
        cleaned = clean_display_text(messy_text)
        assert "```" not in cleaned
        assert "  " not in cleaned  # No double spaces

    def test_end_to_end_response_processing(self, mock_standardized_response):
        """Test end-to-end processing of a standardized response."""
        # Simulate extracting from n8n response
        n8n_response = [{"json": mock_standardized_response}]
        records = get_records_from_n8n_response(n8n_response)
        assert len(records) == 1
        assert records[0].get("agent_name") == "test_agent"
        assert len(records[0].get("sections", [])) > 0

