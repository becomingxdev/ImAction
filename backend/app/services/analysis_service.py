import logging
import time
from typing import List, Any
from pydantic import BaseModel, Field
from app.schemas.search import SearchMatchRecord
from app.schemas.analysis import AnalysisResponse
from app.services.llm_service import get_llm_provider

logger = logging.getLogger("imaction.analysis")


class SREAnalysisStructuredSchema(BaseModel):
    """
    Structured Pydantic schema passed directly to the LLM generation config.
    Forces the LLM to yield standardized field keys and values.
    """
    rootCause: str = Field(..., description="Likely technical root cause of the incident")
    confidenceScore: float = Field(..., description="Estimated SRE confidence score between 0.0 and 1.0")
    recommendedAction: str = Field(..., description="Actionable next step recommendation for the SRE team")
    supportingEvidenceCount: int = Field(..., description="Total count of supporting evidence records that back this analysis")
    executiveSummary: str = Field(..., description="High-level business-focused summary of the SRE analysis")


class AnalysisService:
    """
    Service responsible for AI synthesis and executive structured SRE root cause analysis.
    """
    
    def __init__(self) -> None:
        self.llm = get_llm_provider()
        logger.info("Initialized AnalysisService.")
        
    def analyze(self, query: str, evidence: List[Any]) -> AnalysisResponse:
        """
        Accepts the query and retrieved search evidence, formats the analytical prompt,
        calls the active LLM provider to generate the structured output,
        and constructs the final AnalysisResponse.
        """
        logger.info(f"Synthesizing incident analysis for query='{query}' using {len(evidence)} evidence records.")
        start_time = time.perf_counter()
        
        # Resiliently convert evidence dictionary items into type-safe SearchMatchRecord objects
        validated_evidence: List[SearchMatchRecord] = []
        for item in evidence:
            if isinstance(item, dict):
                validated_evidence.append(SearchMatchRecord.model_validate(item))
            else:
                validated_evidence.append(item)
        
        # 1. Format the analytical SRE prompt
        prompt = self._format_prompt(query, validated_evidence)
        
        try:
            # 2. Call active LLM provider to fetch structured Pydantic object
            structured_output: SREAnalysisStructuredSchema = self.llm.generate_structured(
                prompt=prompt,
                schema=SREAnalysisStructuredSchema
            )
            
            # 3. Construct the response envelope including the original matches
            response = AnalysisResponse(
                query=query,
                rootCause=structured_output.rootCause,
                confidenceScore=structured_output.confidenceScore,
                recommendedAction=structured_output.recommendedAction,
                supportingEvidenceCount=len(validated_evidence),  # Standardize with the actual evidence size
                executiveSummary=structured_output.executiveSummary,
                evidence=validated_evidence
            )
            
            duration = (time.perf_counter() - start_time) * 1000
            logger.info(
                f"Structured SRE analysis generated successfully in {duration:.2f}ms. "
                f"Confidence={response.confidence_score:.2f}"
            )
            return response

            
        except Exception as e:
            logger.error(f"Error during AI SRE analysis synthesis: {e}", exc_info=True)
            raise RuntimeError(f"AI synthesis generation failed: {e}")
            
    def _format_prompt(self, query: str, records: List[SearchMatchRecord]) -> str:
        """
        Formats retrieved SRE evidence logs into a structured context prompt.
        """
        evidence_blocks = []
        for i, record in enumerate(records):
            evidence_blocks.append(
                f"Evidence [{i+1}] (Source: {record.source}, Title: {record.title})\n"
                f"Timestamp: {record.timestamp}\n"
                f"Content:\n{record.content}\n"
                f"Match Reason: {record.match_reason}\n"
                f"----------------------------------------"
            )
        
        evidence_str = "\n".join(evidence_blocks) if evidence_blocks else "No relevant evidence records found."
        
        prompt = f"""You are ImAction's Contextual Knowledge SRE Analyzer, a production-grade incident diagnostic AI.
Your objective is to analyze the following retrieved evidence logs to perform root cause analysis and synthesize an executive business summary.

User Query: "{query}"

Retrieved Evidence Records:
{evidence_str}

Please generate an SRE analytical synthesis that maps out:
1. SRE Root Cause ("rootCause"): Pinpoint the precise system failure, logic disparity, database timeout, or webhook validation error.
2. Confidence Score ("confidenceScore"): Estimate from 0.0 (no confidence) to 1.0 (absolute certainty) based on evidence corroboration.
3. Recommended Action ("recommendedAction"): Detail SRE/Operational mitigation steps (e.g. rollback client header change, increase database connection pools, fix Stripe routing logic).
4. Supporting Evidence Count ("supportingEvidenceCount"): Number of evidence records that explicitly back this analysis.
5. Executive Summary ("executiveSummary"): A high-level, business-focused summary of the incident, context, and immediate path to SRE resolution.

You must follow the strict JSON schema provided and populate all fields completely."""
        return prompt


# Singleton Instance
analysis_service = AnalysisService()
