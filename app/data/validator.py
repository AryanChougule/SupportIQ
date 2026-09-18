from pathlib import Path
import pandas as pd
import re
from datetime import datetime
from typing import Any

REQUIRED_COLUMNS = [
    "ticket_id",
    "created_at",
    "category",
    "priority",
    "status",
    "response_time_hrs",
    "resolution_time_hrs",
    "agent_id",
    "customer_rating",
    "issue_summary",
]

ALLOWED_VALUES = {
    "category": {"Billing", "Technical", "General"},
    "priority": {"Low", "Medium", "High", "Critical"},
    "status": {"Open", "Resolved", "Escalated"},
}


class DataValidationError(ValueError):
    pass

def parse_flexible_datetime(value: Any):
    """
    Parse common date/time formats safely.

    Supports:
    - DD-MM-YYYY HH:MM
    - DD/MM/YYYY HH:MM
    - YYYY-MM-DD HH:MM:SS
    - YYYY-MM-DDTHH:MM:SS
    - MM/DD/YYYY
    - DD-MM-YYYY
    - Unix timestamps
    - Existing datetime and pandas Timestamp values
    """

    if pd.isna(value):
        return pd.NaT

    if isinstance(value, (pd.Timestamp, datetime)):
        return pd.Timestamp(value)

    # Handle numeric timestamps where appropriate
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            # Treat large numbers as Unix seconds
            if value > 10_000_000:
                return pd.to_datetime(value, unit="s", errors="coerce")
        except (ValueError, TypeError, OverflowError):
            pass

    text = str(value).strip()

    if not text or text.lower() in {
        "nan", "none", "null", "n/a", "na", "unknown", "-"
    }:
        return pd.NaT

    # Explicit formats are tried first to avoid day/month confusion.
    formats = [
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d.%m.%Y %H:%M",
        "%d.%m.%Y %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d.%m.%Y",
        "%Y/%m/%d",
        "%m/%d/%Y",
        "%B %d, %Y",
        "%b %d, %Y",
    ]

    for date_format in formats:
        try:
            return pd.Timestamp(
                datetime.strptime(text, date_format)
            )
        except (ValueError, TypeError):
            continue

    # Final fallback for other formats supported by pandas.
    try:
        parsed = pd.to_datetime(
            text,
            errors="coerce",
            dayfirst=True,
            format="mixed",
        )
        return parsed
    except (ValueError, TypeError):
        return pd.NaT

def validate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
    if missing:
        raise DataValidationError(f"Missing required columns: {missing}")

    result = df[REQUIRED_COLUMNS].copy()
    
    original_dates = result["created_at"].copy()

    result["created_at"] = original_dates.apply(
        parse_flexible_datetime
    )

    invalid_dates = result["created_at"].isna()

    if invalid_dates.any():
        invalid_values = (
            original_dates[invalid_dates]
            .drop_duplicates()
            .astype(str)
            .tolist()
        )

        preview = invalid_values[:10]

        raise DataValidationError(
            "Unable to parse dates in 'created_at'. "
            f"Invalid values: {preview}"
            + (
                f" ... and {len(invalid_values) - 10} more."
                if len(invalid_values) > 10
                else ""
            )
        )

    if result["created_at"].isna().any():
        raise DataValidationError("One or more created_at values are invalid.")

    for column in ["response_time_hrs", "resolution_time_hrs", "customer_rating"]:
        result[column] = pd.to_numeric(result[column], errors="coerce")

    for column, allowed in ALLOWED_VALUES.items():
        invalid = set(result[column].dropna().unique()) - allowed
        if invalid:
            raise DataValidationError(
                f"Invalid values in {column}: {sorted(invalid)}"
            )

    if result["ticket_id"].duplicated().any():
        raise DataValidationError("ticket_id values must be unique.")

    if ((result["customer_rating"] < 1) | (result["customer_rating"] > 5)).any():
        raise DataValidationError("customer_rating must be between 1 and 5.")

    return result


def load_csv(path):
    """
    Load a CSV using common encodings and provide useful errors.

    The function does not silently discard malformed rows.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"CSV file not found: {path.resolve()}"
        )

    encodings = [
        "utf-8-sig",
        "utf-8",
        "cp1252",
        "latin1",
    ]

    last_error = None

    for encoding in encodings:
        try:
            df = pd.read_csv(
                path,
                encoding=encoding,
                sep=None,
                engine="python",
            )

            return validate_dataframe(df)

        except UnicodeDecodeError as error:
            last_error = error
            continue

        except pd.errors.ParserError as error:
            raise DataValidationError(
                f"CSV structure is invalid: {error}. "
                "Check the delimiter, header, and quoted commas."
            ) from error

    raise DataValidationError(
        f"Unable to decode CSV file. Last error: {last_error}"
    )