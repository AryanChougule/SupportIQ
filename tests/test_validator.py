from pathlib import Path
from app.data.validator import load_csv


def test_sample_dataset_loads():
    df = load_csv(Path("data/support_tickets.csv"))
    assert len(df) > 0
    assert set(["ticket_id", "created_at", "priority"]).issubset(df.columns)
