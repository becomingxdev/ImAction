import logging
import time
from fastapi import APIRouter, HTTPException, status
from app.schemas.challenge import ChallengeRequest, ChallengeResponse
from app.services.retrieval_service import retrieval_service
from app.services.analysis_service import analysis_service
from app.services.challenge_service import challenge_service

logger = logging.getLogger("imaction.api.challenge")
router = APIRouter(tags=["challenge"])


@router.post(
    "/challenge",
    response_model=ChallengeResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Structured Devil's Advocate Challenge Review",
    description=(
        "Accepts a natural language query, retrieves top relevant evidence "
        "via semantic retrieval, performs the original SRE AI analysis, "
        "challenges the conclusion critically, and returns a unified "
        "report containing original results and structured Devil's Advocate findings."
    )
)
def generate_challenge(request_payload: ChallengeRequest):
    """
    HTTP POST Endpoint to generate Devil's Advocate audit and structured challenge findings.
    """
    query = request_payload.query
    logger.info(f"Received Devil's Advocate challenge review request: query='{query}'")
    
    start_time = time.perf_counter()
    try:
        # Step 1: Semantic Retrieval (Get supporting evidence)
        logger.info(f"Step 1: Retrieving supporting SRE evidence for query='{query}'")
        evidence = retrieval_service.search(query=query, top_k=5)
        logger.info(f"Retrieved {len(evidence)} evidence matches.")
        
        # Step 2: AI SRE Synthesis (Generate original structured analysis)
        logger.info(f"Step 2: Generating original structured SRE analysis for query='{query}'")
        analysis_response = analysis_service.analyze(query=query, evidence=evidence)
        
        # Step 3: Devil's Advocate Mode (Audit original SRE conclusion and check assumptions)
        logger.info(f"Step 3: Performing Devil's Advocate critical challenge review for query='{query}'")
        challenge_result = challenge_service.challenge(
            query=query,
            analysis=analysis_response,
            evidence=evidence
        )
        
        # Step 4: Construct consolidated response envelope
        response = ChallengeResponse(
            query=query,
            analysis=analysis_response,
            challenge=challenge_result
        )
        
        duration = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"Devil's Advocate challenge review complete for query='{query}'. "
            f"Execution time={duration:.2f}ms"
        )
        
        return response
    except Exception as e:
        logger.error(
            f"Unhandled error during Devil's Advocate review for query='{query}': {e}", 
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during Devil's Advocate challenge processing."
        )
