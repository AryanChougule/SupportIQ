
import gradio as gr

import json
import logging
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

SUGGESTED_QUERIES = [
    "How many tickets are currently open?",
    "Show the number of tickets by priority.",
    "Show critical tickets that are still unresolved.",
    "Which agent resolved the most tickets?",
    "What is the average customer rating by category?",
    "Are there any anomalies in resolution times?",
]


CUSTOM_CSS = """
/* Overall application */
.gradio-container {
    max-width: 1500px !important;
    margin: auto !important;
    padding: 12px 20px !important;
}

/* Header */
.app-header {
    text-align: center;
    margin-bottom: 10px;
}

.app-title {
    font-size: 32px !important;
    font-weight: 700 !important;
    margin-bottom: 2px !important;
}

.app-subtitle {
    font-size: 14px !important;
    opacity: 0.75;
}

/* Main cards */
.panel-card {
    border: 1px solid var(--border-color-primary);
    border-radius: 14px;
    padding: 14px;
    height: 100%;
}

/* Chat area */
#chatbot {
    border-radius: 12px;
}

/* Hide Gradio's Share button */
#chatbot button[aria-label*="share" i],
#chatbot button[title*="share" i],
#chatbot button[data-testid*="share" i],
#chatbot [class*="share" i] {
    display: none !important;
}

/* Input area */
#question-input textarea {
    font-size: 15px !important;
}

/* Suggested questions */
.suggestion-btn {
    text-align: left !important;
    white-space: normal !important;
    font-size: 12px !important;
    min-height: 38px !important;
}

/* Small headings */
.panel-heading {
    font-size: 17px !important;
    font-weight: 650 !important;
    margin-bottom: 6px !important;
}

/* Compact text */
.compact-text {
    font-size: 12px !important;
    opacity: 0.8;
}

/* Footer */
.footer-text {
    text-align: center;
    font-size: 11px;
    opacity: 0.6;
    margin-top: 8px;
}
"""


def create_download_file(result: dict) -> str:
    """
    Create a temporary text file containing the complete query result.

    Returns:
        str: File path for Gradio's DownloadButton.
    """
    answer = result.get("answer", "")

    report = f"""SupportIQ Query Report
=====================

Question:
{result.get("question", "")}

Answer:
{answer}

Query Plan:
{json.dumps(result.get("plan", {}), indent=2, default=str)}

Raw Result:
{json.dumps(result.get("result", {}), indent=2, default=str)}
"""

    temp_file = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        prefix="supportiq_report_",
        delete=False,
        encoding="utf-8",
    )

    with temp_file:
        temp_file.write(report)

    return temp_file.name


def get_env_file_path() -> Path:
    """
    Get the project's .env path.

    This assumes that gradio_app.py is located inside the app/
    directory and .env is located in the project root.
    """
    return Path(__file__).resolve().parent.parent / ".env"


def save_api_key_to_env(api_key: str) -> None:
    """
    Save or update GEMINI_API_KEY in the project's .env file.
    """
    env_path = get_env_file_path()

    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    else:
        lines = []

    updated = False
    new_lines = []

    for line in lines:
        if line.strip().startswith("GEMINI_API_KEY="):
            new_lines.append(f"GEMINI_API_KEY={api_key}")
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.append(f"GEMINI_API_KEY={api_key}")

    env_path.write_text(
        "\n".join(new_lines) + "\n",
        encoding="utf-8",
    )


def build_ui(answer_service, anomaly_service, db):

    def validate_and_update_gemini_key(new_api_key):
        """
        Validate the API key through the planner and save it to .env.
        """
        if not new_api_key or not new_api_key.strip():
            return (
                "⚠️ Please enter a Gemini API key.",
                "",
            )

        new_api_key = new_api_key.strip()

        try:
            planner = getattr(
                answer_service,
                "planner",
                None,
            )

            if (
                planner is None
                or not hasattr(planner, "update_api_key")
            ):
                return (
                    "❌ Gemini API-key updates are not available.",
                    "",
                )

            # Validate and apply the key to the running planner.
            message = planner.update_api_key(new_api_key)

            # Save the key only after the planner accepts it.
            save_api_key_to_env(new_api_key)

            # Update the current process environment.
            os.environ["GEMINI_API_KEY"] = new_api_key

            # Refresh dotenv values for any code that reads them.
            load_dotenv(
                dotenv_path=get_env_file_path(),
                override=True,
            )

            return (
                f"✅ {message}",
                "",
            )

        except Exception:
            logger.exception("Gemini API-key update failed")

            return (
                "❌ The API key could not be validated. "
                "Please check the key and try again.",
                "",
            )

    def run_query(question, history):
        """
        Process a user question and return the updated chat state.
        """
        history = history or []

        if not question or not question.strip():
            return (
                history,
                history,
                "",
                gr.update(value=None, visible=False),
            )

        # Show a helpful message instead of a generic error when
        # the Gemini API key has not been configured.
        current_api_key = os.getenv("GEMINI_API_KEY", "").strip()

        if (
            not current_api_key
            or current_api_key.lower() in {
                "your_gemini_api_key_here",
                "your_api_key_here",
                "your_key_here",
                "gemini_api_key",
            }
        ):
            history.append({
                "role": "user",
                "content": question,
            })
            history.append({
                "role": "assistant",
                "content": (
                    "🔑 **Gemini API key is not configured.**\n\n"
                    "Please enter your Gemini API key in the "
                    "**Gemini API Settings** panel on the right, "
                    "then click **Validate & Save** and try again."
                ),
            })

            return (
                history,
                history,
                "",
                gr.update(value=None, visible=False),
            )

        try:
            result = answer_service.answer(question)

            answer = result.get(
                "answer",
                "No answer generated.",
            )

            history.append({
                "role": "user",
                "content": question,
            })
            history.append({
                "role": "assistant",
                "content": answer,
            })

            download_path = create_download_file(result)

            return (
                history,
                history,
                "",
                gr.update(
                    value=download_path,
                    visible=True,
                ),
            )

        except Exception:
            logger.exception("UI query failed")

            history.append({
                "role": "user",
                "content": question,
            })
            history.append({
                "role": "assistant",
                "content": (
                    "⚠️ I couldn't process your question. "
                    "Please verify your Gemini API key and try again."
                ),
            })

            return (
                history,
                history,
                "",
                gr.update(
                    value=None,
                    visible=False,
                ),
            )

    def clear_chat():
        return (
            [],
            [],
            "",
            gr.update(
                value=None,
                visible=False,
            ),
        )

    with gr.Blocks(
        title="SupportIQ",
        css=CUSTOM_CSS,
    ) as demo:

        # Header
        gr.Markdown(
            """
            <div class="app-header">
                <div class="app-title">📊 SupportIQ</div>
                <div class="app-subtitle">
                    AI-powered customer-support analytics
                    · Ask questions about your support tickets
                </div>
            </div>
            """,
            elem_classes=["app-header"],
        )

        # Main dashboard
        with gr.Row(equal_height=True):

            # Left: Chat
            with gr.Column(
                scale=3,
                elem_classes=["panel-card"],
            ):

                gr.Markdown(
                    "### 💬 Analytics Assistant",
                    elem_classes=["panel-heading"],
                )

                chatbot = gr.Chatbot(
                    label="Conversation",
                    height=390,
                    elem_id="chatbot",
                )

                question_input = gr.Textbox(
                    label="Ask your question",
                    placeholder=(
                        "Example: How many critical tickets are unresolved?"
                    ),
                    lines=2,
                    elem_id="question-input",
                )

                with gr.Row():

                    submit_button = gr.Button(
                        "🚀 Ask SupportIQ",
                        variant="primary",
                        scale=3,
                    )

                    download_button = gr.DownloadButton(
                        label="Download Report",
                        value=None,
                        visible=False,
                    )

                    clear_button = gr.Button(
                        "🗑️ Clear",
                        scale=1,
                    )

                gr.Markdown(
                    """
                    <div class="compact-text">
                        Press <b>Enter</b> to submit a question.
                        Use <b>Shift + Enter</b> for a new line.
                    </div>
                    """
                )

            # Right: Controls
            with gr.Column(
                scale=2,
                elem_classes=["panel-card"],
            ):

                gr.Markdown(
                    "### 💡 Suggested questions",
                    elem_classes=["panel-heading"],
                )

                gr.Markdown(
                    "Select a question to automatically fill the input.",
                    elem_classes=["compact-text"],
                )

                for query in SUGGESTED_QUERIES:

                    suggestion_button = gr.Button(
                        f"▸ {query}",
                        size="sm",
                        elem_classes=["suggestion-btn"],
                    )

                    suggestion_button.click(
                        fn=lambda q=query: q,
                        inputs=None,
                        outputs=question_input,
                    )

                gr.Markdown("---")

                gr.Markdown(
                    "### 🔑 Gemini API Settings",
                    elem_classes=["panel-heading"],
                )

                gr.Markdown(
                    """
                    <div class="compact-text">
                        Add your Gemini API key to enable
                        LLM-powered responses.
                        <br><br>
                        <a href="https://aistudio.google.com/app/apikey"
                           target="_blank">
                           🔗 Get a Gemini API key from Google AI Studio
                        </a>
                    </div>
                    """
                )

                new_api_key = gr.Textbox(
                    label="Gemini API key",
                    placeholder="Paste your API key here",
                    type="password",
                    lines=1,
                )

                with gr.Row():

                    update_key_button = gr.Button(
                        "✓ Validate & Save",
                        variant="primary",
                        size="sm",
                    )

                    clear_key_button = gr.Button(
                        "Clear",
                        size="sm",
                    )

                key_update_status = gr.Markdown(
                    "",
                    elem_classes=["compact-text"],
                )

                gr.Markdown("---")

                gr.Markdown(
                    "### 📌 Quick tips",
                    elem_classes=["panel-heading"],
                )

                gr.Markdown(
                    """
                    <div class="compact-text">
                        • Ask for counts, averages, and breakdowns.<br>
                        • Use “show” or “list” for ticket details.<br>
                        • Ask about overdue tickets and anomalies.<br>
                        • Use follow-up questions for clarification.
                    </div>
                    """
                )

        # State and events
        state = gr.State([])

        submit_button.click(
            fn=run_query,
            inputs=[
                question_input,
                state,
            ],
            outputs=[
                chatbot,
                state,
                question_input,
                download_button,
            ],
        )

        question_input.submit(
            fn=run_query,
            inputs=[
                question_input,
                state,
            ],
            outputs=[
                chatbot,
                state,
                question_input,
                download_button,
            ],
        )

        clear_button.click(
            fn=clear_chat,
            inputs=None,
            outputs=[
                chatbot,
                state,
                question_input,
                download_button,
            ],
        )

        update_key_button.click(
            fn=validate_and_update_gemini_key,
            inputs=new_api_key,
            outputs=[
                key_update_status,
                new_api_key,
            ],
        )

        new_api_key.blur(
            fn=validate_and_update_gemini_key,
            inputs=new_api_key,
            outputs=[
                key_update_status,
                new_api_key,
            ],
        )

        clear_key_button.click(
            fn=lambda: ("", ""),
            inputs=None,
            outputs=[
                new_api_key,
                key_update_status,
            ],
        )

        gr.Markdown(
            """
            <div class="footer-text">
                SupportIQ · AI-assisted support-ticket analytics
            </div>
            """
        )

    return demo
