# LangChain Pipeline — Event-Driven Microservices + MLOps

Full-stack application demonstrating **LangChain orchestration**, **AWS Bedrock integration**, **event-driven microservices**, and **MLOps** practices.

## Architecture

```
┌──────────────────────────────────────────────┐
│               API Gateway (FastAPI)           │
├──────────────┬───────────────┬───────────────┤
│  Document    │   Analysis    │    Report     │
│  Service     │   Service     │    Service    │
│  (CRUD)      │  (LangChain)  │  (Generator)  │
├──────────────┴───────────────┴───────────────┤
│           Event Bus (In-Memory Pub/Sub)       │
├──────────────────────────────────────────────┤
│     MLOps: Prompt Registry │ Metrics │ Logs   │
└──────────────────────────────────────────────┘
```

## Tech Stack

| Layer     | Technology                                   |
| --------- | -------------------------------------------- |
| Backend   | FastAPI, LangChain, Pydantic, Python 3.11+   |
| AI/LLM    | AWS Bedrock (Claude), Mock LLM fallback       |
| MLOps     | Versioned Prompts, Quality Metrics, Logging   |
| Frontend  | React 18, Vite                                |
| Infra     | Docker, Vercel                                |

## Quick Start

```bash
# Backend
pip install ".[dev]"
uvicorn gateway.main:app --reload

# Frontend
cd frontend && npm install && npm run dev

# Tests
python -m pytest tests/ -v
```

## Features

- **3 Microservices** communicating via event bus
- **LangChain Chains**: Extract → Quality Review → Report generation
- **LangChain Tools**: Keyword extraction, risk detection, sentiment analysis
- **AWS Bedrock** integration with mock fallback for demo mode
- **MLOps Dashboard**: Prompt versioning, quality metrics, structured logging
- **Bilingual UI** (EN/ES) with ElevenLabs voice assistant
- **25+ tests** covering all services, chains, and MLOps components

## API Endpoints

| Endpoint                    | Description              |
| --------------------------- | ------------------------ |
| `GET /api/health`           | Service health check     |
| `POST /api/documents-service/documents` | Create document |
| `POST /api/analysis-service/analyze`    | Run analysis    |
| `GET /api/reports-service/reports`      | List reports    |
| `GET /api/events`           | Event log                |
| `GET /api/mlops/metrics`    | MLOps metrics dashboard  |
| `GET /api/mlops/prompts`    | Prompt registry          |
| `GET /api/mlops/logs`       | Structured logs          |

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=services --cov=gateway --cov-report=term-missing
```

**114 tests passing** | **86.2% code coverage**

| Module | Coverage |
|---|---|
| services/analysis_service | 59–100% |
| services/event_bus | 100% |
| services/mlops | 97–100% |
| services/document_service | 84–94% |
| services/report_service | 68–100% |
| gateway | 81–93% |

## License

MIT
