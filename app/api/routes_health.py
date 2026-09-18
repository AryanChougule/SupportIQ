from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
def health(request: Request):
    db = request.app.state.db
    return {
        "status": "ok",
        "service": "SupportIQ",
        "dataset_ready": db.is_ready(),
        "ticket_count": db.count() if db.is_ready() else 0,
    }


@router.get("/summary")
def summary(request: Request):
    return request.app.state.db.summary()
