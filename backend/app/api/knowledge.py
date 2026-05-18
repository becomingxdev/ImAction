import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from app.schemas.knowledge import KnowledgeListResponse
from app.services.knowledge_loader import knowledge_loader

logger = logging.getLogger("imaction")

router = APIRouter(
    prefix="/knowledge",
    tags=["Ingestion"],
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Internal Server Error occurred during knowledge ingestion"
        }
    }
)


@router.get(
    "",
    response_model=KnowledgeListResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Normalized Enterprise Knowledge",
    description="Loads, normalizes, and merges fintech incident records from Slack logs, Jira issues, and Support tickets."
)
def get_knowledge(
    source: Optional[str] = Query(
        None,
        description="Filter records by source system: 'slack', 'jira', or 'support_ticket'."
    )
) -> KnowledgeListResponse:
    """
    HTTP GET endpoint to retrieve the list of unified normalized knowledge records.
    """
    try:
        # Load and merge records from files
        records = knowledge_loader.load_and_merge_all()

        # Apply filtering if a source is requested
        if source:
            normalized_source = source.strip().lower()
            valid_sources = {"slack", "jira", "support_ticket"}
            
            if normalized_source not in valid_sources:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid source filter: '{source}'. Allowed options are: {', '.join(valid_sources)}."
                )
            
            records = [r for r in records if r.source == normalized_source]
            logger.info(f"Filtered ingested records by source='{normalized_source}'. Found {len(records)} matching records.")

        return KnowledgeListResponse(
            count=len(records),
            records=records
        )

    except HTTPException:
        # Re-raise HTTP client errors directly
        raise
    except Exception as e:
        logger.error(f"Failed to fetch and normalize knowledge records: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A severe error occurred while loading and normalizing enterprise knowledge."
        )
