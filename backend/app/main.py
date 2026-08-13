from fastapi import FastAPI

app = FastAPI(
    title="AI Workflow Studio API",
    description="Backend API for building and running configurable AI workflows.",
    version="0.1.0"
)


@app.get("/")
def root():
    return {
        "message": "Welcome to AI Workflow Studio"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }