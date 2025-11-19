# Hiring Agent — Multi-Agent Insights Platform

A comprehensive hiring intelligence platform that uses multiple specialized AI agents to analyze hiring data and provide actionable insights for Engineering Managers. The system processes CSV files through n8n workflows, generates analytics, and uses LLMs to produce recommendations.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Running Locally](#running-locally)
- [Configuration](#configuration)
- [Data Format](#data-format)
- [Agents](#agents)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

This platform provides Engineering Managers with real-time visibility into:
- **Sourcing Quality**: Which channels produce the best candidates
- **Rejection Patterns**: Why candidates are rejected and where in the funnel
- **Panel Workload**: Interviewer capacity and load balancing
- **Offer Analytics**: Why candidates reject offers
- **Pipeline Health**: Conversion rates and bottlenecks
- **Open Roles**: Hiring needs and prioritization

## 🏗️ Architecture

The system consists of three main components:

### 1. **Streamlit Frontend** (`frontend/hiring-agent-ui.py`)
- Web-based UI for uploading CSV files
- Displays agent results with metrics, tables, charts, and recommendations
- Consolidates insights from all agents

### 2. **n8n Workflows** (`n8n_flows/`)
- Orchestrates agent workflows
- Processes CSV data and generates analytics
- Integrates with LLM (Ollama) for insights and recommendations
- Each agent is a separate n8n workflow with a webhook endpoint

### 3. **LLM Backend** (Ollama)
- Generates actionable insights and recommendations
- Uses local model (gemma2:2b) for privacy and cost efficiency

### Data Flow

```
CSV Upload → Streamlit UI → n8n Webhook → Agent Processing → LLM Analysis → Formatted Response → UI Display
```

## 📦 Prerequisites

Before setting up, ensure you have:

1. **Python 3.8+** installed
   ```bash
   python3 --version
   ```

2. **n8n** installed and running
   - Download from [n8n.io](https://n8n.io/)
   - Or install via npm: `npm install n8n -g`
   - n8n should be accessible at `http://localhost:5678`

3. **Ollama** installed with gemma2:2b model
   ```bash
   # Install Ollama from https://ollama.ai/
   ollama pull gemma2:2b
   ```
   - Ollama should be running at `http://localhost:11434`

4. **Git** (for cloning the repository)

## 🚀 Installation & Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/vijaymuruvalugit/HiringAgentEM.git
cd HiringAgentEM
```

### Step 2: Create Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### Step 3: Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `streamlit` - Web UI framework
- `pandas` - Data processing
- `requests` - HTTP requests to n8n
- `pyyaml` - Configuration file parsing
- `pytest` - Testing framework

### Step 4: Set Up n8n Workflows

1. **Start n8n**:
   ```bash
   n8n start
   ```
   n8n will be available at `http://localhost:5678`

2. **Import Workflows**:
   - Open n8n UI at `http://localhost:5678`
   - For each workflow in `n8n_flows/`:
     - Click "Import from File"
     - Select the JSON file (e.g., `n8n_flows/hiring_tracker/sourcing_quality_agent.json`)
     - Click "Import"
     - **Activate the workflow** (toggle switch in top-right)
     - **Copy the webhook URL** from the Webhook node

3. **Update `config.yaml`**:
   - Replace the `webhook_path` values with your actual webhook IDs
   - The webhook ID is the UUID in the webhook URL (e.g., `/webhook/35f7df3a-1934-4e5f-82ac-cdedd7cb99e7`)

### Step 5: Configure Ollama LLM

1. **Start Ollama**:
   ```bash
   ollama serve
   ```

2. **Verify Model**:
   ```bash
   ollama list
   # Should show gemma2:2b
   ```

3. **Test Connection**:
   ```bash
   curl http://localhost:11434/api/chat
   ```

### Step 6: Generate Sample Data (Optional)

If you need sample data for testing:

```bash
# Generate OpenRoles.csv
cd data_generator
python3 generate_open_roles.py

# For other sample data, use the Jupyter notebook
jupyter notebook sameple-data-generator.ipynb
```

Sample CSV files are already provided in `sample_inputs/`:
- `Summary.csv` - Candidate summary data
- `Feedback.csv` - Interview feedback
- `Funnel.csv` - Stage-by-stage funnel data
- `OpenRoles.csv` - Open job positions

## 🏃 Running Locally

### 1. Start n8n

```bash
n8n start
```

Verify it's running: Open `http://localhost:5678` in your browser.

### 2. Start Ollama

```bash
ollama serve
```

Verify it's running: `curl http://localhost:11434/api/chat`

### 3. Start Streamlit App

```bash
# Make sure virtual environment is activated
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows

# Run Streamlit
streamlit run frontend/hiring-agent-ui.py
```

The app will open automatically in your browser at `http://localhost:8501`

### 4. Use the Application

1. **Upload CSV files**:
   - Click "Upload agent CSVs" in the UI
   - Select your CSV files (Summary.csv, Feedback.csv, Funnel.csv, OpenRoles.csv)
   - Files are automatically matched to agents based on filename keywords

2. **Run Agents**:
   - Click "▶️ Run agents for uploaded files"
   - Wait for agents to process (you'll see spinners)

3. **View Results**:
   - Results are displayed grouped by agent category
   - Each agent shows:
     - Summary metrics
     - Data tables with charts
     - Actionable insights (LLM-generated)
     - Recommendations (LLM-generated)

4. **Consolidated Insights**:
   - Scroll to the bottom to see all recommendations consolidated

## ⚙️ Configuration

### `config.yaml`

The main configuration file defines all agents and their webhooks:

```yaml
n8n:
  base_url: "http://localhost:5678"  # n8n base URL
  
  agents:
    sourcing_quality_agent:
      webhook_path: "/webhook/YOUR_WEBHOOK_ID"
      description: "Analyzes sourcing channel quality"
      enabled: true
      filename_keywords:
        - summary
```

**Key Settings**:
- `base_url`: n8n server URL (default: `http://localhost:5678`)
- `webhook_path`: The webhook path from n8n (UUID after `/webhook/`)
- `enabled`: Set to `false` to disable an agent
- `filename_keywords`: Keywords in filename that trigger this agent

### File Matching

Files are matched to agents based on keywords in the filename:
- `Summary.csv` → `sourcing_quality_agent`, `offer_rejection_agent`
- `Feedback.csv` → `panel_load_balancer`
- `Funnel.csv` → `rejection_pattern_agent`, `pipeline_health_agent`
- `OpenRoles.csv` → `open_roles_agent`

## 📊 Data Format

### Summary.csv
Required columns:
- `CandidateName`, `AppliedRole`, `InterviewStage`, `Status`
- `Source`, `ResumeScore`, `SalaryExpectation`
- `ApplicationDate`, `DaysInPipeline`

### Feedback.csv
Required columns:
- `Interviewer` (or `Panelist`), `InterviewDate`
- `InterviewStage`, `FeedbackText`

### Funnel.csv
Required columns:
- `CandidateName`, `FunnelStage` (or `InterviewStage`), `Status`
- `RejectionReason`, `Interviewer`

### OpenRoles.csv
Required columns:
- `RoleName`, `Department`, `Level`
- `TargetHeadcount`, `FilledCount`, `OpenPositions`
- `PostingDate`, `Status`, `Priority`, `DaysOpen`

## 🤖 Agents

### 1. Sourcing Quality Agent
**File**: `Summary.csv`  
**Purpose**: Analyzes which sourcing channels produce the best candidates  
**Output**: Source performance table, rejection rates, resume scores

### 2. Rejection Pattern Agent
**File**: `Funnel.csv`  
**Purpose**: Identifies why and where candidates are rejected  
**Output**: Rejections by stage, by interviewer, top rejection reasons

### 3. Panel Load Balancer
**File**: `Feedback.csv`  
**Purpose**: Analyzes interviewer workload and identifies overloaded panelists  
**Output**: Panelist workload table, stage coverage, rebalancing recommendations

### 4. Offer Rejection Insight Agent
**File**: `Summary.csv`  
**Purpose**: Analyzes why candidates reject offers  
**Output**: Decline reasons, delay analysis, source analysis

### 5. Pipeline Health Agent
**File**: `Funnel.csv`  
**Purpose**: Monitors overall pipeline health and conversion rates  
**Output**: Stage conversion overview, bottlenecks, conversion metrics

### 6. Open Roles Agent
**File**: `OpenRoles.csv`  
**Purpose**: Analyzes open positions and hiring needs  
**Output**: Role overview, department summary, priority breakdown, roles needing attention

## 🧪 Testing

Run the test suite:

```bash
# Activate virtual environment first
source venv/bin/activate

# Run all tests
pytest

# Run with coverage report
pytest --cov=frontend --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
# or
start htmlcov/index.html  # Windows
```

**Test Coverage**: Currently at 85%+ coverage

## 🔧 Troubleshooting

### Issue: "404 Client Error" when calling agents

**Solution**:
1. Verify n8n is running: `http://localhost:5678`
2. Check that workflows are **activated** in n8n
3. Verify webhook paths in `config.yaml` match the webhook IDs in n8n
4. Ensure webhook paths start with `/webhook/` (not full URL)

### Issue: "ECONNREFUSED" when calling LLM

**Solution**:
1. Verify Ollama is running: `curl http://localhost:11434/api/chat`
2. Check n8n HTTP Request node uses `http://127.0.0.1:11434` (not `::1` or `localhost`)
3. Verify model is installed: `ollama list`

### Issue: Files not matching to agents

**Solution**:
1. Check filename contains keywords from `config.yaml`
2. Keywords are case-insensitive
3. Example: `Summary.csv` matches `summary` keyword

### Issue: JSON parsing errors in UI

**Solution**:
1. Check n8n workflow returns standardized format:
   ```json
   {
     "agent_name": "agent_name",
     "display_title": "Title",
     "sections": [...]
   }
   ```
2. Verify LLM response is properly parsed in "Merge Responses" node
3. Check browser console for errors

### Issue: Streamlit not starting

**Solution**:
1. Verify virtual environment is activated
2. Check all dependencies installed: `pip install -r requirements.txt`
3. Try: `streamlit run frontend/hiring-agent-ui.py --server.port 8501`

### Issue: Agents showing raw JSON instead of formatted output

**Solution**:
1. This is usually a parsing issue - the frontend should handle it automatically
2. If persists, check that n8n workflows return proper JSON structure
3. Verify `sections` array contains objects with `type`, `title`, and `data` fields

## 📁 Project Structure

```
hiring_agent_em/
├── frontend/
│   └── hiring-agent-ui.py      # Streamlit UI application
├── n8n_flows/                   # n8n workflow definitions
│   ├── hiring_tracker/         # Hiring tracker agents
│   └── offer_analysis/         # Offer & funnel agents
├── data_generator/             # Scripts to generate sample data
├── sample_inputs/              # Sample CSV files
├── tests/                      # Test suite
├── config.yaml                 # Agent configuration
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 🔐 Security Notes

- This is a local development setup
- n8n and Ollama run on localhost (not exposed to internet)
- For production, configure proper authentication and HTTPS
- CSV files may contain sensitive data - handle appropriately

## 📝 License

[Add your license information here]

## 👥 Contributing

[Add contribution guidelines if applicable]

## 📧 Support

For issues or questions, please open an issue on GitHub.

---

**Happy Hiring! 🚀**

