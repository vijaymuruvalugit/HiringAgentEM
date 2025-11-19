# Coverage Analysis: Path to 85%

## Current Status
- **Current Coverage**: 77.19%
- **Target**: 85%
- **Gap**: ~21 lines need to be covered

## Missing Lines Breakdown

### Hard to Test (Module-level Streamlit code)
- **Lines 303-362** (60 lines): Main processing loop
  - Executes when `uploaded_files and run_all` is True
  - Requires Streamlit runtime with actual file uploads
  - Contains: file iteration, agent matching, webhook calls, response processing

- **Lines 371-379** (9 lines): Consolidated insights panel
  - Executes at module level
  - Displays deduplicated recommendations

- **Lines 151, 158** (2 lines): Sidebar UI
  - BASE_URL assignment and info message

- **Line 392**: End of file marker

**Total**: 72 lines (but we only need ~21 more to reach 85%)

## Solutions to Reach 85%

### Option 1: Extract Logic into Testable Functions (Recommended)
Refactor the main processing loop into a testable function:

```python
def process_uploaded_files(uploaded_files, run_all):
    """Process uploaded files and return results."""
    # Extract logic from lines 303-362
    consolidated_recs = []
    # ... processing logic ...
    return consolidated_recs
```

**Pros**: Makes code more testable and maintainable
**Cons**: Requires code refactoring

### Option 2: Advanced Mocking with Module Import
Use importlib to import the module and trigger execution with mocks:

```python
def test_main_loop_with_mocks():
    with patch('streamlit.file_uploader') as mock_upload:
        with patch('streamlit.button') as mock_button:
            # Import module to trigger execution
            import frontend.hiring_agent_ui
```

**Pros**: Tests actual code paths
**Cons**: Complex, may have side effects

### Option 3: Integration Tests with Streamlit
Create integration tests that actually run Streamlit:

```python
def test_with_streamlit_runtime():
    # Use streamlit.testing or similar
    # Actually run the app with test data
```

**Pros**: Tests real behavior
**Cons**: Requires Streamlit testing framework, slower

## Recommendation

**Extract the main processing logic** into a testable function. This would:
1. Improve code maintainability
2. Make testing easier
3. Allow us to reach 85%+ coverage
4. Follow best practices (separation of concerns)

## n8n Files Testing

n8n JSON files are **configuration files**, not executable code, so they don't count toward Python code coverage. However, we can:

1. **Validate JSON structure** (schema validation)
2. **Check webhook paths** match config.yaml
3. **Verify required nodes** exist
4. **Integration test** by calling actual webhooks

See `TESTING_N8N_FILES.md` for details.

## Next Steps

To reach 85% coverage, I recommend:
1. Extract main processing loop into `process_uploaded_files()` function
2. Extract consolidated insights into `format_consolidated_insights()` function
3. Add tests for these extracted functions
4. Keep UI rendering code separate (harder to test, but less critical)

Would you like me to proceed with Option 1 (extracting logic into testable functions)?

