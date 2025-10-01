"""Utility script to import JSON dumps into MongoDB."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Any

from pymongo import MongoClient


def import_collection(client: MongoClient, database: str, collection: str, file_path: Path) -> int:
    db = client[database]
    col = db[collection]
    col.delete_many({})

    inserted = 0
    with file_path.open("r", encoding="utf-8") as fh:
        raw = fh.read().strip()
        if not raw:
            return 0
        docs = json.loads(f"[{raw.replace('}{', '},{')}]")
        if docs:
            col.insert_many(docs)
            inserted = len(docs)
    return inserted


def main() -> None:
    parser = argparse.ArgumentParser(description="Import DAACS JSON dataset")
    parser.add_argument("--connection-string", default="mongodb://localhost:27017/")
    parser.add_argument("--database", default="daacs_analytics")
    parser.add_argument("--data-dir", default="analytic_database")
    args = parser.parse_args()

    client = MongoClient(args.connection_string)
    data_dir = Path(args.data_dir)

    collections = {
        "users": data_dir / "users.json",
        "user_assessments": data_dir / "user_assessments.json",
        "event_containers": data_dir / "event_containers.json",
    }

    for name, path in collections.items():
        if not path.exists():
            print(f"Skipping {name}: file not found at {path}")
            continue
        count = import_collection(client, args.database, name, path)
        print(f"Imported {count} documents into {name}")


if __name__ == "__main__":
    main()
