from datetime import datetime, timezone
from typing import List, Dict

from google_play_scraper import reviews, Sort
from logger_config import get_logger

logger = get_logger(__name__)


def fetch_reviews_for_date(app_link: str, target_date: str) -> List[Dict]:
    """
    Fetch reviews for a given Google Play Store app for a specific date.
    """
    logger.debug(f"Fetching reviews for {target_date}")
    try:
        target_date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
    except ValueError:
        logger.error(f"Invalid date format: {target_date}")
        raise ValueError("target_date must be in YYYY-MM-DD format")

    logger.debug(f"Extracting app ID from link: {app_link}")
    app_id = _extract_app_id(app_link)

    all_reviews = []
    continuation_token = None

    try:
        while True:
            logger.debug(f"Fetching reviews batch for {target_date}")
            result, continuation_token = reviews(
                app_id,
                lang="en",
                country="in",
                sort=Sort.NEWEST,
                count=200,
                continuation_token=continuation_token,
            )

            if not result:
                logger.debug("No more reviews to fetch")
                break

            for r in result:
                review_id = r.get('reviewId')
                logger.debug(f"Processing review: {review_id}")
                review_date = _safe_extract_date(r)
                if review_date is None:
                    logger.debug(f"Skipping review {review_id} - invalid date")
                    continue

                if review_date == target_date_obj:
                    normalized = _normalize_review(r, review_date)
                    if normalized:
                        all_reviews.append(normalized)
                elif review_date < target_date_obj:
                    logger.debug("Reached reviews older than target date, stopping fetch")
                    return all_reviews
            logger.debug(f"Fetched {len(all_reviews)} reviews so far")
            if continuation_token is None:
                break

    except Exception as e:
        logger.error(f"Review ingestion failed: {e}", exc_info=True)
        return []

    return all_reviews


def _safe_extract_date(raw_review: Dict):
    at = raw_review.get("at")
    if at is None:
        return None
    return at.astimezone(timezone.utc).date()


def _extract_app_id(app_link: str) -> str:
    if "id=" not in app_link:
        raise ValueError("Invalid Google Play Store URL")
    return app_link.split("id=")[-1].split("&")[0]


def _normalize_review(raw_review: Dict, review_date) -> Dict:
    text = raw_review.get("content", "").strip()
    if not text:
        return None

    return {
        "review_id": raw_review.get("reviewId"),
        "date": review_date.isoformat(),
        "text": text,
        "rating": raw_review.get("score"),
    }


# if __name__ == "__main__":
#     print("Fetching sample reviews...")
#     reviews = fetch_reviews_for_date(
#         "https://play.google.com/store/apps/details?id=in.swiggy.android&hl=en_IN",
#         "2025-12-01"
#     )
#     print("Sample reviews fetched:")
#     print(len(reviews))
#     print(reviews[:2])
