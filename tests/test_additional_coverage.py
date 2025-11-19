"""Additional tests to increase coverage to 80%+."""
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


class TestAdditionalCoverage:
    """Additional tests to cover edge cases and increase coverage."""

    def test_get_matching_agents_with_file_patterns(self, sample_config, monkeypatch):
        """Test matching with file_patterns instead of filename_keywords."""
        agents = sample_config["n8n"]["agents"].copy()
        agents["test_agent"] = {
            "webhook_path": "/webhook/test",
            "file_patterns": ["test"],
        }
        monkeypatch.setattr(ui_module, "ENABLED_AGENTS", agents)
        monkeypatch.setattr(ui_module, "AGENTS_CONFIG", agents)
        monkeypatch.setattr(ui_module, "DEFAULT_AGENT", "none")
        
        matches = get_matching_agents_for_file("test_file.csv")
        assert "test_agent" in matches

    def test_get_matching_agents_no_enabled_agents(self, sample_config, monkeypatch):
        """Test matching when no enabled agents exist."""
        monkeypatch.setattr(ui_module, "ENABLED_AGENTS", {})
        monkeypatch.setattr(ui_module, "AGENTS_CONFIG", sample_config["n8n"]["agents"])
        monkeypatch.setattr(ui_module, "DEFAULT_AGENT", "none")
        
        matches = get_matching_agents_for_file("Summary.csv")
        # Should fall back to AGENTS_CONFIG
        assert len(matches) > 0

    def test_get_records_from_n8n_response_dict_with_dict_value(self):
        """Test extracting from dict where value is a dict."""
        response = {"data": {"key": "value"}}
        records = get_records_from_n8n_response(response)
        assert len(records) > 0

    def test_get_records_from_n8n_response_dict_with_non_list_value(self):
        """Test extracting from dict with non-list value."""
        response = {"sources": "not a list"}
        records = get_records_from_n8n_response(response)
        assert len(records) > 0

    @patch("hiring_agent_ui.requests.post")
    @patch.object(ui_module, "AGENTS_CONFIG", {
        "test_agent": {
            "endpoint": "/webhook/test-123",  # Using endpoint instead of webhook_path
        }
    })
    @patch.object(ui_module, "BASE_URL", "http://localhost:5678")
    def test_call_n8n_agent_with_endpoint_key(self, mock_post):
        """Test calling agent with endpoint key instead of webhook_path."""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "success"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        file_obj = BytesIO(b"test")
        file_obj.name = "test.csv"

        result = call_n8n_agent("test_agent", file_obj)
        assert result is not None

    @patch("hiring_agent_ui.st")
    def test_render_standardized_response_with_empty_sections(self, mock_st):
        """Test rendering response with empty sections list."""
        response = {
            "agent_name": "test_agent",
            "display_title": "Test Agent",
            "sections": [],
        }
        result = render_standardized_agent_response(response)
        assert result is True

    @patch("hiring_agent_ui.st")
    def test_render_standardized_response_table_without_columns(self, mock_st):
        """Test rendering table section without columns."""
        response = {
            "agent_name": "test_agent",
            "display_title": "Test Agent",
            "sections": [
                {
                    "type": "table",
                    "title": "Data Table",
                    "rows": [{"Col1": "A", "Col2": 1}],
                }
            ],
        }
        result = render_standardized_agent_response(response)
        assert result is True
        mock_st.table.assert_called_once()

    @patch("hiring_agent_ui.st")
    def test_render_standardized_response_table_empty_rows(self, mock_st):
        """Test rendering table section with empty rows."""
        response = {
            "agent_name": "test_agent",
            "display_title": "Test Agent",
            "sections": [
                {
                    "type": "table",
                    "title": "Data Table",
                    "columns": ["Col1", "Col2"],
                    "rows": [],
                }
            ],
        }
        result = render_standardized_agent_response(response)
        assert result is True

    @patch("hiring_agent_ui.st")
    def test_render_standardized_response_insights_without_title(self, mock_st):
        """Test rendering insights section without title."""
        response = {
            "agent_name": "test_agent",
            "display_title": "Test Agent",
            "sections": [
                {
                    "type": "insights",
                    "data": ["Insight 1"],
                }
            ],
        }
        result = render_standardized_agent_response(response)
        assert result is True

    @patch("hiring_agent_ui.st")
    def test_render_standardized_response_insights_with_items_key(self, mock_st):
        """Test rendering insights section with items key."""
        response = {
            "agent_name": "test_agent",
            "display_title": "Test Agent",
            "sections": [
                {
                    "type": "insights",
                    "title": "Insights",
                    "items": ["Insight 1", "Insight 2"],
                }
            ],
        }
        result = render_standardized_agent_response(response)
        assert result is True

    @patch("hiring_agent_ui.st")
    def test_render_standardized_response_table_column_mismatch(self, mock_st):
        """Test rendering table where columns don't match DataFrame columns."""
        response = {
            "agent_name": "test_agent",
            "display_title": "Test Agent",
            "sections": [
                {
                    "type": "table",
                    "title": "Data Table",
                    "columns": ["NonExistentCol"],
                    "rows": [{"Col1": "A", "Col2": 1}],
                }
            ],
        }
        result = render_standardized_agent_response(response)
        assert result is True
        mock_st.table.assert_called_once()

    @patch("hiring_agent_ui.st")
    def test_render_standardized_response_table_no_numeric_columns(self, mock_st):
        """Test rendering table with no numeric columns (no chart)."""
        response = {
            "agent_name": "test_agent",
            "display_title": "Test Agent",
            "sections": [
                {
                    "type": "table",
                    "title": "Data Table",
                    "columns": ["Source", "Status"],
                    "rows": [
                        {"Source": "LinkedIn", "Status": "Active"},
                        {"Source": "Referral", "Status": "Active"},
                    ],
                }
            ],
        }
        result = render_standardized_agent_response(response)
        assert result is True
        mock_st.table.assert_called_once()

    def test_get_records_from_n8n_response_list_without_json_key(self):
        """Test extracting from list without json key."""
        response = [{"key": "value"}]
        records = get_records_from_n8n_response(response)
        assert len(records) == 1

    def test_get_records_from_n8n_response_dict_with_results_dict(self):
        """Test extracting from dict with results as dict."""
        response = {"results": {"key": "value"}}
        records = get_records_from_n8n_response(response)
        assert len(records) > 0

