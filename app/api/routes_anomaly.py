from typing import Literal
from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["anomalies"])


class AnomalyRequest(BaseModel):
    anomaly_type: Literal[
        "all", "resolution_time", "unresolved_priority", "response_time"
    ] = "all"


@router.post("/anomalies")
def anomalies(payload: AnomalyRequest, request: Request):
    return request.app.state.anomaly_service.detect(payload.anomaly_type)
