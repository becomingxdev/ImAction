import logging
import time
from fastapi import APIRouter, HTTPException, status
from app.schemas.search import SearchRequest, SearchResponse
from app.services.retrieval_service import retrieval_service

logger = logging.getLogger("imaction.api.search")
router = APIRouter(tags=["search"])


@router.post(
    "/search", 
    response_model=SearchResponse, 
    status_code=status.HTTP_200_OK,
    summary="Semantic Retrieval Search",
    description=(
        "Accepts a natural language search query, generates its query embedding, "
        "computes cosine similarity against all precomputed/cached enterprise records, "
        "and returns the top matches sorted by relevance score."
    )
)
def semantic_search(request_payload: SearchRequest):
    """
    HTTP POST Endpoint to perform natural language semantic queries.
    """
    query = request_payload.query
    logger.info(f"Received semantic search request: query='{query}', top_k={request_payload.top_k}")
    
    start_time = time.perf_counter()
    try:
        matches = retrieval_service.search(
            query=query,
            top_k=request_payload.top_k
        )
        
        duration = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"Semantic retrieval complete for query='{query}'. "
            f"Matches={len(matches)}. Execution time={duration:.2f}ms"
        )
        
        return SearchResponse(
            query=query,
            matches=matches,
            totalMatches=len(matches)
        )
    except Exception as e:
        logger.error(
            f"Unhandled error during semantic search execution for query='{query}': {e}", 
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during semantic search retrieval processing."
        )
