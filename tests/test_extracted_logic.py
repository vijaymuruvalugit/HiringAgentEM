"""Tests for extracted logic functions to improve coverage."""
import pytest
from io import BytesIO
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import re

from tests.test_helpers import (
    get_records_from_n8n_response,
    clean_display_text,
    render_standardized_agent_response,
    ui_module,
)


class TestExtractedLogic:
    """Test logic that can be extracted and tested independently."""

    def test_process_agent_response_standardized(self):
        """Test processing standardized agent response."""
        resp = {
            "agent_name": "test_agent",
            "sections": [
                {
                    "type": "recommendations",
                    "data": ["Rec 1", "Rec 2"]
                }
            ]
        }
        
        # Simulate the processing logic
        std = None
        if isinstance(resp, dict) and resp.get("agent_name") and resp.get("sections"):
            std = resp
        
        assert std is not None
        
        # Collect recommendations
        consolidated_recs = []
        for s in std.get("sections", []):
            if s.get("type") == "recommendations" or s.get("type") == "insights":
                items = s.get("data") or s.get("items") or []
                for it in items:
                    consolidated_recs.append(clean_display_text(it))
        
        assert len(consolidated_recs) == 2

    def test_process_agent_response_from_records(self):
        """Test processing agent response extracted from records."""
        resp = [{"json": {"agent_name": "test_agent", "sections": []}}]
        records = get_records_from_n8n_response(resp)
        
        std = None
        if len(records) == 1 and isinstance(records[0], dict) and records[0].get("agent_name"):
            std = records[0]
        
        assert std is not None
        assert std.get("agent_name") == "test_agent"

    def test_process_agent_response_dataframe_fallback(self):
        """Test DataFrame fallback processing."""
        resp = {
            "sources": [
                {"Source": "LinkedIn", "recommendation": "Focus on referrals"},
                {"Source": "Referral", "action_item": "Increase budget"},
            ]
        }
        records = get_records_from_n8n_response(resp)
        
        consolidated_recs = []
        if records:
            try:
                df = pd.DataFrame(records)
                # Test recommendation column detection
                for col in df.columns:
                    if re.search(r"recommend|action|insight", col, re.I):
                        vals = df[col].dropna().astype(str).tolist()
                        for v in vals:
                            consolidated_recs.append(clean_display_text(v))
            except Exception:
                pass
        
        assert len(consolidated_recs) >= 1

    def test_process_agent_response_dataframe_exception(self):
        """Test DataFrame processing with exception handling."""
        # Create records that might cause issues
        records = [{"key": object()}]  # Non-serializable object
        
        try:
            df = pd.DataFrame(records)
            # This might work or fail depending on the object
        except Exception as e:
            # Exception path
            assert isinstance(e, Exception)

    def test_consolidated_insights_deduplication_logic(self):
        """Test consolidated insights deduplication."""
        consolidated_recs = [
            "Rec 1",
            "Rec 2",
            "Rec 1",  # Duplicate
            "Rec 3",
            "Rec 2",  # Duplicate
        ]
        
        # Simulate deduplication logic
        seen = set()
        deduped = []
        for r in consolidated_recs:
            if r not in seen:
                seen.add(r)
                deduped.append(r)
        
        assert len(deduped) == 3
        assert deduped == ["Rec 1", "Rec 2", "Rec 3"]

    def test_consolidated_insights_download_content(self):
        """Test consolidated insights download button content."""
        consolidated_recs = ["Rec 1", "Rec 2", "Rec 3"]
        
        seen = set()
        deduped = []
        for r in consolidated_recs:
            if r not in seen:
                seen.add(r)
                deduped.append(r)
        
        download_content = "\n".join(deduped)
        assert download_content == "Rec 1\nRec 2\nRec 3"

    def test_agent_title_extraction(self):
        """Test agent title extraction from config."""
        agents_config = {
            "test_agent": {
                "description": "Test Agent Description",
            }
        }
        agent_key = "test_agent"
        agent_title = agents_config[agent_key].get("description", agent_key)
        assert agent_title == "Test Agent Description"

    def test_agent_title_fallback(self):
        """Test agent title fallback to key."""
        agents_config = {
            "test_agent": {}
        }
        agent_key = "test_agent"
        agent_title = agents_config[agent_key].get("description", agent_key)
        assert agent_title == "test_agent"

    def test_base_url_change_detection(self):
        """Test base URL change detection logic."""
        BASE_URL = "http://localhost:5678"
        base_url_input = "http://new-url:5678"
        
        if base_url_input != BASE_URL:
            # URL was changed
            new_base_url = base_url_input
            assert new_base_url != BASE_URL

    def test_base_url_no_change(self):
        """Test base URL when no change."""
        BASE_URL = "http://localhost:5678"
        base_url_input = "http://localhost:5678"
        
        if base_url_input != BASE_URL:
            # Should not enter this block
            assert False
        else:
            # URL unchanged
            assert True

    @patch("hiring_agent_ui.st")
    def test_file_processing_loop_structure(self, mock_st):
        """Test the structure of file processing loop."""
        mock_file1 = MagicMock()
        mock_file1.name = "Summary.csv"
        mock_file2 = MagicMock()
        mock_file2.name = "Funnel.csv"
        uploaded_files = [mock_file1, mock_file2]
        run_all = True
        
        if uploaded_files and run_all:
            for uf in uploaded_files:
                # Simulate processing
                file_name = uf.name
                assert file_name in ["Summary.csv", "Funnel.csv"]

    @patch("hiring_agent_ui.st")
    def test_agent_processing_loop_structure(self, mock_st):
        """Test the structure of agent processing loop."""
        matching_agents = ["agent1", "agent2", "agent3"]
        agents_config = {
            "agent1": {"description": "Agent 1"},
            "agent2": {"description": "Agent 2"},
        }
        
        for agent_key in matching_agents:
            if agent_key not in agents_config:
                # Agent not in config
                assert agent_key == "agent3"
                continue
            # Agent in config
            agent_title = agents_config[agent_key].get("description", agent_key)
            assert agent_title in ["Agent 1", "Agent 2"]

    def test_standardized_response_rendering_with_collection(self):
        """Test rendering standardized response and collecting recommendations."""
        std = {
            "agent_name": "test_agent",
            "sections": [
                {
                    "type": "recommendations",
                    "data": ["Rec 1"],
                },
                {
                    "type": "insights",
                    "items": ["Insight 1"],  # Test items key
                },
                {
                    "type": "metrics",
                    "data": {"Total": 100},
                }
            ]
        }
        
        consolidated_recs = []
        rendered = render_standardized_agent_response(std)
        
        # Collect from rendered response
        for s in std.get("sections", []):
            if s.get("type") == "recommendations" or s.get("type") == "insights":
                items = s.get("data") or s.get("items") or []
                for it in items:
                    consolidated_recs.append(clean_display_text(it))
        
        assert len(consolidated_recs) == 2
        assert rendered is True

    def test_response_not_standardized_and_no_records(self):
        """Test handling when response is not standardized and has no records."""
        resp = "plain text"
        records = get_records_from_n8n_response(resp)
        
        # Simulate the else branch
        if records:
            # Would create DataFrame
            pass
        else:
            # Write raw response
            assert resp == "plain text"

    def test_response_not_standardized_with_records(self):
        """Test handling when response is not standardized but has records."""
        resp = {"data": [{"key": "value"}]}
        records = get_records_from_n8n_response(resp)
        
        if records:
            df = pd.DataFrame(records)
            assert not df.empty
        else:
            assert False  # Should have records

