# ColdMail AI V3

Evidence-grounded AI outreach system built around LangGraph. V3 upgrades the original pipeline from simple skill overlap and template/LLM generation into a more reliable research → match → retrieve → generate → review workflow.

## V3 Architecture
```text
Resume / JD / Recipient
        |
        v
   Input Parsing
        |
        v
  Company Research --------> Source-backed Evidence
        |
        v
 Semantic Resume <-> JD Matching
        |
        v
 Hybrid Retrieval (BM25 + Dense)
        |
        v
 Evidence-aware LLM Generation
        |
        v
 Quality + Grounding Review
        |
   +----+----+
   |         |
 rewrite    approve
   |         |
   +----+----+
        |
        v
 Human Approval -> Send
```

## V3 Improvements
- **Evidence-backed company research** using public company/careers pages with `trafilatura` extraction.
- **Semantic resume ↔ JD matching** using sentence-transformer embeddings plus normalized exact skill matching.
- **Hybrid retrieval** combining BM25 lexical retrieval with dense embeddings.
- **Metadata-aware ChromaDB** records for separating companies from prior emails.
- **Structured AI outputs** validated with Pydantic schemas.
- **Evidence-aware generation**: company-specific claims are restricted to supplied research evidence.
- **LLM quality review** covering personalization, clarity, grounding, hallucination risk, and spam risk.
- **Deterministic quality gates** for missing recipients, excessive length, spam signals, and unsupported company claims.
- **LangGraph parsing flow** now parses inputs before research and preserves a richer existing user profile.

## Architecture Components
```text
LangGraph StateGraph
├── Resume Parser
├── Job Description Parser
├── Evidence-backed Research Agent
├── Semantic Match Agent
├── Hybrid Retrieval
├── Evidence-aware Writer
├── Quality / Grounding Reviewer
├── Human Approval
└── Email Sender
```

## Services
- **Redis** - caching layer
- **ChromaDB** - persistent vector store
- **Sentence Transformers** - dense embeddings
- **BM25** - lexical retrieval
- **PostgreSQL** - persistent application data
- **FastAPI** - REST API
- **Streamlit** - web UI
- **Groq** - current LLM provider (model can be configured with `GROQ_MODEL`)

## Quick Start
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure your environment variables
cp .env.example .env

streamlit run ui/app.py
# or
uvicorn api.main:app --reload
```

## Required Keys
| Key | Purpose |
|-----|---------|
| `GROQ_API_KEY` | LLM generation and review |
| `SMTP_PASSWORD` | Email delivery |

## Testing
```bash
pytest -q
```

## Roadmap
- [x] Semantic matching
- [x] Source-backed research
- [x] Hybrid retrieval
- [x] Structured generation/review
- [x] Grounding gates
- [ ] Dedicated reranker model
- [ ] Retrieval/generation benchmark dataset
- [ ] Campaign analytics and A/B testing
- [ ] Follow-up and reply intelligence
- [ ] Gemini provider
