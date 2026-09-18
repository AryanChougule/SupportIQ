from pathlib import Path
import duckdb
import pandas as pd


class TicketDatabase:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = duckdb.connect(str(db_path))

    def load_dataframe(self, df: pd.DataFrame) -> None:
        self.connection.register("incoming_tickets", df)
        self.connection.execute("DROP TABLE IF EXISTS tickets")
        self.connection.execute("""
            CREATE TABLE tickets AS
            SELECT
                ticket_id::VARCHAR AS ticket_id,
                created_at::TIMESTAMP AS created_at,
                category::VARCHAR AS category,
                priority::VARCHAR AS priority,
                status::VARCHAR AS status,
                response_time_hrs::DOUBLE AS response_time_hrs,
                resolution_time_hrs::DOUBLE AS resolution_time_hrs,
                agent_id::VARCHAR AS agent_id,
                customer_rating::DOUBLE AS customer_rating,
                issue_summary::VARCHAR AS issue_summary
            FROM incoming_tickets
        """)
        self.connection.unregister("incoming_tickets")

    def is_ready(self) -> bool:
        try:
            count = self.connection.execute(
                "SELECT COUNT(*) FROM tickets"
            ).fetchone()[0]
            return count >= 0
        except Exception:
            return False

    def count(self) -> int:
        return int(self.connection.execute("SELECT COUNT(*) FROM tickets").fetchone()[0])

    def query_df(self, sql: str, params: list | None = None) -> pd.DataFrame:
        return self.connection.execute(sql, params or []).df()

    def query_rows(self, sql: str, params: list | None = None) -> list[dict]:
        return self.query_df(sql, params).to_dict(orient="records")

    def schema_text(self) -> str:
        rows = self.connection.execute("DESCRIBE tickets").fetchall()
        return "\n".join(f"- {name}: {dtype}" for name, dtype, *_ in rows)

    def summary(self) -> dict:
        status = self.query_rows("""
            SELECT status, COUNT(*) AS count
            FROM tickets GROUP BY status ORDER BY status
        """)
        categories = self.query_rows("""
            SELECT category, COUNT(*) AS count
            FROM tickets GROUP BY category ORDER BY category
        """)
        return {
            "total_tickets": self.count(),
            "status_counts": status,
            "category_counts": categories,
            "schema": self.schema_text(),
        }
