"""Pytest fixtures and test configuration."""
import pytest
import pandas as pd
from pathlib import Path
from io import StringIO, BytesIO
import sys

# Add parent directory to path to import frontend module
sys.path.insert(0, str(Path(__file__).parent.parent))

# Sample data paths
SAMPLE_DATA_DIR = Path(__file__).parent.parent / "sample_inputs"


@pytest.fixture
def sample_data_dir():
    """Return path to sample data directory."""
    return SAMPLE_DATA_DIR


@pytest.fixture
def sample_summary_csv(sample_data_dir):
    """Load sample Summary.csv as file-like object."""
    csv_path = sample_data_dir / "Summary.csv"
    if csv_path.exists():
        with open(csv_path, "rb") as f:
            content = f.read()
        return BytesIO(content)
    return None


@pytest.fixture
def sample_funnel_csv(sample_data_dir):
    """Load sample Funnel.csv as file-like object."""
    csv_path = sample_data_dir / "Funnel.csv"
    if csv_path.exists():
        with open(csv_path, "rb") as f:
            content = f.read()
        return BytesIO(content)
    return None


@pytest.fixture
def sample_feedback_csv(sample_data_dir):
    """Load sample Feedback.csv as file-like object."""
    csv_path = sample_data_dir / "Feedback.csv"
    if csv_path.exists():
        with open(csv_path, "rb") as f:
            content = f.read()
        return BytesIO(content)
    return None


@pytest.fixture
def sample_config():
    """Return sample config dictionary."""
    return {
        "n8n": {
            "base_url": "http://localhost:5678",
            "agents": {
                "sourcing_quality_agent": {
                    "webhook_path": "/webhook/test-1",
                    "description": "Test sourcing agent",
                    "enabled": True,
                    "filename_keywords": ["summary"],
                },
                "rejection_pattern_agent": {
                    "webhook_path": "/webhook/test-2",
                    "description": "Test rejection agent",
                    "enabled": True,
                    "filename_keywords": ["funnel"],
                },
                "panel_load_balancer": {
                    "webhook_path": "/webhook/test-3",
                    "description": "Test panel agent",
                    "enabled": True,
                    "filename_keywords": ["feedback"],
                },
            },
        },
        "default_agent": "none",
    }


@pytest.fixture
def mock_standardized_response():
    """Return a mock standardized agent response."""
    return {
        "agent_name": "test_agent",
        "display_title": "Test Agent Output",
        "sections": [
            {
                "type": "metrics",
                "title": "Summary",
                "data": {
                    "Total Candidates": 100,
                    "Rejection Rate": "25%",
                    "Avg Score": 7.5,
                },
            },
            {
                "type": "table",
                "title": "Source Performance",
                "columns": ["Source", "Candidates", "Rejections"],
                "rows": [
                    {"Source": "LinkedIn", "Candidates": 50, "Rejections": 10},
                    {"Source": "Referral", "Candidates": 30, "Rejections": 5},
                ],
            },
            {
                "type": "insights",
                "title": "Actionable Insights",
                "data": [
                    "LinkedIn shows higher rejection rates",
                    "Referral sources perform better",
                ],
            },
            {
                "type": "recommendations",
                "title": "Recommendations",
                "data": [
                    "Focus on referral sources",
                    "Review LinkedIn screening process",
                ],
            },
        ],
    }


@pytest.fixture
def mock_legacy_response():
    """Return a mock legacy n8n response format."""
    return {
        "sources": [
            {"Source": "LinkedIn", "Candidates": 50, "Rejections": 10},
            {"Source": "Referral", "Candidates": 30, "Rejections": 5},
        ]
    }

