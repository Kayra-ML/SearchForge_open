from fastapi import APIRouter, HTTPException, Query
from app.models.search import SearchResponse
from app.services.search_service import search, IndexNotReadyError
from app.core.security import validate_search_query

router = APIRouter()


@router.get("/search", response_model=SearchResponse)
async def search_documents(
    q: str = Query(..., min_length=1, max_length=200),
    mime_type: str = Query("all", alias="type"),
    folder: str = Query(None),
):
    validated_q = validate_search_query(q)
    try:
        results = await search(
            query=validated_q,
            mime_filter=mime_type if mime_type != "all" else None,
            folder_filter=folder,
        )
    except IndexNotReadyError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Search failed")

    return SearchResponse(
        query=validated_q,
        total=len(results),
        results=results,
    )