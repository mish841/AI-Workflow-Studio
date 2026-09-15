import os

from dotenv import load_dotenv
from fastapi import HTTPException
from openai import APIError, APITimeoutError, AuthenticationError, OpenAI, RateLimitError
from pydantic import BaseModel

load_dotenv()


class WorkflowResult(BaseModel):
    summary: str
    key_points: list[str]


def execute_workflow(document_content: str, workflow_instruction: str) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not set.",
        )

    client = OpenAI(api_key=api_key)

    try:
        response = client.responses.parse(
            model="gpt-4o-mini",
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are a document workflow engine. Follow the workflow "
                        "instruction and return a structured result."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Workflow instruction:\n{workflow_instruction}\n\n"
                        f"Document:\n{document_content}"
                    ),
                },
            ],
            text_format=WorkflowResult,
        )
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=502,
            detail="OpenAI authentication failed. Check OPENAI_API_KEY.",
        ) from exc
    except RateLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail="OpenAI rate limit reached. Try again shortly.",
        ) from exc
    except APITimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail="OpenAI request timed out.",
        ) from exc
    except APIError as exc:
        raise HTTPException(
            status_code=502,
            detail="OpenAI request failed.",
        ) from exc

    parsed = response.output_parsed
    if parsed is None:
        raise HTTPException(
            status_code=502,
            detail="OpenAI returned an empty structured result.",
        )

    return parsed.model_dump()
