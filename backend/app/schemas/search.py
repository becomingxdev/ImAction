from typing import List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class SearchRequest(BaseModel):
    """
    Schema for incoming client search queries.
    """
    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        examples=["Why did payouts fail?"],
        description="The natural language question or search query."
    )
    
    top_k: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Number of top relevant records to return."
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "Why did payouts fail?",
                "top_k": 5
            }
        }
    )


class SearchMatchRecord(BaseModel):
    """
    Schema representing a single matched knowledge record with relevance scoring.
    """
    source: str = Field(..., description="Source platform (slack, jira, support_ticket).")
    title: str = Field(..., description="Descriptive derived title of the record.")
    content: str = Field(..., description="Content payload of the record.")
    timestamp: str = Field(..., description="ISO-8601 formatted timestamp of the event.")
    raw_metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        alias="rawMetadata", 
        description="Raw metadata associated with the event."
    )
    relevance_score: float = Field(
        ..., 
        alias="relevanceScore", 
        description="Cosine similarity score."
    )
    match_reason: str = Field(
        ..., 
        alias="matchReason", 
        description="Human-readable explanation of why this record is matching."
    )

    model_config = ConfigDict(
        populate_by_name=True
    )


class SearchResponse(BaseModel):
    """
    Standardized API response envelope for CKA semantic search queries.
    """
    query: str = Field(..., description="The queried text.")
    matches: List[SearchMatchRecord] = Field(
        ..., 
        description="List of matching records ordered by relevance score."
    )
    total_matches: int = Field(
        ..., 
        alias="totalMatches", 
        description="Total count of items in the search results."
    )

    model_config = ConfigDict(
        populate_by_name=True
    )
