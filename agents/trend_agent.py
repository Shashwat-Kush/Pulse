import os
import sqlite3
from datetime import datetime, timedelta
import pandas as pd


DB_PATH = "data/topic_registry.db"
DATE_FORMAT = "%Y-%m-%d"


def generate_trend_report(start_date: str, end_date: str, output_path: str):
    """
    Generate a topic trend report from start_date to end_date (inclusive).
    """
    print(f"📈 Generating trend report from {start_date} to {end_date}...")
    # ---- Validate dates ----
    start = _parse_date(start_date)
    end = _parse_date(end_date)

    if start > end:
        raise ValueError("start_date must be <= end_date")

    # ---- Ensure DB directory exists and initialize ----
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS topics (
        topic_id TEXT PRIMARY KEY,
        canonical_name TEXT UNIQUE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS daily_frequencies (
        topic_id TEXT,
        date TEXT,
        count INTEGER,
        UNIQUE(topic_id, date)
    )
    """)

    conn.commit()

    topics_df = pd.read_sql_query(
        "SELECT topic_id, canonical_name FROM topics",
        conn
    )

    if topics_df.empty:
        conn.close()
        _write_empty_report(start, end, output_path)
        return

    freq_df = pd.read_sql_query(
        """
        SELECT topic_id, date, count
        FROM daily_frequencies
        WHERE date BETWEEN ? AND ?
        """,
        conn,
        params=(start_date, end_date)
    )

    conn.close()

    date_range = _build_date_range(start, end)

    base_df = (
        topics_df.assign(key=1)
        .merge(pd.DataFrame({"date": date_range, "key": 1}), on="key")
        .drop("key", axis=1)
    )

    merged_df = base_df.merge(
        freq_df,
        on=["topic_id", "date"],
        how="left"
    )

    merged_df["count"] = merged_df["count"].fillna(0).astype(int)

    report_df = merged_df.pivot_table(
        index="canonical_name",
        columns="date",
        values="count",
        fill_value=0
    ).reset_index()

    report_df = report_df.sort_values("canonical_name")

    _safe_mkdir(output_path)
    report_df.to_csv(output_path, index=False)

    print(f"✅ Trend report written to {output_path}")


# ---------- Helpers ----------

def _parse_date(date_str: str):
    print("📅 Parsing date...")
    try:
        return datetime.strptime(date_str, DATE_FORMAT).date()
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")


def _build_date_range(start, end):
    print("📅 Building date range...")
    dates = []
    current = start
    while current <= end:
        dates.append(current.isoformat())
        current += timedelta(days=1)
    return dates


def _safe_mkdir(path: str):
    print("📁 Ensuring output directory exists...")
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)


def _write_empty_report(start, end, output_path):
    print("📈 Writing empty trend report...")
    date_range = _build_date_range(start, end)
    df = pd.DataFrame(columns=["canonical_name"] + date_range)
    _safe_mkdir(output_path)
    df.to_csv(output_path, index=False)
