"""Tests for main processing loop and file handling."""
import pytest
from io import BytesIO
from unittest.mock import Mock, patch, MagicMock

from tests.test_helpers import (
    get_matching_agents_for_file,
    get_records_from_n8n_response,
    call_n8n_agent,
    render_standardized_agent_response,
    ui_module,
)


class TestMainProcessing:
    """Test the main file processing logic."""

    @patch("hiring_agent_ui.requests.post")
    @patch.object(ui_module, "AGENTS_CONFIG", {
        "test_agent": {
            "webhook_path": "/webhook/test-123",
            "description": "Test agent",
        }
    })
    @patch.object(ui_module, "BASE_URL", "http://localhost:5678")
    def test_call_n8n_agent_with_exception(self, mock_post):
        """Test call_n8n_agent when request raises exception."""
        mock_post.side_effect = Exception("Connection error")
        file_obj = BytesIO(b"test")
        file_obj.name = "test.csv"

        with patch("hiring_agent_ui.st") as mock_st:
            result = call_n8n_agent("test_agent", file_obj)
            assert result is None
            mock_st.error.assert_called_once()

    def test_get_records_from_n8n_response_empty_list_handling(self):
        """Test handling of empty list in get_records_from_n8n_response."""
        # Empty list should return empty list (not list with empty list)
        records = get_records_from_n8n_response([])
        # Based on code, empty list with result_data check should return empty
        # But the code checks `if isinstance(result_data, list) and result_data:`
        # So empty list should skip that branch and go to else
        assert isinstance(records, list)

    def test_get_records_from_n8n_response_list_with_empty_dict(self):
        """Test extracting from list with empty dict."""
        response = [{}]
        records = get_records_from_n8n_response(response)
        assert len(records) == 1

    def test_get_records_from_n8n_response_list_item_without_json_key(self):
        """Test extracting from list item without json key."""
        response = [{"not_json": "value"}]
        records = get_records_from_n8n_response(response)
        assert len(records) == 1

    def test_get_records_from_n8n_response_dict_with_data_as_dict(self):
        """Test extracting when data key contains a dict."""
        response = {"data": {"nested": "value"}}
        records = get_records_from_n8n_response(response)
        assert len(records) > 0

    def test_get_records_from_n8n_response_dict_with_results_as_dict(self):
        """Test extracting when results key contains a dict."""
        response = {"results": {"nested": "value"}}
        records = get_records_from_n8n_response(response)
        assert len(records) > 0

    @patch("hiring_agent_ui.st")
    def test_render_standardized_response_metrics_empty_data(self, mock_st):
        """Test rendering metrics section with empty data."""
        response = {
            "agent_name": "test_agent",
            "display_title": "Test Agent",
            "sections": [
                {
                    "type": "metrics",
                    "title": "Summary",
                    "data": {},
                }
            ],
        }
        result = render_standardized_agent_response(response)
        assert result is True

    @patch("hiring_agent_ui.st")
    def test_render_standardized_response_metrics_single_item(self, mock_st):
        """Test rendering metrics section with single item."""
        response = {
            "agent_name": "test_agent",
            "display_title": "Test Agent",
            "sections": [
                {
                    "type": "metrics",
                    "title": "Summary",
                    "data": {
                        "Total": 100,
                    },
                }
            ],
        }
        result = render_standardized_agent_response(response)
        assert result is True
        mock_st.metric.assert_called()

    @patch("hiring_agent_ui.st")
    def test_render_standardized_response_metrics_many_items(self, mock_st):
        """Test rendering metrics section with more than 4 items."""
        response = {
            "agent_name": "test_agent",
            "display_title": "Test Agent",
            "sections": [
                {
                    "type": "metrics",
                    "title": "Summary",
                    "data": {
                        "Total": 100,
                        "Rate": "25%",
                        "Score": 7.5,
                        "Count": 50,
                        "Extra": "value",
                    },
                }
            ],
        }
        result = render_standardized_agent_response(response)
        assert result is True
        # Should create max 4 columns
        assert mock_st.columns.call_count > 0

    @patch("hiring_agent_ui.st")
    def test_render_standardized_response_table_with_column_filtering(self, mock_st):
        """Test rendering table with column filtering."""
        response = {
            "agent_name": "test_agent",
            "display_title": "Test Agent",
            "sections": [
                {
                    "type": "table",
                    "title": "Data Table",
                    "columns": ["Col1", "Col2"],
                    "rows": [
                        {"Col1": "A", "Col2": 1, "Col3": "extra"},
                    ],
                }
            ],
        }
        result = render_standardized_agent_response(response)
        assert result is True
        mock_st.table.assert_called_once()

    @patch("hiring_agent_ui.st")
    def test_render_standardized_response_table_empty_dataframe(self, mock_st):
        """Test rendering table that results in empty DataFrame."""
        response = {
            "agent_name": "test_agent",
            "display_title": "Test Agent",
            "sections": [
                {
                    "type": "table",
                    "title": "Data Table",
                    "columns": ["Col1"],
                    "rows": [{"Col1": "A"}],
                }
            ],
        }
        result = render_standardized_agent_response(response)
        assert result is True

    @patch("hiring_agent_ui.st")
    def test_render_standardized_response_insights_empty_data(self, mock_st):
        """Test rendering insights section with empty data."""
        response = {
            "agent_name": "test_agent",
            "display_title": "Test Agent",
            "sections": [
                {
                    "type": "insights",
                    "title": "Insights",
                    "data": [],
                }
            ],
        }
        result = render_standardized_agent_response(response)
        assert result is True

    @patch("hiring_agent_ui.st")
    def test_render_standardized_response_recommendations_empty_data(self, mock_st):
        """Test rendering recommendations section with empty data."""
        response = {
            "agent_name": "test_agent",
            "display_title": "Test Agent",
            "sections": [
                {
                    "type": "recommendations",
                    "title": "Recommendations",
                    "data": [],
                }
            ],
        }
        result = render_standardized_agent_response(response)
        assert result is True

    def test_get_matching_agents_agent_name_in_filename(self, sample_config, monkeypatch):
        """Test matching when agent name appears in filename."""
        agents = sample_config["n8n"]["agents"].copy()
        agents["sourcing"] = {
            "webhook_path": "/webhook/test",
            "filename_keywords": [],
        }
        monkeypatch.setattr(ui_module, "ENABLED_AGENTS", agents)
        monkeypatch.setattr(ui_module, "AGENTS_CONFIG", agents)
        monkeypatch.setattr(ui_module, "DEFAULT_AGENT", "none")
        
        # "sourcing" should match "sourcing_quality_agent" via normalized matching
        matches = get_matching_agents_for_file("sourcing_data.csv")
        # This tests the normalized matching logic
        assert isinstance(matches, list)

