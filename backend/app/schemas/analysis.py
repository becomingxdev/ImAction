from typing import List
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.search import SearchMatchRecord


class AnalysisRequest(BaseModel):
    """
    Schema for incoming client query for incident analysis synthesis.
    """
    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        examples=["Why did Stripe payouts fail?"],
        description="The natural language query or incident details to analyze."
    )


class AnalysisResponse(BaseModel):
    """
    Schema representing the structured SRE incident analysis output.
    """
    query: str = Field(..., description="The queried natural language query.")
    root_cause: str = Field(
        ..., 
        alias="rootCause", 
        description="Identified SRE root cause of the fintech incident."
    )
    confidence_score: float = Field(
        ..., 
        alias="confidenceScore", 
        ge=0.0,
        le=1.0,
        description="Reliability confidence score between 0.0 and 1.0 based on evidence context."
    )
    recommended_action: str = Field(
        ..., 
        alias="recommendedAction", 
        description="Highly actionable steps for immediate SRE resolution or mitigation."
    )
    supporting_evidence_count: int = Field(
        ..., 
        alias="supportingEvidenceCount", 
        ge=0,
        description="Number of ingested evidence records directly supporting the analysis."
    )
    executive_summary: str = Field(
        ..., 
        alias="executiveSummary", 
        description="High-level business-focused summary of the SRE incident analysis."
    )
    evidence: List[SearchMatchRecord] = Field(
        default_factory=list,
        description="List of supporting semantic search records retrieved and analyzed."
    )

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "query": "Why did Stripe payouts fail?",
                "rootCause": "Stripe webhook payment gateway verification timeouts leading to routing validation errors.",
                "confidenceScore": 0.95,
                "recommendedAction": "Deploy standard bank routing validation checks and standardize webhook notification timeouts.",
                "supportingEvidenceCount": 3,
                "executiveSummary": "A system routing verification mismatch triggered multiple payout failures. Resolved by adjusting routing validations and webhooks.",
                "evidence": []
            }
        }
    )
