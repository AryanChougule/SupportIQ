from datetime import timedelta
import pandas as pd
from app.data.database import TicketDatabase


class AnomalyService:
    def __init__(
        self,
        db: TicketDatabase,
        iqr_multiplier: float = 1.5,
        unresolved_age_hours: float = 24.0,
    ):
        self.db = db
        self.iqr_multiplier = iqr_multiplier
        self.unresolved_age_hours = unresolved_age_hours

    def _all(self) -> pd.DataFrame:
        return self.db.query_df("SELECT * FROM tickets")

    def resolution_time_anomalies(self) -> list[dict]:
        df = self._all()
        values = df["resolution_time_hrs"].dropna()
        if values.empty:
            return []
        q1 = values.quantile(0.25)
        q3 = values.quantile(0.75)
        iqr = q3 - q1
        upper = q3 + self.iqr_multiplier * iqr
        result = df[df["resolution_time_hrs"] > upper].copy()
        result["anomaly_type"] = "long_resolution_time"
        result["reason"] = result["resolution_time_hrs"].map(
            lambda x: f"Resolution time {x:.2f} hrs exceeds IQR threshold {upper:.2f} hrs."
        )
        return result.to_dict(orient="records")

    def unresolved_priority_anomalies(self) -> list[dict]:
        df = self._all()
        reference_time = df["created_at"].max()
        age_hours = (reference_time - df["created_at"]).dt.total_seconds() / 3600
        mask = (
            df["priority"].isin(["High", "Critical"])
            & df["status"].isin(["Open", "Escalated"])
            & (age_hours > self.unresolved_age_hours)
        )
        result = df[mask].copy()
        result["age_hours_at_reference"] = age_hours[mask]
        result["anomaly_type"] = "old_unresolved_priority_ticket"
        result["reason"] = (
            f"High/Critical ticket unresolved for more than "
            f"{self.unresolved_age_hours:.1f} hours relative to the dataset reference time."
        )
        return result.to_dict(orient="records")

    def response_time_anomalies(self) -> list[dict]:
        df = self._all()
        values = df["response_time_hrs"].dropna()
        if values.empty:
            return []
        q1 = values.quantile(0.25)
        q3 = values.quantile(0.75)
        upper = q3 + self.iqr_multiplier * (q3 - q1)
        result = df[df["response_time_hrs"] > upper].copy()
        result["anomaly_type"] = "long_response_time"
        result["reason"] = result["response_time_hrs"].map(
            lambda x: f"Response time {x:.2f} hrs exceeds IQR threshold {upper:.2f} hrs."
        )
        return result.to_dict(orient="records")

    def detect(self, anomaly_type: str = "all") -> dict:
        groups = {}
        if anomaly_type in ("all", "resolution_time"):
            groups["resolution_time"] = self.resolution_time_anomalies()
        if anomaly_type in ("all", "unresolved_priority"):
            groups["unresolved_priority"] = self.unresolved_priority_anomalies()
        if anomaly_type in ("all", "response_time"):
            groups["response_time"] = self.response_time_anomalies()

        total = sum(len(items) for items in groups.values())
        return {
            "reference_time": str(self._all()["created_at"].max()),
            "total_anomalies": total,
            "by_type": groups,
        }
