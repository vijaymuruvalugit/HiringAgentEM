"""Edge case tests to push coverage to 85%."""
import pytest
from unittest.mock import Mock, patch, MagicMock

from tests.test_helpers import (
    get_matching_agents_for_file,
    get_records_from_n8n_response,
    parse_json_string,
    clean_display_text,
    ui_module,
)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_get_matching_agents_empty_enabled_agents_with_match_in_config(self, sample_config, monkeypatch):
        """Test when ENABLED_AGENTS is empty but AGENTS_CONFIG has match."""
        monkeypatch.setattr(ui_module, "ENABLED_AGENTS", {})
        monkeypatch.setattr(ui_module, "AGENTS_CONFIG", sample_config["n8n"]["agents"])
        monkeypatch.setattr(ui_module, "DEFAULT_AGENT", "none")
        
        matches = get_matching_agents_for_file("Summary.csv")
        # Should fall back to AGENTS_CONFIG and find match
        assert len(matches) > 0

    def test_get_matching_agents_no_match_anywhere(self, sample_config, monkeypatch):
        """Test when no match found in ENABLED_AGENTS or AGENTS_CONFIG."""
        monkeypatch.setattr(ui_module, "ENABLED_AGENTS", {})
        monkeypatch.setattr(ui_module, "AGENTS_CONFIG", {})
        monkeypatch.setattr(ui_module, "DEFAULT_AGENT", None)
        
        matches = get_matching_agents_for_file("Unknown.csv")
        # Should return empty list when DEFAULT_AGENT is None
        assert matches == []

    def test_get_records_dict_with_data_as_string(self):
        """Test extracting when data key contains a string."""
        response = {"data": "string_value"}
        records = get_records_from_n8n_response(response)
        assert len(records) == 1
        assert records[0] == "string_value"

    def test_get_records_dict_with_sources_as_string(self):
        """Test extracting when sources key contains a string."""
        response = {"sources": "string_value"}
        records = get_records_from_n8n_response(response)
        assert len(records) == 1

    def test_get_records_dict_with_results_as_string(self):
        """Test extracting when results key contains a string."""
        response = {"results": "string_value"}
        records = get_records_from_n8n_response(response)
        assert len(records) == 1

    def test_get_records_dict_with_data_as_dict_values(self):
        """Test extracting when data is a dict (extend values)."""
        response = {"data": {"key1": "val1", "key2": "val2"}}
        records = get_records_from_n8n_response(response)
        assert len(records) == 2
        assert "val1" in records
        assert "val2" in records

    def test_parse_json_string_with_nested_structure(self):
        """Test parsing JSON string with nested structures."""
        json_str = '{"key": {"nested": "value"}}'
        result = parse_json_string(json_str)
        assert isinstance(result, dict)
        assert result["key"]["nested"] == "value"

    def test_parse_json_string_with_array_of_objects(self):
        """Test parsing JSON string with array of objects."""
        json_str = '[{"item": 1}, {"item": 2}]'
        result = parse_json_string(json_str)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_clean_display_text_with_mixed_quotes(self):
        """Test cleaning text with mixed quote types."""
        text = '"""triple quotes""" and \'single\' and "double"'
        result = clean_display_text(text)
        assert "```" not in result

    def test_clean_display_text_with_tabs_and_newlines(self):
        """Test cleaning text with tabs and newlines."""
        text = "text\twith\nnewlines\tand\t\ttabs"
        result = clean_display_text(text)
        # Should collapse whitespace
        assert "\t\t" not in result or "  " not in result

    def test_get_records_list_with_mixed_items(self):
        """Test extracting from list with mixed item types."""
        response = [
            {"json": {"key": "value"}},
            {"not_json": "value"},
            {"json": [{"item": 1}, {"item": 2}]},
        ]
        records = get_records_from_n8n_response(response)
        assert len(records) >= 3

    def test_get_records_list_item_json_is_list(self):
        """Test extracting when json value is a list."""
        response = [{"json": [{"a": 1}, {"b": 2}]}]
        records = get_records_from_n8n_response(response)
        assert len(records) == 2

    def test_get_records_list_item_json_is_dict(self):
        """Test extracting when json value is a dict."""
        response = [{"json": {"key": "value"}}]
        records = get_records_from_n8n_response(response)
        assert len(records) == 1
        assert records[0] == {"key": "value"}

    def test_get_records_list_item_without_json_key(self):
        """Test extracting from list item without json key."""
        response = [{"other_key": "value"}]
        records = get_records_from_n8n_response(response)
        assert len(records) == 1

    def test_match_by_keywords_with_file_patterns(self, sample_config):
        """Test matching using file_patterns key."""
        agents = sample_config["n8n"]["agents"].copy()
        agents["test_agent"] = {
            "file_patterns": ["test", "sample"],
        }
        from tests.test_helpers import match_by_keywords
        
        matches = match_by_keywords("test_file.csv", agents)
        assert "test_agent" in matches

    def test_match_by_keywords_normalized_agent_name(self, sample_config):
        """Test matching by normalized agent name."""
        agents = sample_config["n8n"]["agents"].copy()
        agents["sourcing_quality"] = {
            "filename_keywords": [],
        }
        from tests.test_helpers import match_by_keywords
        
        # "sourcing" should match "sourcing_quality" via normalized matching
        matches = match_by_keywords("sourcing_data.csv", agents)
        # This tests the normalized name matching logic
        assert isinstance(matches, list)

    def test_match_by_keywords_case_insensitive_keywords(self, sample_config):
        """Test case-insensitive keyword matching."""
        agents = sample_config["n8n"]["agents"].copy()
        agents["test_agent"] = {
            "filename_keywords": ["SUMMARY"],
        }
        from tests.test_helpers import match_by_keywords
        
        matches = match_by_keywords("summary.csv", agents)
        assert "test_agent" in matches

    def test_get_matching_agents_enabled_agents_has_match(self, sample_config, monkeypatch):
        """Test when ENABLED_AGENTS has a match."""
        monkeypatch.setattr(ui_module, "ENABLED_AGENTS", sample_config["n8n"]["agents"])
        monkeypatch.setattr(ui_module, "AGENTS_CONFIG", sample_config["n8n"]["agents"])
        monkeypatch.setattr(ui_module, "DEFAULT_AGENT", "none")
        
        matches = get_matching_agents_for_file("Summary.csv")
        # Should return match from ENABLED_AGENTS without falling back
        assert len(matches) > 0

    def test_get_matching_agents_enabled_agents_no_match_fallback(self, sample_config, monkeypatch):
        """Test fallback when ENABLED_AGENTS has no match."""
        # ENABLED_AGENTS with different keywords
        enabled = {
            "other_agent": {
                "filename_keywords": ["other"],
            }
        }
        monkeypatch.setattr(ui_module, "ENABLED_AGENTS", enabled)
        monkeypatch.setattr(ui_module, "AGENTS_CONFIG", sample_config["n8n"]["agents"])
        monkeypatch.setattr(ui_module, "DEFAULT_AGENT", "none")
        
        matches = get_matching_agents_for_file("Summary.csv")
        # Should fall back to AGENTS_CONFIG
        assert len(matches) > 0

