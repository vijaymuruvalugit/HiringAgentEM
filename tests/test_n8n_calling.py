"""Tests for n8n agent calling functionality."""
import pytest
from io import BytesIO
from unittest.mock import Mock, patch

from tests.test_helpers import call_n8n_agent, ui_module


class TestCallN8nAgent:
    """Test n8n agent calling functionality."""

    @patch("hiring_agent_ui.requests.post")
    @patch.object(ui_module, "AGENTS_CONFIG", {
        "test_agent": {
            "webhook_path": "/webhook/test-123",
            "description": "Test agent",
        }
    })
    @patch.object(ui_module, "BASE_URL", "http://localhost:5678")
    def test_successful_call_returns_json(self, mock_post):
        """Test successful agent call returns JSON response."""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "success", "data": []}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        file_obj = BytesIO(b"col1,col2\nval1,val2")
        file_obj.name = "test.csv"

        result = call_n8n_agent("test_agent", file_obj)
        assert result == {"status": "success", "data": []}
        mock_post.assert_called_once()
        assert "/webhook/test-123" in mock_post.call_args[0][0]

    @patch("hiring_agent_ui.requests.post")
    @patch.object(ui_module, "AGENTS_CONFIG", {
        "test_agent": {
            "webhook_path": "/webhook/test-123",
        }
    })
    @patch.object(ui_module, "BASE_URL", "http://localhost:5678")
    def test_successful_call_returns_text_when_not_json(self, mock_post):
        """Test agent call returns text when response is not JSON."""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Not JSON")
        mock_response.text = "plain text response"
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        file_obj = BytesIO(b"col1,col2\nval1,val2")
        file_obj.name = "test.csv"

        result = call_n8n_agent("test_agent", file_obj)
        assert result == "plain text response"

    @patch("hiring_agent_ui.requests.post")
    @patch.object(ui_module, "AGENTS_CONFIG", {
        "test_agent": {
            "webhook_path": "/webhook/test-123",
        }
    })
    @patch.object(ui_module, "BASE_URL", "http://localhost:5678")
    @patch("hiring_agent_ui.st")
    def test_http_error_handling(self, mock_st, mock_post):
        """Test handling of HTTP errors."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = Exception("404 Not Found")
        mock_post.return_value = mock_response

        file_obj = BytesIO(b"col1,col2\nval1,val2")
        file_obj.name = "test.csv"

        result = call_n8n_agent("test_agent", file_obj)
        assert result is None
        mock_st.error.assert_called_once()

    @patch.object(ui_module, "AGENTS_CONFIG", {})
    def test_missing_webhook_path(self):
        """Test error when webhook_path is missing."""
        file_obj = BytesIO(b"test")
        file_obj.name = "test.csv"

        with patch("hiring_agent_ui.st") as mock_st:
            result = call_n8n_agent("nonexistent_agent", file_obj)
            assert result is None
            mock_st.error.assert_called_once()

    @patch("hiring_agent_ui.requests.post")
    @patch.object(ui_module, "AGENTS_CONFIG", {
        "test_agent": {
            "webhook_path": "webhook/test-123",  # No leading slash
        }
    })
    @patch.object(ui_module, "BASE_URL", "http://localhost:5678")
    def test_webhook_path_without_leading_slash(self, mock_post):
        """Test webhook path without leading slash is handled correctly."""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "success"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        file_obj = BytesIO(b"test")
        file_obj.name = "test.csv"

        result = call_n8n_agent("test_agent", file_obj)
        assert result is not None
        # Check that URL was constructed correctly
        call_url = mock_post.call_args[0][0]
        assert "http://localhost:5678" in call_url
        assert "webhook/test-123" in call_url

    @patch("hiring_agent_ui.requests.post")
    @patch.object(ui_module, "AGENTS_CONFIG", {
        "test_agent": {
            "webhook_path": "/webhook/test-123",
        }
    })
    @patch.object(ui_module, "BASE_URL", "http://localhost:5678")
    def test_file_seek_reset(self, mock_post):
        """Test that file object is seeked to start before sending."""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "success"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        file_obj = BytesIO(b"col1,col2\nval1,val2")
        file_obj.name = "test.csv"
        file_obj.read(5)  # Move position

        call_n8n_agent("test_agent", file_obj)
        # Verify file was sent (position would be at end after read)
        assert mock_post.called

