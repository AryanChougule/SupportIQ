from pathlib import Path
from app.data.database import TicketDatabase
from app.data.validator import load_csv
from app.services.anomaly_service import AnomalyService


def test_anomaly_engine_returns_report():
    data_path = Path("data/support_tickets.csv")
    db = TicketDatabase(Path("/tmp/supportiq_test.duckdb"))
    db.load_dataframe(load_csv(data_path))
    service = AnomalyService(db)
    result = service.detect("all")
    assert "total_anomalies" in result
    assert "by_type" in result
