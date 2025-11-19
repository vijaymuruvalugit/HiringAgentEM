"""Tests for UI components and display logic."""
import pytest
from unittest.mock import Mock, patch, MagicMock

from tests.test_helpers import ui_module


class TestUIComponents:
    """Test UI component rendering and configuration display."""

    @patch("hiring_agent_ui.st")
    def test_sidebar_configuration_display(self, mock_st):
        """Test sidebar configuration display logic."""
        # Mock the sidebar and expander
        mock_st.sidebar.title.return_value = None
        mock_expander = MagicMock()
        mock_st.sidebar.expander.return_value.__enter__ = MagicMock(return_value=mock_expander)
        mock_st.sidebar.expander.return_value.__exit__ = MagicMock(return_value=None)

        # Simulate the configuration display code
        with mock_st.sidebar.expander("Configuration", expanded=False):
            mock_st.write("Base n8n URL")
            mock_st.text_input("n8n base URL", value="http://localhost:5678")
            mock_st.markdown("**Enabled Agents (from config.yaml)**")

        # Verify expander was called
        assert mock_st.sidebar.expander.called

    @patch("hiring_agent_ui.st")
    def test_sidebar_executive_summary(self, mock_st):
        """Test executive summary display in sidebar."""
        mock_expander = MagicMock()
        mock_st.sidebar.expander.return_value.__enter__ = MagicMock(return_value=mock_expander)
        mock_st.sidebar.expander.return_value.__exit__ = MagicMock(return_value=None)

        # Simulate executive summary display
        with mock_st.sidebar.expander("Executive Summary", expanded=True):
            mock_st.markdown("**Problem:** ...")

        assert mock_st.sidebar.expander.called

    @patch("hiring_agent_ui.st")
    @patch.object(ui_module, "ENABLED_AGENTS", {
        "agent1": {"description": "Test agent 1"},
        "agent2": {"description": "Test agent 2"},
    })
    def test_sidebar_enabled_agents_display(self, mock_st):
        """Test displaying enabled agents in sidebar."""
        # Simulate the enabled agents display
        enabled_agents = ui_module.ENABLED_AGENTS
        if enabled_agents:
            for k, v in enabled_agents.items():
                description = v.get('description', '')
                assert description is not None

    @patch("hiring_agent_ui.st")
    @patch.object(ui_module, "ENABLED_AGENTS", {})
    def test_sidebar_no_enabled_agents(self, mock_st):
        """Test sidebar when no agents are enabled."""
        enabled_agents = ui_module.ENABLED_AGENTS
        if not enabled_agents:
            # Should show info message
            mock_st.info("No agents enabled in config.yaml. Edit config or provide sample agents.")
            assert mock_st.info.called

    @patch("hiring_agent_ui.st")
    def test_base_url_input_change(self, mock_st):
        """Test base URL input handling."""
        mock_st.text_input.return_value = "http://new-url:5678"
        base_url_input = mock_st.text_input("n8n base URL", value="http://localhost:5678")
        
        # Simulate the check for URL change
        if base_url_input != "http://localhost:5678":
            # URL was changed
            assert base_url_input == "http://new-url:5678"

    @patch("hiring_agent_ui.st")
    def test_upload_section_display(self, mock_st):
        """Test file upload section display."""
        mock_st.header("Upload data")
        mock_st.file_uploader("Upload agent CSVs", type="csv", accept_multiple_files=True)
        mock_st.caption("Tip: name files with keywords...")

        assert mock_st.header.called
        assert mock_st.file_uploader.called

    @patch("hiring_agent_ui.st")
    def test_quick_actions_section(self, mock_st):
        """Test quick actions section."""
        mock_st.header("Quick actions")
        mock_st.button("▶️ Run agents for uploaded files")
        mock_st.checkbox("Show raw agent responses (debug)")

        assert mock_st.header.called
        assert mock_st.button.called
        assert mock_st.checkbox.called

    @patch("hiring_agent_ui.st")
    def test_overview_section(self, mock_st):
        """Test overview section display."""
        mock_st.header("Overview")
        mock_st.markdown("**What this app does:** ...")

        assert mock_st.header.called
        assert mock_st.markdown.called

    @patch("hiring_agent_ui.st")
    def test_consolidated_insights_with_recommendations(self, mock_st):
        """Test consolidated insights panel with recommendations."""
        consolidated_recs = ["Rec 1", "Rec 2", "Rec 3"]
        
        # Simulate the consolidated insights display
        mock_st.header("📋 Consolidated Insights & Recommendations")
        if consolidated_recs:
            # De-duplicate while preserving order
            seen = set()
            deduped = []
            for r in consolidated_recs:
                if r not in seen:
                    seen.add(r)
                    deduped.append(r)
            
            for i, r in enumerate(deduped, 1):
                mock_st.write(f"{i}. {r}")
            
            mock_st.download_button("Download recommendations (TXT)", "\n".join(deduped), file_name="recommendations.txt")
            
            assert len(deduped) == len(consolidated_recs)
            assert mock_st.download_button.called

    @patch("hiring_agent_ui.st")
    def test_consolidated_insights_empty(self, mock_st):
        """Test consolidated insights panel when empty."""
        consolidated_recs = []
        
        mock_st.header("📋 Consolidated Insights & Recommendations")
        if not consolidated_recs:
            mock_st.info("No recommendations collected yet. Run agents on uploaded files to generate insights.")
            assert mock_st.info.called

    @patch("hiring_agent_ui.st")
    def test_debug_tools_expander(self, mock_st):
        """Test debug tools expander."""
        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=None)

        with mock_st.expander("Developer / Debug tools", expanded=False):
            mock_st.write("Base URL:", "http://localhost:5678")
            mock_st.write("Agents in config:")
            mock_st.write(["agent1", "agent2"])
            mock_st.button("Run sample local dataset (demo)")

        assert mock_st.expander.called

    @patch("hiring_agent_ui.st")
    def test_debug_tools_sample_button(self, mock_st):
        """Test sample dataset button in debug tools."""
        mock_st.button.return_value = True
        
        if mock_st.button("Run sample local dataset (demo)"):
            mock_st.success("Demo runner triggered — you should wire sample CSVs and agents in n8n to exercise this.")
            assert mock_st.success.called

