import logging
import time
from fastapi import APIRouter, HTTPException, status
from app.schemas.analysis import AnalysisRequest, AnalysisResponse
from app.services.retrieval_service import retrieval_service
from app.services.analysis_service import analysis_service

logger = logging.getLogger("imaction.api.analysis")
router = APIRouter(tags=["analysis"])


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Structured SRE Analysis",
    description=(
        "Accepts a natural language query, retrieves top relevant evidence "
        "via semantic retrieval, synthesizes the results using the active LLM provider, "
        "and returns a structured executive analysis and root cause report."
    )
)
def generate_analysis(request_payload: AnalysisRequest):
    """
    HTTP POST Endpoint to generate SRE incident root cause analysis.
    """
    query = request_payload.query
    logger.info(f"Received SRE analysis generation request: query='{query}'")
    
    start_time = time.perf_counter()
    try:
        # Step 1: Semantic Retrieval (Get supporting evidence)
        logger.info(f"Step 1: Retrieving supporting SRE evidence for query='{query}'")
        evidence = retrieval_service.search(query=query, top_k=5)
        logger.info(f"Retrieved {len(evidence)} evidence matches.")
        
        # Step 2: AI SRE Synthesis (Generate structured answer)
        logger.info(f"Step 2: Performing SRE structured analysis synthesis for query='{query}'")
        response = analysis_service.analyze(query=query, evidence=evidence)
        
        duration = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"SRE analysis generation complete for query='{query}'. "
            f"Execution time={duration:.2f}ms"
        )
        
        return response
    except Exception as e:
        logger.error(
            f"Unhandled error during SRE analysis generation for query='{query}': {e}", 
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during AI analysis synthesis processing."
        )
