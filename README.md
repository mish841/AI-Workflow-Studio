# AI Workflow Studio

AI Workflow Studio is an in-progress backend for reusable AI document-processing workflows. The current MVP defines a small domain model—**Document**, **Workflow**, and **Run**—and exposes it as a FastAPI REST API.

This phase is about getting the API and data model right before adding persistence, LLM calls, or retrieval.

## Why I’m Building This

During my previous internship in the AI Transformation Experience team at Maximus, I built several enterprise agents that all did variations of the same thing: take a document, apply instructions (and sometimes reference material), then return a structured result. Contracts, policies, and resumes look different on the surface, but the pipeline is similar: ingest → instruct or retrieve → evaluate or transform → structured output.

Building a separate agent for each use case repeats that plumbing. This project is an attempt to extract the shared engine—starting with a typed API that can later host extract, summarize, retrieve, compare, evaluate, and generate steps.

Intended later workflows include:

- **Contract:** extract metadata → summarize → identify risks → structured report
- **Policy:** retrieve a checklist → evaluate coverage → flag gaps → score/report
- **Resume:** extract skills → compare to a job description → evaluation → interview questions

None of those multi-step pipelines are implemented yet.

## Architecture

```
Document
   ↓
Workflow
   ↓
Run
   ↓
Processing (mocked today)
   ↓
Structured Result
```

- **Document** — named text a user wants processed (`name`, `content`).
- **Workflow** — named instructions for how to process a document (`name`, `instruction`).
- **Run** — one execution of a workflow against a document. It records `document_id`, `workflow_id`, `status`, and a `result` object.

Conceptually: **Document + Workflow → Run → Structured Result**.

Today, processing does not call a model. `POST /runs` validates that both IDs exist, then stores a **mocked** `result` with `summary` and `key_points`.

## Current MVP

Python FastAPI app with Pydantic request/response models. State lives in process-local lists with incrementing integer IDs (lost on restart). There is no database, auth, file upload, queue, or LLM client.

What works:

- App metadata, root welcome payload, and a health check
- Create and fetch documents by ID
- Create and fetch workflows by ID
- Create a run that joins an existing document and workflow
- **404** when a document, workflow, or referenced run ID is missing
- Mock structured results (`status: "completed"`)

What does **not** work yet: listing collections, fetching a run by ID, PostgreSQL, embeddings, a frontend, or real generation.

## API Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/` | Welcome payload |
| `GET` | `/health` | Liveness check (`{"status": "healthy"}`) |
| `POST` | `/documents` | Create a document (`name`, `content`) |
| `GET` | `/documents/{document_id}` | Fetch a document; **404** if missing |
| `POST` | `/workflows` | Create a workflow (`name`, `instruction`) |
| `GET` | `/workflows/{workflow_id}` | Fetch a workflow; **404** if missing |
| `POST` | `/runs` | Run a workflow on a document; **404** if either ID is missing |

There is no `GET /runs/{id}` or list endpoint.

## Example

Interactive docs: `/docs`. Results below match the current mock implementation, not an LLM.

**1. Create a document**

```http
POST /documents
```

```json
{
  "name": "Q3 vendor contract.txt",
  "content": "This agreement is between Acme Corp and Northwind Supplies..."
}
```

```json
{
  "id": 1,
  "name": "Q3 vendor contract.txt",
  "content": "This agreement is between Acme Corp and Northwind Supplies..."
}
```

**2. Create a workflow**

```http
POST /workflows
```

```json
{
  "name": "Contract review",
  "instruction": "Extract parties, dates, and liability terms. Summarize risks."
}
```

```json
{
  "id": 1,
  "name": "Contract review",
  "instruction": "Extract parties, dates, and liability terms. Summarize risks."
}
```

**3. Run the workflow against the document**

```http
POST /runs
```

```json
{
  "document_id": 1,
  "workflow_id": 1
}
```

**4. Mocked structured result (not an LLM)**

```json
{
  "id": 1,
  "document_id": 1,
  "workflow_id": 1,
  "status": "completed",
  "result": {
    "summary": "Mock summary of 'Q3 vendor contract.txt' using 'Contract review'.",
    "key_points": [
      "Extract parties, dates, and liability terms. Summarize risks.",
      "Processed document: Q3 vendor contract.txt"
    ]
  }
}
```

The next stage is to replace this mock with a real model call that still returns structured JSON.

## Tech Stack

**Current**

- Python
- FastAPI
- Pydantic
- In-memory lists (temporary persistence)

**Planned**

- PostgreSQL
- pgvector
- LLM integration (structured generation)
- Embeddings and semantic retrieval
- React
- AWS

## Project Structure

```
AI-Workflow-Studio/
├── README.md
├── .gitignore
└── backend/
    ├── requirements.txt
    └── app/
        ├── main.py              # FastAPI app and routes
        └── models/
            ├── document.py      # DocumentCreate, DocumentResponse
            ├── workflow.py      # WorkflowCreate, WorkflowResponse
            └── run.py           # RunCreate, RunResponse
```

## Roadmap

- [x] FastAPI backend
- [x] Document models and endpoints
- [x] Workflow models and endpoints
- [x] Workflow execution model (`POST /runs`)
- [x] Mock structured results
- [ ] PostgreSQL persistence
- [ ] Document ingestion beyond JSON `content`
- [ ] LLM integration
- [ ] Embedding generation
- [ ] pgvector semantic retrieval
- [ ] Knowledge library
- [ ] Configurable multi-step workflow engine
- [ ] React frontend
- [ ] Workflow history / version comparison
- [ ] AWS deployment

## Running Locally

Requires Python 3 and a clone of this repo.

```bash
git clone https://github.com/mish841/AI-Workflow-Studio.git
cd AI-Workflow-Studio/backend

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for Swagger UI, or hit `/health` to confirm the server is up. In-memory data resets whenever the process restarts.

## Status

This is an actively developed MVP. The current work is the API and domain foundation: typed resources, ID validation, and a run object that can later carry real model output. Persistence, LLM orchestration, and retrieval are not in the codebase yet.
