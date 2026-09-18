from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
import logging
logger = logging.getLogger(__name__)
router = APIRouter(tags=["query"])


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


@router.post("/query")
def query(payload: QueryRequest, request: Request):
    try:
        return request.app.state.answer_service.answer(payload.question)
    except Exception:
        logger.exception("Query API failed")
        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while processing the query.",
        )
