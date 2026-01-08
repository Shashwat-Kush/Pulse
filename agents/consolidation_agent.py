import os
import json
import sqlite3
from typing import List, Dict
from uuid import uuid4
from dotenv import load_dotenv
load_dotenv()
from groq import Groq, APIError
from logger_config import get_logger

logger = get_logger(__name__)


DB_PATH = "data/topic_registry.db"
MODEL_NAME = "llama-3.3-70b-versatile"

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ---------- Database Setup ----------

def _get_connection():
    logger.debug("Connecting to topic registry database...")
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)


def _init_db():
    logger.debug("Initializing topic registry database...")
    conn = _get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS topics (
        topic_id TEXT PRIMARY KEY,
        canonical_name TEXT UNIQUE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS aliases (
        alias TEXT,
        topic_id TEXT,
        UNIQUE(alias, topic_id)
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
    logger.debug("Topic registry database initialized")
    conn.commit()
    conn.close()


# ---------- Public Entry ----------

def consolidate_topics(candidate_topics: List[Dict], date: str):
    _init_db()
    logger.info(f"Consolidating {len(candidate_topics)} candidate topics for {date}")
    for ct in candidate_topics:
        topic_text = ct.get("topic_text")

        if not topic_text:
            logger.warning("Skipping candidate topic with missing text")
            continue

        topic_id = _match_or_create_topic(topic_text)
        _increment_frequency(topic_id, date)


# ---------- Topic Matching ----------

def _match_or_create_topic(candidate_text: str) -> str:
    logger.debug(f"Matching or creating topic for candidate: {candidate_text}")
    conn = _get_connection()
    cur = conn.cursor()

    cur.execute("SELECT topic_id, canonical_name FROM topics")
    existing_topics = cur.fetchall()

    if not existing_topics:
        logger.debug(f"No existing topics found, creating new topic for: {candidate_text}")
        topic_id = _create_new_topic(candidate_text, conn)
        conn.commit()
        conn.close()
        return topic_id

    decision = _llm_match_decision(candidate_text, existing_topics)

    if decision["decision"] == "match" and decision.get("topic_id"):
        topic_id = decision["topic_id"]

    elif decision["decision"] == "new":
        canonical_name = decision.get("canonical_name")
        if not canonical_name:
            print("⚠️ Missing canonical_name from LLM, using candidate text")
            canonical_name = candidate_text

        topic_id = _create_new_topic(canonical_name, conn)

    else:
    # Ultra-safe fallback
        topic_id = _create_new_topic(candidate_text, conn)

    _add_alias(candidate_text, topic_id, conn)

    conn.commit()
    conn.close()
    return topic_id


def _create_new_topic(canonical_name: str, conn) -> str:
    logger.debug(f"Creating new topic: {canonical_name}")
    topic_id = str(uuid4())
    logger.debug(f"Generated topic ID: {topic_id}")
    conn.execute(
        "INSERT INTO topics (topic_id, canonical_name) VALUES (?, ?)",
        (topic_id, canonical_name)
    )
    return topic_id


def _add_alias(alias: str, topic_id: str, conn):
    logger.debug(f"Adding alias '{alias}' for topic ID {topic_id}")
    conn.execute(
        "INSERT OR IGNORE INTO aliases (alias, topic_id) VALUES (?, ?)",
        (alias, topic_id)
    )


# ---------- LLM Decision ----------

def _llm_match_decision(candidate_text: str, existing_topics: List):
    logger.debug(f"Getting LLM match decision for candidate: {candidate_text}")
    topics_payload = [
        {"topic_id": tid, "name": name} for tid, name in existing_topics
    ]

    prompt = f"""
Candidate topic:
"{candidate_text}"

Existing topics:
{json.dumps(topics_payload, indent=2)}

Decide:
- SAME issue → match
- DIFFERENT issue → new

Return ONLY valid JSON:
{{
  "decision": "match" | "new",
  "topic_id": "string or null",
  "canonical_name": "string or null"
}}
"""
    logger.debug("Sending prompt to LLM for decision...")
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You maintain a topic registry."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=256
        )

        parsed = json.loads(response.choices[0].message.content)
        logger.debug(f"LLM decision: {parsed.get('decision')}")

        if parsed.get("decision") not in {"match", "new"}:
            logger.error("Invalid decision value from LLM")
            raise ValueError("Invalid decision value")

        return parsed

    except Exception as e:
        # Safe fallback: never merge incorrectly
        logger.warning(f"LLM match decision failed, defaulting to 'new': {e}")
        return {
            "decision": "new",
            "topic_id": None,
            "canonical_name": candidate_text
        }


# ---------- Frequency Update ----------

def _increment_frequency(topic_id: str, date: str):
    logger.debug(f"Incrementing frequency for topic ID {topic_id} on {date}")
    conn = _get_connection()
    conn.execute("""
    INSERT INTO daily_frequencies (topic_id, date, count)
    VALUES (?, ?, 1)
    ON CONFLICT(topic_id, date)
    DO UPDATE SET count = count + 1
    """, (topic_id, date))
    conn.commit()
    conn.close()
