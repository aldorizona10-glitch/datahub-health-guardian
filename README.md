# DataHub Health Guardian Agent 🏥

An autonomous AI agent that monitors your data ecosystem through DataHub, detects anomalies, auto-tags problematic assets, and generates incident reports — all grounded in real DataHub context.

## 🏆 Built for [Build with DataHub: The Agent Hackathon](https://datahub.devpost.com)

## Features

- **🔍 Data Quality Scanner** — Queries DataHub for freshness issues, schema drift, missing metadata
- **🔗 Lineage Impact Analyzer** — Traces upstream/downstream impact when issues are found
- **🏷️ Auto-Tagger** — Automatically tags affected datasets with severity labels
- **📊 Incident Report Generator** — Creates detailed reports with root cause analysis
- **🔔 Alert System** — Notifies data owners about issues
- **🛠️ Self-Healing Suggestions** — Proposes SQL fixes or pipeline patches

## Architecture

```
┌─────────────────────────────────┐
│     Next.js Dashboard           │
│  (Real-time health monitoring)  │
├─────────────────────────────────┤
│     FastAPI Backend             │
│  (Agent orchestration + API)    │
├─────────────────────────────────┤
│     Agent Core (Python)         │
│  ├── Google Gemini AI           │
│  ├── DataHub MCP Tools          │
│  └── Autonomous Loop            │
├─────────────────────────────────┤
│     DataHub Platform            │
│  (Metadata, Lineage, Quality)   │
└─────────────────────────────────┘
```

## Quick Start

```bash
# 1. Clone
git clone https://github.com/aldorizona10-glitch/datahub-health-guardian.git
cd datahub-health-guardian

# 2. Setup Python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# Edit .env with your DataHub and Gemini API keys

# 4. Run Agent
python -m guardian.agent

# 5. Run Dashboard
cd dashboard && npm install && npm run dev
```

## Configuration

Set the following environment variables in `.env`:

```env
DATAHUB_GMS_URL=http://localhost:8080
DATAHUB_TOKEN=your_datahub_token
GOOGLE_API_KEY=your_gemini_api_key
```

## Tech Stack

- **Agent**: Python 3.11+, Google Gemini API, DataHub Agent Context Kit
- **Backend**: FastAPI, uvicorn
- **Frontend**: Next.js 14, React, Tailwind CSS
- **DataHub**: MCP Server, Agent Context Kit, DataHub Skills

## License

MIT
