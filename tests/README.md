# Test Suite for Hiring Agent

This directory contains comprehensive tests for the hiring agent frontend application.

## Coverage

Current test coverage: **76.81%**

The test suite includes:
- Configuration loading tests
- Agent matching logic tests
- Response parsing tests (JSON, markdown, etc.)
- n8n agent calling tests (mocked)
- Rendering and data extraction tests
- Integration tests with sample data
- Streamlit integration tests

## Running Tests

```bash
# Run all tests with coverage
pytest tests/ -v --cov=frontend --cov-report=term-missing --cov-report=html

# Run specific test file
pytest tests/test_config_loading.py -v

# Run with coverage threshold (currently set to 75%)
pytest tests/ --cov=frontend --cov-fail-under=75
```

## Test Structure

- `test_config_loading.py`: Tests for YAML config loading
- `test_agent_matching.py`: Tests for file-to-agent matching logic
- `test_response_parsing.py`: Tests for parsing n8n responses and LLM output
- `test_n8n_calling.py`: Tests for calling n8n webhooks (mocked)
- `test_rendering.py`: Tests for rendering standardized agent responses
- `test_integration.py`: Integration tests using sample CSV files
- `test_additional_coverage.py`: Additional edge case tests
- `test_main_processing.py`: Tests for main processing logic
- `test_streamlit_integration.py`: Tests for Streamlit-specific functionality

## Sample Data

Tests use sample data from `sample_inputs/`:
- `Summary.csv`
- `Funnel.csv`
- `Feedback.csv`

## Coverage Gaps

The following lines are not covered (mostly UI/Streamlit-specific code):
- Lines 151, 158: Sidebar UI configuration display
- Line 222: DEFAULT_AGENT fallback edge case
- Lines 303-362: Main processing loop (requires Streamlit runtime)
- Lines 371-379: Consolidated insights panel display
- Line 392: End of file marker

These gaps are primarily due to Streamlit's runtime requirements and UI rendering code that's difficult to test in isolation.

