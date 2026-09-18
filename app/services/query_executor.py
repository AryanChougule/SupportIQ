from datetime import datetime
import re
from app.llm.schemas import QueryPlan
from app.data.database import TicketDatabase
import logging
import time

logger = logging.getLogger(__name__)

class QueryExecutor:
    ALLOWED_GROUPS = {"agent_id", "category", "priority", "status"}

    def __init__(self, db: TicketDatabase, max_rows: int = 100):
        self.db = db
        self.max_rows = max_rows

    def _where_clause(self, plan: QueryPlan) -> tuple[str, list]:
        clauses = []
        params = []
        f = plan.filters

        if f.category:
            clauses.append("category = ?")
            params.append(f.category)

        if f.priority:
            clauses.append("priority = ?")
            params.append(f.priority)

        if f.status:
            clauses.append("status = ?")
            params.append(f.status)

        if f.agent_id:
            clauses.append("agent_id = ?")
            params.append(f.agent_id)

        if f.unresolved is True:
            clauses.append("status IN ('Open', 'Escalated')")

        if f.min_response_time_hrs is not None:
            clauses.append("response_time_hrs >= ?")
            params.append(f.min_response_time_hrs)

        if f.max_response_time_hrs is not None:
            clauses.append("response_time_hrs <= ?")
            params.append(f.max_response_time_hrs)

        if f.min_resolution_time_hrs is not None:
            clauses.append("resolution_time_hrs >= ?")
            params.append(f.min_resolution_time_hrs)

        if f.max_resolution_time_hrs is not None:
            clauses.append("resolution_time_hrs <= ?")
            params.append(f.max_resolution_time_hrs)

        if f.created_after:
            clauses.append("created_at >= CAST(? AS TIMESTAMP)")
            params.append(f.created_after)

        if f.created_before:
            clauses.append("created_at <= CAST(? AS TIMESTAMP)")
            params.append(f.created_before)

        where_clause = (
            " WHERE " + " AND ".join(clauses)
            if clauses
            else ""
        )

        return where_clause, params

    def _execute_query(
            self,
            sql: str,
            params: list,
        ) -> list:
            start_time = time.perf_counter()
    
            try:
                rows = self.db.query_rows(sql, params)
    
                duration = time.perf_counter() - start_time
    
                logger.info(
                    "SQL execution completed in %.2f seconds; rows=%d",
                    duration,
                    len(rows),
                )
    
                return rows
    
            except Exception:
                duration = time.perf_counter() - start_time
    
                logger.exception(
                    "SQL execution failed after %.2f seconds",
                    duration,
                )
                raise  
    
    def execute(self, plan: QueryPlan) -> dict:
        if plan.operation == "summary":
            return self.db.summary()

        if plan.operation == "detect_anomalies":
            return {"route": "anomaly_engine", "anomaly_type": plan.anomaly_type or "all"}

        where, params = self._where_clause(plan)

        if plan.operation == "count":
            rows = self._execute_query(
                f"SELECT COUNT(*) AS ticket_count FROM tickets{where}", params
            )
            return {"rows": rows, "columns": ["ticket_count"]}

        if plan.operation == "average_rating":
            rows = self._execute_query(
                f"""SELECT AVG(customer_rating) AS average_customer_rating
                    FROM tickets
                    {where + (' AND ' if where else ' WHERE ')}
                    customer_rating IS NOT NULL""",
                params,
            )
            return {"rows": rows, "columns": ["average_customer_rating"]}

        if plan.operation == "group_count":
            group = plan.group_by or "agent_id"
            if group not in self.ALLOWED_GROUPS:
                raise ValueError("Unsupported group-by field.")
            direction = "DESC" if plan.sort == "descending" else "ASC"
            rows = self._execute_query(
                f"""SELECT {group}, COUNT(*) AS ticket_count
                    FROM tickets{where}
                    GROUP BY {group}
                    ORDER BY ticket_count {direction}
                    LIMIT ?""",
                [*params, min(plan.limit, self.max_rows)],
            )
            return {"rows": rows, "columns": [group, "ticket_count"]}

        if plan.operation == "list":
            rows = self._execute_query(
                f"""SELECT ticket_id, created_at, category, priority, status,
                           response_time_hrs, resolution_time_hrs, agent_id,
                           customer_rating, issue_summary
                    FROM tickets{where}
                    ORDER BY created_at DESC
                    LIMIT ?""",
                [*params, self.max_rows],
            )
            return {"rows": rows}

        raise ValueError(f"Unsupported operation: {plan.operation}")
    
    