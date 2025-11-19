# Testing n8n Files

## Can we test n8n JSON files?

**Short answer:** Not directly for code coverage, but we can validate them.

## Why n8n files don't count toward coverage

n8n workflow files (`.json`) are **configuration files**, not executable Python code. Code coverage tools like `pytest-cov` only measure coverage of executable code (Python, JavaScript, etc.), not JSON configuration files.

## What we CAN do with n8n files

1. **JSON Schema Validation**: Validate that n8n workflow files have the correct structure
2. **Webhook Path Verification**: Check that webhook paths in n8n files match `config.yaml`
3. **Required Node Validation**: Verify that required nodes (Webhook, Code, HTTP Request, etc.) exist
4. **Integration Testing**: Test the actual n8n workflows by calling webhooks with sample data

## Example: n8n File Validation Test

```python
def test_n8n_workflow_structure():
    """Validate n8n workflow JSON structure."""
    import json
    from pathlib import Path
    
    workflow_file = Path("n8n_flows/hiring_tracker/sourcing_quality_agent.json")
    with open(workflow_file) as f:
        workflow = json.load(f)
    
    # Validate required fields
    assert "nodes" in workflow
    assert "connections" in workflow
    
    # Check for required nodes
    node_types = [node.get("type") for node in workflow.get("nodes", [])]
    assert "n8n-nodes-base.webhook" in node_types
    assert "n8n-nodes-base.code" in node_types
```

## Current Coverage Status

- **Python Code Coverage**: 77.19% (target: 85%)
- **n8n Files**: Not included in coverage (configuration files)

## Recommendations

1. **For n8n files**: Create separate validation tests (not coverage-based)
2. **For Python code**: Continue improving test coverage of the frontend code
3. **Integration tests**: Test n8n workflows end-to-end by calling webhooks

## Missing Coverage

The remaining uncovered lines (77% → 85% gap) are primarily:
- **Lines 303-362**: Main processing loop (requires Streamlit runtime)
- **Lines 371-379**: Consolidated insights panel (requires Streamlit runtime)
- **Lines 151, 158**: Sidebar UI components (requires Streamlit runtime)

These are difficult to test without running Streamlit, but we can:
1. Extract logic into testable functions
2. Use more sophisticated mocking
3. Create integration tests that run with Streamlit

