from pydantic import BaseModel, Field
from app.schemas.analysis import AnalysisResponse


class ChallengeRequest(BaseModel):
    """
    Validation schema for Devil's Advocate Challenge requests.
    """
    query: str = Field(
        ...,
        min_length=1,
        description="The natural language query detailing the incident to review and audit."
    )


class ChallengeStructuredResult(BaseModel):
    """
    Structured Pydantic schema passed directly to the LLM generation config.
    Forces the LLM to yield standardized field keys and values.
    """
    original_hypothesis: str = Field(
        ...,
        alias="originalHypothesis",
        description="The original technical analysis hypothesis that is audited."
    )
    challenge_finding: str = Field(
        ...,
        alias="challengeFinding",
        description="Findings, contradictory evidence, or gaps identified by the Devil's Advocate audit."
    )
    alternative_hypothesis: str = Field(
        ...,
        alias="alternativeHypothesis",
        description="Alternative technical root cause or explanation for the incident logs."
    )
    risk_level: str = Field(
        ...,
        alias="riskLevel",
        description="Operational risk level of accepting the original hypothesis without verification (e.g. LOW, MEDIUM, HIGH)."
    )
    confidence_adjustment: float = Field(
        ...,
        alias="confidenceAdjustment",
        description="Estimated adjustment to the original confidence score (usually negative, e.g. -0.15)."
    )
    recommended_next_check: str = Field(
        ...,
        alias="recommendedNextCheck",
        description="Validation action recommended for verifying the alternative hypothesis."
    )

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "originalHypothesis": "Stripe webhook payment gateway verification timeouts leading to international bank routing validation failures.",
                "challengeFinding": "Detected support tickets reporting delayed processing status instead of direct validation errors, indicating a message queue bottleneck.",
                "alternativeHypothesis": "The queue processor handling the Stripe webhook notifications was saturated and dropping delivery packets.",
                "riskLevel": "MEDIUM",
                "confidenceAdjustment": -0.15,
                "recommendedNextCheck": "Inspect RabbitMQ/Celery worker queue length metrics and delivery delay logs during the incident window."
            }
        }


class ChallengeResponse(BaseModel):
    """
    Response envelope containing the original query, original analysis,
    and structured Devil's Advocate review results.
    """
    query: str = Field(..., description="The original incident query text.")
    analysis: AnalysisResponse = Field(..., description="The original technical AI analysis results.")
    challenge: ChallengeStructuredResult = Field(..., description="The structured Devil's Advocate challenge result.")

    class Config:
        populate_by_name = True
