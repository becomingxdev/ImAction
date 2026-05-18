import logging
import time
from typing import List, Any
from app.schemas.search import SearchMatchRecord
from app.schemas.analysis import AnalysisResponse
from app.schemas.challenge import ChallengeStructuredResult
from app.services.llm_service import get_llm_provider

logger = logging.getLogger("imaction.challenge")


class ChallengeService:
    """
    Service responsible for structured auditing and challenging original SRE hypotheses
    using the active LLM provider (Devil's Advocate Mode).
    """

    def __init__(self) -> None:
        self.llm = get_llm_provider()
        logger.info("Initialized ChallengeService.")

    def challenge(
        self,
        query: str,
        analysis: Any,
        evidence: List[Any]
    ) -> ChallengeStructuredResult:
        """
        Accepts original incident query, original AI analysis, and retrieved search evidence.
        Formats a challenge prompt, invokes the active LLM provider with the strict
        ChallengeStructuredResult Pydantic schema, and returns the audited challenge results.
        """
        logger.info(f"Initiating Devil's Advocate review for query='{query}'...")
        start_time = time.perf_counter()

        # 1. Resiliently parse input analysis into AnalysisResponse
        validated_analysis: AnalysisResponse
        if isinstance(analysis, dict):
            validated_analysis = AnalysisResponse.model_validate(analysis)
        else:
            validated_analysis = analysis

        # 2. Resiliently parse input evidence list into SearchMatchRecord models
        validated_evidence: List[SearchMatchRecord] = []
        for item in evidence:
            if isinstance(item, dict):
                validated_evidence.append(SearchMatchRecord.model_validate(item))
            else:
                validated_evidence.append(item)

        # 3. Format SRE Challenge prompt
        prompt = self._format_prompt(query, validated_analysis, validated_evidence)

        try:
            # 4. Invoke LLM provider to fetch structured Pydantic object
            structured_challenge: ChallengeStructuredResult = self.llm.generate_structured(
                prompt=prompt,
                schema=ChallengeStructuredResult
            )

            duration = (time.perf_counter() - start_time) * 1000
            logger.info(
                f"Devil's Advocate challenge generated successfully in {duration:.2f}ms. "
                f"RiskLevel={structured_challenge.risk_level}, ConfidenceAdjustment={structured_challenge.confidence_adjustment:.2f}"
            )
            return structured_challenge

        except Exception as e:
            logger.error(f"Error during Devil's Advocate analysis generation: {e}", exc_info=True)
            raise RuntimeError(f"Devil's Advocate review failed: {e}")

    def _format_prompt(
        self,
        query: str,
        analysis: AnalysisResponse,
        evidence: List[SearchMatchRecord]
    ) -> str:
        """
        Formats original SRE analysis and retrieved log evidence into a critical audit prompt
        designed to trigger contradictory hypothesis generation and assumption check.
        """
        evidence_blocks = []
        for i, record in enumerate(evidence):
            evidence_blocks.append(
                f"Evidence [{i+1}] (Source: {record.source}, Title: {record.title})\n"
                f"Timestamp: {record.timestamp}\n"
                f"Content:\n{record.content}\n"
                f"Match Reason: {record.match_reason}\n"
                f"----------------------------------------"
            )
        evidence_str = "\n".join(evidence_blocks) if evidence_blocks else "No relevant evidence records found."

        prompt = f"""You are ImAction's SRE Devil's Advocate, a production-grade diagnostic auditor.
Your goal is to critically audit the following original AI analysis conclusion, search for contradictory evidence in the retrieved log records, identify missing assumptions, estimate operational risk, and formulate a viable alternative hypothesis.

=== INCIDENT AUDIT INPUT ===
Original User Query: "{query}"

Original AI Analysis Conclusion:
- Root Cause Identified: {analysis.root_cause}
- AI Confidence Score: {analysis.confidence_score}
- Recommended Next Step: {analysis.recommended_action}
- Executive Summary: {analysis.executive_summary}

=== RETRIEVED LOG EVIDENCE RECORDS ===
{evidence_str}

=== OPERATIONAL AUDIT CHALLENGE GUIDELINES ===
Please analyze this information critically under the following objectives:
1. Search for contradictory evidence in the logs that might conflict with the identified root cause.
2. Formulate a solid alternative hypothesis explaining the incident logs (e.g. queue saturation instead of network timeout, middleware stripping parameters instead of client mismatch).
3. Evaluate operational risk level ("riskLevel"): "LOW", "MEDIUM", or "HIGH" based on how severe taking the wrong action on the original recommended action would be.
4. Recommend a precise technical verification check ("recommendedNextCheck") to definitively validate this alternative hypothesis.
5. Provide a confidence adjustment score ("confidenceAdjustment") which should be negative (e.g., -0.15, -0.05) indicating how much the original confidence should be discounted until validated.

You must follow the strict JSON schema provided and populate all fields completely using the exact keys: originalHypothesis, challengeFinding, alternativeHypothesis, riskLevel, confidenceAdjustment, recommendedNextCheck."""
        return prompt


# Singleton Instance
challenge_service = ChallengeService()
