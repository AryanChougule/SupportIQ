import logging
from contextlib import asynccontextmanager

import gradio as gr
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_anomaly import router as anomaly_router
from app.api.routes_health import router as health_router
from app.api.routes_query import router as query_router
from app.core.config import get_settings
from app.core.logging_config import setup_logging
from app.data.database import TicketDatabase
from app.data.validator import load_csv
from app.llm.gemini_client import GeminiPlanner
from app.services.anomaly_service import AnomalyService
from app.services.answer_service import AnswerService
from app.services.query_executor import QueryExecutor
from app.ui.gradio_app import build_ui

# Initialize logging once, before creating the application.
setup_logging()
logger = logging.getLogger(__name__)

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SupportIQ API started")

    try:
        yield
    finally:
        logger.info("SupportIQ API shutting down")
        

def create_app() -> FastAPI:
    logger.info("Starting SupportIQ application")

    db = TicketDatabase(settings.absolute_duckdb_path())

    logger.info("Loading ticket dataset")
    df = load_csv(settings.absolute_data_path())
    db.load_dataframe(df)
    logger.info("Ticket dataset loaded successfully")

    planner = GeminiPlanner(settings)
    executor = QueryExecutor(db, settings.max_result_rows)

    anomaly_service = AnomalyService(
        db,
        iqr_multiplier=settings.anomaly_iqr_multiplier,
        unresolved_age_hours=settings.unresolved_age_hours,
    )

    answer_service = AnswerService(
        planner,
        executor,
        anomaly_service,
    )

    app = FastAPI(
        title="SupportIQ API",
        version="1.0.0",
        description="AI-powered customer support analytics.",
        lifespan=lifespan,
        
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.db = db
    app.state.anomaly_service = anomaly_service
    app.state.answer_service = answer_service

    app.include_router(health_router)
    app.include_router(query_router)
    app.include_router(anomaly_router)

    demo = build_ui(answer_service, anomaly_service, db)
    app = gr.mount_gradio_app(app, demo, path="/")

    logger.info("SupportIQ application initialized successfully")

    return app


app = create_app()