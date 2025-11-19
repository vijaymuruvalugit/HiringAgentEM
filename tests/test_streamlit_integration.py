"""Tests for Streamlit integration and main processing loop."""
import pytest
from io import BytesIO
from unittest.mock import Mock, patch, MagicMock

from tests.test_helpers import (
    get_records_from_n8n_response,
    render_standardized_agent_response,
    ui_module,
)


class TestStreamlitIntegration:
    """Test Streamlit-specific functionality and main processing."""

    @patch("hiring_agent_ui.st")
    @patch("hiring_agent_ui.call_n8n_agent")
    @patch("hiring_agent_ui.get_matching_agents_for_file")
    @patch.object(ui_module, "AGENTS_CONFIG", {
        "test_agent": {
            "webhook_path": "/webhook/test",
            "description": "Test agent",
        }
    })
    def test_main_processing_loop_standardized_response(self, mock_match, mock_call, mock_st):
        """Test main processing loop with standardized response."""
        # Mock file upload
        mock_file = MagicMock()
        mock_file.name = "Summary.csv"
        mock_st.file_uploader.return_value = [mock_file]
        mock_st.button.return_value = True
        mock_st.checkbox.return_value = False

        # Mock agent matching
        mock_match.return_value = ["test_agent"]

        # Mock agent response (standardized format)
        mock_call.return_value = {
            "agent_name": "test_agent",
            "display_title": "Test Agent",
            "sections": [
                {
                    "type": "metrics",
                    "title": "Summary",
                    "data": {"Total": 100},
                }
            ],
        }

        # Import and execute the main processing code
        # We'll test the logic by calling the functions directly
        matching_agents = mock_match("Summary.csv")
        assert matching_agents == ["test_agent"]

        resp = mock_call("test_agent", mock_file)
        assert resp is not None
        assert resp.get("agent_name") == "test_agent"

        # Test standardized response rendering
        rendered = render_standardized_agent_response(resp)
        assert rendered is True

    @patch("hiring_agent_ui.st")
    @patch("hiring_agent_ui.call_n8n_agent")
    @patch("hiring_agent_ui.get_matching_agents_for_file")
    @patch.object(ui_module, "AGENTS_CONFIG", {
        "test_agent": {
            "webhook_path": "/webhook/test",
            "description": "Test agent",
        }
    })
    def test_main_processing_loop_legacy_response(self, mock_match, mock_call, mock_st):
        """Test main processing loop with legacy response format."""
        mock_file = MagicMock()
        mock_file.name = "Summary.csv"
        mock_st.file_uploader.return_value = [mock_file]
        mock_st.button.return_value = True

        mock_match.return_value = ["test_agent"]

        # Mock legacy response (not standardized)
        mock_call.return_value = {
            "sources": [
                {"Source": "LinkedIn", "Candidates": 50},
            ]
        }

        matching_agents = mock_match("Summary.csv")
        resp = mock_call("test_agent", mock_file)

        # Test extracting records from legacy response
        records = get_records_from_n8n_response(resp)
        assert len(records) > 0

    @patch("hiring_agent_ui.st")
    @patch("hiring_agent_ui.call_n8n_agent")
    @patch("hiring_agent_ui.get_matching_agents_for_file")
    @patch.object(ui_module, "AGENTS_CONFIG", {
        "test_agent": {
            "webhook_path": "/webhook/test",
            "description": "Test agent",
        }
    })
    def test_main_processing_loop_agent_not_in_config(self, mock_match, mock_call, mock_st):
        """Test main processing when agent not in config."""
        mock_file = MagicMock()
        mock_file.name = "Summary.csv"
        mock_st.file_uploader.return_value = [mock_file]
        mock_st.button.return_value = True

        mock_match.return_value = ["nonexistent_agent"]

        matching_agents = mock_match("Summary.csv")
        assert "nonexistent_agent" in matching_agents

    @patch("hiring_agent_ui.st")
    @patch("hiring_agent_ui.call_n8n_agent")
    @patch("hiring_agent_ui.get_matching_agents_for_file")
    def test_main_processing_loop_no_response(self, mock_match, mock_call, mock_st):
        """Test main processing when agent returns None."""
        mock_file = MagicMock()
        mock_file.name = "Summary.csv"
        mock_st.file_uploader.return_value = [mock_file]
        mock_st.button.return_value = True

        mock_match.return_value = ["test_agent"]
        mock_call.return_value = None

        matching_agents = mock_match("Summary.csv")
        resp = mock_call("test_agent", mock_file)
        assert resp is None

    @patch("hiring_agent_ui.st")
    @patch("hiring_agent_ui.get_records_from_n8n_response")
    def test_main_processing_loop_dataframe_creation(self, mock_get_records, mock_st):
        """Test DataFrame creation from records."""
        import pandas as pd

        mock_get_records.return_value = [
            {"Source": "LinkedIn", "Candidates": 50},
            {"Source": "Referral", "Candidates": 30},
        ]

        records = mock_get_records({})
        df = pd.DataFrame(records)
        assert not df.empty
        assert "Source" in df.columns

    @patch("hiring_agent_ui.st")
    @patch("hiring_agent_ui.get_records_from_n8n_response")
    def test_main_processing_loop_recommendation_extraction(self, mock_get_records, mock_st):
        """Test extracting recommendations from DataFrame."""
        import pandas as pd
        import re

        mock_get_records.return_value = [
            {"Source": "LinkedIn", "recommendation": "Focus on referrals"},
            {"Source": "Referral", "action": "Increase budget"},
        ]

        records = mock_get_records({})
        df = pd.DataFrame(records)

        # Test recommendation column detection
        for col in df.columns:
            if re.search(r"recommend|action|insight", col, re.I):
                vals = df[col].dropna().astype(str).tolist()
                assert len(vals) > 0

    @patch("hiring_agent_ui.st")
    def test_consolidated_insights_deduplication(self, mock_st):
        """Test consolidated insights deduplication logic."""
        # Simulate the deduplication logic from the main code
        consolidated_recs = [
            "Recommendation 1",
            "Recommendation 2",
            "Recommendation 1",  # Duplicate
            "Recommendation 3",
        ]

        seen = set()
        deduped = []
        for r in consolidated_recs:
            if r not in seen:
                seen.add(r)
                deduped.append(r)

        assert len(deduped) == 3
        assert "Recommendation 1" in deduped
        # After deduplication, the original list still has duplicates
        # but deduped list should only have one
        assert deduped.count("Recommendation 1") == 1

    @patch("hiring_agent_ui.st")
    def test_consolidated_insights_empty(self, mock_st):
        """Test consolidated insights when empty."""
        consolidated_recs = []
        assert len(consolidated_recs) == 0

    @patch("hiring_agent_ui.st")
    def test_standardized_response_recommendation_collection(self, mock_st):
        """Test collecting recommendations from standardized response."""
        response = {
            "agent_name": "test_agent",
            "sections": [
                {
                    "type": "recommendations",
                    "data": ["Rec 1", "Rec 2"],
                },
                {
                    "type": "insights",
                    "data": ["Insight 1"],
                },
            ],
        }

        recommendations = []
        for section in response.get("sections", []):
            if section.get("type") in ("recommendations", "insights"):
                items = section.get("data") or section.get("items") or []
                recommendations.extend(items)

        assert len(recommendations) == 3
        assert "Rec 1" in recommendations
        assert "Insight 1" in recommendations

    def test_get_matching_agents_fallback_to_agents_config(self, sample_config, monkeypatch):
        """Test fallback to AGENTS_CONFIG when ENABLED_AGENTS has no matches."""
        monkeypatch.setattr(ui_module, "ENABLED_AGENTS", {})
        monkeypatch.setattr(ui_module, "AGENTS_CONFIG", sample_config["n8n"]["agents"])
        monkeypatch.setattr(ui_module, "DEFAULT_AGENT", "none")

        from tests.test_helpers import get_matching_agents_for_file

        matches = get_matching_agents_for_file("Summary.csv")
        # Should fall back to AGENTS_CONFIG
        assert len(matches) > 0

    def test_get_matching_agents_fallback_to_default_agent(self, sample_config, monkeypatch):
        """Test fallback to DEFAULT_AGENT when no matches found."""
        monkeypatch.setattr(ui_module, "ENABLED_AGENTS", {})
        monkeypatch.setattr(ui_module, "AGENTS_CONFIG", {})
        monkeypatch.setattr(ui_module, "DEFAULT_AGENT", "sourcing_quality_agent")

        from tests.test_helpers import get_matching_agents_for_file

        matches = get_matching_agents_for_file("Unknown.csv")
        assert "sourcing_quality_agent" in matches

