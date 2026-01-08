import argparse
from datetime import datetime, timedelta

from logger_config import get_logger
from agents.ingestion_agent import fetch_reviews_for_date
from agents.extraction_agent import extract_topics_from_reviews
from agents.consolidation_agent import consolidate_topics
from agents.trend_agent import generate_trend_report

logger = get_logger(__name__)


DATE_FORMAT = "%Y-%m-%d"
DEFAULT_WINDOW_DAYS = 30


def _parse_date(date_str: str):
    logger.debug("Parsing date...")
    try:
        return datetime.strptime(date_str, DATE_FORMAT).date()
    except ValueError:
        logger.error(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")


def daterange(start_date, end_date):
    logger.debug("Generating date range...")
    """
    Generate dates from start_date to end_date (inclusive).
    """
    for n in range((end_date - start_date).days + 1):
        yield start_date + timedelta(days=n)


def run_daily_pipeline(app_link: str, date: str):
    logger.info(f"Running pipeline for {date}...")
    reviews = fetch_reviews_for_date(app_link, date)

    if not reviews:
        logger.warning(f"No reviews found for {date}")
        return {"status": "no_reviews"}

    logger.debug(f"Fetched {len(reviews)} reviews for {date}")
    candidate_topics = extract_topics_from_reviews(reviews)

    if not candidate_topics:
        logger.warning(f"No topics extracted from reviews for {date}")
        return {"status": "no_topics"}

    logger.debug(f"Extracted {len(candidate_topics)} candidate topics")
    consolidate_topics(candidate_topics, date)
    logger.info(f"Successfully processed {len(candidate_topics)} topics for {date}")
    return {"status": "success", "topics": len(candidate_topics)}


def main():
    logger.info("Starting pipeline initialization...")
    parser = argparse.ArgumentParser(description="App Review Trend Analysis Pipeline")
    parser.add_argument("--app_link", required=True)
    parser.add_argument("--target_date", required=True)
    parser.add_argument("--window_days", type=int, default=DEFAULT_WINDOW_DAYS)

    args = parser.parse_args()
    logger.debug(f"App Link: {args.app_link}")
    logger.debug(f"Target Date: {args.target_date}")
    logger.debug(f"Window Days: {args.window_days}")
    if args.window_days < 0:
        logger.error("window_days must be >= 0")
        raise ValueError("window_days must be >= 0")

    target_date = _parse_date(args.target_date)
    start_date = target_date - timedelta(days=args.window_days)

    logger.info(f"Pipeline Configuration")
    logger.info(f"  App: {args.app_link}")
    logger.info(f"  Window: {start_date} → {target_date}")
    logger.info(f"  Window days: {args.window_days}")

    stats = {
        "success": 0,
        "no_reviews": 0,
        "no_topics": 0,
        "errors": 0,
    }

    for day in daterange(start_date, target_date):
        logger.info(f"Processing {day.isoformat()}")

        try:
            result = run_daily_pipeline(args.app_link, day.isoformat())
            stats[result["status"]] += 1

            if result["status"] == "success":
                logger.info(f"Successfully processed {result['topics']} candidate topics for {day}")
            else:
                logger.info(f"Status: {result['status'].replace('_', ' ')} for {day}")

        except Exception as e:
            stats["errors"] += 1
            logger.error(f"Error processing {day}: {e}", exc_info=True)

    logger.info("Generating trend report...")
    generate_trend_report(
        start_date=start_date.isoformat(),
        end_date=target_date.isoformat(),
        output_path="output/trend_report_sample.csv",
    )

    logger.info("Pipeline Execution Summary:")
    for k, v in stats.items():
        logger.info(f"  {k}: {v}")

    logger.info("Pipeline completed successfully!")


if __name__ == "__main__":
    main()
