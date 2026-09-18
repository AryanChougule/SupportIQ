import logging
import time

from app.llm.gemini_client import GeminiPlanner
from app.services.anomaly_service import AnomalyService
from app.services.query_executor import QueryExecutor

logger = logging.getLogger(__name__)


class AnswerService:
    def __init__(
        self,
        planner: GeminiPlanner,
        executor: QueryExecutor,
        anomalies: AnomalyService,
    ):
        self.planner = planner
        self.executor = executor
        self.anomalies = anomalies

    def answer(self, question: str) -> dict:
        start_time = time.perf_counter()

        logger.info("Query received")

        try:
            # Generate the structured query plan.
            plan = self.planner.plan(
                question,
                self.executor.db.schema_text(),
            )

            logger.info(
                "Executing operation: %s",
                plan.operation,
            )

            # Execute the appropriate analytics operation.
            if plan.operation == "detect_anomalies":
                result = self.anomalies.detect(
                    plan.anomaly_type or "all"
                )
            else:
                result = self.executor.execute(plan)

            # Generate a natural-language explanation.
            explanation = self.planner.explain(
                question,
                result,
            )

            duration = time.perf_counter() - start_time

            logger.info(
                "Query completed successfully in %.2f seconds",
                duration,
            )

            return {
                "success": True,
                "question": question,
                "answer": explanation,
                "plan": plan.model_dump(),
                "result": result,
            }

        except Exception:
            duration = time.perf_counter() - start_time

            logger.exception(
                "Query processing failed after %.2f seconds",
                duration,
            )
            raise