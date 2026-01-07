# Pulse
pulsegen-review-trend-agent/
│
├── README.md
│
├── agents/
│   ├── ingestion_agent.py        # Fetches daily reviews
│   ├── extraction_agent.py       # High-recall topic extraction
│   ├── consolidation_agent.py    # Topic matching & merging
│   └── trend_agent.py            # Builds T-30 → T report
│
├── data/
│   ├── topic_registry.db         # Canonical topics + aliases
│   └── daily_frequencies.db     # (topic_id, date, count)
│
├── prompts/
│   ├── extract_topics.md
│   └── consolidate_topics.md
│
├── output/
│   └── trend_report_sample.csv
│
├── run_pipeline.py               # One command end-to-end run
│
├── demo.ipynb                    # Used in video walkthrough
│
├── requirements.txt
└── .gitignore


# Review Trend Analysis using Agentic AI

## Problem
Generate a 30-day rolling trend of issues and requests from app reviews.

## Approach
- Daily batch processing
- Agentic topic extraction
- Persistent topic registry
- Semantic topic consolidation

## How Duplicate Topics Are Prevented
(Short explanation + example)

## How to Run
python run_pipeline.py

## Output
Trend report stored in /output