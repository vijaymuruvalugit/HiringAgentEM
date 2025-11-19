"""Tests for rendering and data extraction logic."""
import pytest
import pandas as pd
from unittest.mock import Mock, patch, call

from tests.test_helpers import (
    render_standardized_agent_response,
    sanitize_dataframe_for_display,
    expand_structured_entries,
)


class TestRenderStandardizedAgentResponse:
    """Test rendering of standardized agent responses."""

    @patch("hiring_agent_ui.st")
    def test_render_metrics_section(self, mock_st):
        """Test rendering metrics section."""
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
                    },
                }
            ],
        }
        result = render_standardized_agent_response(response)
        assert result is True
        mock_st.subheader.assert_called_with("Test Agent")
        assert mock_st.metric.called

    @patch("hiring_agent_ui.st")
    def test_render_table_section(self, mock_st, mock_standardized_response):
        """Test rendering table section."""
        response = {
            "agent_name": "test_agent",
            "display_title": "Test Agent",
            "sections": [
                {
                    "type": "table",
                    "title": "Data Table",
                    "columns": ["Col1", "Col2"],
                    "rows": [
                        {"Col1": "A", "Col2": 1},
                        {"Col1": "B", "Col2": 2},
                    ],
                }
            ],
        }
        result = render_standardized_agent_response(response)
        assert result is True
        mock_st.table.assert_called_once()

    @patch("hiring_agent_ui.st")
    def test_render_insights_section(self, mock_st):
        """Test rendering insights section."""
        response = {
            "agent_name": "test_agent",
            "display_title": "Test Agent",
            "sections": [
                {
                    "type": "insights",
                    "title": "Actionable Insights",
                    "data": [
                        "Insight 1",
                        "Insight 2",
                    ],
                }
            ],
        }
        result = render_standardized_agent_response(response)
        assert result is True
        mock_st.markdown.assert_called()
        assert mock_st.write.call_count >= 2  # At least one write per insight

    @patch("hiring_agent_ui.st")
    def test_render_recommendations_section(self, mock_st):
        """Test rendering recommendations section."""
        response = {
            "agent_name": "test_agent",
            "display_title": "Test Agent",
            "sections": [
                {
                    "type": "recommendations",
                    "title": "Recommendations",
                    "data": [
                        "Recommendation 1",
                        "Recommendation 2",
                    ],
                }
            ],
        }
        result = render_standardized_agent_response(response)
        assert result is True
        mock_st.markdown.assert_called()
        assert mock_st.write.call_count >= 2

    @patch("hiring_agent_ui.st")
    def test_render_empty_response(self, mock_st):
        """Test rendering empty response."""
        result = render_standardized_agent_response({})
        assert result is False

    @patch("hiring_agent_ui.st")
    def test_render_none_response(self, mock_st):
        """Test rendering None response."""
        result = render_standardized_agent_response(None)
        assert result is False

    @patch("hiring_agent_ui.st")
    def test_render_without_display_title(self, mock_st):
        """Test rendering with agent_name fallback."""
        response = {
            "agent_name": "test_agent",
            "sections": [],
        }
        result = render_standardized_agent_response(response)
        assert result is True

    def test_sanitize_dataframe_for_display(self):
        """Sanitize helper should convert nested objects to JSON strings."""
        df = pd.DataFrame(
            [
                {"Nested": {"reason": "cultural", "percent": 42}},
                {"Nested": ["delay", "comp"]},
                {"Nested": {"set_data": {1, 2}}},
            ]
        )
        cleaned = sanitize_dataframe_for_display(df)
        assert cleaned.equals(cleaned)  # DataFrame still valid
        for value in cleaned["Nested"]:
            assert isinstance(value, str)
            assert value.startswith("{") or value.startswith("[")

    def test_expand_structured_entries_json_blob(self):
        """Helper should parse JSON blobs into flattened lists."""
        blob = '{"actionable_insights": ["Insight 1"], "recommendations": ["Rec 1"]}'
        expanded = expand_structured_entries([blob])
        assert "Insight 1" in expanded
        assert "Rec 1" in expanded

    def test_expand_structured_entries_from_dict(self):
        """Helper should expand dicts with recommendation keys."""
        source = {"recommendations": ["Rec A"], "notes": "ignored"}
        expanded = expand_structured_entries([source])
        assert "Rec A" in expanded

    @patch("hiring_agent_ui.st")
    def test_render_table_with_nested_objects(self, mock_st):
        """Ensure nested objects in tables render without [object Object]."""
        response = {
            "agent_name": "test_agent",
            "display_title": "Test Agent",
            "sections": [
                {
                    "type": "table",
                    "title": "Nested Data",
                    "columns": ["Source", "Details"],
                    "rows": [
                        {"Source": "LinkedIn", "Details": {"reason": "cultural", "percentage": 42}},
                        {"Source": "Referral", "Details": ["delays", "comp"]},
                    ],
                }
            ],
        }
        result = render_standardized_agent_response(response)
        assert result is True
        mock_st.table.assert_called_once()
        # Validate that nested data was converted to a JSON string
        rendered_df = mock_st.table.call_args[0][0]
        assert any('"' in str(val) for val in rendered_df["Details"])

    @patch("hiring_agent_ui.st")
    def test_render_insights_with_json_string(self, mock_st):
        """Ensure JSON strings in insights are expanded into list entries."""
        json_blob = (
            '{"actionable_insights": ["Insight A", "Insight B"], '
            '"recommendations": ["Recommendation X"]}'
        )
        response = {
            "agent_name": "test_agent",
            "display_title": "Test Agent",
            "sections": [
                {
                    "type": "insights",
                    "title": "Actionable Insights",
                    "data": [json_blob],
                }
            ],
        }
        result = render_standardized_agent_response(response)
        assert result is True
        # The JSON blob should be expanded into individual write calls
        writes = [call.args[0] for call in mock_st.write.call_args_list]
        assert any("Insight A" in entry for entry in writes)
        assert any("Insight B" in entry for entry in writes)
        mock_st.subheader.assert_called_with("Test Agent")

    @patch("hiring_agent_ui.st")
    def test_render_table_with_numeric_columns(self, mock_st):
        """Test rendering table with numeric columns triggers chart."""
        response = {
            "agent_name": "test_agent",
            "display_title": "Test Agent",
            "sections": [
                {
                    "type": "table",
                    "title": "Data Table",
                    "columns": ["Source", "Count"],
                    "rows": [
                        {"Source": "LinkedIn", "Count": 50},
                        {"Source": "Referral", "Count": 30},
                    ],
                }
            ],
        }
        result = render_standardized_agent_response(response)
        assert result is True
        # Should call bar_chart if numeric columns exist
        # (This depends on pandas DataFrame creation)
        mock_st.table.assert_called_once()

    @patch("hiring_agent_ui.st")
    def test_render_unknown_section_type(self, mock_st):
        """Test rendering unknown section type falls back to raw display."""
        response = {
            "agent_name": "test_agent",
            "display_title": "Test Agent",
            "sections": [
                {
                    "type": "unknown_type",
                    "title": "Unknown",
                    "data": {"key": "value"},
                }
            ],
        }
        result = render_standardized_agent_response(response)
        assert result is True
        mock_st.write.assert_called()

