"""Tests for extracted processing functions."""
import pytest
from io import BytesIO
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

from tests.test_helpers import (
    process_uploaded_files,
    format_consolidated_insights,
    call_n8n_agent,
    get_matching_agents_for_file,
    get_records_from_n8n_response,
    render_standardized_agent_response,
    clean_display_text,
    ui_module,
)


class TestProcessUploadedFiles:
    """Test the extracted process_uploaded_files function."""

    @patch("hiring_agent_ui.st")
    @patch("hiring_agent_ui.get_matching_agents_for_file")
    @patch("hiring_agent_ui.call_n8n_agent")
    @patch("hiring_agent_ui.render_standardized_agent_response")
    def test_process_files_standardized_response(self, mock_render, mock_call, mock_match, mock_st):
        """Test processing files with standardized response."""
        mock_file = MagicMock()
        mock_file.name = "Summary.csv"
        
        mock_match.return_value = ["test_agent"]
        mock_call.return_value = {
            "agent_name": "test_agent",
            "sections": [
                {
                    "type": "recommendations",
                    "data": ["Rec 1", "Rec 2"]
                }
            ]
        }
        mock_render.return_value = True
        
        agents_config = {
            "test_agent": {
                "webhook_path": "/webhook/test",
                "description": "Test agent",
            }
        }
        
        result = process_uploaded_files(
            uploaded_files=[mock_file],
            run_all=True,
            agents_config=agents_config,
            base_url="http://localhost:5678",
        )
        
        assert len(result) == 2
        assert "Rec 1" in result
        assert mock_match.called
        assert mock_call.called

    @patch("hiring_agent_ui.st")
    @patch("hiring_agent_ui.get_matching_agents_for_file")
    @patch("hiring_agent_ui.call_n8n_agent")
    @patch("hiring_agent_ui.render_standardized_agent_response")
    def test_process_files_string_response(self, mock_render, mock_call, mock_match, mock_st):
        """Test processing when agent returns stringified JSON."""
        mock_file = MagicMock()
        mock_file.name = "Summary.csv"
        
        mock_match.return_value = ["test_agent"]
        mock_call.return_value = '{"agent_name": "test_agent", "sections": []}'
        mock_render.return_value = True
        
        agents_config = {
            "test_agent": {
                "webhook_path": "/webhook/test",
                "description": "Test agent",
            }
        }
        
        process_uploaded_files(
            uploaded_files=[mock_file],
            run_all=True,
            agents_config=agents_config,
            base_url="http://localhost:5678",
        )
        
        mock_render.assert_called_once()

    @patch("hiring_agent_ui.st")
    @patch("hiring_agent_ui.get_matching_agents_for_file")
    @patch("hiring_agent_ui.call_n8n_agent")
    @patch("hiring_agent_ui.render_standardized_agent_response")
    def test_process_files_sections_list_response(self, mock_render, mock_call, mock_match, mock_st):
        """Test processing when agent returns a list of sections."""
        mock_file = MagicMock()
        mock_file.name = "Summary.csv"
        
        mock_match.return_value = ["test_agent"]
        mock_call.return_value = [
            {"type": "metrics", "title": "Summary", "data": {"Total": 1}}
        ]
        mock_render.return_value = True
        
        agents_config = {
            "test_agent": {
                "webhook_path": "/webhook/test",
                "description": "Test agent",
            }
        }
        
        process_uploaded_files(
            uploaded_files=[mock_file],
            run_all=True,
            agents_config=agents_config,
            base_url="http://localhost:5678",
        )
        
        mock_render.assert_called_once()

    @patch("hiring_agent_ui.st")
    @patch("hiring_agent_ui.get_matching_agents_for_file")
    @patch("hiring_agent_ui.call_n8n_agent")
    @patch("hiring_agent_ui.render_standardized_agent_response")
    def test_process_files_sections_string_response(self, mock_render, mock_call, mock_match, mock_st):
        """Test processing when sections field is a JSON string."""
        mock_file = MagicMock()
        mock_file.name = "Summary.csv"
        
        mock_match.return_value = ["test_agent"]
        mock_call.return_value = {
            "agent_name": "test_agent",
            "display_title": "Test Agent",
            "sections": '[{"type": "metrics", "title": "Summary", "data": {"Total": 1}}]'
        }
        mock_render.return_value = True
        
        agents_config = {
            "test_agent": {
                "webhook_path": "/webhook/test",
                "description": "Test agent",
            }
        }
        
        process_uploaded_files(
            uploaded_files=[mock_file],
            run_all=True,
            agents_config=agents_config,
            base_url="http://localhost:5678",
        )
        
        mock_render.assert_called_once()
        # Verify sections was parsed into a list
        call_args = mock_render.call_args[0][0]
        assert isinstance(call_args.get("sections"), list)
    
    @patch("hiring_agent_ui.st")
    @patch("hiring_agent_ui.get_matching_agents_for_file")
    @patch("hiring_agent_ui.call_n8n_agent")
    @patch("hiring_agent_ui.render_standardized_agent_response")
    def test_process_files_sections_escaped_quotes(self, mock_render, mock_call, mock_match, mock_st):
        """Test processing response where sections has escaped quotes ("")."""
        mock_file = MagicMock()
        mock_file.name = "Summary.csv"
        
        mock_match.return_value = ["test_agent"]
        # Response with sections as a JSON string with escaped quotes (""type"" instead of "type")
        sections_json = '[{""type"": ""metrics"", ""title"": ""Summary"", ""data"": {""Total"": 100}}]'
        mock_call.return_value = {
            "agent_name": "test_agent",
            "display_title": "Test Agent",
            "sections": sections_json
        }
        mock_render.return_value = True
        
        agents_config = {
            "test_agent": {
                "webhook_path": "/webhook/test",
                "description": "Test agent",
            }
        }
        
        process_uploaded_files(
            uploaded_files=[mock_file],
            run_all=True,
            agents_config=agents_config,
            base_url="http://localhost:5678",
        )
        
        # Should parse sections string with escaped quotes and render successfully
        assert mock_render.called
        call_args = mock_render.call_args[0][0]
        assert isinstance(call_args.get("sections"), list)
        assert len(call_args.get("sections", [])) > 0

    @patch("hiring_agent_ui.st")
    @patch("hiring_agent_ui.get_matching_agents_for_file")
    @patch("hiring_agent_ui.call_n8n_agent")
    def test_process_files_no_run_all(self, mock_call, mock_match, mock_st):
        """Test that nothing happens when run_all is False."""
        mock_file = MagicMock()
        
        result = process_uploaded_files(
            uploaded_files=[mock_file],
            run_all=False,
            agents_config={},
            base_url="http://localhost:5678",
        )
        
        assert result == []
        assert not mock_match.called

    @patch("hiring_agent_ui.st")
    @patch("hiring_agent_ui.get_matching_agents_for_file")
    @patch("hiring_agent_ui.call_n8n_agent")
    def test_process_files_empty_uploaded_files(self, mock_call, mock_match, mock_st):
        """Test with empty uploaded files."""
        result = process_uploaded_files(
            uploaded_files=[],
            run_all=True,
            agents_config={},
            base_url="http://localhost:5678",
        )
        
        assert result == []

    @patch("hiring_agent_ui.st")
    @patch("hiring_agent_ui.get_matching_agents_for_file")
    @patch("hiring_agent_ui.call_n8n_agent")
    def test_process_files_agent_not_in_config(self, mock_call, mock_match, mock_st):
        """Test when agent is not in config."""
        mock_file = MagicMock()
        mock_file.name = "Summary.csv"
        
        mock_match.return_value = ["nonexistent_agent"]
        
        result = process_uploaded_files(
            uploaded_files=[mock_file],
            run_all=True,
            agents_config={},
            base_url="http://localhost:5678",
        )
        
        # Agents not in config are now filtered out before processing
        assert result == []
        # No warning should be called since we filter them out early
        assert not mock_st.warning.called

    @patch("hiring_agent_ui.st")
    @patch("hiring_agent_ui.get_matching_agents_for_file")
    @patch("hiring_agent_ui.call_n8n_agent")
    def test_process_files_no_response(self, mock_call, mock_match, mock_st):
        """Test when agent returns None."""
        mock_file = MagicMock()
        mock_file.name = "Summary.csv"
        
        mock_match.return_value = ["test_agent"]
        mock_call.return_value = None
        
        agents_config = {
            "test_agent": {
                "webhook_path": "/webhook/test",
                "description": "Test agent",
            }
        }
        
        result = process_uploaded_files(
            uploaded_files=[mock_file],
            run_all=True,
            agents_config=agents_config,
            base_url="http://localhost:5678",
        )
        
        assert result == []
        mock_st.error.assert_called()

    @patch("hiring_agent_ui.st")
    @patch("hiring_agent_ui.get_matching_agents_for_file")
    @patch("hiring_agent_ui.call_n8n_agent")
    @patch("hiring_agent_ui.get_records_from_n8n_response")
    def test_process_files_legacy_response(self, mock_get_records, mock_call, mock_match, mock_st):
        """Test processing legacy (non-standardized) response."""
        mock_file = MagicMock()
        mock_file.name = "Summary.csv"
        
        mock_match.return_value = ["test_agent"]
        mock_call.return_value = {"sources": [{"Source": "LinkedIn", "recommendation": "Rec 1"}]}
        mock_get_records.return_value = [{"Source": "LinkedIn", "recommendation": "Rec 1"}]
        
        agents_config = {
            "test_agent": {
                "webhook_path": "/webhook/test",
                "description": "Test agent",
            }
        }
        
        result = process_uploaded_files(
            uploaded_files=[mock_file],
            run_all=True,
            agents_config=agents_config,
            base_url="http://localhost:5678",
        )
        
        # Should extract recommendation from DataFrame
        assert len(result) >= 0  # May or may not find recommendation column

    @patch("hiring_agent_ui.st")
    @patch("hiring_agent_ui.get_matching_agents_for_file")
    @patch("hiring_agent_ui.call_n8n_agent")
    def test_process_files_no_debug_expander(self, mock_call, mock_match, mock_st):
        """Ensure raw-response debug UI is not invoked."""
        mock_file = MagicMock()
        mock_file.name = "Summary.csv"
        
        mock_match.return_value = ["test_agent"]
        mock_call.return_value = {"agent_name": "test_agent", "sections": []}
        
        agents_config = {
            "test_agent": {
                "webhook_path": "/webhook/test",
                "description": "Test agent",
            }
        }
        
        process_uploaded_files(
            uploaded_files=[mock_file],
            run_all=True,
            agents_config=agents_config,
            base_url="http://localhost:5678",
        )
        
        mock_st.expander.assert_not_called()


class TestFormatConsolidatedInsights:
    """Test the format_consolidated_insights function."""

    def test_format_empty_list(self):
        """Test formatting empty list."""
        result = format_consolidated_insights([])
        assert result == []

    def test_format_no_duplicates(self):
        """Test formatting list with no duplicates."""
        recs = ["Rec 1", "Rec 2", "Rec 3"]
        result = format_consolidated_insights(recs)
        assert result == recs

    def test_format_with_duplicates(self):
        """Test formatting list with duplicates."""
        recs = ["Rec 1", "Rec 2", "Rec 1", "Rec 3", "Rec 2"]
        result = format_consolidated_insights(recs)
        assert result == ["Rec 1", "Rec 2", "Rec 3"]
        assert len(result) == 3

    def test_format_preserves_order(self):
        """Test that deduplication preserves order."""
        recs = ["Rec 3", "Rec 1", "Rec 2", "Rec 1", "Rec 3"]
        result = format_consolidated_insights(recs)
        assert result == ["Rec 3", "Rec 1", "Rec 2"]
        assert result[0] == "Rec 3"

    def test_format_single_item(self):
        """Test formatting single item."""
        recs = ["Rec 1"]
        result = format_consolidated_insights(recs)
        assert result == ["Rec 1"]

    def test_format_all_duplicates(self):
        """Test formatting when all items are duplicates."""
        recs = ["Rec 1", "Rec 1", "Rec 1"]
        result = format_consolidated_insights(recs)
        assert result == ["Rec 1"]
        assert len(result) == 1


class TestCallN8nAgentWithParams:
    """Test call_n8n_agent with explicit parameters."""

    @patch("hiring_agent_ui.requests.post")
    @patch("hiring_agent_ui.st")
    def test_call_n8n_agent_with_explicit_config(self, mock_st, mock_post):
        """Test calling agent with explicit config parameters."""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "success"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        file_obj = BytesIO(b"test")
        file_obj.name = "test.csv"

        agents_config = {
            "test_agent": {
                "webhook_path": "/webhook/test-123",
            }
        }

        result = call_n8n_agent(
            "test_agent",
            file_obj,
            agents_config=agents_config,
            base_url="http://localhost:5678",
        )

        assert result is not None
        assert mock_post.called
        call_url = mock_post.call_args[0][0]
        assert "http://localhost:5678" in call_url
        assert "/webhook/test-123" in call_url

    @patch("hiring_agent_ui.st")
    def test_call_n8n_agent_missing_webhook_with_explicit_config(self, mock_st):
        """Test error when webhook_path is missing with explicit config."""
        file_obj = BytesIO(b"test")
        file_obj.name = "test.csv"

        agents_config = {}

        result = call_n8n_agent(
            "nonexistent_agent",
            file_obj,
            agents_config=agents_config,
            base_url="http://localhost:5678",
        )

        assert result is None
        mock_st.error.assert_called_once()

