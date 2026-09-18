import json
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import set_key
from google import genai
from google.genai import types

from app.core.config import Settings
from app.llm.prompts import SYSTEM_PROMPT
from app.llm.schemas import QueryPlan
import time
logger = logging.getLogger(__name__)


class GeminiPlanner:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = None

        if settings.enable_gemini and settings.gemini_api_key:
            self.client = genai.Client(
                api_key=settings.gemini_api_key
            )

    @property
    def available(self) -> bool:
        return self.client is not None

    @staticmethod
    def _env_path() -> Path:
        return Path(__file__).resolve().parents[2] / ".env"

    @staticmethod
    def validate_api_key(
        api_key: str,
        model: str
    ) -> tuple[bool, str]:
        """Validate a Gemini API key using an authenticated API call."""

        api_key = (api_key or "").strip()

        if not api_key:
            return False, "API key cannot be empty."

        try:
            client = genai.Client(api_key=api_key)

            # Make an authenticated request to verify the key.
            models = client.models.list()

            # Consume one item to ensure the request is executed.
            next(iter(models), None)

            return True, "Gemini API key validated successfully."

        except Exception as exc:
            logger.warning(
                "Gemini API-key validation failed: %s",
                exc
            )

            return False, f"Gemini rejected this API key: {exc}"

    def plan(
        self,
        question: str,
        schema_text: str
    ) -> QueryPlan:

        if not self.available:
            raise RuntimeError(
                "Gemini is not configured. "
                "Set GEMINI_API_KEY or use mock mode."
            )

        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"Database schema:\n{schema_text}\n\n"
            f"User question:\n{question}\n\n"
            "Return a JSON object matching the QueryPlan schema."
        )

        logger.info("Generating query plan with Gemini")

        start_time = time.perf_counter()

        try:
            response = self.client.models.generate_content(
                model=self.settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0,
                    response_mime_type="application/json",
                    response_schema=QueryPlan,
                ),
            )

            duration = time.perf_counter() - start_time

            logger.info(
                "Gemini query-planning request completed in %.2f seconds",
                duration,
            )

            plan = QueryPlan.model_validate_json(response.text)

            logger.info(
                "Generated query plan: operation=%s, metric=%s, group_by=%s",
                plan.operation,
                plan.metric,
                plan.group_by,
            )

            return plan

        except Exception:
            duration = time.perf_counter() - start_time

            logger.exception(
                "Gemini query-planning request failed after %.2f seconds",
                duration,
            )
            raise

        

    def update_api_key(self, new_api_key: str) -> str:
        """
        Validate, save, and activate a new Gemini API key.
        """

        new_api_key = (new_api_key or "").strip()

        is_valid, message = self.validate_api_key(
            new_api_key,
            self.settings.gemini_model,
        )

        if not is_valid:
            raise ValueError(message)

        env_path = self._env_path()

        # Save only after successful validation.
        set_key(
            str(env_path),
            "GEMINI_API_KEY",
            new_api_key
        )

        os.environ["GEMINI_API_KEY"] = new_api_key
        self.settings.gemini_api_key = new_api_key

        # Activate the new key immediately.
        self.client = genai.Client(
            api_key=new_api_key
        )

        return message

    def explain(
        self,
        question: str,
        result: Any
    ) -> str:

        if not self.available:
            return (
                "The result was calculated by the deterministic "
                "analytics engine.\n\n"
                f"Computed result:\n"
                f"{json.dumps(result, default=str, indent=2)}"
            )

        prompt = f"""
You are SupportIQ's customer-support analytics assistant.

Answer the user's question using ONLY the supplied computed result.

Strict rules:
1. Never invent, modify, or estimate numbers.
2. Do not claim that data exists if it is not present in the result.
3. Start with a direct answer to the question.
4. Add a useful breakdown when the result contains grouped data.
5. Highlight important patterns, risks, or unusual findings only when supported
   by the computed result.
6. If ticket records are provided, show the most relevant records in a
   readable Markdown table.
7. Mention the applied filters when they are available.
8. If the result is empty, clearly explain that no matching records were found.
9. Keep the response professional, clear, and reasonably detailed.
10. Use Markdown formatting with headings, bullet points, and tables where useful.

Response structure:
- Direct answer
- Supporting breakdown or relevant details
- Important insight, if supported by the data
- Filters or limitations, if applicable

User question:
{question}

Computed result:
{json.dumps(result, default=str, indent=2)}
"""

        response = self.client.models.generate_content(
            model=self.settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2
            ),
        )

        return response.text.strip()