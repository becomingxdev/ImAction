from typing import Dict, Any, List
from pydantic import BaseModel, Field


class NormalizedKnowledgeRecord(BaseModel):
    """
    Schema for a unified normalized enterprise knowledge record.
    """
    source: str = Field(
        ...,
        description="The source system of the record (e.g., 'slack', 'jira', 'support_ticket')."
    )
    title: str = Field(
        ...,
        description="A concise summary or derived title for the record."
    )
    content: str = Field(
        ...,
        description="The raw descriptive content of the incident/record."
    )
    timestamp: str = Field(
        ...,
        description="ISO-8601 formatted timestamp indicating when the record was created."
    )
    raw_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="The raw payload structure preserved for auditing and rich context mapping."
    )


class KnowledgeListResponse(BaseModel):
    """
    Envelope response for querying merged knowledge records.
    """
    count: int = Field(
        ...,
        description="The total number of merged knowledge records returned."
    )
    records: List[NormalizedKnowledgeRecord] = Field(
        ...,
        description="The list of unified normalized knowledge records."
    )
