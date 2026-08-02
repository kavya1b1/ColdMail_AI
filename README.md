# ColdMail AI Pro v2.0

Production-grade multi-agent cold outreach system with LangGraph orchestration .

## Architecture

```
LangGraph StateGraph
├── Supervisor Node (routing logic)
├── Research Node (web scraping + cache)
├── Parse Nodes (resume + job description)
├── Match Node (skill matching + embeddings)
├── Write Node (Groq LLM + RAG context)
├── Review Node (quality check)
├── Human Approval Node (checkpoint)
└── Send Node (SMTP + resume attachment)
```

## Services
- **Redis Cache** - Company research & LLM response caching
- **ChromaDB** - Vector store for RAG and semantic search
- **PostgreSQL** - Persistent data storage
- **FastAPI** - REST API backend
- **Streamlit** - Web UI

## Quick Start

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your keys

# Run UI
streamlit run ui/app.py

# Run API
uvicorn api.main:app --reload

# Run with Docker
docker-compose up --build
```

## Required Keys

| Key | Purpose | Get From |
|-----|---------|----------|
| GROQ_API_KEY | AI email generation | https://console.groq.com/keys |
| SMTP_PASSWORD | Send emails | https://myaccount.google.com/apppasswords |

## Features

- ✅ LangGraph StateGraph (real MCP orchestration)
- ✅ Resume Parser (PyMuPDF)
- ✅ Job Description Parser
- ✅ Reviewer Agent (LLM quality scoring)
- ✅ Redis caching
- ✅ ChromaDB RAG
- ✅ PostgreSQL database
- ✅ FastAPI backend
- ✅ Docker support
- ✅ Retry logic (3 attempts)
- ✅ Human approval checkpoint
