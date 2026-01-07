from pathlib import Path

# Root repository name
ROOT_DIR = "."

# Folder and file structure
STRUCTURE = {
    "agents": [
        "ingestion_agent.py",
        "extraction_agent.py",
        "consolidation_agent.py",
        "trend_agent.py",
    ],
    "data": [
        "topic_registry.db",
        "daily_frequencies.db",
    ],
    "prompts": [
        "extract_topics.md",
        "consolidate_topics.md",
    ],
    "output": [
        "trend_report_sample.csv",
    ],
    ".": [
        "README.md",
        "run_pipeline.py",
        "demo.ipynb",
        "requirements.txt",
        ".gitignore",
    ]
}

def create_repo_structure():
    root = Path(ROOT_DIR)
    root.mkdir(exist_ok=True)

    for folder, files in STRUCTURE.items():
        dir_path = root if folder == "." else root / folder
        dir_path.mkdir(exist_ok=True)

        for file in files:
            file_path = dir_path / file
            file_path.touch(exist_ok=True)

    print(f"✅ Repository structure created at ./{ROOT_DIR}")

if __name__ == "__main__":
    create_repo_structure()
