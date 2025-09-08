from fastapi import APIRouter, Depends, Query
from api.deps import require_api_key, get_db
from api.schemas import LoadSearchRequest, LoadSearchResponse
from api.services.loads_search import LoadSearchService
from sqlalchemy.orm import Session

router = APIRouter()

@router.get("/loads", response_model=LoadSearchResponse)
async def search_loads(
    origin: str = Query(None, description="Origin state or city"),
    destination: str = Query(None, description="Destination state or city"),
    equipment: str = Query(None, description="Equipment type"),
    min_rate: float = Query(None, description="Minimum rate per mile"),
    max_rate: float = Query(None, description="Maximum rate per mile"),
    limit: int = Query(10, description="Maximum number of results"),
    api_key: str = Depends(require_api_key),
    db: Session = Depends(get_db)
):
    """
    Search for available loads with filtering and ranking.
    """
    try:
        # Create search request
        search_request = LoadSearchRequest(
            origin_state=origin,
            destination_state=destination,
            equipment_type=equipment,
            min_rate=min_rate,
            max_rate=max_rate,
            limit=limit
        )
        
        # Use search service
        search_service = LoadSearchService(db)
        results = search_service.search_loads(search_request)
        
        return LoadSearchResponse(
            ok=True,
            data=results
        )
        
    except Exception as e:
        return LoadSearchResponse(
            ok=False,
            error=f"Search failed: {str(e)}"
        )

@router.post("/loads/search", response_model=LoadSearchResponse)
async def search_loads_post(
    search_request: LoadSearchRequest,
    api_key: str = Depends(require_api_key),
    db: Session = Depends(get_db)
):
    """
    Search for available loads with filtering and ranking (POST version).
    """
    try:
        # Use search service
        search_service = LoadSearchService(db)
        results = search_service.search_loads(search_request)
        
        return LoadSearchResponse(
            ok=True,
            data=results
        )
        
    except Exception as e:
        return LoadSearchResponse(
            ok=False,
            error=f"Search failed: {str(e)}"
        )
