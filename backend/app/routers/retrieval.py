from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


def _extract_bearer(authorization: str = Header(...)) -> str:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")
    return token


class ExplainRequest(BaseModel):
    query: str


@router.post("/explain")
async def explain_retrieval(body: ExplainRequest, token: str = Depends(_extract_bearer)):
    """Run the classifier and return which strategies would be selected for a query."""
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    from app.services.retrieval.classifier import classify_query
    result = await classify_query(body.query)
    return result


@router.post("/search")
async def adaptive_search(body: ExplainRequest, token: str = Depends(_extract_bearer)):
    """Run full adaptive retrieval and return merged results with trace."""
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    from app.services.retrieval.router import adaptive_retrieve
    result = await adaptive_retrieve(body.query)
    return result
