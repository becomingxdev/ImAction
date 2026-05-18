import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


# ==============================================================================
# Query Requests Validation Schemas
# ==============================================================================
class QueryRequest(BaseModel):
    """
    Schema for incoming client search queries.
    """
    text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        examples=["How do I configure the production OAuth key?"],
        description="The natural language question or search query."
    )
    
    top_k: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Maximum number of context matching records to return."
    )
    
    source_types: Optional[List[str]] = Field(
        default=None,
        examples=[["slack", "jira"]],
        description="Optional filter to limit results to specific source platforms."
    )
    
    metadata_filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional key-value pairs to match against JSONB metadata fields."
    )

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "text": "Where is the deployment pipeline config stored?",
                "top_k": 5,
                "source_types": ["slack", "jira"],
                "metadata_filters": {"channel": "ops-deployment"}
            }
        }
    )


# ==============================================================================
# Query Result & Response Envelopes
# ==============================================================================
class QueryResultResponse(BaseModel):
    """
    Schema representing a single matched knowledge record in search results.
    """
    id: uuid.UUID = Field(..., description="Internal unique UUID of the record.")
    source_type: str = Field(..., alias="sourceType", description="Type of source platform (slack, jira, support_ticket).")
    external_id: str = Field(..., alias="externalId", description="Original ID of the entity in the source system.")
    content: str = Field(..., description="Content payload of the matched record.")
    meta_data: Dict[str, Any] = Field(..., alias="metaData", description="Additional metadata fields associated with the record.")
    score: Optional[float] = Field(None, description="Semantic similarity relevance score (nullable).")
    created_at: datetime = Field(..., alias="createdAt", description="Timestamp when record was indexed locally.")
    updated_at: datetime = Field(..., alias="updatedAt", description="Timestamp when record was last updated locally.")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True  # Equivalent to Pydantic v1's orm_mode=True
    )


class QueryResponseEnvelope(BaseModel):
    """
    Standardized top-level API response envelope for CKA search queries.
    """
    query: str = Field(..., description="The query string that was searched.")
    count: int = Field(..., description="Total number of matches returned.")
    results: List[QueryResultResponse] = Field(..., description="List of matching records ordered by relevance.")

    model_config = ConfigDict(
        populate_by_name=True
    )
