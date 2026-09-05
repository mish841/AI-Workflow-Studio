def execute_workflow(document_content: str, workflow_instruction: str) -> dict:
    return {
        "summary": f"Mock summary of '{document_content}' using '{workflow_instruction}'.",
        "key_points": [
            workflow_instruction,
            f"Processed document: {document_content}",
        ],
    }
