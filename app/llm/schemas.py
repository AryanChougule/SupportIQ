from typing import Literal

from pydantic import BaseModel, Field


class QueryFilters(BaseModel):
    category: Literal["Billing", "Technical", "General"] | None = Field(
        default=None,
        description="Filter by ticket category.",
    )

    priority: Literal["Low", "Medium", "High", "Critical"] | None = Field(
        default=None,
        description="Filter by ticket priority.",
    )

    status: Literal["Open", "Resolved", "Escalated"] | None = Field(
        default=None,
        description="Filter by ticket status.",
    )

    agent_id: str | None = Field(
        default=None,
        description="Filter by support agent ID.",
    )

    unresolved: bool | None = Field(
        default=None,
        description="If true, include Open and Escalated tickets.",
    )

    min_response_time_hrs: float | None = None
    max_response_time_hrs: float | None = None
    min_resolution_time_hrs: float | None = None
    max_resolution_time_hrs: float | None = None

    created_after: str | None = Field(
        default=None,
        description="Include tickets created after this timestamp.",
    )

    created_before: str | None = Field(
        default=None,
        description="Include tickets created before this timestamp.",
    )


class QueryPlan(BaseModel):
    operation: Literal[
        "count",
        "average_rating",
        "group_count",
        "list",
        "summary",
        "detect_anomalies",
    ] = Field(
        description=(
            "The analytics operation to execute. "
            "Use 'average_rating' for average customer ratings. "
            "When group_by is provided, calculate the metric separately "
            "for each group."
        )
    )

    metric: str | None = Field(
        default=None,
        description=(
            "Metric to calculate. For rating questions, use "
            "'customer_rating'. If the user asks for results 'by category', "
            "'by agent', 'by priority', or 'by status', use group_by."
        ),
    )

    group_by: Literal[
        "agent_id",
        "category",
        "priority",
        "status",
    ] | None = Field(
        default=None,
        description=(
            "Field used to group results. Set this when the user asks "
            "for a metric by category, agent, priority, or status."
        ),
    )

    filters: QueryFilters = Field(
        default_factory=QueryFilters
    )

    sort: Literal[
        "ascending",
        "descending",
    ] | None = Field(
        default=None,
        description="Sort order for grouped results.",
    )

    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of rows to return.",
    )

    anomaly_type: Literal[
        "all",
        "resolution_time",
        "unresolved_priority",
        "response_time",
    ] | None = None

    explanation: str | None = Field(
        default=None,
        description=(
            "Brief explanation of how the question was interpreted."
        ),
    )