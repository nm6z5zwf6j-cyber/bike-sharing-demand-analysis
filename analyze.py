"""Analyze hourly bike rentals with only the Python standard library."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import sqlite3
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = "https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip"
SOURCE_SHA256 = "b70182d0d0508e9abbb79306ce5c0cec34869000f8220175ac83d11dbe845401"


def load_data():
    archive = ROOT / "data" / "source.zip"
    archive.parent.mkdir(exist_ok=True)
    if archive.exists():
        content = archive.read_bytes()
    else:
        with urllib.request.urlopen(SOURCE, timeout=60) as response:
            content = response.read()
    actual_sha256 = hashlib.sha256(content).hexdigest()
    if actual_sha256 != SOURCE_SHA256:
        raise ValueError(
            f"Source archive SHA-256 mismatch: expected {SOURCE_SHA256}, got {actual_sha256}. "
            "Verify the dataset before updating the pinned checksum."
        )
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        rows = list(csv.DictReader(io.StringIO(z.read("hour.csv").decode("utf-8-sig"))))
    if not archive.exists():
        archive.write_bytes(content)
    return rows


def main():
    rows = load_data()
    if not rows:
        raise ValueError("Hourly dataset is empty")
    records = [(r["dteday"], int(r["hr"]), int(r["workingday"]), int(r["casual"]), int(r["registered"]), int(r["cnt"])) for r in rows]
    if any(not 0 <= hour <= 23 or work not in (0, 1) or min(c, reg, total) < 0 or c + reg != total for _, hour, work, c, reg, total in records):
        raise ValueError("Invalid hour, day type, count, or inconsistent total")
    if len({(day, hour) for day, hour, *_ in records}) != len(records):
        raise ValueError("Duplicate date-hour records")
    with sqlite3.connect(":memory:") as db:
        db.execute("CREATE TABLE rentals (date TEXT, hour INTEGER, workingday INTEGER, casual INTEGER, registered INTEGER, total INTEGER)")
        db.executemany("INSERT INTO rentals VALUES (?, ?, ?, ?, ?, ?)", records)
        queries = (ROOT / "analysis.sql").read_text(encoding="utf-8").split("-- QUERY ")[1:]
        output = ROOT / "outputs"
        output.mkdir(exist_ok=True)
        for query in queries:
            name, sql = query.split("\n", 1)
            cursor = db.execute(sql)
            with (output / f"{name.strip()}.csv").open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([column[0] for column in cursor.description])
                writer.writerows(cursor)
    print(json.dumps({"observed_hours": len(records), "first_date": min(r[0] for r in records), "last_date": max(r[0] for r in records), "rentals": sum(r[5] for r in records)}, indent=2))


if __name__ == "__main__":
    main()
