import argparse
from datetime import datetime, timedelta

from agents.ingestion_agent import fetch_reviews_for_date
from agents.extraction_agent import extract_topics_from_reviews
from agents.consolidation_agent import consolidate_topics
from agents.trend_agent import generate_trend_report


DATE_FORMAT = "%Y-%m-%d"
DEFAULT_WINDOW_DAYS = 30


def _parse_date(date_str: str):
    print("📅 Parsing date...")
    try:
        return datetime.strptime(date_str, DATE_FORMAT).date()
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")


def daterange(start_date, end_date):
    print("📅 Generating date range...")
    """
    Generate dates from start_date to end_date (inclusive).
    """
    for n in range((end_date - start_date).days + 1):
        yield start_date + timedelta(days=n)


def run_daily_pipeline(app_link: str, date: str):
    print(f"🚀 Running pipeline for {date}...")
    reviews = fetch_reviews_for_date(app_link, date)

    if not reviews:
        return {"status": "no_reviews"}

    candidate_topics = extract_topics_from_reviews(reviews)

    if not candidate_topics:
        return {"status": "no_topics"}

    consolidate_topics(candidate_topics, date)
    return {"status": "success", "topics": len(candidate_topics)}


def main():
    print("🚀 Starting pipeline")
    parser = argparse.ArgumentParser(description="App Review Trend Analysis Pipeline")
    parser.add_argument("--app_link", required=True)
    parser.add_argument("--target_date", required=True)
    parser.add_argument("--window_days", type=int, default=DEFAULT_WINDOW_DAYS)

    args = parser.parse_args()
    print(f"App Link: {args.app_link}")
    print(f"Target Date: {args.target_date}")
    print(f"Window Days: {args.window_days}")
    if args.window_days < 0:
        raise ValueError("window_days must be >= 0")

    target_date = _parse_date(args.target_date)
    start_date = target_date - timedelta(days=args.window_days)

    print("🚀 Starting pipeline")
    print(f"App: {args.app_link}")
    print(f"Window: {start_date} → {target_date}")
    print(f"Window days: {args.window_days}")

    stats = {
        "success": 0,
        "no_reviews": 0,
        "no_topics": 0,
        "errors": 0,
    }

    for day in daterange(start_date, target_date):
        print(f"\n📅 Processing {day.isoformat()}")

        try:
            result = run_daily_pipeline(args.app_link, day.isoformat())
            stats[result["status"]] += 1

            if result["status"] == "success":
                print(f"✅ {result['topics']} candidate topics processed")
            else:
                print(f"⚠️ {result['status'].replace('_', ' ')}")

        except Exception as e:
            stats["errors"] += 1
            print(f"❌ Error processing {day}: {e}")

    print("\n📊 Generating trend report...")
    generate_trend_report(
        start_date=start_date.isoformat(),
        end_date=target_date.isoformat(),
        output_path="output/trend_report_sample.csv",
    )

    print("\n📈 Pipeline Summary")
    for k, v in stats.items():
        print(f"{k}: {v}")

    print("\n🎉 Pipeline completed")


if __name__ == "__main__":
    main()
